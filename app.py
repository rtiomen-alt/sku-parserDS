import streamlit as st
import pandas as pd
import re
from io import BytesIO

# ---------- Справочник групп по кодам ТН ВЭД ----------
GROUP_MAP = {
    '2101': 'продукты из кофе и цикория',
    '21011': 'кофе растворимый',
    '210112': 'кофейные напитки (3 в 1 гипотеза)',
    '21012': 'напитки чайные растворимые',
    '21013': 'напитки цикорий',
    '2106': 'сухие растворимые продукты (неконкретно)',
    '21069': 'смеси для чайных и прочих напитков',
    '2106108000': 'сухие смеси для коктейлей',
    '2106905800': 'сиропы, концентраты',
    '2106909300': 'сухие чаи и смеси, пищевые добавки',
    '2201': 'минералка с газом и без',
    '2202': 'б/а газированные и нет, с сахаром и/или ароматизаторами',
    '2202100000': 'напитки безалкогольные газированные и нет',
    '2202910000': 'пиво б/а',
    '2202991500': 'напитки на основе сои и орехов',
    '2202991800': 'нектары / сокосодержащие / морсы / прочие',
    '2203': 'пиво солодовое и пивные напитки',
    '2204': 'вина виноградные в т.ч. игристые',
    '2205': 'вермуты и ароматизированные вина',
    '2206': 'сброженные напитки (сидры, пивные, винные)',
    '220600': 'сброженные напитки',
    '2206003100': 'сидры и перри',
    '2206003901': 'сидры и перри',
    '2206003909': 'сидры и перри',
    '2206005100': 'сидры и перри',
    '220600590': 'сидры и перри',
    '2206005901': 'сидры и перри',
    '2206005909': 'напитки винные сухие',
    '2206008100': 'сидры и перри',
    '2208': 'крепкий алкоголь',
    '220820': 'дистилляты винограда (коньяки…)',
    '220830': 'виски',
    '220840': 'ром',
    '220850': 'джин',
    '220860': 'водка',
    '220870': 'ликеры',
    '220890': 'слабоалкогольные и другие спиртные напитки',
    '2208905608': 'настойки',
    '0901': 'кофе',
    '09011': 'Кофе натуральный нежареный',
    '09012': 'Кофе натуральный жареный',
    '09019': 'Прочие',
    '0901909000': 'Заменители кофе, содержащие кофе',
    '0902': 'чай',
    '09021': 'Чай зеленый',
    '09022': 'Чай зеленый',
    '09023': 'Чай черный',
}

# ---------- Вспомогательные функции ----------
def get_detailed_code(code_str):
    """Из строки с кодами (через запятую) выбирает самый длинный код."""
    if not isinstance(code_str, str):
        return ''
    codes = [c.strip() for c in code_str.split(',') if c.strip()]
    if not codes:
        return ''
    # Выбираем код с максимальной длиной (наиболее детализированный)
    return max(codes, key=len)

def get_group(code):
    """Возвращает группу по коду ТН ВЭД (сначала точное совпадение, затем по префиксу)."""
    if not code:
        return 'Неизвестно'
    # точное совпадение
    if code in GROUP_MAP:
        return GROUP_MAP[code]
    # поиск по префиксам (от длинного к короткому)
    for i in range(len(code), 0, -1):
        prefix = code[:i]
        if prefix in GROUP_MAP:
            return GROUP_MAP[prefix]
    return 'Неизвестно'

def normalize_flavor(flavor):
    """Приводит вкус к каноническому виду."""
    if not flavor or flavor.strip() == '':
        return 'не указан'
    # Удаляем лишние слова и знаки
    flavor = re.sub(r'^(со вкусом|с ароматом|вкус|аромат)\s*', '', flavor.strip(), flags=re.I)
    flavor = re.sub(r'\s+', ' ', flavor)
    # Унификация разделителей (и, &, -)
    flavor = re.sub(r'\s+и\s+', '-', flavor)
    flavor = re.sub(r'\s*&\s*', '-', flavor)
    flavor = re.sub(r'\s*-\s*', '-', flavor)
    # Приведение к нижнему регистру
    flavor = flavor.lower()
    # Можно добавить словарь синонимов (пример)
    synonyms = {
        'манго и маракуйя': 'манго-маракуйя',
        'манго-маракуйя': 'манго-маракуйя',
        'лимон-лайм': 'лимон-лайм',
        'лимон и лайм': 'лимон-лайм',
        # ... добавляйте по мере выявления
    }
    return synonyms.get(flavor, flavor)

def split_products(product_text):
    """Разбивает строку с перечислением продуктов на отдельные SKU (список строк)."""
    if not isinstance(product_text, str):
        return []
    # Если в тексте есть маркеры перечисления в виде кавычек «...», разбиваем по ним
    # Сначала попробуем разбить по точкам с запятой, если их много
    if ';' in product_text:
        parts = [p.strip() for p in product_text.split(';') if p.strip()]
        # если после разбивки получилось больше 1 части, используем их
        if len(parts) > 1:
            return parts
    # Если есть переносы строк
    if '\n' in product_text:
        parts = [p.strip() for p in product_text.split('\n') if p.strip()]
        if len(parts) > 1:
            return parts
    # Если есть перечисление через запятую, но нужно отличать перечисление внутри названия
    # Простая эвристика: если запятых много (>=3), разбиваем
    if product_text.count(',') >= 3:
        parts = [p.strip() for p in product_text.split(',') if p.strip()]
        # Проверяем, что части не слишком короткие и не являются перечислением вкусов
        if len(parts) > 1:
            # Если первая часть содержит слово "напиток" или "пиво" и т.п., то это список SKU
            if any(key in parts[0].lower() for key in ['напиток', 'пиво', 'квас', 'чай']):
                return parts
    # Если не удалось разбить, возвращаем исходную строку как один элемент
    return [product_text]

def extract_sku_and_flavor(product_str):
    """
    Из строки продукта извлекает SKU и вкус.
    Возвращает кортеж (sku, flavor).
    """
    # Ищем ключевые фразы "со вкусом", "с ароматом", "вкус", "аромат"
    patterns = [
        r'(.*?)\s+(со вкусом|с ароматом|вкус|аромат)\s+(.*)',
        r'(.*?)\s*[:]\s*(.*)',  # после двоеточия может быть вкус
    ]
    sku = product_str.strip()
    flavor = ''
    for pat in patterns:
        match = re.search(pat, product_str, re.I)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                sku = groups[0].strip()
                flavor = groups[2].strip()
            elif len(groups) == 2:
                # Если после двоеточия, возможно это уточнение вкуса
                sku = groups[0].strip()
                flavor = groups[1].strip()
            break
    # Если вкус не найден, пытаемся взять последнюю часть после "(" или " - "
    if not flavor:
        # иногда вкус в скобках
        match = re.search(r'\(([^)]*)\)', product_str)
        if match:
            flavor = match.group(1).strip()
            # убираем вкус из SKU
            sku = re.sub(r'\s*\([^)]*\)', '', sku).strip()
        else:
            # возможно, после тире
            if ' - ' in product_str:
                parts = product_str.split(' - ', 1)
                sku = parts[0].strip()
                flavor = parts[1].strip() if len(parts) > 1 else ''
    return sku, normalize_flavor(flavor)

# ---------- Основная функция обработки ----------
def process_dataframe(df):
    """
    Принимает DataFrame с колонками как в примере, возвращает атомизированный DataFrame.
    """
    required_cols = ['Регистрационный номер', 'Наименование (обозначение) продукции',
                     'Общее наименование продукции', 'Код ТН ВЭД', 'Действие с',
                     'Действие по', 'Заявитель']
    # Проверяем наличие колонок
    for col in required_cols:
        if col not in df.columns:
            st.error(f"В файле отсутствует колонка '{col}'")
            return pd.DataFrame()

    # Создаём список для новых строк
    new_rows = []

    for _, row in df.iterrows():
        reg_num = row['Регистрационный номер']
        product_name = row['Наименование (обозначение) продукции']
        general_name = row['Общее наименование продукции']
        code_str = row['Код ТН ВЭД']
        action_from = row['Действие с']
        action_to = row['Действие по']
        applicant = row['Заявитель']

        # Выбираем наиболее детализированный код
        detailed_code = get_detailed_code(code_str)
        group = get_group(detailed_code)

        # Определяем текст для разбивки: сначала специфическое наименование, если пусто - общее
        text_for_split = product_name if pd.notna(product_name) and str(product_name).strip() else general_name
        if pd.isna(text_for_split) or str(text_for_split).strip() == '':
            continue

        # Разбиваем на отдельные продукты
        products = split_products(str(text_for_split))

        for prod in products:
            if not prod.strip():
                continue
            sku, flavor = extract_sku_and_flavor(prod)
            if not sku:
                sku = prod.strip()
            new_rows.append({
                'SKU': sku,
                'Группа': group,
                'Вкус': flavor,
                'Код ТН ВЭД': detailed_code,
                'Регистрационный номер': reg_num,
                'Действие с': action_from,
                'Действие по': action_to,
                'Заявитель': applicant,
            })

    return pd.DataFrame(new_rows)

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Атомизация деклараций", layout="wide")
st.title("📋 Атомизация номенклатуры из деклараций")

uploaded_file = st.file_uploader("Загрузите Excel-файл с декларациями", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, sheet_name=0)
        st.subheader("Исходные данные (первые 5 строк)")
        st.dataframe(df.head())

        with st.spinner("Выполняется атомизация..."):
            result_df = process_dataframe(df)

        if result_df.empty:
            st.warning("Не удалось обработать данные. Проверьте структуру файла.")
        else:
            st.subheader("Результат атомизации")
            st.dataframe(result_df)

            # Кнопка скачивания результата
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                result_df.to_excel(writer, index=False, sheet_name='Атомизация')
            st.download_button(
                label="📥 Скачать результат в Excel",
                data=output.getvalue(),
                file_name="atomized_result.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # Дополнительно: статистика по группам и вкусам
            st.subheader("Статистика")
            col1, col2 = st.columns(2)
            with col1:
                st.write("Распределение по группам")
                st.dataframe(result_df['Группа'].value_counts())
            with col2:
                st.write("Топ-10 вкусов")
                st.dataframe(result_df['Вкус'].value_counts().head(10))

    except Exception as e:
        st.error(f"Ошибка при обработке файла: {e}")
else:
    st.info("Загрузите Excel-файл для начала обработки.")

# Примечание: для работы с большими файлами можно добавить кэширование
