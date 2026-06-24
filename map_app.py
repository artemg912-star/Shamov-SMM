import streamlit as st
import pandas as pd
import os
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# Set Page Config (Full width, collapsed sidebar)
st.set_page_config(
    page_title="Карта Трасс России «SHAMOV»",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------
# GOOGLE SHEETS CONNECTION
# Fallback to local CSV if secrets not configured yet
# ---------------------------------------------------------
TRACKS_FILE = "rollerski_tracks_v2.csv"   # резервный локальный файл
DEFAULT_SHEET_NAME = "shamov_tracks"     # имя листа по умолчанию

COLUMNS = [
    "name", "city", "lat", "lon", "asphalt_quality", "length_km",
    "safety", "description", "contributor", "elevation_drop_m",
    "max_grade_pct", "climb_length_m", "difficulty_color", "is_verified", "likes"
]

def _admin_password():
    if "admin_password" in st.secrets:
        return st.secrets["admin_password"]
    # на случай если пароль положили в секцию [secrets] в Streamlit Cloud
    if "secrets" in st.secrets and "admin_password" in st.secrets["secrets"]:
        return st.secrets["secrets"]["admin_password"]
    return "shamov2026"


def _normalize_sheet_url(url):
    """Убирает лишние #gid=.../edit из ссылки Google Sheets."""
    return url.split("#")[0].strip().rstrip("/")


def _worksheet_name():
    try:
        return st.secrets.get("gsheets", {}).get("worksheet", DEFAULT_SHEET_NAME)
    except Exception:
        return DEFAULT_SHEET_NAME


def _parse_verified(series):
    """TRUE/FALSE из Google Sheets → bool."""
    def to_bool(value):
        if isinstance(value, bool):
            return value
        if pd.isna(value):
            return False
        return str(value).strip().lower() in ("true", "1", "yes", "да")
    return series.map(to_bool)


def get_gsheet():
    """Возвращает объект worksheet или None если secrets не настроены."""
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(dict(creds_dict), scopes=scopes)
        client = gspread.authorize(creds)
        sheet_url = _normalize_sheet_url(st.secrets["gsheets"]["url"])
        spreadsheet = client.open_by_url(sheet_url)
        ws_name = _worksheet_name()
        try:
            ws = spreadsheet.worksheet(ws_name)
        except gspread.exceptions.WorksheetNotFound:
            ws = spreadsheet.sheet1
            st.session_state["_sheet_fallback"] = (
                f"Лист «{ws_name}» не найден — используется «{ws.title}»"
            )
        st.session_state["_active_sheet"] = ws.title
        return ws
    except Exception as exc:
        st.session_state["_gsheet_error"] = str(exc)
        return None


def sheets_status():
    """Краткий статус подключения к Google Sheets."""
    try:
        ws = get_gsheet()
        if ws is not None:
            return "connected", "Google Sheets подключён"
        if "gcp_service_account" in st.secrets and "gsheets" in st.secrets:
            err = st.session_state.get("_gsheet_error", "неизвестная ошибка")
            return "error", f"Ошибка Sheets: {err}"
    except Exception as exc:
        return "csv", f"Локальный CSV ({exc})"
    return "csv", "Локальный CSV (secrets не настроены)"

def _records_to_dataframe(records):
    df = pd.DataFrame(records)
    df.columns = [str(c).strip() for c in df.columns]
    if "is_verified" not in df.columns:
        df["is_verified"] = False
    df["is_verified"] = _parse_verified(df["is_verified"])
    if "likes" in df.columns:
        df["likes"] = pd.to_numeric(df["likes"], errors="coerce").fillna(0).astype(int)
    else:
        df["likes"] = 0
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    if "asphalt_quality" in df.columns:
        df["asphalt_quality"] = pd.to_numeric(df["asphalt_quality"], errors="coerce").fillna(3).astype(int)
    else:
        df["asphalt_quality"] = 3
    if "length_km" in df.columns:
        df["length_km"] = pd.to_numeric(df["length_km"], errors="coerce")
    return df


def _fetch_sheet_records(ws):
    """Читает строки из листа. expected_headers — обход дублей пустых колонок справа."""
    try:
        return ws.get_all_records(expected_headers=COLUMNS)
    except Exception:
        rows = ws.get_all_values()
        if len(rows) < 2:
            return []
        records = []
        for row in rows[1:]:
            values = (row + [""] * len(COLUMNS))[: len(COLUMNS)]
            records.append(dict(zip(COLUMNS, values)))
        return records


def load_tracks():
    """Загружает трассы из Google Sheets, при недоступности — из CSV."""
    ws = get_gsheet()
    if ws is not None:
        try:
            data = _fetch_sheet_records(ws)
            st.session_state["_sheets_row_count"] = len(data)
            if data:
                df = _records_to_dataframe(data)
                st.session_state["_data_source"] = f"Google Sheets → «{ws.title}»"
                st.session_state["_load_tracks_error"] = None
                return df
            st.session_state["_load_tracks_error"] = "Таблица подключена, но данных нет (только заголовки)"
        except Exception as exc:
            st.session_state["_load_tracks_error"] = str(exc)
    else:
        st.session_state["_sheets_row_count"] = None

    # Резерв: локальный CSV — здесь нет ваших черновиков из Google Таблицы!
    if os.path.exists(TRACKS_FILE):
        df = pd.read_csv(TRACKS_FILE, encoding="utf-8")
        if "is_verified" not in df.columns:
            df["is_verified"] = True
        else:
            df["is_verified"] = _parse_verified(df["is_verified"])
        if "likes" not in df.columns:
            df["likes"] = 0
        st.session_state["_data_source"] = "⚠️ локальный CSV (Sheets не прочитан — см. ошибку выше)"
        return df
    st.session_state["_data_source"] = "пусто"
    return pd.DataFrame(columns=COLUMNS)

def _sheet_value(value):
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    return str(value) if value is not None else ""


def save_track(track_dict):
    """Добавляет одну трассу в Google Sheets (или в CSV как резерв)."""
    row = [_sheet_value(track_dict.get(c, "")) for c in COLUMNS]
    ws = get_gsheet()
    if ws is not None:
        try:
            ws.append_row(row, value_input_option="USER_ENTERED")
            return
        except Exception:
            pass
    # Резерв: CSV
    df = load_tracks()
    df = pd.concat([df, pd.DataFrame([track_dict])], ignore_index=True)
    df.to_csv(TRACKS_FILE, index=False, encoding="utf-8")

def update_track_field(track_name, field, value):
    """Обновляет одно поле трассы по имени в Google Sheets (или CSV)."""
    ws = get_gsheet()
    if ws is not None:
        try:
            col_idx = COLUMNS.index(field) + 1   # gspread 1-based
            cell = ws.find(track_name, in_column=1)
            if cell:
                ws.update_cell(cell.row, col_idx, _sheet_value(value))
                return
        except Exception:
            pass
    # Резерв: CSV
    df = load_tracks()
    idx = df[df["name"] == track_name].index
    if not idx.empty:
        df.loc[idx[0], field] = value
        df.to_csv(TRACKS_FILE, index=False, encoding="utf-8")

def delete_track(track_name):
    """Удаляет трассу по имени из Google Sheets (или CSV)."""
    ws = get_gsheet()
    if ws is not None:
        try:
            cell = ws.find(track_name, in_column=1)
            if cell:
                ws.delete_rows(cell.row)
                return
        except Exception:
            pass
    # Резерв: CSV
    df = load_tracks()
    df = df[df["name"] != track_name]
    df.to_csv(TRACKS_FILE, index=False, encoding="utf-8")

# Load FontAwesome CDN for modern vector icons in HTML cards
st.markdown('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">', unsafe_allow_html=True)

# ---------------------------------------------------------
# STYLISH GLASSMORPHISM & SOFT DARK RACING THEME OVERRIDES
# ---------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

    /* Completely hide Streamlit Header & Footer elements and sidebars */
    header, footer, [data-testid="stSidebar"], #MainMenu {
        visibility: hidden !important;
        height: 0px !important;
        width: 0px !important;
        display: none !important;
    }

    button[data-testid="collapsedSidebarCodegen"] {
        display: none !important;
    }

    /* Deep dark background with subtle red glow */
    .stApp {
        background-color: #080C14;
        background-image:
            radial-gradient(ellipse at 0% 0%, rgba(239, 68, 68, 0.06) 0px, transparent 55%),
            radial-gradient(ellipse at 100% 100%, rgba(239, 68, 68, 0.04) 0px, transparent 55%);
        color: #E2E8F0;
        font-family: 'Inter', sans-serif;
    }

    /* Tighter top padding — eliminates dead zone */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 3rem !important;
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
        max-width: 100% !important;
    }

    h1, h2, h3, h4 {
        color: #FFFFFF !important;
        font-family: 'Inter', sans-serif;
        font-weight: 800;
    }

    /* Brand title — larger, bolder, sport energy */
    .brand-title {
        background: linear-gradient(135deg, #EF4444 0%, #F97316 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 900;
        font-size: 2.4rem;
        letter-spacing: -0.03em;
        line-height: 1.1;
        margin-bottom: 0.25rem;
        font-family: 'Inter', sans-serif;
    }

    .brand-subtitle {
        color: #64748B;
        font-size: 0.9rem;
        font-weight: 500;
        margin-top: 0;
        letter-spacing: 0.01em;
    }

    /* Divider line — thinner and more elegant */
    hr {
        border: none !important;
        border-top: 1px solid rgba(255,255,255,0.06) !important;
        margin: 0.75rem 0 !important;
    }

    /* Card blocks */
    .card-block {
        background: linear-gradient(145deg, #161F30, #111827);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 16px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
    }

    /* Buttons — sharp sport look */
    .stButton>button {
        background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%) !important;
        color: white !important;
        font-weight: 700 !important;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        font-size: 0.78rem !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 0.55rem 1.5rem !important;
        width: 100%;
        box-shadow: 0 2px 12px rgba(239, 68, 68, 0.3);
        transition: all 0.2s ease !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(239, 68, 68, 0.5) !important;
    }

    /* Form Inputs */
    .stTextInput>div>div>input,
    .stNumberInput>div>div>input,
    .stTextArea>div>textarea {
        background-color: #0D1117 !important;
        color: #F1F5F9 !important;
        border-radius: 8px !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        font-family: 'Inter', sans-serif !important;
    }

    .stSelectbox>div>div, .stMultiSelect>div>div {
        background-color: #0D1117 !important;
        color: #F1F5F9 !important;
        border-radius: 8px !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
    }

    .stTextInput>div>div>input:focus,
    .stTextArea>div>textarea:focus {
        border-color: #EF4444 !important;
        box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.2) !important;
    }

    /* Slider styling */
    div.row-widget.stSlider {
        margin-top: -2px !important;
        margin-bottom: 0px !important;
    }

    /* Section subheader styling */
    .section-label {
        color: #475569;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin-bottom: 0.4rem;
        font-family: 'Inter', sans-serif;
    }

    /* Sheriff badge */
    .sheriff-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.4rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.04);
    }
    .sheriff-row:last-child { border-bottom: none; }

    /* Stat chip in track card */
    .stat-chip {
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 10px;
        padding: 0.6rem;
        text-align: center;
    }

    /* Mobile */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            padding-top: 0.8rem !important;
        }
        .brand-title { font-size: 1.7rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# SEED DATA — заполняется только если таблица/CSV пустые
# ---------------------------------------------------------
SEED_TRACKS = [
    {
        "name": "ЛБК «Перекоп»",
        "city": "Кировская область, Кирово-Чепецк",
        "lat": 58.5205, "lon": 50.0543,
        "asphalt_quality": 5, "length_km": 5.0,
        "safety": "🟢 Полностью закрытая",
        "description": "Профессиональная трасса в Кирово-Чепецке с серьёзным рельефом. Крутые спуски, длинные подъёмы и качественный асфальт. Отличный вариант для интенсивных тренировок.",
        "contributor": "SMM SHAMOV",
        "elevation_drop_m": 110, "max_grade_pct": 18, "climb_length_m": 1200,
        "difficulty_color": "⚪ Профи (Белая)", "is_verified": True, "likes": 124
    },
    {
        "name": "Трасса им. Ларисы Лазутиной (Одинцово)",
        "city": "Московская область, Одинцово",
        "lat": 55.6917, "lon": 37.2478,
        "asphalt_quality": 5, "length_km": 6.0,
        "safety": "🟢 Полностью закрытая",
        "description": "Превосходная роллерная трасса в сосновом лесу. Тяжёлый рабочий рельеф, скоростные спуски со светофорами безопасности. Идеальна для коньковых тренировок.",
        "contributor": "лыжник_одинцово",
        "elevation_drop_m": 75, "max_grade_pct": 12, "climb_length_m": 800,
        "difficulty_color": "🔴 Сложная (Красная)", "is_verified": True, "likes": 98
    },
    {
        "name": "УТЦ «Кавголово» (НГУ им. Лесгафта)",
        "city": "Ленинградская область, Токсово",
        "lat": 60.1581, "lon": 30.5186,
        "asphalt_quality": 5, "length_km": 3.0,
        "safety": "🟢 Полностью закрытая",
        "description": "Профессиональный биатлонный центр. Крутые виражи, отличный накат и жёсткие подъёмы. Кататься рекомендуется только в шлеме!",
        "contributor": "spb_skier",
        "elevation_drop_m": 60, "max_grade_pct": 15, "climb_length_m": 500,
        "difficulty_color": "⚪ Профи (Белая)", "is_verified": True, "likes": 84
    },
    {
        "name": "ОЦСП «Жемчужина Сибири»",
        "city": "Тюменская область, Тюмень",
        "lat": 57.0016, "lon": 65.2536,
        "asphalt_quality": 5, "length_km": 7.5,
        "safety": "🟢 Полностью закрытая",
        "description": "Один из лучших лыжно-биатлонных комплексов страны. Широкая трасса, идеальный асфальт, длинный круг. Подходит для накатывания больших летних объёмов.",
        "contributor": "siberia_biathlon",
        "elevation_drop_m": 45, "max_grade_pct": 8, "climb_length_m": 600,
        "difficulty_color": "🔵 Средняя (Синяя)", "is_verified": True, "likes": 76
    },
    {
        "name": "ОУСЦ «Планерная» (Химки)",
        "city": "Московская область, Химки",
        "lat": 55.9184, "lon": 37.3516,
        "asphalt_quality": 4, "length_km": 2.5,
        "safety": "🟢 Полностью закрытая",
        "description": "Хорошая тренировочная трасса на севере Подмосковья. Рельеф средней сложности, асфальт рабочий, но местами бывает листва и ветки.",
        "contributor": "msk_skate",
        "elevation_drop_m": 30, "max_grade_pct": 7, "climb_length_m": 400,
        "difficulty_color": "🔵 Средняя (Синяя)", "is_verified": True, "likes": 43
    },
    {
        "name": "ЛБК «Ангарский»",
        "city": "Иркутская область, Ангарск",
        "lat": 52.5401, "lon": 103.8860,
        "asphalt_quality": 4, "length_km": 2.5,
        "safety": "🟢 Полностью закрытая",
        "description": "Освещённая трасса для тренировок сибиряков. Асфальт качественный, подъёмы плавные, подходит для любителей.",
        "contributor": "baikal_skier",
        "elevation_drop_m": 25, "max_grade_pct": 5, "climb_length_m": 300,
        "difficulty_color": "🔵 Средняя (Синяя)", "is_verified": True, "likes": 39
    },
    {
        "name": "Парк «Крылатские холмы» (Москва)",
        "city": "Москва, Крылатское",
        "lat": 55.7621, "lon": 37.4243,
        "asphalt_quality": 4, "length_km": 4.2,
        "safety": "🔴 Открытая дорога",
        "description": "Олимпийская велотрасса. Бешеный рельеф, огромные скорости на спусках. Будьте предельно осторожны — тормозить негде, а на трассе часто гуляют люди!",
        "contributor": "pro_skier_moscow",
        "elevation_drop_m": 120, "max_grade_pct": 16, "climb_length_m": 1500,
        "difficulty_color": "⚪ Профи (Белая)", "is_verified": True, "likes": 115
    },
    {
        "name": "Трасса «Ветлужанка»",
        "city": "Красноярск",
        "lat": 56.0125, "lon": 92.7483,
        "asphalt_quality": 3, "length_km": 3.0,
        "safety": "🟢 Полностью закрытая",
        "description": "Лесная тренировочная трасса. Асфальт местами неровный (крупное зерно), отлично подходит для тренировок на мягком каучуке Shamov 02-1.",
        "contributor": "krsk_ski",
        "elevation_drop_m": 20, "max_grade_pct": 4, "climb_length_m": 200,
        "difficulty_color": "🟢 Простая (Зеленая)", "is_verified": True, "likes": 27
    },
]

def init_seed():
    """Заполняет базу начальными данными только если она пуста."""
    df = load_tracks()
    if df.empty:
        ws = get_gsheet()
        if ws is not None:
            try:
                # Записываем заголовки + все строки одним вызовом
                rows = [COLUMNS] + [[_sheet_value(t.get(c, "")) for c in COLUMNS] for t in SEED_TRACKS]
                ws.clear()
                ws.update("A1", rows)
                return
            except Exception:
                pass
        # Резерв: CSV
        pd.DataFrame(SEED_TRACKS).to_csv(TRACKS_FILE, index=False, encoding="utf-8")

init_seed()
tracks_df = load_tracks()


# ---------------------------------------------------------
# DIFFICULTY ALGORITHM
# ---------------------------------------------------------
def calculate_difficulty_by_metrics(drop, grade, climb):
    if grade <= 4 and drop <= 20:
        return "🟢 Простая (Зеленая)"
    elif grade <= 8 and drop <= 45:
        return "🔵 Средняя (Синяя)"
    elif grade <= 14 and drop <= 90:
        return "🔴 Сложная (Красная)"
    else:
        return "⚪ Профи (Белая)"

# ---------------------------------------------------------
# HEADER ROW — compact, no dead zone
# ---------------------------------------------------------
col_header_left, col_header_right = st.columns([5, 1])

with col_header_left:
    # Inline CTA button next to title using HTML
    st.markdown("""
        <div style="display:flex; align-items:center; gap:1.2rem; flex-wrap:wrap;">
            <div>
                <div class="brand-title">📍 Карта трасс России</div>
                <p class="brand-subtitle">Единая спортивная карта лыжероллерных трасс — Проект SHAMOV</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

with col_header_right:
    if os.path.exists("logo.png"):
        st.markdown('<div style="text-align:right; padding-top:4px;">', unsafe_allow_html=True)
        st.image("logo.png", width=180)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="text-align:right; padding-top:8px;">
                <span style="font-size:1.6rem; font-weight:900; letter-spacing:-0.02em;
                    background:linear-gradient(135deg,#EF4444,#F97316);
                    -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
                    ШАМОВ
                </span><br>
                <span style="color:#475569; font-size:0.7rem; font-weight:600; letter-spacing:0.1em;">РОССИЯ</span>
            </div>
        """, unsafe_allow_html=True)

st.write("---")

# ---------------------------------------------------------
# 1. FILTER PANEL + ADD TRACK BUTTON IN ONE ROW
# ---------------------------------------------------------
st.markdown('<div class="section-label">🗺️ Живой GPS-навигатор трасс</div>', unsafe_allow_html=True)

col_f1, col_f2, col_f3, col_search, col_add = st.columns([1, 1.2, 0.9, 1.1, 0.6])

with col_f1:
    min_rating = st.slider("⭐ Мин. оценка асфальта:", 1, 5, 3)

with col_f2:
    diff_filter = st.multiselect(
        "Фильтр сложности:",
        options=list(tracks_df["difficulty_color"].unique()),
        default=list(tracks_df["difficulty_color"].unique())
    )

with col_f3:
    show_mode = st.selectbox(
        "Показ трасс:",
        ["Все подтвержденные трассы", "Показать также черновики/новые"]
    )

with col_search:
    search_query = st.text_input("🔍 Поиск", placeholder="Название или регион...")

with col_add:
    st.write("")
    st.write("")
    with st.popover("➕ Добавить трассу", use_container_width=True):
        st.subheader("📝 Нанести новую трассу")
        st.write("Заполните характеристики. Категория сложности рассчитается автоматически!")

        t_name = st.text_input("Название трассы / комплекса *", value="ЛБК «Ангара»")
        t_city = st.text_input("Город / Регион *", value="Свердловская область, Екатеринбург")

        with st.expander("🌐 Настроить точные GPS-координаты"):
            t_lat = st.number_input("Широта (Lat) *", format="%.5f", value=55.75580)
            t_lon = st.number_input("Долгота (Lon) *", format="%.5f", value=37.61730)

        t_asphalt = st.slider("⭐ Качество асфальта (1-5) *", 1, 5, 4)
        t_length = st.number_input("📏 Длина круга (км) *", min_value=0.1, max_value=50.0, value=3.0, step=0.1)

        st.write("---")
        st.write("#### ⛰️ Характеристики рельефа:")
        t_drop = st.slider("📈 Перепад высот (м) *", min_value=0, max_value=200, value=35, step=5)
        t_grade = st.slider("📐 Макс. уклон (%) *", min_value=0, max_value=25, value=6, step=1)
        t_climb_len = st.slider("🏃 Длина макс. подъема (м) *", 0, 2000, 300)

        calculated_color = calculate_difficulty_by_metrics(t_drop, t_grade, t_climb_len)
        st.info(f"Рассчитанная сложность: {calculated_color}")

        t_safety = st.selectbox("🛡️ Безопасность *", ["🟢 Полностью закрытая", "🟡 Частично открытая", "🔴 Открытая дорога"])
        t_desc = st.text_area("Советы и описание трассы *", value="Трасса широкая, асфальт уложили в прошлом году.")
        t_contrib = st.text_input("Никнейм в соцсетях (@)", value="лыжник_любитель")
        t_show_nick = st.checkbox("Показать мой ник на карте", value=True)

        submit_btn = st.button("🔥 ОТПРАВИТЬ ЧЕРНОВИК НА КАРТУ")
        if submit_btn:
            if not t_name or not t_city:
                st.error("Заполните обязательные поля!")
            else:
                author_display = t_contrib if t_contrib and t_show_nick else "Анонимный лыжник"
                new_track = {
                    "name": t_name, "city": t_city,
                    "lat": float(t_lat), "lon": float(t_lon),
                    "asphalt_quality": int(t_asphalt), "length_km": float(t_length),
                    "safety": t_safety, "description": t_desc,
                    "contributor": author_display,
                    "elevation_drop_m": int(t_drop),
                    "max_grade_pct": int(t_grade),
                    "climb_length_m": int(t_climb_len),
                    "difficulty_color": calculated_color,
                    "is_verified": False, "likes": 0
                }
                save_track(new_track)
                st.success("🎉 Черновик добавлен! Пройдите верификацию в детальном обзоре.")
                st.balloons()
                st.rerun()

# Filter database
filtered_tracks = tracks_df[
    (tracks_df["asphalt_quality"] >= min_rating) &
    (tracks_df["difficulty_color"].isin(diff_filter))
]
if show_mode == "Все подтвержденные трассы":
    filtered_tracks = filtered_tracks[filtered_tracks["is_verified"] == True]

if search_query.strip():
    q = search_query.strip().lower()
    filtered_tracks = filtered_tracks[
        filtered_tracks["name"].str.lower().str.contains(q, na=False) |
        filtered_tracks["city"].str.lower().str.contains(q, na=False)
    ]

verified_count = int(filtered_tracks[filtered_tracks["is_verified"] == True].shape[0]) if not filtered_tracks.empty else 0
total_km = float(filtered_tracks["length_km"].sum()) if not filtered_tracks.empty else 0.0
region_count = filtered_tracks["city"].nunique() if not filtered_tracks.empty else 0

st.markdown(f"""
<div style="display:flex; flex-wrap:wrap; gap:0.6rem; margin:0.4rem 0 0.8rem;">
  <span style="background:rgba(239,68,68,0.12); border:1px solid rgba(239,68,68,0.25);
      color:#FCA5A5; padding:0.35rem 0.75rem; border-radius:999px; font-size:0.78rem; font-weight:700;">
    📍 {len(filtered_tracks)} трасс на карте
  </span>
  <span style="background:rgba(59,130,246,0.12); border:1px solid rgba(59,130,246,0.25);
      color:#93C5FD; padding:0.35rem 0.75rem; border-radius:999px; font-size:0.78rem; font-weight:700;">
    ✅ {verified_count} проверенных
  </span>
  <span style="background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.25);
      color:#6EE7B7; padding:0.35rem 0.75rem; border-radius:999px; font-size:0.78rem; font-weight:700;">
    📏 {total_km:.1f} км суммарно
  </span>
  <span style="background:rgba(148,163,184,0.1); border:1px solid rgba(148,163,184,0.2);
      color:#94A3B8; padding:0.35rem 0.75rem; border-radius:999px; font-size:0.78rem; font-weight:700;">
    🗺️ {region_count} регионов
  </span>
</div>
""", unsafe_allow_html=True)

# Initialize selection session state
if "clicked_track_name" not in st.session_state:
    st.session_state.clicked_track_name = ""

# ---------------------------------------------------------
# 2. MAP RENDERING (BUG FIX #2: center on Russia)
# ---------------------------------------------------------
if filtered_tracks.empty:
    st.warning("⚠️ Нет трасс, подходящих под выбранные фильтры. Снизьте требования к асфальту!")
else:
    try:
        import plotly.express as px

        fig_map = px.scatter_mapbox(
            filtered_tracks,
            lat="lat",
            lon="lon",
            color="difficulty_color",
            color_discrete_map={
                "🟢 Простая (Зеленая)": "#10B981",
                "🔵 Средняя (Синяя)": "#3B82F6",
                "🔴 Сложная (Красная)": "#EF4444",
                "⚪ Профи (Белая)": "#FFFFFF"
            },
            center={"lat": 60.0, "lon": 68.0},   # FIX #2: центр на Россию
            zoom=3,
            height=400,
            hover_name="name",
            hover_data={
                "lat": False, "lon": False,
                "city": True, "length_km": True,
                "asphalt_quality": True, "difficulty_color": True,
                "safety": True, "likes": True
            },
            labels={
                "city": "📍 Регион / Город",
                "length_km": "📏 Длина круга",
                "asphalt_quality": "⭐ Оценка асфальта",
                "difficulty_color": "🏃 Сложность",
                "safety": "🛡️ Безопасность",
                "likes": "👍 Лайков"
            }
        )

        fig_map.update_layout(
            mapbox_style="carto-darkmatter",
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            coloraxis_showscale=False,
            legend=dict(
                bgcolor="rgba(8,12,20,0.85)",
                bordercolor="rgba(255,255,255,0.1)",
                borderwidth=1,
                font=dict(color="#CBD5E1", size=11),
                title=dict(text="Сложность", font=dict(color="#94A3B8", size=11))
            )
        )
        fig_map.update_traces(marker=dict(size=14))

        select_event = st.plotly_chart(
            fig_map,
            use_container_width=True,
            config={"scrollZoom": True},
            on_select="rerun"
        )

        # Process Map Clicks
        if select_event and "selection" in select_event and "points" in select_event["selection"]:
            points = select_event["selection"]["points"]
            if len(points) > 0:
                point_index = points[0].get("point_index")
                if point_index is not None and point_index < len(filtered_tracks):
                    st.session_state.clicked_track_name = filtered_tracks.iloc[point_index]["name"]

    except Exception as e:
        st.error(f"⚠️ Ошибка графического движка: {str(e)}")

# ---------------------------------------------------------
# 3. TRACK DETAIL + LEADERBOARD
# ---------------------------------------------------------
st.write("")
col_spot_left, col_spot_right = st.columns([1, 2.5])

with col_spot_left:
    track_list = list(filtered_tracks["name"].unique()) if not filtered_tracks.empty else ["-- Нет подходящих трасс --"]

    default_idx = 0
    if st.session_state.clicked_track_name in track_list:
        default_idx = track_list.index(st.session_state.clicked_track_name)

    selected_track_name = st.selectbox(
        "🔎 Детальный обзор трассы:",
        options=track_list,
        index=default_idx
    )

    # Top-3 tracks by likes using native Streamlit (no HTML rendering issues)
    top_tracks = (
        tracks_df[tracks_df["is_verified"] == True]
        .sort_values("likes", ascending=False)
        .head(3)
        .reset_index(drop=True)
    )
    medals = ["🥇", "🥈", "🥉"]

    with st.container():
        st.markdown(
            "<div style='color:#94A3B8; font-size:0.7rem; font-weight:700; "
            "text-transform:uppercase; letter-spacing:0.1em; margin-bottom:4px;'>"
            "🔥 Топ трасс по голосам</div>",
            unsafe_allow_html=True
        )
        for i, row in top_tracks.iterrows():
            col_m, col_n, col_l = st.columns([0.3, 2.5, 0.7])
            col_m.markdown(medals[i])
            col_n.markdown(
                f"<span style='color:#F1F5F9; font-size:0.82rem; font-weight:600;'>{row['name']}</span>",
                unsafe_allow_html=True
            )
            col_l.markdown(
                f"<span style='color:#EF4444; font-size:0.8rem; font-weight:700;'>👍 {int(row['likes'])}</span>",
                unsafe_allow_html=True
            )

with col_spot_right:
    if selected_track_name and selected_track_name != "-- Нет подходящих трасс --":
        track_info = filtered_tracks[filtered_tracks["name"] == selected_track_name].iloc[0]

        # Like & Verification
        col_act1, col_act2 = st.columns([1, 2.5])
        with col_act1:
            like_key = f"like_f_{track_info['name']}"
            if st.button(f"👍 Проголосовать ({track_info['likes']})", key=like_key):
                new_likes = int(track_info['likes']) + 1
                update_track_field(track_info["name"], "likes", new_likes)
                st.success("Спасибо за голос!")
                st.rerun()

        with col_act2:
            if not track_info["is_verified"]:
                with st.popover("⏳ Черновик! Подтвердить и опубликовать"):
                    st.write("Чтобы сделать трассу публичной:")
                    st.button("📍 Подтвердить геолокацию (Я на месте!)", key=f"geo_verify_{track_info['name']}")
                    st.file_uploader("Загрузите 1 реальное фото покрытия:", type=["jpg","jpeg","png"], key=f"photo_{track_info['name']}")
                    if st.button("🔥 Активировать на общую карту", key=f"pub_final_{track_info['name']}"):
                        update_track_field(track_info["name"], "is_verified", True)
                        st.success("🎉 Трасса проверена и опубликована!")
                        st.balloons()
                        st.rerun()
            else:
                st.markdown("<span style='color:#A3E635; font-weight:700; font-size:0.9rem;'><i class='fa-solid fa-circle-check'></i> Проверенная трасса сообщества</span>", unsafe_allow_html=True)

        # Wheel recommendation
        asphalt_val = int(track_info['asphalt_quality'])
        if asphalt_val == 5:
            wheel_recommendation = "🚀 <b>Профи-накат:</b> Идеальный асфальт! Рекомендуем топовые карбоновые модели <code>Shamov 04-3PU (карбон)</code> или полиуретан на алюминиевых дисках <code>Shamov 04-2</code> (100 мм)."
        elif asphalt_val == 4:
            wheel_recommendation = "⚡ <b>Отличный баланс:</b> Трасса позволяет кататься как на полиуретане <code>Shamov 04-2</code>, так и на мягком каучуке <code>Shamov 04-1 (100 мм)</code> или карбоновых <code>Shamov 04-3R</code> для гашения вибраций."
        else:
            wheel_recommendation = "🔧 <b>Амортизация вибрации:</b> Рекомендуем мягкие резиновые колеса <code>Shamov 02-1</code> или классику <code>05 Elpex</code> для защиты суставов."

        # Difficulty badge color
        diff_badge_style = "linear-gradient(135deg, #EF4444 0%, #B91C1C 100%)"
        diff_text_color = "#FFFFFF"
        if "Зеленая" in track_info['difficulty_color']:
            diff_badge_style = "linear-gradient(135deg, #10B981 0%, #047857 100%)"
        elif "Синяя" in track_info['difficulty_color']:
            diff_badge_style = "linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)"
        elif "Белая" in track_info['difficulty_color']:
            diff_badge_style = "linear-gradient(135deg, #E2E8F0 0%, #94A3B8 100%)"
            diff_text_color = "#0F172A"

        # Stars for asphalt quality
        stars = "⭐" * int(track_info['asphalt_quality']) + "☆" * (5 - int(track_info['asphalt_quality']))
        lat, lon = float(track_info["lat"]), float(track_info["lon"])
        yandex_url = f"https://yandex.ru/maps/?pt={lon},{lat}&z=15&l=map"
        google_url = f"https://www.google.com/maps?q={lat},{lon}"

        html_card = f"""
<div style="background:linear-gradient(145deg,#161F30,#111827); border:1px solid rgba(255,255,255,0.07);
    backdrop-filter:blur(12px); border-radius:16px; padding:1.4rem;
    box-shadow:0 8px 32px rgba(0,0,0,0.5); border-left:4px solid #EF4444;">

  <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:0.5rem; margin-bottom:0.9rem;">
    <div>
      <h3 style="margin:0; color:#FFFFFF !important; font-size:1.5rem; font-weight:800;
          font-family:'Inter',sans-serif; letter-spacing:-0.02em;">{track_info['name']}</h3>
      <p style="color:#64748B; font-size:0.85rem; margin:0.15rem 0 0; font-family:'Inter',sans-serif;">
        <i class="fa-solid fa-location-dot" style="color:#EF4444; margin-right:4px;"></i>{track_info['city']}
      </p>
    </div>
    <div style="background:{diff_badge_style}; color:{diff_text_color}; padding:5px 14px;
        border-radius:20px; font-weight:700; font-size:0.72rem; text-transform:uppercase;
        font-family:'Inter',sans-serif; box-shadow:0 2px 8px rgba(0,0,0,0.3); white-space:nowrap;">
      {track_info['difficulty_color']}
    </div>
  </div>

  <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(130px,1fr)); gap:0.6rem; margin-bottom:0.9rem;">
    <div class="stat-chip">
      <div style="color:#475569; font-size:0.68rem; font-weight:700; font-family:'Inter',sans-serif;
          letter-spacing:0.08em; text-transform:uppercase; margin-bottom:0.25rem;">
        <i class="fa-solid fa-route" style="color:#EF4444;"></i> Длина круга
      </div>
      <div style="color:#FFFFFF; font-size:1.25rem; font-weight:800; font-family:'Inter',sans-serif;">
        {track_info['length_km']} км
      </div>
    </div>
    <div class="stat-chip">
      <div style="color:#475569; font-size:0.68rem; font-weight:700; font-family:'Inter',sans-serif;
          letter-spacing:0.08em; text-transform:uppercase; margin-bottom:0.25rem;">
        <i class="fa-solid fa-mountain" style="color:#EF4444;"></i> Перепад / Уклон
      </div>
      <div style="color:#FFFFFF; font-size:1.1rem; font-weight:800; font-family:'Inter',sans-serif;">
        {int(track_info['elevation_drop_m'])}м / {int(track_info['max_grade_pct'])}%
      </div>
    </div>
    <div class="stat-chip">
      <div style="color:#475569; font-size:0.68rem; font-weight:700; font-family:'Inter',sans-serif;
          letter-spacing:0.08em; text-transform:uppercase; margin-bottom:0.25rem;">
        <i class="fa-solid fa-shield-halved" style="color:#EF4444;"></i> Безопасность
      </div>
      <div style="color:#FFFFFF; font-size:0.82rem; font-weight:600; margin-top:0.3rem; font-family:'Inter',sans-serif;">
        {track_info['safety']}
      </div>
    </div>
    <div class="stat-chip">
      <div style="color:#475569; font-size:0.68rem; font-weight:700; font-family:'Inter',sans-serif;
          letter-spacing:0.08em; text-transform:uppercase; margin-bottom:0.25rem;">
        <i class="fa-solid fa-star" style="color:#EF4444;"></i> Асфальт
      </div>
      <div style="color:#FCD34D; font-size:0.95rem; font-weight:600; font-family:'Inter',sans-serif; margin-top:0.15rem;">
        {stars}
      </div>
    </div>
  </div>

  <div style="background:rgba(8,12,20,0.5); border:1px solid rgba(255,255,255,0.04);
      border-radius:10px; padding:0.8rem; margin-bottom:0.6rem;">
    <p style="color:#94A3B8; font-size:0.72rem; font-weight:700; text-transform:uppercase;
        letter-spacing:0.1em; margin:0 0 0.35rem; font-family:'Inter',sans-serif;">
      📝 Совет эксперта SHAMOV
    </p>
    <p style="color:#CBD5E1; font-size:0.9rem; line-height:1.55; margin:0;
        font-style:italic; font-family:'Inter',sans-serif;">«{track_info['description']}»</p>
  </div>

  <div style="background:rgba(239,68,68,0.07); border:1px solid rgba(239,68,68,0.15);
      border-radius:10px; padding:0.75rem; margin-bottom:0.6rem;">
    <p style="color:#FCA5A5; font-size:0.85rem; line-height:1.55; margin:0; font-family:'Inter',sans-serif;">
      <i class="fa-solid fa-circle-info" style="color:#EF4444; margin-right:5px;"></i>{wheel_recommendation}
    </p>
  </div>

  <div style="display:flex; flex-wrap:wrap; gap:0.5rem; margin-bottom:0.5rem;">
    <a href="{yandex_url}" target="_blank" rel="noopener noreferrer"
       style="text-decoration:none; background:rgba(239,68,68,0.15); border:1px solid rgba(239,68,68,0.35);
       color:#FCA5A5; padding:0.45rem 0.85rem; border-radius:8px; font-size:0.75rem; font-weight:700;
       font-family:'Inter',sans-serif;">
      <i class="fa-solid fa-map-location-dot"></i> Яндекс.Карты
    </a>
    <a href="{google_url}" target="_blank" rel="noopener noreferrer"
       style="text-decoration:none; background:rgba(59,130,246,0.12); border:1px solid rgba(59,130,246,0.3);
       color:#93C5FD; padding:0.45rem 0.85rem; border-radius:8px; font-size:0.75rem; font-weight:700;
       font-family:'Inter',sans-serif;">
      <i class="fa-brands fa-google"></i> Google Maps
    </a>
    <span style="color:#475569; font-size:0.72rem; align-self:center; font-family:'Inter',sans-serif;">
      GPS: {lat:.5f}, {lon:.5f}
    </span>
  </div>

  <div style="margin-top:0.2rem; text-align:right; color:#334155; font-size:0.75rem; font-family:'Inter',sans-serif;">
    <i class="fa-solid fa-user-check" style="margin-right:4px;"></i>Добавил:
    <span style="color:#34D399; font-weight:600;">@{track_info['contributor']}</span>
  </div>
</div>"""
        st.markdown(html_card, unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. ADMIN PANEL
# ---------------------------------------------------------
st.write("---")
col_foo_left, col_foo_right = st.columns([4, 1.2])

with col_foo_right:
    with st.expander("🛠️ Модерация базы (для SMM)"):
        # Источник данных — видно сразу, без пароля
        _data_src = st.session_state.get("_data_source", "—")
        if "Google Sheets" in str(_data_src):
            st.success(f"📂 {_data_src} · строк в таблице: {st.session_state.get('_sheets_row_count', '?')}")
        elif "CSV" in str(_data_src):
            st.warning(
                f"📂 {_data_src}\n\n"
                "Сайт **не читает** вашу Google Таблицу и показывает старый CSV из кода. "
                "Черновики из Sheets поэтому не видны."
            )
        else:
            st.info(f"📂 {_data_src}")

        status_code, status_text = sheets_status()
        if status_code == "connected":
            st.success(f"🟢 {status_text}")
            if st.session_state.get("_active_sheet"):
                st.caption(f"Активный лист: **{st.session_state['_active_sheet']}**")
            if st.session_state.get("_sheet_fallback"):
                st.warning(st.session_state["_sheet_fallback"])
        elif status_code == "error":
            st.error(f"🔴 {status_text}")
        else:
            st.info(f"🟡 {status_text}")

        if st.session_state.get("_load_tracks_error"):
            st.warning(f"Ошибка чтения Sheets: {st.session_state['_load_tracks_error']}")

        if st.button("🔄 Обновить данные", key="reload_tracks"):
            st.rerun()

        SECURE_PASSWORD = _admin_password()
        admin_pass = st.text_input("Введите пароль модератора:", type="password", key="sec_admin_pass")
        st.caption("ℹ️ *После ввода пароля нажмите **Enter**.*")
        if admin_pass == SECURE_PASSWORD:
            st.success("Доступ разрешен!")
            moderation_df = load_tracks()
            drafts_count = int((~moderation_df["is_verified"]).sum()) if not moderation_df.empty else 0
            st.caption(
                f"📊 {st.session_state.get('_data_source', '—')} · "
                f"всего записей: **{len(moderation_df)}** · черновиков: **{drafts_count}**"
            )
            unverified_df = moderation_df[~moderation_df["is_verified"]]
            if unverified_df.empty:
                st.info("🎉 Все трассы проверены! Новых черновиков нет.")
            else:
                st.write("📋 **Новые черновики на проверку:**")
                for idx, row in unverified_df.iterrows():
                    st.write(f"📍 **{row['name']}** ({row['city']})")
                    st.write(f"📏 {row['length_km']}км | {row['difficulty_color']} | GPS: {row['lat']},{row['lon']}")
                    col_adm_b1, col_adm_b2 = st.columns(2)
                    with col_adm_b1:
                        if st.button("✅ Одобрить", key=f"adm_ok_{row['name']}"):
                            update_track_field(row["name"], "is_verified", True)
                            st.success("Одобрено!")
                            st.rerun()
                    with col_adm_b2:
                        if st.button("❌ Удалить", key=f"adm_del_{row['name']}"):
                            delete_track(row["name"])
                            st.warning("Удалено!")
                            st.rerun()

st.markdown("""
<div style="text-align:center; color:#334155; font-size:0.78rem; padding:12px 0 4px;">
    Проект разработан специально для SMM-службы ПТФ «ШАМОВ» © 2026 &nbsp;·&nbsp; Киров • 15 лет качества спортивного инвентаря
</div>
""", unsafe_allow_html=True)
