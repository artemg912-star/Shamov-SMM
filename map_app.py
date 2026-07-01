import streamlit as st
import pandas as pd
import os
import requests
import base64
import re
import numpy as np
from datetime import datetime, date

# Set Page Config (Full width, collapsed sidebar, custom Page Title!)
st.set_page_config(
    page_title="GRBNV PROD Track",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# File path for storing tracks database
TRACKS_FILE = "rollerski_tracks_v2.csv"

# Load FontAwesome CDN for modern vector icons in HTML cards
st.markdown('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">', unsafe_allow_html=True)

# ---------------------------------------------------------
# STRICT BLACK MINIMALIST THEME OVERRIDES (HIGH-CONTRAST UI)
# ---------------------------------------------------------
st.markdown("""
<style>
    /* Completely hide Streamlit Header & Footer elements and sidebars! */
    header, footer, [data-testid="stSidebar"], #MainMenu {
        visibility: hidden !important;
        height: 0px !important;
        width: 0px !important;
        display: none !important;
    }
    
    /* Hide default sidebar navigation control arrow completely */
    button[data-testid="collapsedSidebarCodegen"] {
        display: none !important;
    }
    
    /* Main Dark Theme Background (Solid #0B0F14, no gradients!) */
    .stApp {
        background-color: #0B0F14 !important;
        background-image: none !important;
        color: #E2E8F0 !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* 🌟 WIDE CONTAINER FOR PREMIUM LOOK 🌟 */
    .block-container {
        max-width: 1450px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        padding-top: 10px !important; /* Tiny top gap */
        padding-bottom: 2rem !important;
        padding-left: 20px !important;
        padding-right: 20px !important;
    }
    
    /* Header styling */
    h1, h2, h3, h4, h5, h6 {
        color: #FFFFFF !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 800;
    }
    
    /* Branded Accent Title */
    .brand-title {
        color: #EF4444 !important;
        font-weight: 900;
        font-size: 2.2rem;
        letter-spacing: -0.02em;
        margin-bottom: 0.1rem;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* 📐 EXACT 28PX VERTICAL GAP BETWEEN SECTIONS 📐 */
    .card-block, .floating-filter-panel, [data-testid="stPlotlyChart"], hr, .mobile-header-container {
        margin-bottom: 28px !important;
    }
    
    /* Strict Minimalist Card Blocks (Solid #0D1117, border 1px, no shadows, 6px radius, 16px padding) */
    .card-block {
        background-color: #0D1117 !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 6px !important;
        padding: 16px !important;
        box-shadow: none !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
    }
    
    /* FLOATING CONTROL PANEL ABOVE THE MAP (Zero shadow, 6px radius, 16px padding) */
    .floating-filter-panel {
        background: #0D1117 !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 6px !important;
        padding: 16px !important;
        box-shadow: none !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
    }
    
    /* Interactive Button Styles (Outline Red, 6px radius, hover highlights) */
    .stButton>button {
        background: #0D1117 !important;
        color: #EF4444 !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
        font-weight: 800 !important;
        font-family: 'Inter', sans-serif !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        border-radius: 6px !important;
        padding: 0.6rem 2rem !important;
        min-height: 44px !important; /* Min height 44px! */
        width: 100%;
        box-shadow: none !important;
        transition: all 0.15s ease-in-out !important;
    }
    .stButton>button:hover {
        background-color: #EF4444 !important;
        color: #FFFFFF !important;
        border-color: #EF4444 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important; /* Soft shadow on hover */
    }
    .stButton>button:active {
        background-color: #B91C1C !important; /* Darker red on click */
    }
    
    /* Popover CTA button min-height */
    div[data-testid="stPopover"]>div>button {
        min-height: 44px !important;
        border-radius: 6px !important;
        background: #0D1117 !important;
        color: #EF4444 !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
        font-weight: bold !important;
        box-shadow: none !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        transition: all 0.15s ease-in-out !important;
    }
    div[data-testid="stPopover"]>div>button:hover {
        background-color: #EF4444 !important;
        color: #FFFFFF !important;
        border-color: #EF4444 !important;
    }
    
    /* Form Inputs styling (Elegant dark matte inputs, 6px radius, min-height 44px) */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        background-color: #0B0F14 !important;
        color: #E2E8F0 !important;
        border-radius: 6px !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        padding: 0.35rem 0.6rem !important;
        min-height: 44px !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stTextInput>div>div>input:hover, .stNumberInput>div>div>input:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
    }
    .stTextArea>div>textarea {
        background-color: #0B0F14 !important;
        color: #E2E8F0 !important;
        border-radius: 6px !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        padding: 0.35rem 0.6rem !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stTextArea>div>textarea:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
    }
    
    /* Selectboxes and multiselects (6px radius, border 1px, min-height 44px) */
    .stSelectbox>div>div, .stMultiSelect>div>div {
        background-color: #0B0F14 !important;
        color: #E2E8F0 !important;
        border-radius: 6px !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        min-height: 44px !important;
    }
    .stSelectbox>div>div:hover, .stMultiSelect>div>div:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
    }
    
    /* Caption and labels styled to gray-blue (#94A3B8) */
    .stMarkdown p, label, .stSlider p {
        color: #94A3B8 !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* SLATE PILL TABS WITH 6PX RADIUS */
    div[data-testid="stTabBar"] {
        background-color: #0D1117 !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        padding: 4px !important;
        border-radius: 6px !important;
        display: inline-flex !important;
        margin-bottom: 1rem !important;
    }
    
    button[data-baseweb="tab"] {
        background-color: transparent !important;
        border-radius: 4px !important;
        padding: 6px 18px !important;
        color: #94A3B8 !important;
        border: none !important;
        margin-right: 4px !important;
        font-weight: 700 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase;
        min-height: 44px !important;
        font-family: 'Inter', sans-serif !important;
        transition: all 0.15s ease !important;
    }
    
    button[data-baseweb="tab"]:hover {
        color: #FFFFFF !important;
        background-color: rgba(255, 255, 255, 0.03) !important;
    }
    
    /* Minimalist Dark-Grey Active Tab (NO RED BG, pure premium white/red text!) */
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #0B0F14 !important;
        color: #EF4444 !important; /* Red text accent instead of background! */
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        box-shadow: none !important;
    }
    
    /* Hide active border line */
    div[data-testid="stTabBar"] div[role="tablist"] div {
        background-color: transparent !important;
    }
    
    /* Compact element paddings */
    div.row-widget.stSlider {
        margin-top: -5px !important;
        margin-bottom: -5px !important;
    }
    
    /* 📱 MOBILE RESPONSIVENESS AND OPTIMIZATIONS (Media Queries) 📱 */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            padding-top: 1rem !important;
        }
        div[data-testid="stPlotlyChart"] iframe {
            height: 310px !important;
        }
        /* Style mobile header nicely */
        .mobile-header-container {
            grid-template-columns: 1fr !important;
            text-align: center !important;
            gap: 12px !important;
            padding: 16px !important;
        }
        .header-sponsor-section {
            justify-content: center !important;
            gap: 8px !important;
        }
        /* Forces filters to stack into columns on mobile! */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            margin-bottom: 12px !important;
        }
        /* Stack navigation buttons vertically on small phones for readability */
        .mobile-btn-container {
            flex-direction: column !important;
            height: auto !important;
            gap: 8px !important;
        }
        .mobile-btn-container a {
            width: 100% !important;
            height: 44px !important; /* Touch friendly min-height 44px */
            min-height: 44px !important;
        }
        /* Stack partner row on mobile and stretch button to 100% width! */
        .mobile-partner-container {
            flex-direction: column !important;
            align-items: center !important;
            text-align: center !important;
            gap: 12px !important;
        }
        .mobile-cta-button {
            width: 100% !important;
            height: 44px !important; /* Touch friendly min-height 44px */
            min-height: 44px !important;
        }
    }
    
    /* 📱 2. SMALL SMARTPHONES RESPONSIVENESS OVERRIDES (@media (max-width: 480px)) 📱 */
    @media (max-width: 480px) {
        /* Compress spacing to absolute minimum to fit screen perfectly */
        .block-container {
            padding-left: 12px !important;
            padding-right: 12px !important;
            padding-top: 12px !important;
        }
        
        /* Smaller scaled-down headings */
        .brand-title {
            font-size: 1.5rem !important;
        }
        h1, h2, h3, h4 {
            font-size: 1.15rem !important;
        }
        
        /* 5. Typography: base text inside cards not less than 0.85rem */
        p, span, div, a {
            font-size: 0.85rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# PRE-POPULATE TRACKS DATA WITH NEW METRICS & GAMIFICATION
# ---------------------------------------------------------
def init_tracks():
    if os.path.exists(TRACKS_FILE):
        os.remove(TRACKS_FILE)
        
    real_tracks = [
        {
            "name": "ЛБК «Перекоп» 🏆",
            "city": "Кировская область, Кирово-Чепецк",
            "lat": 58.487645,
            "lon": 49.969925,
            "asphalt_quality": 4, # Updated from 5 to 4 stars!
            "length_km": 5.0, # FIXED: Restored missing length parameter!
            "safety": "🟢 Полностью закрытая",
            "description": "Легендарная профессиональная трасса, где регулярно проходят этапы Кубка России. Крутые спуски, серьезные подъемы и безупречный асфальт.",
            "contributor": "SMM SHAMOV",
            "elevation_drop_m": 110,
            "max_grade_pct": 18,
            "climb_length_m": 1200,
            "difficulty_color": "⚪ Профи (Белая)", # Updated Black -> White for dark map visibility
            "is_verified": True,
            "likes": 124
        },
        {
            "name": "Трасса им. Ларисы Лазутиной (Одинцово)",
            "city": "Московская область, Одинцово",
            "lat": 55.6917,
            "lon": 37.2478,
            "asphalt_quality": 5,
            "length_km": 6.0,
            "safety": "🟢 Полностью закрытая",
            "description": "Превосходная роллерная трасса в сосновом лесу. Имеет тяжелый рабочий рельеф, скоростные спуски со светофорами безопасности. Идеальна для коньковых тренировок.",
            "contributor": "лыжник_одинцово",
            "elevation_drop_m": 75,
            "max_grade_pct": 12,
            "climb_length_m": 800,
            "difficulty_color": "🔴 Сложная (Красная)",
            "is_verified": True,
            "likes": 98
        },
        {
            "name": "УТЦ «Кавголово» (НГУ им. Лесгафта)",
            "city": "Ленинградская область, Токсово",
            "lat": 60.1581,
            "lon": 30.5186,
            "asphalt_quality": 5,
            "length_km": 3.0,
            "safety": "🟢 Полностью закрытая",
            "description": "Профессиональный биатлонный центр. Трасса имеет крутые виражи, отличный накат и жесткие подъемы. Катать рекомендуется только в шлеме!",
            "contributor": "spb_skier",
            "elevation_drop_m": 60,
            "max_grade_pct": 15,
            "climb_length_m": 500,
            "difficulty_color": "⚫ Профи (Белая)", # Updated Black -> White
            "is_verified": True,
            "likes": 84
        },
        {
            "name": "ОЦСП «Жемчужина Сибири»",
            "city": "Тюменская область, Тюмень",
            "lat": 57.0016,
            "lon": 65.2536,
            "asphalt_quality": 5,
            "length_km": 7.5,
            "safety": "🟢 Полностью закрытая",
            "description": "Один из лучших лыжно-биатлонных комплексов мира. Широкая трасса, идеальный асфальт, длинный круг. Подходит для накатывания больших летних объемов.",
            "contributor": "siberia_biathlon",
            "elevation_drop_m": 45,
            "max_grade_pct": 8,
            "climb_length_m": 600,
            "difficulty_color": "🔵 Средняя (Синяя)",
            "is_verified": True,
            "likes": 76
        },
        {
                "name": "ОУСЦ «Планерная» (Химки)",
                "city": "Московская область, Химки",
                "lat": 55.9184,
                "lon": 37.3516,
                "asphalt_quality": 4,
                "length_km": 2.5,
                "safety": "🟢 Полностью закрытая",
                "description": "Хорошая тренировочная трасса на севере Подмосковья. Есть рельеф средней сложности, асфальт рабочий, но местами бывает листва и веточки.",
                "contributor": "msk_skate",
                "elevation_drop_m": 30,
                "max_grade_pct": 7,
                "climb_length_m": 400,
                "difficulty_color": "🔵 Средняя (Синяя)",
                "is_verified": True,
                "likes": 43
        },
        {
            "name": "ЛБК «Ангарский»",
            "city": "Иркутская область, Ангарск",
            "lat": 52.5401,
            "lon": 103.8860,
            "asphalt_quality": 4,
            "length_km": 2.5,
            "safety": "🟢 Полностью закрытая",
            "description": "Хорошая освещенная трасса для тренировок сибиряков. Асфальт качественный, подъемы плавные, подходит для любителей.",
            "contributor": "baikal_skier",
            "elevation_drop_m": 25,
            "max_grade_pct": 5,
            "climb_length_m": 300,
            "difficulty_color": "🔵 Средняя (Синяя)",
            "is_verified": True,
            "likes": 39
        },
        {
            "name": "Парк «Крылатские холмы» (Москва)",
            "city": "Москва, Крылатское",
            "lat": 55.7621,
            "lon": 37.4243,
            "asphalt_quality": 4,
            "length_km": 4.2,
            "safety": "🔴 Открытая дорога",
            "description": "Олимпийская велотрасса. Бешеный рельеф, огромные скорости на спусках. Будьте предельно осторожны — тормозить негде, а на трассе часто гуляют люди!",
            "contributor": "pro_skier_moscow",
            "elevation_drop_m": 120,
            "max_grade_pct": 16,
            "climb_length_m": 1500,
            "difficulty_color": "⚪ Профи (Белая)", # Updated Black -> White
            "is_verified": True,
            "likes": 115
        },
        {
            "name": "Трасса «Ветлужанка»",
            "city": "Красноярск",
            "lat": 56.0125,
            "lon": 92.7483,
            "asphalt_quality": 3,
            "length_km": 3.0,
            "safety": "🟢 Полностью закрытая",
            "description": "Лесная тренировочная трасса. Асфальт местами неровный (крупное зерно), отлично подходит для тренировок на мягком гасящем каучуке Shamov 02-1.",
            "contributor": "krsk_ski",
            "elevation_drop_m": 20,
            "max_grade_pct": 4,
            "climb_length_m": 200,
            "difficulty_color": "🟢 Простая (Зеленая)",
            "is_verified": True,
            "likes": 27
        }
    ]
    df = pd.DataFrame(real_tracks)
    df.to_csv(TRACKS_FILE, index=False, encoding="utf-8")

init_tracks()

def load_tracks():
    df = pd.read_csv(TRACKS_FILE, encoding="utf-8")
    if "is_verified" not in df.columns:
        df["is_verified"] = True
    if "likes" not in df.columns:
        df["likes"] = 0
    return df

tracks_df = load_tracks()

# ---------------------------------------------------------
# CALCULATION ALGORITHM (Ski-Track Color Code Standard)
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
# BASE64 ENCODING FOR LOCAL LOGO (For 100% reliable HTML rendering)
# ---------------------------------------------------------
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return "data:image/png;base64," + base64.b64encode(img_file.read()).decode('utf-8')
    return ""

logo_base64 = get_base64_image("logo.png")

# ---------------------------------------------------------
# MINIMALIST HEADER BAR (Шапка - #0D1117, Bottom border, GRBNV PROD)
# ---------------------------------------------------------
header_html = f"""
<div class="mobile-header-container" style="display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; background-color: #0D1117; border-bottom: 1px solid rgba(255,255,255,0.05); padding: 14px 24px; border-radius: 6px; margin-bottom: 28px;">
    <div style="font-weight: 800; font-size: 1.4rem; visibility: hidden;">Spacer</div> <!-- Left invisible spacer for perfect centering! -->
    <div style="color: #FFFFFF; font-weight: 800; font-size: 1.4rem; font-family: sans-serif; letter-spacing: 0.05em; text-align: center;">GRBNV PROD</div> <!-- Perfectly Centered Title! -->
    <div class="header-sponsor-section" style="display: flex; align-items: center; gap: 12px; justify-content: flex-end;">
        <span style="color: #94A3B8; font-size: 0.8rem; font-weight: 700; font-family: sans-serif; text-transform: uppercase; letter-spacing: 0.08em;">Главный спонсор</span>
        {"<img src='" + logo_base64 + "' style='max-height: 70px; width: auto; object-fit: contain; vertical-align: middle;'>" if logo_base64 else ""} <!-- LARGER 70PX LOGO AS REQUESTED! -->
    </div>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)



# ---------------------------------------------------------
# AUTO-GPS GEOLOCATION PARSER & NOMINATIM COGeocoder
# ---------------------------------------------------------
def extract_coords_from_link(link):
    if not link:
        return None, None
    try:
        # Resolve short URLs by following redirects
        if "yandex.ru/maps/-/" in link or "maps.app.goo.gl" in link or "clck.ru" in link:
            r = requests.head(link, allow_redirects=True, timeout=5)
            link = r.url
            
        # Yandex format: ll=lon%2Clat or ll=lon,lat
        yandex_ll = re.search(r'll=([0-9.]+)(?:%2C|,)([0-9.]+)', link)
        if yandex_ll:
            lon = float(yandex_ll.group(1))
            lat = float(yandex_ll.group(2))
            return lat, lon
            
        # Google format: destination=lat,lon
        google_dest = re.search(r'destination=([0-9.-]+),([0-9.-]+)', link)
        if google_dest:
            lat = float(google_dest.group(1))
            lon = float(google_dest.group(2))
            return lat, lon
            
        # Generic float pair regex (e.g. 55.12345,37.12345)
        coords = re.findall(r'([0-9]{2}\.[0-9]+)', link)
        if len(coords) >= 2:
            lat = float(coords[0])
            lon = float(coords[1])
            if 40 <= lat <= 80 and 19 <= lon <= 180:
                return lat, lon
            elif 40 <= lon <= 80 and 19 <= lat <= 180:
                return lon, lat
    except Exception:
        pass
    return None, None

def geocode_address(address_string):
    try:
        url = "https://nominatim.openstreetmap.org/search"
        headers = {"User-Agent": "ShamovMapApp/1.0"}
        params = {"q": address_string, "format": "json", "limit": 1}
        r = requests.get(url, params=params, headers=headers, timeout=5).json()
        if r:
            return float(r[0]["lat"]), float(r[0]["lon"])
    except Exception:
        pass
    return None, None

# ---------------------------------------------------------
# 1. SIDE-BY-SIDE MAIN LAYOUT (MAP ON LEFT, CARD ON RIGHT)
# ---------------------------------------------------------
# Left column gets 57% width, right column gets 43% width.
col_left, col_right = st.columns([1.3, 1.0], gap="medium")

with col_left:
    st.subheader("🗺️ Живой GPS-Навигатор трасс")
    min_rating = st.slider("⭐ Минимальная оценка асфальта (Оценка: 1/5 - 5/5):", 1, 5, 3, key="asph_min_rating_slider")

# Filter database based on slider rating
filtered_tracks = tracks_df[tracks_df["asphalt_quality"] >= min_rating]

# Initialize selection session state
if "clicked_track_name" not in st.session_state:
    st.session_state.clicked_track_name = ""

with col_left:
    if filtered_tracks.empty:
        st.warning("⚠️ Нет трасс, подходящих под выбранные фильтры. Снизьте требования к асфальту!")
    else:
        try:
            import plotly.express as px
            
            # Map Rendering (Balanced 500px height!)
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
                zoom=3,
                height=500,
                hover_name="name",
                hover_data={
                    "lat": False,
                    "lon": False,
                    "city": True,
                    "length_km": True,
                    "asphalt_quality": True,
                    "difficulty_color": True,
                    "safety": True,
                    "likes": True
                },
                labels={
                    "city": "📍 Регион / Город",
                    "length_km": "📏 Длина круга",
                    "asphalt_quality": "⭐ Оценка асфальта",
                    "difficulty_color": "🏃‍♂️ Сложность",
                    "safety": "🛡️ Безопасность",
                    "likes": "👍 Лайков"
                }
            )
            
            fig_map.update_layout(
                mapbox_style="carto-darkmatter",
                margin={"r":0,"t":0,"l":0,"b":0},
                coloraxis_showscale=False,
                showlegend=False
            )
            
            fig_map.update_traces(marker=dict(size=14))
            
            select_event = st.plotly_chart(
                fig_map, 
                use_container_width=True,
                config={"scrollZoom": True},
                on_select="rerun"
            )
            
            # Process Map Clicks (100% ROBUST COORDINATES & NAME MATCHING LOGIC!)
            if select_event and "selection" in select_event and "points" in select_event["selection"]:
                points = select_event["selection"]["points"]
                if len(points) > 0:
                    clicked_point = points[0]
                    
                    # 1. Try to match by hovertext (track name) directly
                    clicked_name = clicked_point.get("hovertext")
                    if clicked_name and clicked_name in tracks_df["name"].values:
                        st.session_state.clicked_track_name = clicked_name
                    else:
                        # 2. Fallback: match by exact coordinate lat/lon values
                        clicked_lat = clicked_point.get("lat")
                        clicked_lon = clicked_point.get("lon")
                        if clicked_lat is not None and clicked_lon is not None:
                            # Find matching track in tracks_df
                            match = tracks_df[
                                (np.isclose(tracks_df["lat"], clicked_lat, atol=1e-4)) & 
                                (np.isclose(tracks_df["lon"], clicked_lon, atol=1e-4))
                            ]
                            if not match.empty:
                                st.session_state.clicked_track_name = match.iloc[0]["name"]
            
        except Exception as e:
            st.error(f"⚠️ Ошибка при работе графического движка: {str(e)}")

with col_right:
    # ➕ THE ONLY POPOVER FORM ON SCREEN - FIXED THE ID DUPLICATION CRASH!
    with st.popover("➕ Нанести трассу", use_container_width=True):
        st.subheader("📝 Нанести новую трассу")
        st.write("Заполните форму. Координаты определятся автоматически!")
        
        t_name = st.text_input("Название трассы / комплекса *", value="ЛБК «Ангара»", key="add_t_name_pop")
        t_city = st.text_input("Город / Регион *", value="Свердловская область, Екатеринбург", key="add_t_city_pop")
        
        # 🔗 NEW ULTIMATE EASY COORDINATES METHOD (Map link pasting!)
        t_map_link = st.text_input(
            "🔗 Вставьте ссылку на Яндекс.Карты / Google Maps *",
            value="",
            placeholder="Вставьте ссылку-поделиться локацией...",
            help="Откройте Яндекс.Карты на телефоне, нажмите «Поделиться» и скопируйте ссылку сюда!",
            key="add_t_link_pop"
        )
        
        # Advanced manual GPS fallback (completely hidden behind clean expander)
        with st.expander("🌐 Настроить GPS-координаты вручную (Для профи)"):
            t_lat = st.number_input("Широта (Lat)", format="%.5f", value=0.0, key="add_t_lat_pop")
            t_lon = st.number_input("Долгота (Lon)", format="%.5f", value=0.0, key="add_t_lon_pop")
            
        t_asphalt = st.slider("⭐ Качество асфальта (1-5) *", 1, 5, 4, key="add_t_asph_pop")
        t_length = st.number_input("📏 Длина круга (км) *", min_value=0.1, max_value=50.0, value=3.0, step=0.1, key="add_t_len_pop")
        
        st.write("---")
        st.write("#### ⛰️ Характеристики рельефа:")
        t_drop = st.slider("📈 Перепад высот на круге (метров) *", min_value=0, max_value=200, value=35, step=5, key="add_t_drop_pop")
        t_grade = st.slider("📐 Максимальный уклон (%) *", min_value=0, max_value=25, value=6, step=1, key="add_t_grad_pop")
        t_climb_len = st.slider("🏃‍♂️ Максимальная длина подъема (метров) *", 0, 2000, 300, key="add_t_climb_pop")
        
        calculated_color = calculate_difficulty_by_metrics(t_drop, t_grade, t_climb_len)
        st.info(f"Рассчитанная сложность: {calculated_color}")
        
        t_safety = st.selectbox("🛡️ Безопасность *", ["🟢 Полностью закрытая", "🟡 Частично открытая", "🔴 Открытая дорога"], key="add_t_safe_pop")
        t_desc = st.text_area("Советы и описание трассы *", value="Трасса широкая, асфальт уложили в прошлом году. Опасный спуск в районе 2-го километра, будьте аккуратны в дождь.", key="add_t_desc_pop")
        t_contrib = st.text_input("Никнейм в соцсетях (@)", value="лыжник_любитель", key="add_t_cont_pop")
        t_show_nick = st.checkbox("Показать мой ник на карте", value=True, key="add_t_show_pop")
        
        submit_btn = st.button("🔥 ОТПРАВИТЬ ЧЕРНОВИК НА КАРТУ", key="add_t_btn_pop")
        if submit_btn:
            if not t_name or not t_city:
                st.error("Заполните обязательные поля!")
            else:
                final_lat, final_lon = 0.0, 0.0
                
                # 🛠️ AUTOMATED COORDINATES RESOLVER ENGINE
                with st.spinner("Определяем точные GPS-координаты..."):
                    if t_map_link:
                        final_lat, final_lon = extract_coords_from_link(t_map_link)
                    elif t_lat != 0.0 and t_lon != 0.0:
                        final_lat, final_lon = t_lat, t_lon
                        
                    if not final_lat or not final_lon:
                        final_lat, final_lon = geocode_address(f"{t_name}, {t_city}")
                        
                if not final_lat or not final_lon:
                    st.error("❌ Не удалось автоматически определить координаты! Пожалуйста, укажите координаты вручную во вкладке 'Для профи'.")
                else:
                    author_display = t_contrib if t_contrib and t_show_nick else "Анонимный лыжник"
                    new_track = {
                        "name": t_name,
                        "city": t_city,
                        "lat": float(final_lat),
                        "lon": float(final_lon),
                        "asphalt_quality": int(t_asphalt),
                        "length_km": float(t_length),
                        "safety": t_safety,
                        "description": t_desc,
                        "contributor": author_display,
                        "elevation_drop_m": int(t_drop),
                        "max_grade_pct": int(t_grade),
                        "climb_length_m": int(t_climb_len),
                        "difficulty_color": calculated_color,
                        "is_verified": False,
                        "likes": 0
                    }
                    disk_df = pd.read_csv(TRACKS_FILE, encoding="utf-8")
                    disk_df = pd.concat([disk_df, pd.DataFrame([new_track])], ignore_index=True)
                    disk_df.to_csv(TRACKS_FILE, index=False, encoding="utf-8")
                    st.success(f"🎉 Трасса успешно добавлена в базу по координатам {final_lat:.5f}, {final_lon:.5f}! Пройдите верификацию в детальном обзоре.")
                    st.balloons()
                    st.rerun()

    # Sync dropdown selection with map clicks seamlessly!
    track_list = list(filtered_tracks["name"].unique()) if not filtered_tracks.empty else ["-- Нет подходящих трасс --"]

    default_idx = 0
    if st.session_state.clicked_track_name in track_list:
        default_idx = track_list.index(st.session_state.clicked_track_name)
        
    selected_track_name = st.selectbox(
        "🔎 Детальный обзор трассы:",
        options=track_list,
        index=default_idx
    )

    if selected_track_name and selected_track_name != "-- Нет подходящих трасс --":
        track_info = filtered_tracks[filtered_tracks["name"] == selected_track_name].iloc[0]
        
        # Wheel compatibility advice
        asphalt_val = int(track_info['asphalt_quality'])
        if asphalt_val == 5:
            wheel_recommendation = "🚀 <b>Профи-накат:</b> Идеальный асфальт! Для отличной скорости и износостойкости рекомендуем наши топовые карбоновые модели <code>Shamov 04-3PU (карбон)</code> или полиуретановые колеса на алюминиевых дисках <code>Shamov 04-2</code> (100 мм)."
        elif asphalt_val == 4:
            wheel_recommendation = "⚡ <b>Отличный баланс:</b> Трасса позволяет отлично кататься как на полиуретане <code>Shamov 04-2</code>, так и на мягком каучуке <code>Shamov 04-1 (100 мм)</code> или профессиональных карбоновых <code>Shamov 04-3R (карбон)</code> для безупречного гашения вибраций."
        else:
            wheel_recommendation = "🔧 <b>Амортизация вибрации:</b> Настоятельно рекомендуем мягкие резиновые колеса <code>Shamov 02-1</code> или классику <code>05 Elpex</code> для защиты суставов."

        # Define custom outline color depending on difficulty (No solid backgrounds!)
        diff_color_hex = "#EF4444"
        if "Зеленая" in track_info['difficulty_color']:
            diff_color_hex = "#10B981"
        elif "Синяя" in track_info['difficulty_color']:
            diff_color_hex = "#3B82F6"
        elif "Белая" in track_info['difficulty_color']:
            diff_color_hex = "#FFFFFF"

        # 🌟 HIGH-CONTRAST GORGEOUS HIGH-TECH SPOTLIGHT CARD (HTML block, zero indent, transparent border lights, 6px border radius, line-height 1.6) 🌟
        html_card = f"""<div class="html-spotlight-card" style="background-color: #0D1117; border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 16px; box-shadow: none;">
<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
<div>
<h3 style="margin: 0; color: #FFFFFF !important; font-size: 1.6rem; font-weight: 800; font-family: sans-serif; letter-spacing: -0.01em;">{track_info['name']}</h3>
<p style="color: #94A3B8; font-size: 0.95rem; margin: 0.1rem 0 0 0; font-family: sans-serif;">📍 {track_info['city']}</p>
</div>
<!-- Minimalist outline badge (6px border-radius) -->
<div style="border: 1px solid {diff_color_hex}; color: {diff_color_hex}; padding: 4px 12px; border-radius: 6px; font-weight: bold; font-size: 0.75rem; text-transform: uppercase; font-family: sans-serif; box-shadow: none;">
{track_info['difficulty_color']}
</div>
</div>
<div class="html-card-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.75rem; margin-top: 0.85rem; margin-bottom: 0.85rem;">
<div style="background-color: #0B0F14; border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 0.65rem; text-align: center;">
<div style="color: #94A3B8; font-size: 0.75rem; font-weight: bold; font-family: sans-serif; letter-spacing: 0.02em;"><i class="fa-solid fa-route" style="color: #94A3B8;"></i> ДЛИНА КРУГА</div>
<div style="color: #FFFFFF; font-size: 1.3rem; font-weight: 800; font-family: sans-serif; margin-top: 0.2rem;">{track_info['length_km']} км</div>
</div>
<div style="background-color: #0B0F14; border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 0.65rem; text-align: center;">
<div style="color: #94A3B8; font-size: 0.75rem; font-weight: bold; font-family: sans-serif; letter-spacing: 0.02em;"><i class="fa-solid fa-mountain" style="color: #94A3B8;"></i> ПЕРЕПАД / УКЛОН</div>
<div style="color: #FFFFFF; font-size: 1.1rem; font-weight: 800; font-family: sans-serif; margin-top: 0.25rem;">{int(track_info['elevation_drop_m'])}м / {int(track_info['max_grade_pct'])}%</div>
</div>
<div style="background-color: #0B0F14; border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 0.65rem; text-align: center;">
<div style="color: #94A3B8; font-size: 0.75rem; font-weight: bold; font-family: sans-serif; letter-spacing: 0.02em;"><i class="fa-solid fa-shield-halved" style="color: #94A3B8;"></i> БЕЗОПАСНОСТЬ</div>
<div style="color: #FFFFFF; font-size: 0.85rem; font-weight: bold; margin-top: 0.4rem; font-family: sans-serif;">{track_info['safety']}</div>
</div>
<div style="background-color: #0B0F14; border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 0.65rem; text-align: center;">
<div style="color: #94A3B8; font-size: 0.75rem; font-weight: bold; font-family: sans-serif; letter-spacing: 0.02em;"><i class="fa-solid fa-user-check" style="color: #94A3B8;"></i> ДОБАВИЛ</div>
<div style="color: #34D399; font-size: 0.85rem; font-weight: bold; margin-top: 0.35rem; font-family: sans-serif;">@{track_info['contributor']}</div>
</div>
</div>

<!-- 🌟 COMBINED UNIFIED ADVICE & RECOMMENDATION CONTAINER (Massively saves vertical space, line-height 1.6!) 🌟 -->
<div style="background-color: #0B0F14; border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 12px; margin-bottom: 0.5rem; line-height: 1.6;">
<p style="color: #F1F5F9; font-size: 0.95rem; margin: 0 0 8px 0; font-family: sans-serif;"><b>📝 Совет эксперта SHAMOV:</b> \"{track_info['description']}\"</p>
<p style="color: #E2E8F0; font-size: 0.9rem; margin: 0; font-family: sans-serif;"><i class="fa-solid fa-circle-info" style="color: #94A3B8;"></i> {wheel_recommendation}</p>
</div>

<!-- 🗺️ BRAND NEW ROUTING BUTTONS ROW (Equal 40px height, single row, adaptive desktop/mobile, 6px radius) 🗺️ -->
<div class="mobile-btn-container" style="display: flex; gap: 10px; margin-top: 0.85rem; height: 40px;">
<a href="https://yandex.ru/maps/?rtext=~{track_info['lat']},{track_info['lon']}&rtt=auto" target="_blank" style="flex: 1; height: 40px; display: flex; align-items: center; justify-content: center; background-color: #0B0F14; border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; color: #E2E8F0; text-decoration: none; font-size: 0.8rem; font-weight: 700; font-family: sans-serif; transition: background-color 0.15s;"><i class="fa-solid fa-location-arrow" style="color: #94A3B8; margin-right: 8px;"></i> Проложить в Яндекс.Картах</a>
<a href="https://www.google.com/maps/dir/?api=1&destination={track_info['lat']},{track_info['lon']}" target="_blank" style="flex: 1; height: 40px; display: flex; align-items: center; justify-content: center; background-color: #0B0F14; border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; color: #E2E8F0; text-decoration: none; font-size: 0.8rem; font-weight: 700; font-family: sans-serif; transition: background-color 0.15s;"><i class="fa-solid fa-map-pin" style="color: #94A3B8; margin-right: 8px;"></i> Проложить в Google Картах</a>
</div>

<!-- 📦 SEPARATED PARTNER SECTION WITH ORDER WHEELS CTA (6px border radius, line-height 1.6, full width on mobile) 📦 -->
<hr style="border: none; border-top: 1px solid rgba(255,255,255,0.05); margin: 16px 0 12px 0 !important;">
<div class="mobile-partner-container" style="display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-top: 12px;">
    <div style="display: flex; align-items: center; gap: 8px;">
        <span style="color: #94A3B8; font-size: 0.8rem; font-weight: 700; font-family: sans-serif; text-transform: uppercase; letter-spacing: 0.08em;"><i class="fa-solid fa-handshake" style="color: #94A3B8; margin-right: 4px;"></i> Официальный партнёр</span>
    </div>
    <a href="https://shamov-russia.ru/" target="_blank" class="mobile-cta-button" style="height: 40px; padding: 0 20px; display: inline-flex; align-items: center; justify-content: center; background-color: #EF4444; border-radius: 6px; color: #FFFFFF; text-decoration: none; font-size: 0.85rem; font-weight: 800; font-family: sans-serif; text-transform: uppercase; letter-spacing: 0.05em; transition: background-color 0.15s; box-shadow: none;">Заказать колёса</a>
</div>

</div>"""
        st.markdown(html_card, unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. SECRET MODERATION ADMIN PANEL (CHAMPION SMM FEATURE!)
# ---------------------------------------------------------
st.write("---")
col_foo_left, col_foo_right = st.columns([4, 1.2])

with col_foo_right:
    # Hidden expander for entering moderation password (6px border radius, 1px solid border)
    with st.expander("🛠️ Модерация базы (для SMM)"):
        # 🔒 SECURE PASSWORD LOADING FROM STREAMLIT SECRETS (Hidden from GitHub!)
        # On local PC, fallback to "shamov2026". In Streamlit Cloud, configured in "Secrets" panel securely.
        try:
            SECURE_PASSWORD = st.secrets.get("admin_password", "shamov2026")
        except Exception:
            SECURE_PASSWORD = "shamov2026"
        
        admin_pass = st.text_input("Введите пароль модератора:", type="password", key="sec_admin_pass")
        st.caption("ℹ️ *После ввода пароля просто нажмите **Enter** на клавиатуре для входа.*")
        if admin_pass == SECURE_PASSWORD:
            st.success("Доступ разрешен!")
            # Find all unverified drafts
            unverified_df = tracks_df[tracks_df["is_verified"] == False]
            if unverified_df.empty:
                st.info("🎉 Все трассы проверены! Новых черновиков нет.")
            else:
                st.write("📋 **Новые черновики на проверку:**")
                for idx, row in unverified_df.iterrows():
                    st.write(f"📍 **{row['name']}** ({row['city']})")
                    st.write(f"📏 {row['length_km']}км | {row['difficulty_color']} | Ссылка: {row['lat']},{row['lon']}")
                    
                    col_adm_b1, col_adm_b2 = st.columns(2)
                    with col_adm_b1:
                        if st.button("✅ Одобрить", key=f"adm_ok_{row['name']}"):
                            # Update in CSV
                            disk_df = pd.read_csv(TRACKS_FILE, encoding="utf-8")
                            f_idx = disk_df[disk_df["name"] == row["name"]].index
                            if not f_idx.empty:
                                disk_df.loc[f_idx[0], "is_verified"] = True
                                disk_df.to_csv(TRACKS_FILE, index=False, encoding="utf-8")
                                st.success(f"Одобрено!")
                                st.rerun()
                    with col_adm_b2:
                        if st.button("❌" + "  Удалить", key=f"adm_del_{row['name']}"):
                            # Delete from CSV
                            disk_df = pd.read_csv(TRACKS_FILE, encoding="utf-8")
                            disk_df = disk_df[disk_df["name"] != row["name"]]
                            disk_df.to_csv(TRACKS_FILE, index=False, encoding="utf-8")
                            st.warning(f"Удалено!")
                            st.rerun()

st.markdown("""
<div style="text-align: center; color: #475569; font-size: 0.8rem; padding: 10px 0;">
    Проект Разработан специально для SMM-службы Производственно-торговой фирмы «ШАМОВ» © 2026
    <br>Киров • 15 лет качества спортивного инвентаря по доступной цене.
</div>
""", unsafe_allow_html=True)
