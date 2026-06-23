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
    if not isinstance(code_str, str):
        return ''
    codes = [c.strip() for c in code_str.split(',') if c.strip()]
    if not codes:
        return ''
    return max(codes, key=len)

def get_group(code):
    if not code:
        return 'Неизвестно'
    if code in GROUP_MAP:
        return GROUP_MAP[code]
    for i in range(len(code), 0, -1):
        prefix = code[:i]
        if prefix in GROUP_MAP:
            return GROUP_MAP[prefix]
    return 'Неизвестно'

def normalize_flavor(flavor):
    if not flavor or flavor.strip() == '':
        return 'не указан'
    # Убираем служебные слова
    flavor = re.sub(r'^(со вкусом|с ароматом|вкус|аромат)\s*', '', flavor.strip(), flags=re.I)
    flavor = re.sub(r'\s+', ' ', flavor)
    # Заменяем "и" и "&" на дефис
    flavor = re.sub(r'\s+и\s+', '-', flavor)
    flavor = re.sub(r'\s*&\s*', '-', flavor)
    flavor = re.sub(r'\s*-\s*', '-', flavor)
    # Убираем лишние слова в конце (пастеризованный, газированный и т.п.)
    flavor = re.sub(r'\s*(пастеризованный|сильногазированный|негазированный|газированный|пастериз\.?)\s*$', '', flavor, flags=re.I)
    flavor = flavor.lower().strip()
    # Словарь синонимов можно расширять
    synonyms = {
        'манго и маракуйя': 'манго-маракуйя',
        'манго-маракуйя': 'манго-маракуйя',
        'лимон-лайм': 'лимон-лайм',
        'лимон и лайм': 'лимон-лайм',
        'клубника-земляника': 'клубника-земляника',
        'клубника и земляника': 'клубника-земляника',
        'мохито и ежевика': 'мохито-ежевика',
        'винограда изабелла': 'виноград изабелла',
        'фейхоа': 'фейхоа',
        'гранат': 'гранат',
        'мандарин': 'мандарин',
        'апельсин': 'апельсин',
        'груша': 'груша',
        'персик': 'персик',
        'малина': 'малина',
        'клубника': 'клубника',
        'банан': 'банан',
        'ананас': 'ананас',
        'кокос': 'кокос',
        'манго': 'манго',
        'маракуйя': 'маракуйя',
        'цитрус': 'цитрус',
        'лайм': 'лайм',
        'лимон': 'лимон',
        'грейпфрут': 'грейпфрут',
        'черника': 'черника',
        'смородина': 'смородина',
        'облепиха': 'облепиха',
        'арбуз': 'арбуз',
        'дыня': 'дыня',
        'мята': 'мята',
        'базилик': 'базилик',
        'имбирь': 'имбирь',
        'тархун': 'тархун',
        'эстрагон': 'эстрагон',
        'юдзу': 'юдзу',
        'ромашка': 'ромашка',
        'лаванда': 'лаванда',
        'ваниль': 'ваниль',
        'попкорн': 'попкорн',
        'карамель': 'карамель',
        'бабл гам': 'бабл гам',
        'крем-сода': 'крем-сода',
        'дюшес': 'дюшес',
        'буратино': 'буратино',
        'байкал': 'байкал',
        'колокольчик': 'колокольчик',
        'кола': 'кола',
        'альпи кола': 'альпи кола',
        'тропический микс': 'тропический микс',
    }
    return synonyms.get(flavor, flavor)

# ---------- НОВЫЙ ПАРСЕР ДЛЯ СЛОЖНЫХ ЯЧЕЕК ----------
def parse_complex_cell(text):
    """
    Принимает текст ячейки (строку) и возвращает список кортежей (sku_type, flavor).
    sku_type – это нормализованное название типа продукции (с брендом, если есть).
    """
    if not isinstance(text, str):
        return []

    # Нормализуем переносы строк и лишние пробелы
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r' +', ' ', text)
    text = text.strip()

    results = []

    # Шаг 1: Разбиваем текст на логические блоки по точкам с запятой или по явным переходам типа.
    # Но сначала проверим, есть ли явные блоки с брендом в кавычках или с "СО ВКУСОМ".
    # Будем использовать более сложный подход: сначала ищем все явные указания типа в кавычках (например, «SUNZO»)
    # и разбиваем по ним.

    # Регулярка для поиска блоков с типом, где есть кавычки и "СО ВКУСОМ"
    pattern_explicit = r'(НАПИТОК\s+[А-Я\s]+?)\s*«([^»]+)»?\s*(?:СО\s+ВКУСОМ\s+)?([^;.]+)[;.]?'
    explicit_matches = re.findall(pattern_explicit, text, re.I)
    if explicit_matches:
        # Если есть явные блоки, обрабатываем их
        for match in explicit_matches:
            raw_type = match[0].strip()
            brand = match[1].strip()
            flavor_part = match[2].strip()
            # Собираем полный тип
            sku_type = f"{raw_type} {brand}".strip()
            # Из flavor_part извлекаем вкус (может быть несколько через запятую)
            flavors = extract_flavors_from_text(flavor_part)
            for fl in flavors:
                results.append((sku_type, fl))
        # Удаляем обработанные блоки из текста, чтобы оставшуюся часть обработать как общий список
        # Просто удалим все совпадения
        text = re.sub(pattern_explicit, '', text, flags=re.I)
        # Удаляем оставшиеся точки с запятыми и лишние пробелы
        text = re.sub(r'[;]+', ';', text)
        text = text.strip()

    # Шаг 2: Ищем блоки с общим типом, например "Напитки безалкогольные сильногазированные в ассортименте:"
    # или "НАПИТКИ БЕЗАЛКОГОЛЬНЫЕ АРОМАТИЗИРОВАННЫЕ СИЛЬНОГАЗИРОВАННЫЕ:"
    pattern_general = r'([А-Яа-я\s]+?)\s*(?:в\s+ассортименте)?\s*[:]\s*([^;.]+(?:\s*[;.]\s*[^;.]+)*)'
    general_matches = re.findall(pattern_general, text, re.I)
    if general_matches:
        for match in general_matches:
            general_type = match[0].strip()
            flavor_list_text = match[1].strip()
            # Извлекаем все вкусы из flavor_list_text
            flavors = extract_flavors_from_text(flavor_list_text)
            for fl in flavors:
                results.append((general_type, fl))
        # Удаляем обработанные блоки
        text = re.sub(pattern_general, '', text, flags=re.I)
        text = text.strip()

    # Шаг 3: Если остался текст, возможно, это просто перечисление вкусов без явного типа.
    # Тогда используем дефолтный тип "Напиток безалкогольный" (или можно взять из общего названия, но мы его не знаем)
    # Однако в нашем случае, если остался текст, он может быть частью предыдущих блоков, которые не распарсились.
    # Вместо этого лучше просто проигнорировать оставшийся текст или попытаться извлечь вкусы с дефолтным типом.
    if text.strip():
        # Проверим, нет ли там еще явных "СО ВКУСОМ" без бренда
        remaining_flavors = extract_flavors_from_text(text)
        if remaining_flavors:
            # Используем тип "Напиток безалкогольный" (можно уточнить)
            default_type = "Напиток безалкогольный"
            for fl in remaining_flavors:
                results.append((default_type, fl))

    return results

def extract_flavors_from_text(text):
    """
    Извлекает список вкусов из текста, который может содержать перечисление через запятую,
    точку с запятой, или фразы "со вкусом".
    Возвращает список строк (вкусов).
    """
    if not text:
        return []
    # Убираем слова "со вкусом", "с ароматом" и т.п.
    text = re.sub(r'(со вкусом|с ароматом|вкус|аромат)\s*', '', text, flags=re.I)
    # Разбиваем по разделителям: запятая, точка с запятой, или перенос строки
    # Но нужно быть осторожным, чтобы не разбить составные названия (например, "Апельсин-Манго-Маракуйя")
    # Сначала заменим разделители на единый символ, например ; и затем разобьем.
    # Заменяем запятые на ; если они не являются частью слова (т.е. с пробелом)
    text = re.sub(r',\s*', ';', text)
    text = re.sub(r'\s*;\s*', ';', text)
    text = re.sub(r'\n', ';', text)
    # Убираем лишние точки в конце
    text = re.sub(r'\.$', '', text)
    parts = [p.strip() for p in text.split(';') if p.strip()]
    # Удаляем дубликаты
    seen = set()
    unique_parts = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            unique_parts.append(p)
    # Для каждого элемента нормализуем вкус
    normalized = [normalize_flavor(p) for p in unique_parts]
    return normalized

# ---------- Основная функция обработки ----------
def process_dataframe(df):
    required_cols = ['Регистрационный номер', 'Наименование (обозначение) продукции',
                     'Общее наименование продукции', 'Код ТН ВЭД', 'Действие с',
                     'Действие по', 'Заявитель']
    for col in required_cols:
        if col not in df.columns:
            st.error(f"В файле отсутствует колонка '{col}'")
            return pd.DataFrame()

    new_rows = []

    for _, row in df.iterrows():
        reg_num = row['Регистрационный номер']
        product_name = row['Наименование (обозначение) продукции']
        general_name = row['Общее наименование продукции']
        code_str = row['Код ТН ВЭД']
        action_from = row['Действие с']
        action_to = row['Действие по']
        applicant = row['Заявитель']

        detailed_code = get_detailed_code(code_str)
        group = get_group(detailed_code)

        # Определяем текст для парсинга
        text_for_parse = product_name if pd.notna(product_name) and str(product_name).strip() else general_name
        if pd.isna(text_for_parse) or str(text_for_parse).strip() == '':
            continue

        # Используем новый парсер
        parsed = parse_complex_cell(str(text_for_parse))

        for sku_type, flavor in parsed:
            if not sku_type or not flavor:
                continue
            new_rows.append({
                'SKU': sku_type,
                'Группа': group,
                'Вкус': flavor,
                'Код ТН ВЭД': detailed_code,
                'Регистрационный номер': reg_num,
                'Действие с': action_from,
                'Действие по': action_to,
                'Заявитель': applicant,
            })

    return pd.DataFrame(new_rows)

# ---------- Streamlit UI (без изменений) ----------
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

            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                result_df.to_excel(writer, index=False, sheet_name='Атомизация')
            st.download_button(
                label="📥 Скачать результат в Excel",
                data=output.getvalue(),
                file_name="atomized_result.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

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
