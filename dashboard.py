import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
from calendar import monthrange
from pathlib import Path
import io
import re

# ============ CONFIGURACIÓN DE PÁGINA ============
st.set_page_config(
    page_title="Importaciones de Maquinaria Pesada - Dashboard",
    page_icon="🚜",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============ CONSTANTES ============
COLOR_PRIMARY = '#FFD700'
COLOR_SECONDARY = '#FFA500'
COLOR_DARK = '#3D2E00'
COLOR_ACCENT = '#8B7500'
COLOR_BG = '#FFF8E1'
COLOR_WHITE = '#FFFFFF'

COLOR_ACTUAL = '#2E8B57'
COLOR_ANTERIOR = '#1E448A'
COLOR_NH = '#FF8C00'
COLOR_PALETTE = ['#1E448A', '#2E8B57', '#4A90E2', '#34495E', '#50C878', 
                 '#D98880', '#A9CCE3', '#F39C12', '#9B59B6', '#FF8C00']

MESES_NOMBRES = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
CAT_REQUERIDAS = ["MINICARGADOR FRONTAL", "CARGADOR FRONTAL", "RETROEXCAVADORA", 
                  "EXCAVADORA", "BULLDOZER", "COMPACTADOR", "MOTONIVELADORA"]
MARCA_PROPIA = "NEW HOLLAND"
IMPORTADOR_PROPIO = "WITHMORY"

MAPEO_COLUMNAS = {
    'marca_norm': ['marca_norm', 'marca_normalizada'],
    'modelo': ['modelo_match', 'modelo'],
    'categoria_peso': ['categoria_peso', 'rango_peso', 'capacidad'],
    'grupo_importador': ['grupo_importador', 'importador_grupo', 'importador'],
    'valor_fob': ['valor_fob', 'fob', 'fob_usd'],
    'valor_cif': ['valor_cif', 'cif', 'cif_usd']
}

# ============ FUNCIONES AUXILIARES FALTANTES ============
def seleccionar_todos_pesos():
    """Selecciona todos los pesos disponibles"""
    if 'pesos_disp' in st.session_state:
        for p in st.session_state['pesos_disp']:
            st.session_state[f"peso_{p}"] = True

def limpiar_pesos():
    """Limpia la selección de pesos"""
    if 'pesos_disp' in st.session_state:
        for p in st.session_state['pesos_disp']:
            st.session_state[f"peso_{p}"] = False

# ============ ESTILOS CSS ============
def cargar_css():
    st.markdown("""
    <style>
        /* ===== GLOBAL ===== */
        .block-container { 
            padding: 0.5rem 1.5rem !important; 
            max-width: 100% !important; 
        }
        .main { 
            background-color: #F5F5F5; 
        }
        
        /* ===== OCULTAR SIDEBAR ===== */
        [data-testid="stSidebar"], 
        [data-testid="collapsedControl"] { 
            display: none; 
        }

        /* ===== ESTILOS DEL HEADER HORIZONTAL ===== */
        .top-header-title {
            font-size: 2.2rem;
            font-weight: 800;
            color: #1A1A1A;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .top-header-subtitle {
            font-size: 0.95rem;
            color: #444444;
            margin-top: 4px;
            margin-bottom: 20px;
            font-weight: 500;
        }
        .date-label {
            font-size: 0.85rem;
            color: #555555;
            font-weight: 700;
            margin-bottom: 5px;
            text-transform: uppercase;
        }
        
        /* Ajustes para selects en header */
        .stSelectbox > div {
            margin-bottom: 0 !important;
        }
        .stSelectbox [data-baseweb="select"] {
            min-height: 30px !important;
        }
        .stSelectbox [data-baseweb="select"] > div {
            padding-top: 0px !important;
            padding-bottom: 0px !important;
        }
        .stColumn {
            gap: 0px !important;
        }
        
        /* ===== HACER EL MULTISELECT MÁS GRANDE Y BLANCO ===== */
        div[data-testid="stMultiSelect"] > div {
            min-height: 48px !important;
            background-color: #FFFFFF !important;
            border-radius: 8px !important;
        }
        
        /* Unifica el fondo de la fila inferior (Dark Box) */
        div[data-testid="stHorizontalBlock"]:has(.kpi-row-marker) {
            background-color: #262626;
            padding: 20px 25px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            margin-bottom: 20px;
            align-items: center;
        }
        
        /* Forzar textos claros dentro del Dark Box para widgets nativos */
        div[data-testid="stHorizontalBlock"]:has(.kpi-row-marker) label,
        div[data-testid="stHorizontalBlock"]:has(.kpi-row-marker) .stMarkdown p {
            color: #AAAAAA !important;
            font-size: 0.75rem;
        }

        /* Contenedor KPI Transparente (hereda el fondo de la fila) */
        .kpi-container-transparent {
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            text-align: center;
            width: 100%;
        }
        .kpi-box { 
            flex: 1; 
            border-right: 1px solid rgba(255, 255, 255, 0.1); 
            padding: 0 15px;
        }
        .kpi-box:last-child { 
            border-right: none; 
        }
        .kpi-title { 
            font-size: 0.85rem; 
            color: #CCCCCC; 
            font-weight: 700; 
            text-transform: uppercase; 
            letter-spacing: 0.5px;
        }
        .kpi-subtitle { 
            font-size: 0.75rem; 
            color: #999999; 
            display: block; 
            margin-top: 2px; 
        }
        .kpi-value { 
            font-size: 1.9rem; 
            color: #FFFFFF; 
            font-weight: 800; 
            margin-top: 8px; 
        }
        .kpi-var-up { 
            color: #4CAF50; 
            font-weight: 800; 
            font-size: 1.9rem; 
            margin-top: 8px; 
        }
        .kpi-var-down { 
            color: #FF5252; 
            font-weight: 800; 
            font-size: 1.9rem; 
            margin-top: 8px; 
        }
        
        /* ===== SECCIONES ===== */
        .section-header { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            background: linear-gradient(90deg, #2D2D2D 0%, #1A1A1A 100%);
            color: white; 
            padding: 10px 15px; 
            border-radius: 8px; 
            margin-bottom: 15px; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            border: 1px solid #333;
        }
        .section-title-text { 
            font-size: 0.9rem; 
            font-weight: 600; 
            margin: 0; 
            letter-spacing: 0.3px;
        }
        
        /* ===== DIVISORES ===== */
        .section-divider {
            border: 0;
            height: 2px;
            background: linear-gradient(90deg, #333 0%, #555 50%, #333 100%);
            margin: 25px 0;
            border-radius: 2px;
        }
        
        /* ===== INSIGHTS ===== */
        .insight-card {
            background: white;
            border-left: 4px solid #FFD700;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .insight-positive { border-left-color: #4CAF50; }
        .insight-warning { border-left-color: #FFA500; }
        .insight-danger { border-left-color: #FF5252; }
        .insight-info { border-left-color: #FFD700; }
        
        .insight-title {
            font-size: 0.85rem;
            font-weight: 700;
            color: #1A1A1A;
            margin-bottom: 5px;
        }
        .insight-text {
            font-size: 0.8rem;
            color: #555;
            line-height: 1.5;
        }
        
        /* ===== TABS ===== */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #FFFFFF;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #E0E0E0;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: #F5F5F5;
            border-radius: 6px;
            padding: 8px 16px;
            color: #1A1A1A;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #1A1A1A, #2D2D2D) !important;
            color: #FFFFFF !important;
        }
        
        /* Botón refrescar */
        button[kind="secondary"] {
            background-color: #F0F0F0 !important;
            border-radius: 8px !important;
            transition: all 0.3s ease !important;
        }
        button[kind="secondary"]:hover {
            background-color: #FFD700 !important;
            transform: scale(1.05) !important;
        }
    </style>
    """, unsafe_allow_html=True)

cargar_css()

# ============ FUNCIONES HELPER ============
def destacar_fila_nh(row):
    """Resalta filas de New Holland y totales"""
    if COL_MARCA in row.index and row[COL_MARCA] == MARCA_PROPIA:
        return ['background-color: #FFF8E1; font-weight: bold;'] * len(row)
    if 'Actor Comercial' in row.index and row['Actor Comercial'] == MARCA_PROPIA:
        return ['background-color: #FFF8E1; font-weight: bold;'] * len(row)
    if 'Marca' in row.index and row['Marca'] == MARCA_PROPIA:
        return ['background-color: #FFF8E1; font-weight: bold;'] * len(row)
    if 'mes_nombre' in row.index and row['mes_nombre'] == 'TOTAL YTD':
        return ['background-color: #E0E0E0; font-weight: bold;'] * len(row)
    return [''] * len(row)

def extraer_peso_numerico(val):
    """Extrae valor numérico del peso"""
    nums = re.findall(r'\d+', str(val))
    return float(nums[0]) if nums else 0.0

def normalizar_columnas(df, mapeo):
    """Normaliza nombres de columnas según mapeo"""
    df = df.copy()
    for nombre_estandar, posibles_nombres in mapeo.items():
        for nombre in posibles_nombres:
            if nombre in df.columns:
                if nombre != nombre_estandar:
                    df = df.rename(columns={nombre: nombre_estandar})
                break
    return df

def aplicar_filtros(df, cat_sel):
    """Aplica filtros de categoría"""
    if cat_sel: 
        df = df[df['categoria_maquinaria'].isin(cat_sel)]
    return df

def calc_var(row, col_act, col_ant):
    """Calcula variación porcentual"""
    ant = row[col_ant]
    act = row[col_act]
    if ant == 0: 
        return "+100%" if act > 0 else "0%"
    return f"{((act - ant) / ant * 100):+.1f}%"

@st.cache_data
def descargar_excel_cache(df_tuple, nombre_hoja="Datos"):
    """Prepara descarga Excel desde caché"""
    df = pd.DataFrame(df_tuple)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=nombre_hoja, index=False)
    return output.getvalue()

def descargar_csv(df):
    """Prepara descarga CSV"""
    return df.to_csv(index=False).encode('utf-8')

def generar_insights_ejecutivos(df_actual, df_anterior, total_actual, total_anterior):
    """Genera insights automáticos del período"""
    insights = []
    
    # Insight de variación del mercado
    if total_anterior > 0:
        var_mercado = ((total_actual - total_anterior) / total_anterior) * 100
        if var_mercado > 10:
            insights.append({
                'tipo': 'positive', 
                'titulo': '📈 Mercado en Expansión', 
                'texto': f'El mercado total creció {var_mercado:+.1f}% respecto al año anterior, alcanzando {total_actual:,} unidades importadas.'
            })
        elif var_mercado < -10:
            insights.append({
                'tipo': 'danger', 
                'titulo': '📉 Contracción del Mercado', 
                'texto': f'El mercado total se contrajo {var_mercado:+.1f}% respecto al año anterior, con {total_actual:,} unidades importadas.'
            })
        else:
            insights.append({
                'tipo': 'info', 
                'titulo': '📊 Mercado Estable', 
                'texto': f'El mercado muestra una variación moderada de {var_mercado:+.1f}% respecto al año anterior.'
            })
    
    # Insight de segmento más dinámico
    if not df_actual.empty and not df_anterior.empty:
        seg_act = df_actual['categoria_maquinaria'].value_counts()
        seg_ant = df_anterior['categoria_maquinaria'].value_counts()
        mayor_crecimiento = None
        mayor_var = 0
        for seg in seg_act.index:
            act = seg_act.get(seg, 0)
            ant = seg_ant.get(seg, 0)
            if ant > 0:
                var = ((act - ant) / ant) * 100
                if var > mayor_var and act >= 10:
                    mayor_var = var
                    mayor_crecimiento = seg
        if mayor_crecimiento:
            insights.append({
                'tipo': 'positive', 
                'titulo': f'🚀 Segmento Más Dinámico: {mayor_crecimiento}', 
                'texto': f'Este segmento creció {mayor_var:+.1f}% respecto al año anterior, destacando como el de mayor aceleración.'
            })
    
    # Insight de New Holland
    if COL_MARCA in df_actual.columns and MARCA_PROPIA in df_actual[COL_MARCA].values:
        nh_act = len(df_actual[df_actual[COL_MARCA] == MARCA_PROPIA])
        nh_ant = len(df_anterior[df_anterior[COL_MARCA] == MARCA_PROPIA]) if COL_MARCA in df_anterior.columns and MARCA_PROPIA in df_anterior[COL_MARCA].values else 0
        if nh_ant > 0:
            var_nh = ((nh_act - nh_ant) / nh_ant) * 100
            share_act = (nh_act / total_actual * 100) if total_actual > 0 else 0
            if var_nh > 0:
                insights.append({
                    'tipo': 'positive', 
                    'titulo': f'🟡 {MARCA_PROPIA} en Crecimiento', 
                    'texto': f'{MARCA_PROPIA} registró {nh_act:,} unidades ({var_nh:+.1f}% vs año anterior) con un market share del {share_act:.1f}%.'
                })
            else:
                insights.append({
                    'tipo': 'warning', 
                    'titulo': f'🟡 {MARCA_PROPIA} Requiere Atención', 
                    'texto': f'{MARCA_PROPIA} registró {nh_act:,} unidades ({var_nh:+.1f}% vs año anterior). Market share actual: {share_act:.1f}%.'
                })
    
    # Insight de marca líder
    if not df_actual.empty and COL_MARCA in df_actual.columns:
        top_marca = df_actual[COL_MARCA].value_counts().head(1)
        if not top_marca.empty:
            marca_dom = top_marca.index[0]
            unidades_dom = top_marca.values[0]
            share_dom = (unidades_dom / total_actual * 100) if total_actual > 0 else 0
            insights.append({
                'tipo': 'info', 
                'titulo': f'👑 Marca Líder: {marca_dom}', 
                'texto': f'Domina el mercado con {unidades_dom:,} unidades y un market share del {share_dom:.1f}% en el período actual.'
            })
    
    # Insight de precio FOB
    if COL_FOB and COL_FOB in df_actual.columns and df_actual[COL_FOB].sum() > 0:
        precio_prom = df_actual[COL_FOB].mean()
        if not df_anterior.empty and COL_FOB in df_anterior.columns and df_anterior[COL_FOB].sum() > 0:
            precio_ant = df_anterior[COL_FOB].mean()
            var_precio = ((precio_prom - precio_ant) / precio_ant) * 100
            if abs(var_precio) > 5:
                insights.append({
                    'tipo': 'warning' if var_precio > 0 else 'positive', 
                    'titulo': f'💰 Precio FOB Promedio: ${precio_prom:,.0f}', 
                    'texto': f'El precio FOB promedio varió {var_precio:+.1f}% respecto al año anterior (${precio_ant:,.0f}).'
                })
    
    return insights[:6]

def render_bloque(titulo, fig, df_tabla, key_seccion, nombre_descarga="datos", col_config_table=None):
    """Renderiza un bloque estándar con gráfico y tabla"""
    raw_df = df_tabla.data if hasattr(df_tabla, 'data') else df_tabla
    
    col_h1, col_h2 = st.columns([6, 1])
    with col_h1:
        st.markdown(f'<div class="section-header"><p class="section-title-text">{titulo}</p></div>', unsafe_allow_html=True)
    with col_h2:
        with st.popover("📥 Exportar", use_container_width=True):
            col_xlsx, col_csv = st.columns(2)
            with col_xlsx:
                try:
                    excel_data = descargar_excel_cache(tuple(raw_df.itertuples(index=False)), nombre_descarga[:30])
                    st.download_button("Excel", data=excel_data, file_name=f"{nombre_descarga}.xlsx", key=f"xlsx_{key_seccion}", use_container_width=True)
                except Exception:
                    st.warning("Excel no disponible")
            with col_csv:
                try:
                    st.download_button("CSV", data=descargar_csv(raw_df), file_name=f"{nombre_descarga}.csv", key=f"csv_{key_seccion}", use_container_width=True)
                except Exception:
                    st.warning("CSV no disponible")
    
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True, 'displaylogo': False})
    
    with st.expander("📊 Ver tabla de datos", expanded=False):
        if col_config_table:
            st.dataframe(df_tabla, hide_index=True, use_container_width=True, column_config=col_config_table)
        else:
            st.dataframe(df_tabla, hide_index=True, use_container_width=True)

# ============ CARGA DE DATOS ============
@st.cache_data(ttl=3600)
def cargar_y_transformar_datos():
    """Carga y transforma los datos desde parquet o Excel"""
    ruta_parquet = Path(__file__).parent / 'datos_maquinaria.parquet'
    if ruta_parquet.exists():
        df = pd.read_parquet(ruta_parquet)
        ultima_actualizacion = ruta_parquet.stat().st_mtime
    else:
        ruta_outputs = Path(__file__).parent / 'outputs'
        files = sorted(ruta_outputs.glob('*_normalizado.xlsx'))
        if not files: 
            return pd.DataFrame(), None, False
        dfs = []
        for f in files:
            try: 
                dfs.append(pd.read_excel(f, sheet_name='normalizado_final'))
            except Exception: 
                pass
        if not dfs: 
            return pd.DataFrame(), None, False
        df = pd.concat(dfs)
        ultima_actualizacion = max(f.stat().st_mtime for f in files)
    
    if 'fecha_dua' not in df.columns: 
        return pd.DataFrame(), None, True
    
    # Transformaciones
    df['fecha'] = pd.to_datetime(df['fecha_dua'])
    df['año'] = df['fecha'].dt.year
    df['mes'] = df['fecha'].dt.month
    df['mes_nombre'] = df['mes'].map({i+1: m for i, m in enumerate(MESES_NOMBRES)})
    df = normalizar_columnas(df, MAPEO_COLUMNAS)
    if df.columns.duplicated().any(): 
        df = df.loc[:, ~df.columns.duplicated()]
    
    # Limpieza de texto
    columnas_texto = ['categoria_maquinaria', 'marca_norm', 'modelo', 'grupo_importador', 'categoria_peso']
    for col in columnas_texto:
        if col in df.columns:
            try:
                serie = df[col].iloc[:, 0] if isinstance(df[col], pd.DataFrame) else df[col]
                df[col] = serie.astype(str).str.upper().str.strip()
                df[col] = df[col].replace(['NAN', 'NONE', 'NULL', '', ' '], pd.NA)
            except Exception: 
                pass
    
    # Conversión de valores numéricos
    if 'valor_fob' in df.columns:
        df['valor_fob'] = pd.to_numeric(df['valor_fob'], errors='coerce').fillna(0)
        # Valores < $5,000 son partes/repuestos, no maquinaria completa — se excluyen de promedios
        df.loc[df['valor_fob'] < 5000, 'valor_fob'] = pd.NA
    if 'valor_cif' in df.columns:
        df['valor_cif'] = pd.to_numeric(df['valor_cif'], errors='coerce').fillna(0)
        df.loc[df['valor_cif'] < 5000, 'valor_cif'] = pd.NA
    
    # Categorización
    for col in ['categoria_maquinaria', 'marca_norm', 'grupo_importador']:
        if col in df.columns: 
            df[col] = df[col].astype('category')
    
    return df, ultima_actualizacion, False

# Cargar datos
df, ULTIMA_ACTUALIZACION, falta_columna = cargar_y_transformar_datos()
if df.empty:
    st.error("No se encontraron datos procesables. Verifique la fuente de datos.")
    st.stop()

# Configurar columnas principales
COL_MARCA = 'marca_norm' if 'marca_norm' in df.columns else 'marca'
COL_MODELO = 'modelo'
COL_PESO = 'categoria_peso' if 'categoria_peso' in df.columns else None
COL_FOB = 'valor_fob' if 'valor_fob' in df.columns else None
COL_CIF = 'valor_cif' if 'valor_cif' in df.columns else None

# ============ FILA 1: HEADER HORIZONTAL CON FILTROS ============
años_disp = sorted(df['año'].dropna().unique())
cats_disp = sorted([c for c in df['categoria_maquinaria'].unique() if c in CAT_REQUERIDAS])

# Espaciado superior
st.markdown('<div style="padding-top: 8px;"></div>', unsafe_allow_html=True)

# Estructura de columnas: Título | Desde | Hasta | Botón
col_titulo, col_desde, col_hasta, col_btn = st.columns([2.8, 0.9, 0.9, 0.4])

# ===== COLUMNA 1: DESDE =====
with col_desde:
    st.markdown('<div style="padding-bottom: 4px;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 0.6rem; color: #888; font-weight: 700; margin-bottom: 2px;">📅 Desde</div>', unsafe_allow_html=True)
    col_mes1, col_anio1 = st.columns([1, 1.1], gap="small")
    with col_mes1:
        mes_ini = st.selectbox("Mes inicio", MESES_NOMBRES, index=0, label_visibility="collapsed", key="mes_ini")
    with col_anio1:
        año_ini = st.selectbox("Año inicio", años_disp, index=len(años_disp)-1, label_visibility="collapsed", key="año_ini")

# ===== COLUMNA 2: HASTA =====
with col_hasta:
    st.markdown('<div style="padding-bottom: 4px;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 0.6rem; color: #888; font-weight: 700; margin-bottom: 2px;">📅 Hasta</div>', unsafe_allow_html=True)
    col_mes2, col_anio2 = st.columns([1, 1.1], gap="small")
    with col_mes2:
        mes_fin = st.selectbox("Mes fin", MESES_NOMBRES, index=len(MESES_NOMBRES)-1, label_visibility="collapsed", key="mes_fin")
    with col_anio2:
        año_fin = st.selectbox("Año fin", años_disp, index=len(años_disp)-1, label_visibility="collapsed", key="año_fin")

# ===== COLUMNA 3: TÍTULO =====
with col_titulo:
    st.markdown(f"""
    <div>
        <h1 style="font-size: 1.6rem; font-weight: 800; color: #1A1A1A; margin: 0;">📊 Importaciones de Maquinaria</h1>
        <div style="font-size: 0.7rem; color: #666;">
            Fuente: <strong>Veritrade</strong> | Período: <strong>{mes_ini} {año_ini} - {mes_fin} {año_fin}</strong> | vs {mes_ini} {año_ini-1} - {mes_fin} {año_fin-1}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ===== COLUMNA 4: BOTÓN =====
with col_btn:
    st.markdown('<div style="height: 32px;"></div>', unsafe_allow_html=True)
    if st.button("🔄", use_container_width=True, key="btn_refresh", help="Actualizar datos"):
        st.cache_data.clear()
        st.rerun()

# Espaciado inferior
st.markdown('<div style="padding-bottom: 4px;"></div>', unsafe_allow_html=True)

# ============ CÁLCULOS DE FECHAS Y DATOS ============
mes_ini_num = MESES_NOMBRES.index(mes_ini) + 1
mes_fin_num = MESES_NOMBRES.index(mes_fin) + 1
año_limite_inf = min(años_disp)

_, last_day_fin = monthrange(año_fin, mes_fin_num)
f_inicio = pd.Timestamp(año_ini, mes_ini_num, 1, 0, 0, 0)
f_fin = pd.Timestamp(año_fin, mes_fin_num, last_day_fin, 23, 59, 59)

f_inicio_ant = pd.Timestamp(año_ini - 1, mes_ini_num, 1, 0, 0, 0)
_, last_day_fin_ant = monthrange(año_fin - 1, mes_fin_num)
f_fin_ant = pd.Timestamp(año_fin - 1, mes_fin_num, last_day_fin_ant, 23, 59, 59)

# Filtro temporal base
df_actual = df[(df['fecha'] >= f_inicio) & (df['fecha'] <= f_fin)]
df_anterior = df[(df['fecha'] >= f_inicio_ant) & (df['fecha'] <= f_fin_ant)]
df_base = df[(df['año'] >= año_limite_inf) & (df['año'] <= año_fin)]

# Aviso de mes con datos parciales
_ultima_fecha = df['fecha'].max()
_anio_ult, _mes_ult, _dia_ult = _ultima_fecha.year, _ultima_fecha.month, _ultima_fecha.day
_, _dias_en_mes = monthrange(_anio_ult, _mes_ult)
if _dia_ult < _dias_en_mes and año_fin == _anio_ult and mes_fin_num >= _mes_ult:
    st.warning(
        f"**Datos parciales:** {MESES_NOMBRES[_mes_ult-1]} {_anio_ult} solo tiene registros hasta el {_dia_ult}/{_mes_ult:02d}/{_anio_ult} "
        f"({_dia_ult} de {_dias_en_mes} días). Los totales de ese mes no son comparables con meses completos.",
        icon="⚠️"
    )

# ============ FILA 2: MULTISELECT & KPIs (DARK BOX) ============
col_seg, col_kpis = st.columns([1.8, 3.2])

with col_seg:
    st.markdown('<div class="kpi-row-marker"></div>', unsafe_allow_html=True)
    st.caption("SEGMENTOS")
    cat_sel = st.multiselect(
        "Segmentos", 
        cats_disp, 
        default=cats_disp, 
        label_visibility="collapsed", 
        key="cat_sel"
    )
    st.markdown('<div style="padding-bottom: 4px;"></div>', unsafe_allow_html=True)

# Filtros Globales Categóricos
df_actual = aplicar_filtros(df_actual, cat_sel)
df_anterior = aplicar_filtros(df_anterior, cat_sel)
df_base = aplicar_filtros(df_base, cat_sel)

total_actual = len(df_actual)
total_anterior = len(df_anterior)
var_pct = ((total_actual - total_anterior) / total_anterior * 100) if total_anterior > 0 else None

# Proyección Ajustada por Días
dias_transcurridos = (f_fin - f_inicio).days + 1
dias_totales_anio = 365 if año_fin % 4 != 0 else 366

if dias_transcurridos > 0 and total_actual > 0:
    proyeccion = int(total_actual * (dias_totales_anio / dias_transcurridos))
else:
    proyeccion = 0

df_año_ant = aplicar_filtros(df[df['año'] == año_fin - 1], cat_sel)
cierre_anterior = len(df_año_ant)
var_proy = ((proyeccion - cierre_anterior) / cierre_anterior * 100) if cierre_anterior > 0 else 0

var_str = f"{'▲' if var_pct and var_pct >= 0 else '▼'} {abs(var_pct or 0):.1f}%" if var_pct is not None else "N/D"
var_class = 'kpi-var-up' if (var_pct is not None and var_pct >= 0) else 'kpi-var-down'

with col_kpis:
    st.markdown(f"""
    <div class="kpi-container-transparent">
        <div class="kpi-box">
            <div class="kpi-title"> Período Anterior</div>
            <div class="kpi-value">{total_anterior:,}</div>
            <span class="kpi-subtitle">unidades</span>
        </div>
        <div class="kpi-box">
            <div class="kpi-title"> Período Actual</div>
            <div class="kpi-value">{total_actual:,}</div>
            <span class="kpi-subtitle">unidades</span>
        </div>
        <div class="kpi-box">
            <div class="kpi-title">📊 Variación</div>
            <div class="{var_class}">{var_str}</div>
            <span class="kpi-subtitle">interanual</span>
        </div>
        <div class="kpi-box">
            <div class="kpi-title">🎯 Proyección {año_fin}</div>
            <div class="kpi-value">{proyeccion:,.0f}</div>
            <span class="kpi-subtitle" style="color: {'#4CAF50' if var_proy >=0 else '#FF5252'}">{var_proy:+.1f}% vs cierre ant.</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ============ INSIGHTS EJECUTIVOS ============
insights = generar_insights_ejecutivos(df_actual, df_anterior, total_actual, total_anterior)

if insights:
    st.markdown("### 🔍 Resumen Ejecutivo del Período", unsafe_allow_html=True)
    cols_insights = st.columns(min(len(insights), 3))
    for i, insight in enumerate(insights):
        col_idx = i % 3
        with cols_insights[col_idx]:
            st.markdown(f"""
            <div class="insight-card insight-{insight['tipo']}">
                <div class="insight-title">{insight['titulo']}</div>
                <div class="insight-text">{insight['texto']}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

if df_actual.empty: 
    st.warning("⚠️ Sin datos para el período seleccionado. Ajuste los filtros.")
    st.stop()

# ============ VARIABLE GLOBAL PARA AÑO ACTUAL ============
año_actual = año_fin

# ============ TABS PRINCIPALES ============
tab1, tab2, tab3 = st.tabs([
    "📈 Market Share",
    "🏆 Competencia",
    "🟡 New Holland"
])

# ============================================================
# TAB 1: MARKET SHARE
# ============================================================
with tab1:
    st.markdown('<div class="chart-header"><p class="chart-title-text">📈 Tendencia Mensual Histórica</p></div>', unsafe_allow_html=True)
    
    df_tend = df_actual[df_actual['categoria_maquinaria'].isin(cat_sel if cat_sel else cats_disp)]
    tend_all = df_tend.groupby(['año','mes','mes_nombre']).size().reset_index(name='Unidades')
    tend_all['Año'] = tend_all['año'].astype(str)
    
    tend_tabla = tend_all.pivot_table(index='mes_nombre', columns='Año', values='Unidades', aggfunc='sum').fillna(0)
    tend_tabla = tend_tabla.astype(int).reset_index()
    tend_tabla['mes_nombre'] = pd.Categorical(tend_tabla['mes_nombre'], categories=MESES_NOMBRES, ordered=True)
    tend_tabla = tend_tabla.sort_values('mes_nombre').reset_index(drop=True)
    
    total_dict = {col: (tend_tabla[col].sum() if col != 'mes_nombre' else 'TOTAL YTD') for col in tend_tabla.columns}
    tend_tabla = pd.concat([tend_tabla, pd.DataFrame([total_dict])], ignore_index=True)
    
    meses_ord = [m for m in MESES_NOMBRES if m in tend_all['mes_nombre'].unique()]
    fig_tend = px.line(tend_all, x='mes_nombre', y='Unidades', color='Año', markers=True, color_discrete_sequence=COLOR_PALETTE)
    fig_tend.update_layout(plot_bgcolor='white', height=450, xaxis={'categoryorder':'array','categoryarray':meses_ord})
    
    render_bloque("", fig_tend, tend_tabla.style.apply(destacar_fila_nh, axis=1), "tgl_tend", "tendencia_mensual")
    
    st.divider()
    st.markdown('<div class="chart-header"><p class="chart-title-text">📋 Variación Anual por Segmento</p></div>', unsafe_allow_html=True)
    
    años_lista = sorted(df_actual['año'].unique()) 
    resumen = []
    for cat in (cat_sel if cat_sel else cats_disp):
        fila = {'Segmento': cat}
        prev = None
        for a in años_lista:
            val = len(df_actual[(df_actual['año']==a) & (df_actual['categoria_maquinaria']==cat)])
            fila[f"{a}"] = val
            if prev is not None and prev > 0: 
                fila[f"VAR {a}"] = f"{((val-prev)/prev*100):+.1f}%"
            prev = val
        if any(fila[f"{a}"] > 0 for a in años_lista): 
            resumen.append(fila)
    st.dataframe(pd.DataFrame(resumen), hide_index=True, use_container_width=True)

    st.divider()
    col_sh_l, col_sh_r = st.columns(2)
    with col_sh_l:
        share = df_actual['categoria_maquinaria'].value_counts().reset_index()
        share.columns = ['Categoria', 'Unidades']
        share = share[(share['Categoria'].isin(cat_sel if cat_sel else cats_disp)) & (share['Unidades'] > 0)]
        share['% Share'] = (share['Unidades'] / share['Unidades'].sum() * 100).round(1)
        fig_pie = px.pie(share, values='Unidades', names='Categoria', hole=0.4, color_discrete_sequence=COLOR_PALETTE)
        render_bloque("🥧 Desglose de Market Share", fig_pie, share, "tgl_share", "market_share")
# ============================================================
# TAB 2: COMPETENCIA (Portafolio + Segmentos + FOB/CIF + Modelos + Peso)
# ============================================================
with tab2:
    # ===== RADIO Y TOP N =====
    col_radio, col_topn = st.columns([2, 1])
    
    with col_radio:
        modo_actor = st.radio(
            "Ver por:", 
            ["🏆 Marcas", "🏢 Importadores"], 
            horizontal=True, 
            key="radial_modo_actor",
            label_visibility="collapsed"
        )
    
    with col_topn:
        if "Marcas" in modo_actor:
            top_n = st.number_input(
                "Top N:", 
                min_value=5, 
                max_value=100, 
                value=10, 
                step=5, 
                key="top_n_m",
                label_visibility="collapsed"
            )
        else:
            top_n_imp = st.number_input(
                "Top N:", 
                min_value=5, 
                max_value=100, 
                value=10, 
                step=5, 
                key="top_n_i",
                label_visibility="collapsed"
            )
    
    # ============================================================
    # SECCIÓN MARCAS
    # ============================================================
    if "Marcas" in modo_actor:
        df_act_rank = df_actual.copy()
        df_ant_rank = df_anterior.copy()

        rank_act = df_act_rank[COL_MARCA].value_counts().reset_index(name=str(año_actual))
        rank_ant = df_ant_rank[COL_MARCA].value_counts().reset_index(name=str(año_actual-1))
        ranking = rank_act.merge(rank_ant, on=COL_MARCA, how='outer').fillna(0).sort_values(str(año_actual), ascending=False).head(top_n).reset_index(drop=True)
        ranking[[str(año_actual), str(año_actual-1)]] = ranking[[str(año_actual), str(año_actual-1)]].astype(int)
        ranking.insert(0, 'N°', ranking.index + 1)
        ranking['Market Share'] = (ranking[str(año_actual)] / (ranking[str(año_actual)].sum() if ranking[str(año_actual)].sum() > 0 else 1) * 100).round(1).astype(str) + '%'
        ranking['Var Anual'] = ranking.apply(lambda r: calc_var(r, str(año_actual), str(año_actual-1)), axis=1)
        ranking_view = ranking[['N°', COL_MARCA, str(año_actual-1), str(año_actual), 'Var Anual', 'Market Share']]
        
        # Columnas ajustadas para más espacio al detalle
        col_split_l, col_split_r = st.columns([2.2, 2.8])
        
        # ===== COLUMNA IZQUIERDA: RANKING =====
        with col_split_l:
            st.markdown("##### 📋 Portafolio de Marcas")
            event_marcas = st.dataframe(
                ranking_view.style.apply(destacar_fila_nh, axis=1), 
                hide_index=True, 
                use_container_width=True, 
                on_select="rerun", 
                selection_mode="single-row"
            )
        
        # ===== COLUMNA DERECHA: DETALLE DE MARCA SELECCIONADA =====
        with col_split_r:
            filas_m = event_marcas.selection.rows
            if filas_m:
                marca_unica = ranking_view.iloc[filas_m[0]][COL_MARCA]
                st.markdown(f"#### 🔎 **{marca_unica}**")
                df_fichas = df_act_rank[df_act_rank[COL_MARCA] == marca_unica]
                
                # --- 1. IMPORTADORES DE LA MARCA ---
                st.markdown("##### 🏢 Importadores")
                
                imp_d = df_fichas['grupo_importador'].value_counts().reset_index(name='Unidades')
                imp_d = imp_d[imp_d['Unidades'] > 0]
                
                if not imp_d.empty:
                    fig_imp_d = px.bar(
                        imp_d, 
                        x='grupo_importador', 
                        y='Unidades', 
                        text_auto=True, 
                        color_discrete_sequence=['#4A90E2'],
                        title=f"Importadores que comercializan {marca_unica}"
                    )
                    fig_imp_d.update_layout(
                        plot_bgcolor='white', 
                        height=200, 
                        margin=dict(t=30, b=5, l=5, r=5),
                        showlegend=False
                    )
                    st.plotly_chart(fig_imp_d, use_container_width=True)
                    
                    st.dataframe(
                        imp_d,
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.info("No hay importadores registrados para esta marca en el período seleccionado.")
                
                # --- 2. TOP MODELOS IMPORTADOS ---
                st.markdown("##### 🏗️ Top Modelos Importados")
                
                if COL_MODELO in df_fichas.columns:
                    # Agrupar por modelo y segmento
                    top_modelos = df_fichas.groupby([COL_MODELO, 'categoria_maquinaria']).agg(
                        unidades=(COL_MODELO, 'size')
                    ).reset_index()
                    top_modelos = top_modelos.sort_values('unidades', ascending=False).head(10)
                    
                    # Selector FOB/CIF para top modelos
                    if COL_FOB and COL_FOB in df_fichas.columns:
                        tiene_cif = COL_CIF and COL_CIF in df_fichas.columns
                        
                        if tiene_cif:
                            st.markdown("##### 💰 Selecciona el valor aduanero:")
                            tipo_precio_tabla = st.radio(
                                "Tipo de precio:",
                                ["📦 FOB", "🚢 CIF"],
                                horizontal=True,
                                key=f"tipo_precio_tabla_{marca_unica}",
                                label_visibility="collapsed"
                            )
                            col_precio_tabla = COL_FOB if "FOB" in tipo_precio_tabla else COL_CIF
                            nombre_precio_tabla = "FOB" if "FOB" in tipo_precio_tabla else "CIF"
                        else:
                            col_precio_tabla = COL_FOB
                            nombre_precio_tabla = "FOB"
                    else:
                        col_precio_tabla = None
                        nombre_precio_tabla = "Precio"
                    
                    # Agregar precio si existe
                    if col_precio_tabla and col_precio_tabla in df_fichas.columns:
                        precio_tabla = df_fichas.groupby([COL_MODELO])[col_precio_tabla].agg(['mean']).reset_index()
                        precio_tabla.columns = [COL_MODELO, f'{nombre_precio_tabla} Promedio']
                        top_modelos = top_modelos.merge(precio_tabla, on=COL_MODELO, how='left')
                    
                    top_modelos['unidades'] = top_modelos['unidades'].astype(int)
                    top_modelos = top_modelos.rename(columns={
                        'unidades': 'Unidades', 
                        COL_MODELO: 'Modelo',
                        'categoria_maquinaria': 'Segmento'
                    })
                    
                    cols_order = ['Modelo', 'Segmento', 'Unidades']
                    if f'{nombre_precio_tabla} Promedio' in top_modelos.columns:
                        cols_order.append(f'{nombre_precio_tabla} Promedio')
                    
                    top_modelos = top_modelos[cols_order]
                    
                    format_tabla = {}
                    if f'{nombre_precio_tabla} Promedio' in top_modelos.columns:
                        format_tabla[f'{nombre_precio_tabla} Promedio'] = '${:,.2f}'
                    
                    st.dataframe(
                        top_modelos.style.format(format_tabla),
                        hide_index=True, 
                        use_container_width=True
                    )
                
                # --- 3. EXPLORAR SEGMENTO ESPECÍFICO ---
                with st.expander("🔍 Explorar segmento específico", expanded=False):
                    st.markdown("##### 📊 Segmentos Importados")
                    seg_data = df_fichas['categoria_maquinaria'].value_counts().reset_index()
                    seg_data.columns = ['Segmento', 'Unidades']
                    seg_data = seg_data[seg_data['Unidades'] > 0]
                    
                    if not seg_data.empty:
                        fig_seg = px.bar(
                            seg_data, 
                            x='Segmento', 
                            y='Unidades', 
                            text_auto=True,
                            color='Segmento',
                            color_discrete_sequence=COLOR_PALETTE,
                            title=f"Segmentos comercializados por {marca_unica}"
                        )
                        fig_seg.update_layout(
                            plot_bgcolor='white', 
                            height=200, 
                            margin=dict(t=30, b=5, l=5, r=5),
                            showlegend=False
                        )
                        st.plotly_chart(fig_seg, use_container_width=True)
                        
                        segmentos = ['TODOS'] + list(seg_data['Segmento'].unique())
                        seg_seleccionado = st.selectbox(
                            "🔍 Selecciona un segmento para ver sus modelos:", 
                            segmentos, 
                            key=f"seg_{marca_unica}"
                        )
                        
                        if seg_seleccionado != 'TODOS':
                            df_seg_modelos = df_fichas[df_fichas['categoria_maquinaria'] == seg_seleccionado]
                            
                            if not df_seg_modelos.empty and COL_MODELO in df_seg_modelos.columns:
                                st.markdown(f"##### 🏗️ Modelos - {seg_seleccionado}")
                                
                                # Selector FOB/CIF para el segmento
                                if COL_FOB and COL_FOB in df_seg_modelos.columns:
                                    tiene_cif_seg = COL_CIF and COL_CIF in df_seg_modelos.columns
                                    
                                    if tiene_cif_seg:
                                        st.markdown("##### 💰 Selecciona el valor aduanero:")
                                        tipo_precio_seg = st.radio(
                                            "Tipo de precio:",
                                            ["📦 FOB", "🚢 CIF"],
                                            horizontal=True,
                                            key=f"tipo_precio_seg_{marca_unica}_{seg_seleccionado}",
                                            label_visibility="collapsed"
                                        )
                                        col_precio_seg = COL_FOB if "FOB" in tipo_precio_seg else COL_CIF
                                        nombre_precio_seg = "FOB" if "FOB" in tipo_precio_seg else "CIF"
                                    else:
                                        col_precio_seg = COL_FOB
                                        nombre_precio_seg = "FOB"
                                        st.info("ℹ️ Solo se dispone de datos FOB para este segmento.")
                                    
                                    modelos_seg = df_seg_modelos.groupby([COL_MODELO]).agg(
                                        unidades=(COL_MODELO, 'size')
                                    ).reset_index()
                                    
                                    if col_precio_seg in df_seg_modelos.columns:
                                        precio_agg = df_seg_modelos.groupby([COL_MODELO])[col_precio_seg].agg(['min', 'mean', 'max']).reset_index()
                                        precio_agg.columns = [COL_MODELO, f'{nombre_precio_seg.lower()}_min', f'{nombre_precio_seg.lower()}_prom', f'{nombre_precio_seg.lower()}_max']
                                        modelos_seg = modelos_seg.merge(precio_agg, on=COL_MODELO, how='left')
                                    
                                    modelos_seg['unidades'] = modelos_seg['unidades'].astype(int)
                                    
                                    display_cols_seg = [COL_MODELO, 'unidades']
                                    format_dict_seg = {}
                                    rename_map_seg = {COL_MODELO: 'Modelo', 'unidades': 'Unidades'}
                                    
                                    if f'{nombre_precio_seg.lower()}_prom' in modelos_seg.columns:
                                        display_cols_seg.extend([f'{nombre_precio_seg.lower()}_min', f'{nombre_precio_seg.lower()}_prom', f'{nombre_precio_seg.lower()}_max'])
                                        format_dict_seg[f'{nombre_precio_seg.lower()}_min'] = '${:,.2f}'
                                        format_dict_seg[f'{nombre_precio_seg.lower()}_prom'] = '${:,.2f}'
                                        format_dict_seg[f'{nombre_precio_seg.lower()}_max'] = '${:,.2f}'
                                        rename_map_seg.update({
                                            f'{nombre_precio_seg.lower()}_min': f'{nombre_precio_seg} Mínimo',
                                            f'{nombre_precio_seg.lower()}_prom': f'{nombre_precio_seg} Promedio',
                                            f'{nombre_precio_seg.lower()}_max': f'{nombre_precio_seg} Máximo'
                                        })
                                    
                                    modelos_show_seg = modelos_seg[display_cols_seg].copy()
                                    modelos_show_seg = modelos_show_seg.rename(columns=rename_map_seg)
                                    
                                    styled_seg = modelos_show_seg.style.format(format_dict_seg)
                                    if marca_unica == MARCA_PROPIA:
                                        styled_seg = styled_seg.apply(lambda r: ['background-color: #FFE0B2; font-weight: bold;'] * len(r), axis=1)
                                    
                                    st.dataframe(styled_seg, hide_index=True, use_container_width=True)
                                    
                                    # --- PESO SI ES EXCAVADORA (CON MULTISELECT) ---
                                    if seg_seleccionado == "EXCAVADORA" and COL_PESO and COL_PESO in df_seg_modelos.columns:
                                        with st.expander("⚖️ Distribución por Peso - EXCAVADORA", expanded=True):
                                            
                                            todos_pesos = sorted(df_seg_modelos[COL_PESO].unique(), key=extraer_peso_numerico)
                                            
                                            if len(todos_pesos) > 3:
                                                st.markdown("##### 🔍 Selecciona los rangos de peso a visualizar:")
                                                pesos_seleccionados = st.multiselect(
                                                    "Rangos de peso:",
                                                    options=todos_pesos,
                                                    default=todos_pesos[:3],
                                                    key=f"pesos_sel_{marca_unica}_{seg_seleccionado}"
                                                )
                                            else:
                                                pesos_seleccionados = todos_pesos
                                            
                                            if pesos_seleccionados:
                                                df_peso_filtrado = df_seg_modelos[df_seg_modelos[COL_PESO].isin(pesos_seleccionados)]
                                                
                                                peso_data = df_peso_filtrado.groupby([COL_PESO, COL_MODELO]).size().reset_index(name='Unidades')
                                                peso_data = peso_data[peso_data['Unidades'] > 0]
                                                
                                                if not peso_data.empty:
                                                    fig_peso = px.bar(
                                                        peso_data, 
                                                        x=COL_PESO, 
                                                        y='Unidades', 
                                                        color=COL_MODELO,
                                                        text_auto=True,
                                                        color_discrete_sequence=COLOR_PALETTE,
                                                        title=f"Distribución por Rango de Peso ({len(pesos_seleccionados)} rangos seleccionados)"
                                                    )
                                                    fig_peso.update_layout(
                                                        plot_bgcolor='white', 
                                                        height=300, 
                                                        margin=dict(t=30, b=5, l=5, r=5),
                                                        legend=dict(title="Modelo", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                                                    )
                                                    st.plotly_chart(fig_peso, use_container_width=True)
                                                    
                                                    peso_resumen = df_peso_filtrado.groupby([COL_PESO]).agg(
                                                        unidades=(COL_PESO, 'size'),
                                                        modelos=(COL_MODELO, 'nunique')
                                                    ).reset_index()
                                                    peso_resumen.columns = ['Rango de Peso', 'Unidades', 'Modelos']
                                                    peso_resumen = peso_resumen[peso_resumen['Unidades'] > 0]
                                                    st.dataframe(peso_resumen, hide_index=True, use_container_width=True)
                                                    
                                                    if col_precio_seg and col_precio_seg in df_peso_filtrado.columns:
                                                        st.markdown(f"##### 💰 {nombre_precio_seg} por Rango de Peso")
                                                        precio_peso = df_peso_filtrado.groupby([COL_PESO])[col_precio_seg].mean().reset_index()
                                                        precio_peso.columns = ['Rango de Peso', f'{nombre_precio_seg} Promedio']
                                                        
                                                        st.dataframe(
                                                            precio_peso.style.format({f'{nombre_precio_seg} Promedio': '${:,.2f}'}),
                                                            hide_index=True, 
                                                            use_container_width=True
                                                        )
                                                else:
                                                    st.info("No hay datos para los rangos de peso seleccionados.")
                                            else:
                                                st.info("Selecciona al menos un rango de peso para visualizar.")
                    else:
                        st.info("No hay segmentos disponibles para esta marca en el período seleccionado.")
                
                # --- 4. EVOLUCIÓN DE PRECIOS (EXPANDER SEPARADO) ---
                if COL_MODELO in df_fichas.columns and col_precio_tabla and col_precio_tabla in df_fichas.columns:
                    with st.expander("📈 Evolución de Precios en el tiempo", expanded=False):
                        st.markdown(f"##### Evolución de {nombre_precio_tabla} Promedio - {marca_unica}")
                        
                        evol_data = df_fichas.groupby(['año', 'mes', 'mes_nombre', COL_MODELO])[col_precio_tabla].mean().reset_index()
                        evol_data['periodo'] = evol_data['mes_nombre'] + ' ' + evol_data['año'].astype(str)
                        evol_data = evol_data.sort_values(['año', 'mes'])
                        
                        if not evol_data.empty:
                            ver_todos = st.checkbox("Mostrar todos los modelos", value=False, key=f"ver_todos_precios_{marca_unica}")
                            
                            if not ver_todos:
                                top_5_modelos = top_modelos['Modelo'].head(5).tolist() if 'top_modelos' in locals() else []
                                if top_5_modelos:
                                    evol_data = evol_data[evol_data[COL_MODELO].isin(top_5_modelos)]
                            
                            if not evol_data.empty:
                                fig_evol = px.line(
                                    evol_data,
                                    x='periodo',
                                    y=col_precio_tabla,
                                    color=COL_MODELO,
                                    markers=True,
                                    title=f"Evolución de {nombre_precio_tabla} Promedio por Modelo",
                                    color_discrete_sequence=COLOR_PALETTE
                                )
                                fig_evol.update_layout(
                                    plot_bgcolor='white',
                                    height=350,
                                    margin=dict(t=40, b=10, l=10, r=10),
                                    xaxis_title="Período",
                                    yaxis_title=f"{nombre_precio_tabla} ($)",
                                    legend=dict(title="Modelo", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                                )
                                fig_evol.update_traces(
                                    hovertemplate=f"{nombre_precio_tabla}: $%{{y:,.2f}}<br>Periodo: %{{x}}<br>Modelo: %{{fullData.name}}<extra></extra>"
                                )
                                st.plotly_chart(fig_evol, use_container_width=True)
                                
                                st.markdown("##### 📊 Resumen de Variación de Precios por Modelo")
                                
                                variacion_modelos = []
                                for modelo in evol_data[COL_MODELO].unique():
                                    df_modelo = evol_data[evol_data[COL_MODELO] == modelo]
                                    if len(df_modelo) >= 2:
                                        precio_inicio = df_modelo.iloc[0][col_precio_tabla]
                                        precio_fin = df_modelo.iloc[-1][col_precio_tabla]
                                        variacion = ((precio_fin - precio_inicio) / precio_inicio * 100) if precio_inicio > 0 else 0
                                        variacion_modelos.append({
                                            'Modelo': modelo,
                                            'Precio Inicial': precio_inicio,
                                            'Precio Final': precio_fin,
                                            'Variación %': variacion,
                                            'Tendencia': '📈 Subida' if variacion > 0 else '📉 Bajada' if variacion < 0 else '➡️ Estable'
                                        })
                                
                                if variacion_modelos:
                                    df_variacion = pd.DataFrame(variacion_modelos)
                                    df_variacion = df_variacion.sort_values('Variación %', ascending=False)
                                    
                                    format_variacion = {
                                        'Precio Inicial': '${:,.2f}',
                                        'Precio Final': '${:,.2f}',
                                        'Variación %': '{:+.1f}%'
                                    }
                                    
                                    st.dataframe(
                                        df_variacion.style.format(format_variacion),
                                        hide_index=True,
                                        use_container_width=True
                                    )
                                    
                                    max_var = df_variacion.iloc[0]
                                    min_var = df_variacion.iloc[-1]
                                    
                                    col_var1, col_var2 = st.columns(2)
                                    with col_var1:
                                        st.metric(
                                            f"📈 Mayor Subida: {max_var['Modelo']}",
                                            f"{max_var['Variación %']:+.1f}%",
                                            delta=f"${max_var['Precio Final'] - max_var['Precio Inicial']:+,.2f}"
                                        )
                                    with col_var2:
                                        st.metric(
                                            f"📉 Mayor Bajada: {min_var['Modelo']}",
                                            f"{min_var['Variación %']:+.1f}%",
                                            delta=f"${min_var['Precio Final'] - min_var['Precio Inicial']:+,.2f}"
                                        )
                            else:
                                st.info("No hay suficientes datos para mostrar la evolución de precios.")
                        else:
                            st.info("No hay datos de evolución de precios para esta marca.")
                
                # --- 5. EVOLUCIÓN DE UNIDADES (EXPANDER SEPARADO) ---
                if COL_MODELO in df_fichas.columns:
                    with st.expander("📦 Evolución de Unidades en el tiempo", expanded=False):
                        st.markdown(f"##### Evolución de Unidades Importadas - {marca_unica}")
                        
                        evol_unidades = df_fichas.groupby(['año', 'mes', 'mes_nombre', COL_MODELO]).size().reset_index(name='Unidades')
                        evol_unidades['periodo'] = evol_unidades['mes_nombre'] + ' ' + evol_unidades['año'].astype(str)
                        evol_unidades = evol_unidades.sort_values(['año', 'mes'])
                        
                        if not evol_unidades.empty:
                            ver_todos_unidades = st.checkbox("Mostrar todos los modelos", value=False, key=f"ver_todos_unidades_{marca_unica}")
                            
                            if not ver_todos_unidades:
                                top_5_modelos = top_modelos['Modelo'].head(5).tolist() if 'top_modelos' in locals() else []
                                if top_5_modelos:
                                    evol_unidades = evol_unidades[evol_unidades[COL_MODELO].isin(top_5_modelos)]
                            
                            if not evol_unidades.empty:
                                fig_evol_unidades = px.line(
                                    evol_unidades,
                                    x='periodo',
                                    y='Unidades',
                                    color=COL_MODELO,
                                    markers=True,
                                    title=f"Evolución de Unidades Importadas por Modelo",
                                    color_discrete_sequence=COLOR_PALETTE
                                )
                                fig_evol_unidades.update_layout(
                                    plot_bgcolor='white',
                                    height=350,
                                    margin=dict(t=40, b=10, l=10, r=10),
                                    xaxis_title="Período",
                                    yaxis_title="Unidades",
                                    legend=dict(title="Modelo", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                                )
                                fig_evol_unidades.update_traces(
                                    hovertemplate=f"Unidades: %{{y:,.0f}}<br>Periodo: %{{x}}<br>Modelo: %{{fullData.name}}<extra></extra>"
                                )
                                st.plotly_chart(fig_evol_unidades, use_container_width=True)
                                
                                st.markdown("##### 📊 Resumen de Variación de Unidades por Modelo")
                                
                                variacion_unidades = []
                                for modelo in evol_unidades[COL_MODELO].unique():
                                    df_modelo = evol_unidades[evol_unidades[COL_MODELO] == modelo]
                                    if len(df_modelo) >= 2:
                                        unidades_inicio = df_modelo.iloc[0]['Unidades']
                                        unidades_fin = df_modelo.iloc[-1]['Unidades']
                                        variacion = ((unidades_fin - unidades_inicio) / unidades_inicio * 100) if unidades_inicio > 0 else 0
                                        variacion_unidades.append({
                                            'Modelo': modelo,
                                            'Unidades Iniciales': unidades_inicio,
                                            'Unidades Finales': unidades_fin,
                                            'Variación %': variacion,
                                            'Tendencia': '📈 Subida' if variacion > 0 else '📉 Bajada' if variacion < 0 else '➡️ Estable'
                                        })
                                
                                if variacion_unidades:
                                    df_variacion_unidades = pd.DataFrame(variacion_unidades)
                                    df_variacion_unidades = df_variacion_unidades.sort_values('Variación %', ascending=False)
                                    
                                    format_variacion_unidades = {
                                        'Unidades Iniciales': '{:,.0f}',
                                        'Unidades Finales': '{:,.0f}',
                                        'Variación %': '{:+.1f}%'
                                    }
                                    
                                    st.dataframe(
                                        df_variacion_unidades.style.format(format_variacion_unidades),
                                        hide_index=True,
                                        use_container_width=True
                                    )
                                    
                                    max_var_u = df_variacion_unidades.iloc[0]
                                    min_var_u = df_variacion_unidades.iloc[-1]
                                    
                                    col_var_u1, col_var_u2 = st.columns(2)
                                    with col_var_u1:
                                        st.metric(
                                            f"📈 Mayor Crecimiento: {max_var_u['Modelo']}",
                                            f"{max_var_u['Variación %']:+.1f}%",
                                            delta=f"{max_var_u['Unidades Finales'] - max_var_u['Unidades Iniciales']:+,.0f} unidades"
                                        )
                                    with col_var_u2:
                                        st.metric(
                                            f"📉 Mayor Caída: {min_var_u['Modelo']}",
                                            f"{min_var_u['Variación %']:+.1f}%",
                                            delta=f"{min_var_u['Unidades Finales'] - min_var_u['Unidades Iniciales']:+,.0f} unidades"
                                        )
                            else:
                                st.info("No hay suficientes datos para mostrar la evolución de unidades.")
                        else:
                            st.info("No hay datos de evolución de unidades para esta marca.")
            else:
                st.info("💡 *Haz clic en cualquier marca del ranking para ver su portafolio completo.*")

        # ============================================================
        # COMPARATIVA DE MARCAS (EXPANDABLE)
        # ============================================================
        with st.expander("⚔️ Comparativa entre Marcas", expanded=False):
            st.markdown("### Comparación Detallada entre Marcas")
            
            marcas_h2h = sorted(df_actual[COL_MARCA].dropna().unique())
            if len(marcas_h2h) >= 2:
                c_h1, c_h2 = st.columns(2)
                with c_h1: 
                    m_a = st.selectbox("Marca A", marcas_h2h, index=0, key="h2h_ma")
                with c_h2: 
                    m_b = st.selectbox("Marca B", marcas_h2h, index=min(1, len(marcas_h2h)-1), key="h2h_mb")
                
                if m_a != m_b:
                    df_a = df_actual[df_actual[COL_MARCA] == m_a]
                    df_b = df_actual[df_actual[COL_MARCA] == m_b]
                    
                    # ---- Selector de precio ----
                    st.markdown("##### 💰 Selecciona el valor aduanero para la comparativa:")
                    tipo_precio_comp = st.radio(
                        "Tipo de precio:",
                        ["📦 FOB", "🚢 CIF"],
                        horizontal=True,
                        key="tipo_precio_comp_marcas",
                        label_visibility="collapsed"
                    )
                    col_precio_comp = COL_FOB if "FOB" in tipo_precio_comp else COL_CIF
                    nombre_precio_comp = "FOB" if "FOB" in tipo_precio_comp else "CIF"
                    
                    # ---- Métricas comparativas (3 bloques) ----
                    st.markdown("##### 📊 Métricas Comparativas")
                    col_m1, col_m2, col_m3 = st.columns([1, 0.3, 1])
                    
                    unidades_a = len(df_a)
                    unidades_b = len(df_b)
                    share_a = (unidades_a / total_actual * 100) if total_actual > 0 else 0
                    share_b = (unidades_b / total_actual * 100) if total_actual > 0 else 0
                    
                    if col_precio_comp and col_precio_comp in df_a.columns:
                        precio_a = df_a[col_precio_comp].mean()
                    else:
                        precio_a = None
                    
                    if col_precio_comp and col_precio_comp in df_b.columns:
                        precio_b = df_b[col_precio_comp].mean()
                    else:
                        precio_b = None
                    
                    diff_unidades = unidades_b - unidades_a
                    diff_unidades_pct = ((unidades_b - unidades_a) / unidades_a * 100) if unidades_a > 0 else 0
                    diff_precio = (precio_b - precio_a) if (precio_a is not None and precio_b is not None) else None
                    diff_precio_pct = ((precio_b - precio_a) / precio_a * 100) if (precio_a is not None and precio_b is not None and precio_a > 0) else 0
                    diff_share = share_b - share_a
                    
                    # BLOQUE 1: MARCA A
                    with col_m1:
                        precio_a_str = f"${precio_a:,.2f}" if precio_a is not None else "N/A"
                        st.markdown(f"""
                        <div style="background: #F8F9FA; padding: 15px; border-radius: 10px; border: 1px solid #E8E8E8; text-align: center;">
                            <h4 style="margin: 0 0 10px 0; color: #1A1A1A;">🏷️ {m_a}</h4>
                            <div style="font-size: 1.1rem; font-weight: 600; color: #1A1A1A;">{unidades_a:,}</div>
                            <div style="font-size: 0.75rem; color: #888; margin-bottom: 5px;">📦 Unidades</div>
                            <div style="font-size: 1.1rem; font-weight: 600; color: #1A1A1A;">{precio_a_str}</div>
                            <div style="font-size: 0.75rem; color: #888; margin-bottom: 5px;">💰 {nombre_precio_comp} Promedio</div>
                            <div style="font-size: 1.1rem; font-weight: 600; color: #1A1A1A;">{share_a:.1f}%</div>
                            <div style="font-size: 0.75rem; color: #888;">📊 Market Share</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # BLOQUE 2: VACÍO
                    with col_m2:
                        st.markdown("""
                        <div style="height: 100%; display: flex; align-items: center; justify-content: center;">
                            <div style="width: 2px; height: 80%; background: #E0E0E0; border-radius: 2px;"></div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # BLOQUE 3: MARCA B CON DIFERENCIAS
                    with col_m3:
                        color_unidades = "#4CAF50" if diff_unidades > 0 else "#FF5252" if diff_unidades < 0 else "#888"
                        color_precio = "#4CAF50" if diff_precio is not None and diff_precio < 0 else "#FF5252" if diff_precio is not None and diff_precio > 0 else "#888"
                        color_share = "#4CAF50" if diff_share > 0 else "#FF5252" if diff_share < 0 else "#888"
                        
                        precio_b_str = f"${precio_b:,.2f}" if precio_b is not None else "N/A"
                        
                        if diff_unidades > 0:
                            diff_unidades_str = f"▲ +{diff_unidades:,} ({diff_unidades_pct:+.1f}% vs {m_a})"
                        elif diff_unidades < 0:
                            diff_unidades_str = f"▼ {diff_unidades:+,} ({diff_unidades_pct:+.1f}% vs {m_a})"
                        else:
                            diff_unidades_str = f"±0 ({diff_unidades_pct:+.1f}% vs {m_a})"
                        
                        if diff_precio is not None:
                            if diff_precio > 0:
                                diff_precio_str = f"▲ +{diff_precio:,.2f} ({diff_precio_pct:+.1f}% vs {m_a})"
                            elif diff_precio < 0:
                                diff_precio_str = f"▼ {diff_precio:+,.2f} ({diff_precio_pct:+.1f}% vs {m_a})"
                            else:
                                diff_precio_str = f"±0 ({diff_precio_pct:+.1f}% vs {m_a})"
                        else:
                            diff_precio_str = ""
                        
                        if diff_share > 0:
                            diff_share_str = f"▲ +{diff_share:+.1f} pp vs {m_a}"
                        elif diff_share < 0:
                            diff_share_str = f"▼ {diff_share:+.1f} pp vs {m_a}"
                        else:
                            diff_share_str = f"±0 pp vs {m_a}"
                        
                        st.markdown(f"""
                        <div style="background: #F8F9FA; padding: 15px; border-radius: 10px; border: 1px solid #E8E8E8; text-align: center;">
                            <h4 style="margin: 0 0 10px 0; color: #1A1A1A;">🏷️ {m_b}</h4>
                            <div style="font-size: 1.1rem; font-weight: 600; color: #1A1A1A;">{unidades_b:,}</div>
                            <div style="font-size: 0.75rem; color: #888; margin-bottom: 5px;">📦 Unidades</div>
                            <div style="font-size: 0.7rem; color: {color_unidades}; margin-top: -3px; margin-bottom: 8px;">{diff_unidades_str}</div>
                            <div style="font-size: 1.1rem; font-weight: 600; color: #1A1A1A;">{precio_b_str}</div>
                            <div style="font-size: 0.75rem; color: #888; margin-bottom: 5px;">💰 {nombre_precio_comp} Promedio</div>
                            <div style="font-size: 0.7rem; color: {color_precio}; margin-top: -3px; margin-bottom: 8px;">{diff_precio_str}</div>
                            <div style="font-size: 1.1rem; font-weight: 600; color: #1A1A1A;">{share_b:.1f}%</div>
                            <div style="font-size: 0.75rem; color: #888; margin-bottom: 5px;">📊 Market Share</div>
                            <div style="font-size: 0.7rem; color: {color_share}; margin-top: -3px;">{diff_share_str}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # ---- Tendencia ----
                    st.markdown("##### 📈 Tendencia Mensual")
                    h2h_trends = pd.merge(
                        df_a.groupby('mes_nombre').size().reset_index(name=m_a),
                        df_b.groupby('mes_nombre').size().reset_index(name=m_b),
                        on='mes_nombre', how='outer'
                    ).fillna(0)
                    h2h_trends[[m_a, m_b]] = h2h_trends[[m_a, m_b]].astype(int)
                    h2h_trends['mes_nombre'] = pd.Categorical(h2h_trends['mes_nombre'], categories=MESES_NOMBRES, ordered=True)
                    h2h_trends = h2h_trends.sort_values('mes_nombre').reset_index(drop=True)
                    
                    fig_h2h = px.line(
                        h2h_trends.melt(id_vars='mes_nombre', var_name='Marca', value_name='Unidades'),
                        x='mes_nombre', y='Unidades', color='Marca', markers=True,
                        color_discrete_map={MARCA_PROPIA: COLOR_NH},
                        color_discrete_sequence=COLOR_PALETTE
                    )
                    fig_h2h.update_layout(plot_bgcolor='white', height=250)
                    st.plotly_chart(fig_h2h, use_container_width=True)
                    
                    # ---- Comparación por Segmento (dos tablas separadas con evolución - SIN TOTAL) ----
                    st.markdown("##### 📊 Comparación por Segmento")
                    
                    anios_disponibles = sorted(set(df_a['año'].unique()) | set(df_b['año'].unique()))
                    
                    if anios_disponibles:
                        anio_seleccionado = st.selectbox(
                            "Selecciona un año para comparar:",
                            anios_disponibles,
                            index=len(anios_disponibles)-1,
                            key="anio_seg_comp_marcas"
                        )
                        
                        # ---- GRÁFICO DE BARRAS COMPARATIVO ----
                        df_a_anio = df_a[df_a['año'] == anio_seleccionado]
                        df_b_anio = df_b[df_b['año'] == anio_seleccionado]
                        
                        seg_a = df_a_anio['categoria_maquinaria'].value_counts().reset_index()
                        seg_a.columns = ['Segmento', m_a]
                        seg_b = df_b_anio['categoria_maquinaria'].value_counts().reset_index()
                        seg_b.columns = ['Segmento', m_b]
                        
                        seg_comp = pd.merge(seg_a, seg_b, on='Segmento', how='outer').fillna(0)
                        seg_comp = seg_comp[seg_comp[[m_a, m_b]].sum(axis=1) > 0]
                        seg_comp[[m_a, m_b]] = seg_comp[[m_a, m_b]].astype(int)
                        
                        fig_seg_comp = px.bar(
                            seg_comp.melt(id_vars='Segmento', var_name='Marca', value_name='Unidades'),
                            x='Segmento', y='Unidades', color='Marca', barmode='group',
                            color_discrete_map={MARCA_PROPIA: COLOR_NH},
                            color_discrete_sequence=COLOR_PALETTE,
                            title=f"Comparación por Segmento - {anio_seleccionado}"
                        )
                        fig_seg_comp.update_layout(plot_bgcolor='white', height=250)
                        st.plotly_chart(fig_seg_comp, use_container_width=True)
                        
                        # ---- DOS TABLAS SEPARADAS CON EVOLUCIÓN ANUAL (SIN TOTAL) ----
                        st.markdown("##### 📊 Evolución de Unidades por Segmento")
                        
                        col_tabla_a, col_tabla_b = st.columns(2)
                        
                        with col_tabla_a:
                            st.markdown(f"**{m_a}**")
                            
                            evol_seg_a = df_a.groupby(['año', 'categoria_maquinaria']).size().reset_index(name='Unidades')
                            evol_seg_a = evol_seg_a.pivot(index='categoria_maquinaria', columns='año', values='Unidades').fillna(0).astype(int)
                            evol_seg_a = evol_seg_a.reset_index()
                            
                            cols_a = ['Segmento'] + [str(col) for col in evol_seg_a.columns if col != 'categoria_maquinaria']
                            evol_seg_a.columns = cols_a
                            
                            # Sin columna "Total"
                            if len(evol_seg_a.columns) > 2:
                                anios_cols = [col for col in evol_seg_a.columns if col != 'Segmento']
                                
                                if len(anios_cols) >= 2:
                                    primer_anio = anios_cols[0]
                                    ultimo_anio = anios_cols[-1]
                                    evol_seg_a['Variación %'] = ((evol_seg_a[ultimo_anio] - evol_seg_a[primer_anio]) / evol_seg_a[primer_anio] * 100).replace([float('inf'), -float('inf')], 0).round(1)
                                    evol_seg_a['Variación %'] = evol_seg_a['Variación %'].apply(lambda x: f"{x:+.1f}%" if x != 0 else "0%")
                            
                            for col in evol_seg_a.columns:
                                if col not in ['Segmento', 'Variación %']:
                                    evol_seg_a[col] = evol_seg_a[col].astype(int)
                            
                            if m_a == MARCA_PROPIA:
                                styled_a = evol_seg_a.style.apply(lambda r: ['background-color: #FFE0B2; font-weight: bold;'] * len(r), axis=1)
                            else:
                                styled_a = evol_seg_a.style
                            
                            st.dataframe(styled_a, hide_index=True, use_container_width=True)
                        
                        with col_tabla_b:
                            st.markdown(f"**{m_b}**")
                            
                            evol_seg_b = df_b.groupby(['año', 'categoria_maquinaria']).size().reset_index(name='Unidades')
                            evol_seg_b = evol_seg_b.pivot(index='categoria_maquinaria', columns='año', values='Unidades').fillna(0).astype(int)
                            evol_seg_b = evol_seg_b.reset_index()
                            
                            cols_b = ['Segmento'] + [str(col) for col in evol_seg_b.columns if col != 'categoria_maquinaria']
                            evol_seg_b.columns = cols_b
                            
                            # Sin columna "Total"
                            if len(evol_seg_b.columns) > 2:
                                anios_cols_b = [col for col in evol_seg_b.columns if col != 'Segmento']
                                
                                if len(anios_cols_b) >= 2:
                                    primer_anio_b = anios_cols_b[0]
                                    ultimo_anio_b = anios_cols_b[-1]
                                    evol_seg_b['Variación %'] = ((evol_seg_b[ultimo_anio_b] - evol_seg_b[primer_anio_b]) / evol_seg_b[primer_anio_b] * 100).replace([float('inf'), -float('inf')], 0).round(1)
                                    evol_seg_b['Variación %'] = evol_seg_b['Variación %'].apply(lambda x: f"{x:+.1f}%" if x != 0 else "0%")
                            
                            for col in evol_seg_b.columns:
                                if col not in ['Segmento', 'Variación %']:
                                    evol_seg_b[col] = evol_seg_b[col].astype(int)
                            
                            if m_b == MARCA_PROPIA:
                                styled_b = evol_seg_b.style.apply(lambda r: ['background-color: #FFE0B2; font-weight: bold;'] * len(r), axis=1)
                            else:
                                styled_b = evol_seg_b.style
                            
                            st.dataframe(styled_b, hide_index=True, use_container_width=True)
                    else:
                        st.info("No hay datos de años disponibles para comparar.")
                    
                    # ---- TOP MODELOS (del último año) ----
                    st.markdown("##### 🏗️ Top Modelos Importados")
                    
                    ultimo_anio = max(set(df_a['año'].unique()) | set(df_b['año'].unique()))
                    
                    df_a_ultimo = df_a[df_a['año'] == ultimo_anio]
                    df_b_ultimo = df_b[df_b['año'] == ultimo_anio]
                    
                    col_mod_a, col_mod_b = st.columns(2)
                    
                    with col_mod_a:
                        st.markdown(f"**Top Modelos - {m_a} ({ultimo_anio})**")
                        top_a = df_a_ultimo.groupby([COL_MODELO, 'categoria_maquinaria']).size().reset_index(name='Unidades')
                        top_a = top_a.sort_values('Unidades', ascending=False).head(10)
                        top_a = top_a.rename(columns={COL_MODELO: 'Modelo', 'categoria_maquinaria': 'Segmento'})
                        
                        if col_precio_comp and col_precio_comp in df_a_ultimo.columns:
                            precio_a_top = df_a_ultimo.groupby([COL_MODELO])[col_precio_comp].mean().reset_index()
                            precio_a_top.columns = ['Modelo', f'{nombre_precio_comp} Promedio']
                            top_a = top_a.merge(precio_a_top, on='Modelo', how='left')
                        
                        format_a = {}
                        if f'{nombre_precio_comp} Promedio' in top_a.columns:
                            format_a[f'{nombre_precio_comp} Promedio'] = '${:,.2f}'
                        
                        styled_a = top_a.style.format(format_a)
                        if m_a == MARCA_PROPIA:
                            styled_a = styled_a.apply(lambda r: ['background-color: #FFE0B2; font-weight: bold;'] * len(r), axis=1)
                        
                        st.dataframe(styled_a, hide_index=True, use_container_width=True)
                    
                    with col_mod_b:
                        st.markdown(f"**Top Modelos - {m_b} ({ultimo_anio})**")
                        top_b = df_b_ultimo.groupby([COL_MODELO, 'categoria_maquinaria']).size().reset_index(name='Unidades')
                        top_b = top_b.sort_values('Unidades', ascending=False).head(10)
                        top_b = top_b.rename(columns={COL_MODELO: 'Modelo', 'categoria_maquinaria': 'Segmento'})
                        
                        if col_precio_comp and col_precio_comp in df_b_ultimo.columns:
                            precio_b_top = df_b_ultimo.groupby([COL_MODELO])[col_precio_comp].mean().reset_index()
                            precio_b_top.columns = ['Modelo', f'{nombre_precio_comp} Promedio']
                            top_b = top_b.merge(precio_b_top, on='Modelo', how='left')
                        
                        format_b = {}
                        if f'{nombre_precio_comp} Promedio' in top_b.columns:
                            format_b[f'{nombre_precio_comp} Promedio'] = '${:,.2f}'
                        
                        styled_b = top_b.style.format(format_b)
                        if m_b == MARCA_PROPIA:
                            styled_b = styled_b.apply(lambda r: ['background-color: #FFE0B2; font-weight: bold;'] * len(r), axis=1)
                        
                        st.dataframe(styled_b, hide_index=True, use_container_width=True)
                    
                    # ---- EXPLORAR SEGMENTO ESPECÍFICO (2 COLUMNAS + PESO PARA EXCAVADORA) ----
                    with st.expander("🔍 Explorar segmento específico", expanded=False):
                        st.markdown("##### Selecciona un segmento para ver detalle:")
                        
                        segmentos_disponibles = sorted(set(df_a['categoria_maquinaria'].unique()) | set(df_b['categoria_maquinaria'].unique()))
                        if segmentos_disponibles:
                            seg_seleccionado_comp = st.selectbox(
                                "Segmento:",
                                segmentos_disponibles,
                                key="seg_comp_marcas",
                                label_visibility="collapsed"
                            )
                            
                            df_a_seg = df_a[df_a['categoria_maquinaria'] == seg_seleccionado_comp]
                            df_b_seg = df_b[df_b['categoria_maquinaria'] == seg_seleccionado_comp]
                            
                            if not df_a_seg.empty or not df_b_seg.empty:
                                st.markdown(f"**Modelos - {seg_seleccionado_comp}**")
                                
                                col_seg_a, col_seg_b = st.columns(2)
                                
                                with col_seg_a:
                                    st.markdown(f"### {m_a}")
                                    if COL_MODELO in df_a_seg.columns and not df_a_seg.empty:
                                        modelos_a_seg = df_a_seg.groupby([COL_MODELO]).size().reset_index(name='Unidades')
                                        modelos_a_seg = modelos_a_seg.rename(columns={COL_MODELO: 'Modelo'})
                                        
                                        if col_precio_comp and col_precio_comp in df_a_seg.columns:
                                            precio_a_seg = df_a_seg.groupby([COL_MODELO])[col_precio_comp].agg(['min', 'mean', 'max']).reset_index()
                                            precio_a_seg.columns = ['Modelo', f'{nombre_precio_comp} Mínimo', f'{nombre_precio_comp} Promedio', f'{nombre_precio_comp} Máximo']
                                            modelos_a_seg = modelos_a_seg.merge(precio_a_seg, on='Modelo', how='left')
                                        
                                        format_a_seg = {}
                                        for col in modelos_a_seg.columns:
                                            if 'Mínimo' in col or 'Promedio' in col or 'Máximo' in col:
                                                format_a_seg[col] = '${:,.2f}'
                                        
                                        styled_a_seg = modelos_a_seg.style.format(format_a_seg)
                                        if m_a == MARCA_PROPIA:
                                            styled_a_seg = styled_a_seg.apply(lambda r: ['background-color: #FFE0B2; font-weight: bold;'] * len(r), axis=1)
                                        
                                        st.dataframe(styled_a_seg, hide_index=True, use_container_width=True)
                                    else:
                                        st.info(f"No hay modelos en este segmento para {m_a}")
                                
                                with col_seg_b:
                                    st.markdown(f"### {m_b}")
                                    if COL_MODELO in df_b_seg.columns and not df_b_seg.empty:
                                        modelos_b_seg = df_b_seg.groupby([COL_MODELO]).size().reset_index(name='Unidades')
                                        modelos_b_seg = modelos_b_seg.rename(columns={COL_MODELO: 'Modelo'})
                                        
                                        if col_precio_comp and col_precio_comp in df_b_seg.columns:
                                            precio_b_seg = df_b_seg.groupby([COL_MODELO])[col_precio_comp].agg(['min', 'mean', 'max']).reset_index()
                                            precio_b_seg.columns = ['Modelo', f'{nombre_precio_comp} Mínimo', f'{nombre_precio_comp} Promedio', f'{nombre_precio_comp} Máximo']
                                            modelos_b_seg = modelos_b_seg.merge(precio_b_seg, on='Modelo', how='left')
                                        
                                        format_b_seg = {}
                                        for col in modelos_b_seg.columns:
                                            if 'Mínimo' in col or 'Promedio' in col or 'Máximo' in col:
                                                format_b_seg[col] = '${:,.2f}'
                                        
                                        styled_b_seg = modelos_b_seg.style.format(format_b_seg)
                                        if m_b == MARCA_PROPIA:
                                            styled_b_seg = styled_b_seg.apply(lambda r: ['background-color: #FFE0B2; font-weight: bold;'] * len(r), axis=1)
                                        
                                        st.dataframe(styled_b_seg, hide_index=True, use_container_width=True)
                                    else:
                                        st.info(f"No hay modelos en este segmento para {m_b}")
                                
                                # ---- DISTRIBUCIÓN POR PESO SI ES EXCAVADORA (CORREGIDO) ----
                                if seg_seleccionado_comp == "EXCAVADORA" and COL_PESO and COL_PESO in df_a_seg.columns and COL_PESO in df_b_seg.columns:
                                    with st.expander("⚖️ Distribución por Peso - EXCAVADORA (Comparativa)", expanded=True):
                                        
                                        st.markdown("##### Comparación de Rangos de Peso")
                                        
                                        peso_a = df_a_seg.groupby([COL_PESO]).size().reset_index(name=f'Unidades {m_a}')
                                        peso_b = df_b_seg.groupby([COL_PESO]).size().reset_index(name=f'Unidades {m_b}')
                                        
                                        peso_comp = pd.merge(peso_a, peso_b, on=COL_PESO, how='outer').fillna(0)
                                        peso_comp[[f'Unidades {m_a}', f'Unidades {m_b}']] = peso_comp[[f'Unidades {m_a}', f'Unidades {m_b}']].astype(int)
                                        peso_comp = peso_comp.rename(columns={COL_PESO: 'Rango de Peso'})
                                        
                                        fig_peso_comp = px.bar(
                                            peso_comp.melt(id_vars='Rango de Peso', var_name='Marca', value_name='Unidades'),
                                            x='Rango de Peso', 
                                            y='Unidades', 
                                            color='Marca', 
                                            barmode='group',
                                            color_discrete_map={m_a: '#1E448A', m_b: '#2E8B57'},
                                            title=f"Distribución por Rango de Peso - {seg_seleccionado_comp}"
                                        )
                                        fig_peso_comp.update_layout(
                                            plot_bgcolor='white',
                                            height=300,
                                            margin=dict(t=40, b=10, l=10, r=10),
                                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                                        )
                                        st.plotly_chart(fig_peso_comp, use_container_width=True)
                                        
                                        st.dataframe(peso_comp, hide_index=True, use_container_width=True)
                                        
                                        if col_precio_comp and col_precio_comp in df_a_seg.columns and col_precio_comp in df_b_seg.columns:
                                            st.markdown(f"##### 💰 {nombre_precio_comp} por Rango de Peso")
                                            
                                            precio_peso_a = df_a_seg.groupby([COL_PESO])[col_precio_comp].mean().reset_index()
                                            precio_peso_a.columns = ['Rango de Peso', f'{nombre_precio_comp} {m_a}']
                                            
                                            precio_peso_b = df_b_seg.groupby([COL_PESO])[col_precio_comp].mean().reset_index()
                                            precio_peso_b.columns = ['Rango de Peso', f'{nombre_precio_comp} {m_b}']
                                            
                                            precio_peso_comp = pd.merge(precio_peso_a, precio_peso_b, on='Rango de Peso', how='outer').fillna(0)
                                            
                                            format_precio_peso = {}
                                            if f'{nombre_precio_comp} {m_a}' in precio_peso_comp.columns:
                                                format_precio_peso[f'{nombre_precio_comp} {m_a}'] = '${:,.2f}'
                                            if f'{nombre_precio_comp} {m_b}' in precio_peso_comp.columns:
                                                format_precio_peso[f'{nombre_precio_comp} {m_b}'] = '${:,.2f}'
                                            
                                            st.dataframe(
                                                precio_peso_comp.style.format(format_precio_peso),
                                                hide_index=True, 
                                                use_container_width=True
                                            )
                                        
                                        st.markdown("##### 📈 Evolución de Unidades por Rango de Peso")
                                        
                                        # ✅ CORREGIDO: Usar 'año' (minúscula)
                                        evol_peso_a = df_a_seg.groupby(['año', COL_PESO]).size().reset_index(name='Unidades')
                                        evol_peso_a = evol_peso_a.pivot(index='año', columns=COL_PESO, values='Unidades').fillna(0).astype(int)
                                        evol_peso_a = evol_peso_a.reset_index()
                                        evol_peso_a.columns = ['año'] + [str(col) for col in evol_peso_a.columns if col != 'año']
                                        
                                        evol_peso_b = df_b_seg.groupby(['año', COL_PESO]).size().reset_index(name='Unidades')
                                        evol_peso_b = evol_peso_b.pivot(index='año', columns=COL_PESO, values='Unidades').fillna(0).astype(int)
                                        evol_peso_b = evol_peso_b.reset_index()
                                        evol_peso_b.columns = ['año'] + [str(col) for col in evol_peso_b.columns if col != 'año']
                                        
                                        col_evol_a, col_evol_b = st.columns(2)
                                        
                                        with col_evol_a:
                                            st.markdown(f"**{m_a}**")
                                            st.dataframe(evol_peso_a, hide_index=True, use_container_width=True)
                                        
                                        with col_evol_b:
                                            st.markdown(f"**{m_b}**")
                                            st.dataframe(evol_peso_b, hide_index=True, use_container_width=True)
                            else:
                                st.info(f"No hay modelos en el segmento {seg_seleccionado_comp} para las marcas seleccionadas.")
                        else:
                            st.info("No hay segmentos disponibles para las marcas seleccionadas.")
                    
                    # ---- EVOLUCIÓN DE PRECIOS EN COMPARATIVA ----
                    if col_precio_comp and col_precio_comp in df_a.columns and col_precio_comp in df_b.columns:
                        with st.expander("📈 Ver evolución de precios en el tiempo", expanded=False):
                            st.markdown(f"##### Evolución de {nombre_precio_comp} Promedio")
                            
                            evol_a_comp = df_a.groupby(['año', 'mes', 'mes_nombre'])[col_precio_comp].mean().reset_index()
                            evol_a_comp['periodo'] = evol_a_comp['mes_nombre'] + ' ' + evol_a_comp['año'].astype(str)
                            evol_a_comp = evol_a_comp.sort_values(['año', 'mes'])
                            evol_a_comp['Marca'] = m_a
                            
                            evol_b_comp = df_b.groupby(['año', 'mes', 'mes_nombre'])[col_precio_comp].mean().reset_index()
                            evol_b_comp['periodo'] = evol_b_comp['mes_nombre'] + ' ' + evol_b_comp['año'].astype(str)
                            evol_b_comp = evol_b_comp.sort_values(['año', 'mes'])
                            evol_b_comp['Marca'] = m_b
                            
                            evol_combined = pd.concat([evol_a_comp, evol_b_comp])
                            
                            if not evol_combined.empty:
                                fig_evol_comp = px.line(
                                    evol_combined,
                                    x='periodo',
                                    y=col_precio_comp,
                                    color='Marca',
                                    markers=True,
                                    title=f"Evolución de {nombre_precio_comp} Promedio",
                                    color_discrete_map={MARCA_PROPIA: COLOR_NH, m_a: '#1E448A', m_b: '#2E8B57'},
                                    color_discrete_sequence=COLOR_PALETTE
                                )
                                fig_evol_comp.update_layout(
                                    plot_bgcolor='white',
                                    height=300,
                                    margin=dict(t=40, b=10, l=10, r=10),
                                    xaxis_title="Período",
                                    yaxis_title=f"{nombre_precio_comp} ($)"
                                )
                                fig_evol_comp.update_traces(
                                    hovertemplate=f"{nombre_precio_comp}: $%{{y:,.2f}}<br>Periodo: %{{x}}<br>Marca: %{{fullData.name}}<extra></extra>"
                                )
                                st.plotly_chart(fig_evol_comp, use_container_width=True)
                            else:
                                st.info("No hay datos suficientes para mostrar la evolución de precios.")
            else:
                st.warning("⚠️ No hay suficientes marcas para comparar en el período seleccionado.")

    # ============================================================
    # SECCIÓN IMPORTADORES
    # ============================================================
    else:
        df_act_imp = df_actual.copy()
        df_ant_imp = df_anterior.copy()

        rank_imp_act = df_act_imp['grupo_importador'].value_counts().reset_index(name=str(año_actual))
        rank_imp_ant = df_ant_imp['grupo_importador'].value_counts().reset_index(name=str(año_actual-1))
        ranking_imp = rank_imp_act.merge(rank_imp_ant, on='grupo_importador', how='outer').fillna(0).sort_values(str(año_actual), ascending=False).head(top_n_imp).reset_index(drop=True)
        ranking_imp[[str(año_actual), str(año_actual-1)]] = ranking_imp[[str(año_actual), str(año_actual-1)]].astype(int)
        ranking_imp.insert(0, 'N°', ranking_imp.index + 1)
        ranking_imp['Market Share'] = (ranking_imp[str(año_actual)] / (ranking_imp[str(año_actual)].sum() if ranking_imp[str(año_actual)].sum() > 0 else 1) * 100).round(1).astype(str) + '%'
        ranking_imp['Var Anual'] = ranking_imp.apply(lambda r: calc_var(r, str(año_actual), str(año_actual-1)), axis=1)
        ranking_imp_view = ranking_imp[['N°', 'grupo_importador', str(año_actual-1), str(año_actual), 'Var Anual', 'Market Share']]
        
        col_split_imp_l, col_split_imp_r = st.columns([2.2, 2.8])
        
        with col_split_imp_l:
            st.markdown("##### 📋 Portafolio de Importadores")
            event_imps = st.dataframe(
                ranking_imp_view, 
                hide_index=True, 
                use_container_width=True, 
                on_select="rerun", 
                selection_mode="single-row"
            )
        
        with col_split_imp_r:
            filas_i = event_imps.selection.rows
            if filas_i:
                imp_unico = ranking_imp_view.iloc[filas_i[0]]['grupo_importador']
                st.markdown(f"#### 🏢 **{imp_unico}**")
                df_fichas_imp = df_act_imp[df_act_imp['grupo_importador'] == imp_unico]
                
                # --- 1. MARCAS DEL IMPORTADOR ---
                st.markdown("##### 🏗️ Portafolio de Marcas")
                
                marcas_importador = df_fichas_imp[COL_MARCA].value_counts().reset_index()
                marcas_importador.columns = ['Marca', 'Unidades']
                marcas_importador = marcas_importador[marcas_importador['Unidades'] > 0]
                
                if not marcas_importador.empty:
                    fig_marcas_imp = px.bar(
                        marcas_importador,
                        x='Marca',
                        y='Unidades',
                        text_auto=True,
                        color='Marca',
                        color_discrete_sequence=COLOR_PALETTE,
                        title=f"Marcas comercializadas por {imp_unico}"
                    )
                    fig_marcas_imp.update_layout(
                        plot_bgcolor='white',
                        height=200,
                        margin=dict(t=30, b=5, l=5, r=5),
                        showlegend=False
                    )
                    st.plotly_chart(fig_marcas_imp, use_container_width=True)
                    
                    st.dataframe(
                        marcas_importador,
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.info("Este importador no tiene marcas registradas en el período seleccionado.")
                
                # --- 2. TOP MODELOS IMPORTADOS ---
                st.markdown("##### 🏗️ Top Modelos Importados")
                
                if COL_MODELO in df_fichas_imp.columns:
                    top_modelos_imp = df_fichas_imp.groupby([COL_MODELO, 'categoria_maquinaria']).agg(
                        unidades=(COL_MODELO, 'size')
                    ).reset_index()
                    top_modelos_imp = top_modelos_imp.sort_values('unidades', ascending=False).head(10)
                    
                    if COL_FOB and COL_FOB in df_fichas_imp.columns:
                        tiene_cif_imp = COL_CIF and COL_CIF in df_fichas_imp.columns
                        
                        if tiene_cif_imp:
                            st.markdown("##### 💰 Selecciona el valor aduanero:")
                            tipo_precio_tabla_imp = st.radio(
                                "Tipo de precio:",
                                ["📦 FOB", "🚢 CIF"],
                                horizontal=True,
                                key=f"tipo_precio_tabla_{imp_unico}",
                                label_visibility="collapsed"
                            )
                            col_precio_tabla_imp = COL_FOB if "FOB" in tipo_precio_tabla_imp else COL_CIF
                            nombre_precio_tabla_imp = "FOB" if "FOB" in tipo_precio_tabla_imp else "CIF"
                        else:
                            col_precio_tabla_imp = COL_FOB
                            nombre_precio_tabla_imp = "FOB"
                    else:
                        col_precio_tabla_imp = None
                        nombre_precio_tabla_imp = "Precio"
                    
                    if col_precio_tabla_imp and col_precio_tabla_imp in df_fichas_imp.columns:
                        precio_tabla_imp = df_fichas_imp.groupby([COL_MODELO])[col_precio_tabla_imp].agg(['mean']).reset_index()
                        precio_tabla_imp.columns = [COL_MODELO, f'{nombre_precio_tabla_imp} Promedio']
                        top_modelos_imp = top_modelos_imp.merge(precio_tabla_imp, on=COL_MODELO, how='left')
                    
                    top_modelos_imp['unidades'] = top_modelos_imp['unidades'].astype(int)
                    top_modelos_imp = top_modelos_imp.rename(columns={
                        'unidades': 'Unidades', 
                        COL_MODELO: 'Modelo',
                        'categoria_maquinaria': 'Segmento'
                    })
                    
                    cols_order_imp = ['Modelo', 'Segmento', 'Unidades']
                    if f'{nombre_precio_tabla_imp} Promedio' in top_modelos_imp.columns:
                        cols_order_imp.append(f'{nombre_precio_tabla_imp} Promedio')
                    
                    top_modelos_imp = top_modelos_imp[cols_order_imp]
                    
                    format_tabla_imp = {}
                    if f'{nombre_precio_tabla_imp} Promedio' in top_modelos_imp.columns:
                        format_tabla_imp[f'{nombre_precio_tabla_imp} Promedio'] = '${:,.2f}'
                    
                    st.dataframe(
                        top_modelos_imp.style.format(format_tabla_imp),
                        hide_index=True, 
                        use_container_width=True
                    )
                
                # --- 3. EXPLORAR SEGMENTO ESPECÍFICO ---
                with st.expander("🔍 Explorar segmento específico", expanded=False):
                    st.markdown("##### 📊 Segmentos Importados")
                    seg_data_imp = df_fichas_imp['categoria_maquinaria'].value_counts().reset_index()
                    seg_data_imp.columns = ['Segmento', 'Unidades']
                    seg_data_imp = seg_data_imp[seg_data_imp['Unidades'] > 0]
                    
                    if not seg_data_imp.empty:
                        fig_seg_imp = px.bar(
                            seg_data_imp, 
                            x='Segmento', 
                            y='Unidades', 
                            text_auto=True,
                            color='Segmento',
                            color_discrete_sequence=COLOR_PALETTE,
                            title=f"Segmentos importados por {imp_unico}"
                        )
                        fig_seg_imp.update_layout(
                            plot_bgcolor='white', 
                            height=200, 
                            margin=dict(t=30, b=5, l=5, r=5),
                            showlegend=False
                        )
                        st.plotly_chart(fig_seg_imp, use_container_width=True)
                        
                        segmentos_imp = ['TODOS'] + list(seg_data_imp['Segmento'].unique())
                        seg_seleccionado_imp = st.selectbox(
                            "🔍 Selecciona un segmento para ver sus modelos:", 
                            segmentos_imp, 
                            key=f"seg_imp_{imp_unico}"
                        )
                        
                        if seg_seleccionado_imp != 'TODOS':
                            df_seg_modelos_imp = df_fichas_imp[df_fichas_imp['categoria_maquinaria'] == seg_seleccionado_imp]
                            
                            if not df_seg_modelos_imp.empty and COL_MODELO in df_seg_modelos_imp.columns:
                                st.markdown(f"##### 🏗️ Modelos - {seg_seleccionado_imp}")
                                
                                if COL_FOB and COL_FOB in df_seg_modelos_imp.columns:
                                    tiene_cif_seg_imp = COL_CIF and COL_CIF in df_seg_modelos_imp.columns
                                    
                                    if tiene_cif_seg_imp:
                                        st.markdown("##### 💰 Selecciona el valor aduanero:")
                                        tipo_precio_seg_imp = st.radio(
                                            "Tipo de precio:",
                                            ["📦 FOB", "🚢 CIF"],
                                            horizontal=True,
                                            key=f"tipo_precio_seg_imp_{imp_unico}_{seg_seleccionado_imp}",
                                            label_visibility="collapsed"
                                        )
                                        col_precio_seg_imp = COL_FOB if "FOB" in tipo_precio_seg_imp else COL_CIF
                                        nombre_precio_seg_imp = "FOB" if "FOB" in tipo_precio_seg_imp else "CIF"
                                    else:
                                        col_precio_seg_imp = COL_FOB
                                        nombre_precio_seg_imp = "FOB"
                                        st.info("ℹ️ Solo se dispone de datos FOB para este segmento.")
                                    
                                    modelos_seg_imp = df_seg_modelos_imp.groupby([COL_MODELO]).agg(
                                        unidades=(COL_MODELO, 'size')
                                    ).reset_index()
                                    
                                    if col_precio_seg_imp in df_seg_modelos_imp.columns:
                                        precio_agg_imp = df_seg_modelos_imp.groupby([COL_MODELO])[col_precio_seg_imp].agg(['min', 'mean', 'max']).reset_index()
                                        precio_agg_imp.columns = [COL_MODELO, f'{nombre_precio_seg_imp.lower()}_min', f'{nombre_precio_seg_imp.lower()}_prom', f'{nombre_precio_seg_imp.lower()}_max']
                                        modelos_seg_imp = modelos_seg_imp.merge(precio_agg_imp, on=COL_MODELO, how='left')
                                    
                                    modelos_seg_imp['unidades'] = modelos_seg_imp['unidades'].astype(int)
                                    
                                    display_cols_seg_imp = [COL_MODELO, 'unidades']
                                    format_dict_seg_imp = {}
                                    rename_map_seg_imp = {COL_MODELO: 'Modelo', 'unidades': 'Unidades'}
                                    
                                    if f'{nombre_precio_seg_imp.lower()}_prom' in modelos_seg_imp.columns:
                                        display_cols_seg_imp.extend([f'{nombre_precio_seg_imp.lower()}_min', f'{nombre_precio_seg_imp.lower()}_prom', f'{nombre_precio_seg_imp.lower()}_max'])
                                        format_dict_seg_imp[f'{nombre_precio_seg_imp.lower()}_min'] = '${:,.2f}'
                                        format_dict_seg_imp[f'{nombre_precio_seg_imp.lower()}_prom'] = '${:,.2f}'
                                        format_dict_seg_imp[f'{nombre_precio_seg_imp.lower()}_max'] = '${:,.2f}'
                                        rename_map_seg_imp.update({
                                            f'{nombre_precio_seg_imp.lower()}_min': f'{nombre_precio_seg_imp} Mínimo',
                                            f'{nombre_precio_seg_imp.lower()}_prom': f'{nombre_precio_seg_imp} Promedio',
                                            f'{nombre_precio_seg_imp.lower()}_max': f'{nombre_precio_seg_imp} Máximo'
                                        })
                                    
                                    modelos_show_seg_imp = modelos_seg_imp[display_cols_seg_imp].copy()
                                    modelos_show_seg_imp = modelos_show_seg_imp.rename(columns=rename_map_seg_imp)
                                    
                                    st.dataframe(
                                        modelos_show_seg_imp.style.format(format_dict_seg_imp),
                                        hide_index=True, 
                                        use_container_width=True
                                    )
                                    
                                    # --- PESO SI ES EXCAVADORA (CON MULTISELECT) ---
                                    if seg_seleccionado_imp == "EXCAVADORA" and COL_PESO and COL_PESO in df_seg_modelos_imp.columns:
                                        with st.expander("⚖️ Distribución por Peso - EXCAVADORA", expanded=True):
                                            
                                            todos_pesos_imp = sorted(df_seg_modelos_imp[COL_PESO].unique(), key=extraer_peso_numerico)
                                            
                                            if len(todos_pesos_imp) > 3:
                                                st.markdown("##### 🔍 Selecciona los rangos de peso a visualizar:")
                                                pesos_seleccionados_imp = st.multiselect(
                                                    "Rangos de peso:",
                                                    options=todos_pesos_imp,
                                                    default=todos_pesos_imp[:3],
                                                    key=f"pesos_sel_imp_{imp_unico}_{seg_seleccionado_imp}"
                                                )
                                            else:
                                                pesos_seleccionados_imp = todos_pesos_imp
                                            
                                            if pesos_seleccionados_imp:
                                                df_peso_filtrado_imp = df_seg_modelos_imp[df_seg_modelos_imp[COL_PESO].isin(pesos_seleccionados_imp)]
                                                
                                                peso_data_imp = df_peso_filtrado_imp.groupby([COL_PESO, COL_MODELO]).size().reset_index(name='Unidades')
                                                peso_data_imp = peso_data_imp[peso_data_imp['Unidades'] > 0]
                                                
                                                if not peso_data_imp.empty:
                                                    fig_peso_imp = px.bar(
                                                        peso_data_imp, 
                                                        x=COL_PESO, 
                                                        y='Unidades', 
                                                        color=COL_MODELO,
                                                        text_auto=True,
                                                        color_discrete_sequence=COLOR_PALETTE,
                                                        title=f"Distribución por Rango de Peso ({len(pesos_seleccionados_imp)} rangos seleccionados)"
                                                    )
                                                    fig_peso_imp.update_layout(
                                                        plot_bgcolor='white', 
                                                        height=300, 
                                                        margin=dict(t=30, b=5, l=5, r=5),
                                                        legend=dict(title="Modelo", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                                                    )
                                                    st.plotly_chart(fig_peso_imp, use_container_width=True)
                                                    
                                                    peso_resumen_imp = df_peso_filtrado_imp.groupby([COL_PESO]).agg(
                                                        unidades=(COL_PESO, 'size'),
                                                        modelos=(COL_MODELO, 'nunique')
                                                    ).reset_index()
                                                    peso_resumen_imp.columns = ['Rango de Peso', 'Unidades', 'Modelos']
                                                    peso_resumen_imp = peso_resumen_imp[peso_resumen_imp['Unidades'] > 0]
                                                    st.dataframe(peso_resumen_imp, hide_index=True, use_container_width=True)
                                                    
                                                    if col_precio_seg_imp and col_precio_seg_imp in df_peso_filtrado_imp.columns:
                                                        st.markdown(f"##### 💰 {nombre_precio_seg_imp} por Rango de Peso")
                                                        precio_peso_imp = df_peso_filtrado_imp.groupby([COL_PESO])[col_precio_seg_imp].mean().reset_index()
                                                        precio_peso_imp.columns = ['Rango de Peso', f'{nombre_precio_seg_imp} Promedio']
                                                        
                                                        st.dataframe(
                                                            precio_peso_imp.style.format({f'{nombre_precio_seg_imp} Promedio': '${:,.2f}'}),
                                                            hide_index=True, 
                                                            use_container_width=True
                                                        )
                                                else:
                                                    st.info("No hay datos para los rangos de peso seleccionados.")
                                            else:
                                                st.info("Selecciona al menos un rango de peso para visualizar.")
                    else:
                        st.info("No hay segmentos disponibles para este importador en el período seleccionado.")
                
                # --- 4. EVOLUCIÓN DE PRECIOS (EXPANDER SEPARADO) ---
                if COL_MODELO in df_fichas_imp.columns and col_precio_tabla_imp and col_precio_tabla_imp in df_fichas_imp.columns:
                    with st.expander("📈 Evolución de Precios en el tiempo", expanded=False):
                        st.markdown(f"##### Evolución de {nombre_precio_tabla_imp} Promedio - {imp_unico}")
                        
                        evol_data_imp = df_fichas_imp.groupby(['año', 'mes', 'mes_nombre', COL_MODELO])[col_precio_tabla_imp].mean().reset_index()
                        evol_data_imp['periodo'] = evol_data_imp['mes_nombre'] + ' ' + evol_data_imp['año'].astype(str)
                        evol_data_imp = evol_data_imp.sort_values(['año', 'mes'])
                        
                        if not evol_data_imp.empty:
                            ver_todos_imp = st.checkbox("Mostrar todos los modelos", value=False, key=f"ver_todos_precios_imp_{imp_unico}")
                            
                            if not ver_todos_imp:
                                top_5_modelos_imp = top_modelos_imp['Modelo'].head(5).tolist() if 'top_modelos_imp' in locals() else []
                                if top_5_modelos_imp:
                                    evol_data_imp = evol_data_imp[evol_data_imp[COL_MODELO].isin(top_5_modelos_imp)]
                            
                            if not evol_data_imp.empty:
                                fig_evol_imp = px.line(
                                    evol_data_imp,
                                    x='periodo',
                                    y=col_precio_tabla_imp,
                                    color=COL_MODELO,
                                    markers=True,
                                    title=f"Evolución de {nombre_precio_tabla_imp} Promedio por Modelo",
                                    color_discrete_sequence=COLOR_PALETTE
                                )
                                fig_evol_imp.update_layout(
                                    plot_bgcolor='white',
                                    height=350,
                                    margin=dict(t=40, b=10, l=10, r=10),
                                    xaxis_title="Período",
                                    yaxis_title=f"{nombre_precio_tabla_imp} ($)",
                                    legend=dict(title="Modelo", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                                )
                                fig_evol_imp.update_traces(
                                    hovertemplate=f"{nombre_precio_tabla_imp}: $%{{y:,.2f}}<br>Periodo: %{{x}}<br>Modelo: %{{fullData.name}}<extra></extra>"
                                )
                                st.plotly_chart(fig_evol_imp, use_container_width=True)
                                
                                st.markdown("##### 📊 Resumen de Variación de Precios por Modelo")
                                
                                variacion_modelos_imp = []
                                for modelo in evol_data_imp[COL_MODELO].unique():
                                    df_modelo = evol_data_imp[evol_data_imp[COL_MODELO] == modelo]
                                    if len(df_modelo) >= 2:
                                        precio_inicio = df_modelo.iloc[0][col_precio_tabla_imp]
                                        precio_fin = df_modelo.iloc[-1][col_precio_tabla_imp]
                                        variacion = ((precio_fin - precio_inicio) / precio_inicio * 100) if precio_inicio > 0 else 0
                                        variacion_modelos_imp.append({
                                            'Modelo': modelo,
                                            'Precio Inicial': precio_inicio,
                                            'Precio Final': precio_fin,
                                            'Variación %': variacion,
                                            'Tendencia': '📈 Subida' if variacion > 0 else '📉 Bajada' if variacion < 0 else '➡️ Estable'
                                        })
                                
                                if variacion_modelos_imp:
                                    df_variacion_imp = pd.DataFrame(variacion_modelos_imp)
                                    df_variacion_imp = df_variacion_imp.sort_values('Variación %', ascending=False)
                                    
                                    format_variacion_imp = {
                                        'Precio Inicial': '${:,.2f}',
                                        'Precio Final': '${:,.2f}',
                                        'Variación %': '{:+.1f}%'
                                    }
                                    
                                    st.dataframe(
                                        df_variacion_imp.style.format(format_variacion_imp),
                                        hide_index=True,
                                        use_container_width=True
                                    )
                                    
                                    max_var_imp = df_variacion_imp.iloc[0]
                                    min_var_imp = df_variacion_imp.iloc[-1]
                                    
                                    col_var1_imp, col_var2_imp = st.columns(2)
                                    with col_var1_imp:
                                        st.metric(
                                            f"📈 Mayor Subida: {max_var_imp['Modelo']}",
                                            f"{max_var_imp['Variación %']:+.1f}%",
                                            delta=f"${max_var_imp['Precio Final'] - max_var_imp['Precio Inicial']:+,.2f}"
                                        )
                                    with col_var2_imp:
                                        st.metric(
                                            f"📉 Mayor Bajada: {min_var_imp['Modelo']}",
                                            f"{min_var_imp['Variación %']:+.1f}%",
                                            delta=f"${min_var_imp['Precio Final'] - min_var_imp['Precio Inicial']:+,.2f}"
                                        )
                            else:
                                st.info("No hay suficientes datos para mostrar la evolución de precios.")
                        else:
                            st.info("No hay datos de evolución de precios para este importador.")
                
                # --- 5. EVOLUCIÓN DE UNIDADES (EXPANDER SEPARADO) ---
                if COL_MODELO in df_fichas_imp.columns:
                    with st.expander("📦 Evolución de Unidades en el tiempo", expanded=False):
                        st.markdown(f"##### Evolución de Unidades Importadas - {imp_unico}")
                        
                        evol_unidades_imp = df_fichas_imp.groupby(['año', 'mes', 'mes_nombre', COL_MODELO]).size().reset_index(name='Unidades')
                        evol_unidades_imp['periodo'] = evol_unidades_imp['mes_nombre'] + ' ' + evol_unidades_imp['año'].astype(str)
                        evol_unidades_imp = evol_unidades_imp.sort_values(['año', 'mes'])
                        
                        if not evol_unidades_imp.empty:
                            ver_todos_unidades_imp = st.checkbox("Mostrar todos los modelos", value=False, key=f"ver_todos_unidades_imp_{imp_unico}")
                            
                            if not ver_todos_unidades_imp:
                                top_5_modelos_imp = top_modelos_imp['Modelo'].head(5).tolist() if 'top_modelos_imp' in locals() else []
                                if top_5_modelos_imp:
                                    evol_unidades_imp = evol_unidades_imp[evol_unidades_imp[COL_MODELO].isin(top_5_modelos_imp)]
                            
                            if not evol_unidades_imp.empty:
                                fig_evol_unidades_imp = px.line(
                                    evol_unidades_imp,
                                    x='periodo',
                                    y='Unidades',
                                    color=COL_MODELO,
                                    markers=True,
                                    title=f"Evolución de Unidades Importadas por Modelo",
                                    color_discrete_sequence=COLOR_PALETTE
                                )
                                fig_evol_unidades_imp.update_layout(
                                    plot_bgcolor='white',
                                    height=350,
                                    margin=dict(t=40, b=10, l=10, r=10),
                                    xaxis_title="Período",
                                    yaxis_title="Unidades",
                                    legend=dict(title="Modelo", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                                )
                                fig_evol_unidades_imp.update_traces(
                                    hovertemplate=f"Unidades: %{{y:,.0f}}<br>Periodo: %{{x}}<br>Modelo: %{{fullData.name}}<extra></extra>"
                                )
                                st.plotly_chart(fig_evol_unidades_imp, use_container_width=True)
                                
                                st.markdown("##### 📊 Resumen de Variación de Unidades por Modelo")
                                
                                variacion_unidades_imp = []
                                for modelo in evol_unidades_imp[COL_MODELO].unique():
                                    df_modelo = evol_unidades_imp[evol_unidades_imp[COL_MODELO] == modelo]
                                    if len(df_modelo) >= 2:
                                        unidades_inicio = df_modelo.iloc[0]['Unidades']
                                        unidades_fin = df_modelo.iloc[-1]['Unidades']
                                        variacion = ((unidades_fin - unidades_inicio) / unidades_inicio * 100) if unidades_inicio > 0 else 0
                                        variacion_unidades_imp.append({
                                            'Modelo': modelo,
                                            'Unidades Iniciales': unidades_inicio,
                                            'Unidades Finales': unidades_fin,
                                            'Variación %': variacion,
                                            'Tendencia': '📈 Subida' if variacion > 0 else '📉 Bajada' if variacion < 0 else '➡️ Estable'
                                        })
                                
                                if variacion_unidades_imp:
                                    df_variacion_unidades_imp = pd.DataFrame(variacion_unidades_imp)
                                    df_variacion_unidades_imp = df_variacion_unidades_imp.sort_values('Variación %', ascending=False)
                                    
                                    format_variacion_unidades_imp = {
                                        'Unidades Iniciales': '{:,.0f}',
                                        'Unidades Finales': '{:,.0f}',
                                        'Variación %': '{:+.1f}%'
                                    }
                                    
                                    st.dataframe(
                                        df_variacion_unidades_imp.style.format(format_variacion_unidades_imp),
                                        hide_index=True,
                                        use_container_width=True
                                    )
                                    
                                    max_var_u_imp = df_variacion_unidades_imp.iloc[0]
                                    min_var_u_imp = df_variacion_unidades_imp.iloc[-1]
                                    
                                    col_var_u1_imp, col_var_u2_imp = st.columns(2)
                                    with col_var_u1_imp:
                                        st.metric(
                                            f"📈 Mayor Crecimiento: {max_var_u_imp['Modelo']}",
                                            f"{max_var_u_imp['Variación %']:+.1f}%",
                                            delta=f"{max_var_u_imp['Unidades Finales'] - max_var_u_imp['Unidades Iniciales']:+,.0f} unidades"
                                        )
                                    with col_var_u2_imp:
                                        st.metric(
                                            f"📉 Mayor Caída: {min_var_u_imp['Modelo']}",
                                            f"{min_var_u_imp['Variación %']:+.1f}%",
                                            delta=f"{min_var_u_imp['Unidades Finales'] - min_var_u_imp['Unidades Iniciales']:+,.0f} unidades"
                                        )
                            else:
                                st.info("No hay suficientes datos para mostrar la evolución de unidades.")
                        else:
                            st.info("No hay datos de evolución de unidades para este importador.")
            else:
                st.info("💡 *Haz clic en cualquier importador del ranking para ver su portafolio completo.*")

        # ============================================================
        # COMPARATIVA DE IMPORTADORES (EXPANDABLE)
        # ============================================================
        with st.expander("⚔️ Comparativa entre Importadores", expanded=False):
            st.markdown("### Comparación Detallada entre Importadores")
            
            if 'grupo_importador' in df_actual.columns:
                imps_h2h = sorted(df_actual['grupo_importador'].dropna().unique())
                if len(imps_h2h) >= 2:
                    ci_h1, ci_h2 = st.columns(2)
                    with ci_h1: 
                        i_a = st.selectbox("Importador A", imps_h2h, index=0, key="h2h_ia")
                    with ci_h2: 
                        i_b = st.selectbox("Importador B", imps_h2h, index=min(1, len(imps_h2h)-1), key="h2h_ib")
                    
                    if i_a != i_b:
                        df_ia = df_actual[df_actual['grupo_importador'] == i_a]
                        df_ib = df_actual[df_actual['grupo_importador'] == i_b]
                        
                        # ---- Selector de precio ----
                        st.markdown("##### 💰 Selecciona el valor aduanero para la comparativa:")
                        tipo_precio_comp_i = st.radio(
                            "Tipo de precio:",
                            ["📦 FOB", "🚢 CIF"],
                            horizontal=True,
                            key="tipo_precio_comp_importadores",
                            label_visibility="collapsed"
                        )
                        col_precio_comp_i = COL_FOB if "FOB" in tipo_precio_comp_i else COL_CIF
                        nombre_precio_comp_i = "FOB" if "FOB" in tipo_precio_comp_i else "CIF"
                        
                        # ---- Métricas comparativas (3 bloques) ----
                        st.markdown("##### 📊 Métricas Comparativas")
                        col_m1, col_m2, col_m3 = st.columns([1, 0.3, 1])
                        
                        unidades_ia = len(df_ia)
                        unidades_ib = len(df_ib)
                        share_ia = (unidades_ia / total_actual * 100) if total_actual > 0 else 0
                        share_ib = (unidades_ib / total_actual * 100) if total_actual > 0 else 0
                        
                        if col_precio_comp_i and col_precio_comp_i in df_ia.columns:
                            precio_ia = df_ia[col_precio_comp_i].mean()
                        else:
                            precio_ia = None
                        
                        if col_precio_comp_i and col_precio_comp_i in df_ib.columns:
                            precio_ib = df_ib[col_precio_comp_i].mean()
                        else:
                            precio_ib = None
                        
                        diff_unidades_i = unidades_ib - unidades_ia
                        diff_unidades_pct_i = ((unidades_ib - unidades_ia) / unidades_ia * 100) if unidades_ia > 0 else 0
                        diff_precio_i = (precio_ib - precio_ia) if (precio_ia is not None and precio_ib is not None) else None
                        diff_precio_pct_i = ((precio_ib - precio_ia) / precio_ia * 100) if (precio_ia is not None and precio_ib is not None and precio_ia > 0) else 0
                        diff_share_i = share_ib - share_ia
                        
                        # BLOQUE 1: IMPORTADOR A
                        with col_m1:
                            precio_ia_str = f"${precio_ia:,.2f}" if precio_ia is not None else "N/A"
                            st.markdown(f"""
                            <div style="background: #F8F9FA; padding: 15px; border-radius: 10px; border: 1px solid #E8E8E8; text-align: center;">
                                <h4 style="margin: 0 0 10px 0; color: #1A1A1A;">🏷️ {i_a}</h4>
                                <div style="font-size: 1.1rem; font-weight: 600; color: #1A1A1A;">{unidades_ia:,}</div>
                                <div style="font-size: 0.75rem; color: #888; margin-bottom: 5px;">📦 Unidades</div>
                                <div style="font-size: 1.1rem; font-weight: 600; color: #1A1A1A;">{precio_ia_str}</div>
                                <div style="font-size: 0.75rem; color: #888; margin-bottom: 5px;">💰 {nombre_precio_comp_i} Promedio</div>
                                <div style="font-size: 1.1rem; font-weight: 600; color: #1A1A1A;">{share_ia:.1f}%</div>
                                <div style="font-size: 0.75rem; color: #888;">📊 Market Share</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # BLOQUE 2: VACÍO
                        with col_m2:
                            st.markdown("""
                            <div style="height: 100%; display: flex; align-items: center; justify-content: center;">
                                <div style="width: 2px; height: 80%; background: #E0E0E0; border-radius: 2px;"></div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # BLOQUE 3: IMPORTADOR B CON DIFERENCIAS
                        with col_m3:
                            color_unidades_i = "#4CAF50" if diff_unidades_i > 0 else "#FF5252" if diff_unidades_i < 0 else "#888"
                            color_precio_i = "#4CAF50" if diff_precio_i is not None and diff_precio_i < 0 else "#FF5252" if diff_precio_i is not None and diff_precio_i > 0 else "#888"
                            color_share_i = "#4CAF50" if diff_share_i > 0 else "#FF5252" if diff_share_i < 0 else "#888"
                            
                            precio_ib_str = f"${precio_ib:,.2f}" if precio_ib is not None else "N/A"
                            
                            if diff_unidades_i > 0:
                                diff_unidades_str_i = f"▲ +{diff_unidades_i:,} ({diff_unidades_pct_i:+.1f}% vs {i_a})"
                            elif diff_unidades_i < 0:
                                diff_unidades_str_i = f"▼ {diff_unidades_i:+,} ({diff_unidades_pct_i:+.1f}% vs {i_a})"
                            else:
                                diff_unidades_str_i = f"±0 ({diff_unidades_pct_i:+.1f}% vs {i_a})"
                            
                            if diff_precio_i is not None:
                                if diff_precio_i > 0:
                                    diff_precio_str_i = f"▲ +{diff_precio_i:,.2f} ({diff_precio_pct_i:+.1f}% vs {i_a})"
                                elif diff_precio_i < 0:
                                    diff_precio_str_i = f"▼ {diff_precio_i:+,.2f} ({diff_precio_pct_i:+.1f}% vs {i_a})"
                                else:
                                    diff_precio_str_i = f"±0 ({diff_precio_pct_i:+.1f}% vs {i_a})"
                            else:
                                diff_precio_str_i = ""
                            
                            if diff_share_i > 0:
                                diff_share_str_i = f"▲ +{diff_share_i:+.1f} pp vs {i_a}"
                            elif diff_share_i < 0:
                                diff_share_str_i = f"▼ {diff_share_i:+.1f} pp vs {i_a}"
                            else:
                                diff_share_str_i = f"±0 pp vs {i_a}"
                            
                            st.markdown(f"""
                            <div style="background: #F8F9FA; padding: 15px; border-radius: 10px; border: 1px solid #E8E8E8; text-align: center;">
                                <h4 style="margin: 0 0 10px 0; color: #1A1A1A;">🏷️ {i_b}</h4>
                                <div style="font-size: 1.1rem; font-weight: 600; color: #1A1A1A;">{unidades_ib:,}</div>
                                <div style="font-size: 0.75rem; color: #888; margin-bottom: 5px;">📦 Unidades</div>
                                <div style="font-size: 0.7rem; color: {color_unidades_i}; margin-top: -3px; margin-bottom: 8px;">{diff_unidades_str_i}</div>
                                <div style="font-size: 1.1rem; font-weight: 600; color: #1A1A1A;">{precio_ib_str}</div>
                                <div style="font-size: 0.75rem; color: #888; margin-bottom: 5px;">💰 {nombre_precio_comp_i} Promedio</div>
                                <div style="font-size: 0.7rem; color: {color_precio_i}; margin-top: -3px; margin-bottom: 8px;">{diff_precio_str_i}</div>
                                <div style="font-size: 1.1rem; font-weight: 600; color: #1A1A1A;">{share_ib:.1f}%</div>
                                <div style="font-size: 0.75rem; color: #888; margin-bottom: 5px;">📊 Market Share</div>
                                <div style="font-size: 0.7rem; color: {color_share_i}; margin-top: -3px;">{diff_share_str_i}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # ---- Tendencia ----
                        st.markdown("##### 📈 Tendencia Mensual")
                        h2h_i_trends = pd.merge(
                            df_ia.groupby('mes_nombre').size().reset_index(name=i_a),
                            df_ib.groupby('mes_nombre').size().reset_index(name=i_b),
                            on='mes_nombre', how='outer'
                        ).fillna(0)
                        h2h_i_trends[[i_a, i_b]] = h2h_i_trends[[i_a, i_b]].astype(int)
                        h2h_i_trends['mes_nombre'] = pd.Categorical(h2h_i_trends['mes_nombre'], categories=MESES_NOMBRES, ordered=True)
                        h2h_i_trends = h2h_i_trends.sort_values('mes_nombre').reset_index(drop=True)
                        
                        fig_h2h_i = px.line(
                            h2h_i_trends.melt(id_vars='mes_nombre', var_name='Importador', value_name='Unidades'),
                            x='mes_nombre', y='Unidades', color='Importador', markers=True,
                            color_discrete_sequence=COLOR_PALETTE
                        )
                        fig_h2h_i.update_layout(plot_bgcolor='white', height=250)
                        st.plotly_chart(fig_h2h_i, use_container_width=True)
                        
                        # ---- Comparación por Segmento (dos tablas separadas - SIN TOTAL) ----
                        st.markdown("##### 📊 Comparación por Segmento")
                        
                        anios_disponibles_i = sorted(set(df_ia['año'].unique()) | set(df_ib['año'].unique()))
                        
                        if anios_disponibles_i:
                            anio_seleccionado_i = st.selectbox(
                                "Selecciona un año para comparar:",
                                anios_disponibles_i,
                                index=len(anios_disponibles_i)-1,
                                key="anio_seg_comp_importadores"
                            )
                            
                            df_ia_anio = df_ia[df_ia['año'] == anio_seleccionado_i]
                            df_ib_anio = df_ib[df_ib['año'] == anio_seleccionado_i]
                            
                            seg_ia = df_ia_anio['categoria_maquinaria'].value_counts().reset_index()
                            seg_ia.columns = ['Segmento', i_a]
                            seg_ib = df_ib_anio['categoria_maquinaria'].value_counts().reset_index()
                            seg_ib.columns = ['Segmento', i_b]
                            
                            seg_comp_i = pd.merge(seg_ia, seg_ib, on='Segmento', how='outer').fillna(0)
                            seg_comp_i = seg_comp_i[seg_comp_i[[i_a, i_b]].sum(axis=1) > 0]
                            seg_comp_i[[i_a, i_b]] = seg_comp_i[[i_a, i_b]].astype(int)
                            
                            fig_seg_comp_i = px.bar(
                                seg_comp_i.melt(id_vars='Segmento', var_name='Importador', value_name='Unidades'),
                                x='Segmento', y='Unidades', color='Importador', barmode='group',
                                color_discrete_sequence=COLOR_PALETTE,
                                title=f"Comparación por Segmento - {anio_seleccionado_i}"
                            )
                            fig_seg_comp_i.update_layout(plot_bgcolor='white', height=250)
                            st.plotly_chart(fig_seg_comp_i, use_container_width=True)
                            
                            st.markdown("##### 📊 Evolución de Unidades por Segmento")
                            
                            col_tabla_ia, col_tabla_ib = st.columns(2)
                            
                            with col_tabla_ia:
                                st.markdown(f"**{i_a}**")
                                
                                evol_seg_ia = df_ia.groupby(['año', 'categoria_maquinaria']).size().reset_index(name='Unidades')
                                evol_seg_ia = evol_seg_ia.pivot(index='categoria_maquinaria', columns='año', values='Unidades').fillna(0).astype(int)
                                evol_seg_ia = evol_seg_ia.reset_index()
                                
                                cols_ia = ['Segmento'] + [str(col) for col in evol_seg_ia.columns if col != 'categoria_maquinaria']
                                evol_seg_ia.columns = cols_ia
                                
                                # Sin columna "Total"
                                if len(evol_seg_ia.columns) > 2:
                                    anios_cols_ia = [col for col in evol_seg_ia.columns if col != 'Segmento']
                                    
                                    if len(anios_cols_ia) >= 2:
                                        primer_anio_ia = anios_cols_ia[0]
                                        ultimo_anio_ia = anios_cols_ia[-1]
                                        evol_seg_ia['Variación %'] = ((evol_seg_ia[ultimo_anio_ia] - evol_seg_ia[primer_anio_ia]) / evol_seg_ia[primer_anio_ia] * 100).replace([float('inf'), -float('inf')], 0).round(1)
                                        evol_seg_ia['Variación %'] = evol_seg_ia['Variación %'].apply(lambda x: f"{x:+.1f}%" if x != 0 else "0%")
                                
                                for col in evol_seg_ia.columns:
                                    if col not in ['Segmento', 'Variación %']:
                                        evol_seg_ia[col] = evol_seg_ia[col].astype(int)
                                
                                st.dataframe(evol_seg_ia, hide_index=True, use_container_width=True)
                            
                            with col_tabla_ib:
                                st.markdown(f"**{i_b}**")
                                
                                evol_seg_ib = df_ib.groupby(['año', 'categoria_maquinaria']).size().reset_index(name='Unidades')
                                evol_seg_ib = evol_seg_ib.pivot(index='categoria_maquinaria', columns='año', values='Unidades').fillna(0).astype(int)
                                evol_seg_ib = evol_seg_ib.reset_index()
                                
                                cols_ib = ['Segmento'] + [str(col) for col in evol_seg_ib.columns if col != 'categoria_maquinaria']
                                evol_seg_ib.columns = cols_ib
                                                                # Sin columna "Total"
                                if len(evol_seg_ib.columns) > 2:
                                    anios_cols_ib = [col for col in evol_seg_ib.columns if col != 'Segmento']
                                    
                                    if len(anios_cols_ib) >= 2:
                                        primer_anio_ib = anios_cols_ib[0]
                                        ultimo_anio_ib = anios_cols_ib[-1]
                                        evol_seg_ib['Variación %'] = ((evol_seg_ib[ultimo_anio_ib] - evol_seg_ib[primer_anio_ib]) / evol_seg_ib[primer_anio_ib] * 100).replace([float('inf'), -float('inf')], 0).round(1)
                                        evol_seg_ib['Variación %'] = evol_seg_ib['Variación %'].apply(lambda x: f"{x:+.1f}%" if x != 0 else "0%")
                                
                                for col in evol_seg_ib.columns:
                                    if col not in ['Segmento', 'Variación %']:
                                        evol_seg_ib[col] = evol_seg_ib[col].astype(int)
                                
                                st.dataframe(evol_seg_ib, hide_index=True, use_container_width=True)
                        else:
                            st.info("No hay datos de años disponibles para comparar.")
                        
                        # ---- TOP MODELOS (del último año) ----
                        st.markdown("##### 🏗️ Top Modelos Importados")
                        
                        ultimo_anio_i = max(set(df_ia['año'].unique()) | set(df_ib['año'].unique()))
                        
                        df_ia_ultimo = df_ia[df_ia['año'] == ultimo_anio_i]
                        df_ib_ultimo = df_ib[df_ib['año'] == ultimo_anio_i]
                        
                        col_mod_i_a, col_mod_i_b = st.columns(2)
                        
                        with col_mod_i_a:
                            st.markdown(f"**Top Modelos - {i_a} ({ultimo_anio_i})**")
                            top_i_a = df_ia_ultimo.groupby([COL_MODELO, 'categoria_maquinaria']).size().reset_index(name='Unidades')
                            top_i_a = top_i_a.sort_values('Unidades', ascending=False).head(10)
                            top_i_a = top_i_a.rename(columns={COL_MODELO: 'Modelo', 'categoria_maquinaria': 'Segmento'})
                            
                            if col_precio_comp_i and col_precio_comp_i in df_ia_ultimo.columns:
                                precio_i_a_top = df_ia_ultimo.groupby([COL_MODELO])[col_precio_comp_i].mean().reset_index()
                                precio_i_a_top.columns = ['Modelo', f'{nombre_precio_comp_i} Promedio']
                                top_i_a = top_i_a.merge(precio_i_a_top, on='Modelo', how='left')
                            
                            format_i_a = {}
                            if f'{nombre_precio_comp_i} Promedio' in top_i_a.columns:
                                format_i_a[f'{nombre_precio_comp_i} Promedio'] = '${:,.2f}'
                            
                            st.dataframe(
                                top_i_a.style.format(format_i_a),
                                hide_index=True, 
                                use_container_width=True
                            )
                        
                        with col_mod_i_b:
                            st.markdown(f"**Top Modelos - {i_b} ({ultimo_anio_i})**")
                            top_i_b = df_ib_ultimo.groupby([COL_MODELO, 'categoria_maquinaria']).size().reset_index(name='Unidades')
                            top_i_b = top_i_b.sort_values('Unidades', ascending=False).head(10)
                            top_i_b = top_i_b.rename(columns={COL_MODELO: 'Modelo', 'categoria_maquinaria': 'Segmento'})
                            
                            if col_precio_comp_i and col_precio_comp_i in df_ib_ultimo.columns:
                                precio_i_b_top = df_ib_ultimo.groupby([COL_MODELO])[col_precio_comp_i].mean().reset_index()
                                precio_i_b_top.columns = ['Modelo', f'{nombre_precio_comp_i} Promedio']
                                top_i_b = top_i_b.merge(precio_i_b_top, on='Modelo', how='left')
                            
                            format_i_b = {}
                            if f'{nombre_precio_comp_i} Promedio' in top_i_b.columns:
                                format_i_b[f'{nombre_precio_comp_i} Promedio'] = '${:,.2f}'
                            
                            st.dataframe(
                                top_i_b.style.format(format_i_b),
                                hide_index=True, 
                                use_container_width=True
                            )
                        
                        # ---- EXPLORAR SEGMENTO ESPECÍFICO (2 COLUMNAS + PESO) ----
                        with st.expander("🔍 Explorar segmento específico", expanded=False):
                            st.markdown("##### Selecciona un segmento para ver detalle:")
                            
                            segmentos_disponibles_i = sorted(set(df_ia['categoria_maquinaria'].unique()) | set(df_ib['categoria_maquinaria'].unique()))
                            if segmentos_disponibles_i:
                                seg_seleccionado_comp_i = st.selectbox(
                                    "Segmento:",
                                    segmentos_disponibles_i,
                                    key="seg_comp_importadores",
                                    label_visibility="collapsed"
                                )
                                
                                df_ia_seg = df_ia[df_ia['categoria_maquinaria'] == seg_seleccionado_comp_i]
                                df_ib_seg = df_ib[df_ib['categoria_maquinaria'] == seg_seleccionado_comp_i]
                                
                                if not df_ia_seg.empty or not df_ib_seg.empty:
                                    st.markdown(f"**Modelos - {seg_seleccionado_comp_i}**")
                                    
                                    col_seg_i_a, col_seg_i_b = st.columns(2)
                                    
                                    with col_seg_i_a:
                                        st.markdown(f"### {i_a}")
                                        if COL_MODELO in df_ia_seg.columns and not df_ia_seg.empty:
                                            modelos_ia_seg = df_ia_seg.groupby([COL_MODELO]).size().reset_index(name='Unidades')
                                            modelos_ia_seg = modelos_ia_seg.rename(columns={COL_MODELO: 'Modelo'})
                                            
                                            if col_precio_comp_i and col_precio_comp_i in df_ia_seg.columns:
                                                precio_ia_seg = df_ia_seg.groupby([COL_MODELO])[col_precio_comp_i].agg(['min', 'mean', 'max']).reset_index()
                                                precio_ia_seg.columns = ['Modelo', f'{nombre_precio_comp_i} Mínimo', f'{nombre_precio_comp_i} Promedio', f'{nombre_precio_comp_i} Máximo']
                                                modelos_ia_seg = modelos_ia_seg.merge(precio_ia_seg, on='Modelo', how='left')
                                            
                                            format_ia_seg = {}
                                            for col in modelos_ia_seg.columns:
                                                if 'Mínimo' in col or 'Promedio' in col or 'Máximo' in col:
                                                    format_ia_seg[col] = '${:,.2f}'
                                            
                                            st.dataframe(
                                                modelos_ia_seg.style.format(format_ia_seg),
                                                hide_index=True, 
                                                use_container_width=True
                                            )
                                        else:
                                            st.info(f"No hay modelos en este segmento para {i_a}")
                                    
                                    with col_seg_i_b:
                                        st.markdown(f"### {i_b}")
                                        if COL_MODELO in df_ib_seg.columns and not df_ib_seg.empty:
                                            modelos_ib_seg = df_ib_seg.groupby([COL_MODELO]).size().reset_index(name='Unidades')
                                            modelos_ib_seg = modelos_ib_seg.rename(columns={COL_MODELO: 'Modelo'})
                                            
                                            if col_precio_comp_i and col_precio_comp_i in df_ib_seg.columns:
                                                precio_ib_seg = df_ib_seg.groupby([COL_MODELO])[col_precio_comp_i].agg(['min', 'mean', 'max']).reset_index()
                                                precio_ib_seg.columns = ['Modelo', f'{nombre_precio_comp_i} Mínimo', f'{nombre_precio_comp_i} Promedio', f'{nombre_precio_comp_i} Máximo']
                                                modelos_ib_seg = modelos_ib_seg.merge(precio_ib_seg, on='Modelo', how='left')
                                            
                                            format_ib_seg = {}
                                            for col in modelos_ib_seg.columns:
                                                if 'Mínimo' in col or 'Promedio' in col or 'Máximo' in col:
                                                    format_ib_seg[col] = '${:,.2f}'
                                            
                                            st.dataframe(
                                                modelos_ib_seg.style.format(format_ib_seg),
                                                hide_index=True, 
                                                use_container_width=True
                                            )
                                        else:
                                            st.info(f"No hay modelos en este segmento para {i_b}")
                                    
                                    # ---- DISTRIBUCIÓN POR PESO SI ES EXCAVADORA (CORREGIDO) ----
                                    if seg_seleccionado_comp_i == "EXCAVADORA" and COL_PESO and COL_PESO in df_ia_seg.columns and COL_PESO in df_ib_seg.columns:
                                        with st.expander("⚖️ Distribución por Peso - EXCAVADORA (Comparativa)", expanded=True):
                                            
                                            st.markdown("##### Comparación de Rangos de Peso")
                                            
                                            peso_ia = df_ia_seg.groupby([COL_PESO]).size().reset_index(name=f'Unidades {i_a}')
                                            peso_ib = df_ib_seg.groupby([COL_PESO]).size().reset_index(name=f'Unidades {i_b}')
                                            
                                            peso_comp_i = pd.merge(peso_ia, peso_ib, on=COL_PESO, how='outer').fillna(0)
                                            peso_comp_i[[f'Unidades {i_a}', f'Unidades {i_b}']] = peso_comp_i[[f'Unidades {i_a}', f'Unidades {i_b}']].astype(int)
                                            peso_comp_i = peso_comp_i.rename(columns={COL_PESO: 'Rango de Peso'})
                                            
                                            fig_peso_comp_i = px.bar(
                                                peso_comp_i.melt(id_vars='Rango de Peso', var_name='Importador', value_name='Unidades'),
                                                x='Rango de Peso', 
                                                y='Unidades', 
                                                color='Importador', 
                                                barmode='group',
                                                color_discrete_sequence=COLOR_PALETTE,
                                                title=f"Distribución por Rango de Peso - {seg_seleccionado_comp_i}"
                                            )
                                            fig_peso_comp_i.update_layout(
                                                plot_bgcolor='white',
                                                height=300,
                                                margin=dict(t=40, b=10, l=10, r=10),
                                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                                            )
                                            st.plotly_chart(fig_peso_comp_i, use_container_width=True)
                                            
                                            st.dataframe(peso_comp_i, hide_index=True, use_container_width=True)
                                            
                                            if col_precio_comp_i and col_precio_comp_i in df_ia_seg.columns and col_precio_comp_i in df_ib_seg.columns:
                                                st.markdown(f"##### 💰 {nombre_precio_comp_i} por Rango de Peso")
                                                
                                                precio_peso_ia = df_ia_seg.groupby([COL_PESO])[col_precio_comp_i].mean().reset_index()
                                                precio_peso_ia.columns = ['Rango de Peso', f'{nombre_precio_comp_i} {i_a}']
                                                
                                                precio_peso_ib = df_ib_seg.groupby([COL_PESO])[col_precio_comp_i].mean().reset_index()
                                                precio_peso_ib.columns = ['Rango de Peso', f'{nombre_precio_comp_i} {i_b}']
                                                
                                                precio_peso_comp_i = pd.merge(precio_peso_ia, precio_peso_ib, on='Rango de Peso', how='outer').fillna(0)
                                                
                                                format_precio_peso_i = {}
                                                if f'{nombre_precio_comp_i} {i_a}' in precio_peso_comp_i.columns:
                                                    format_precio_peso_i[f'{nombre_precio_comp_i} {i_a}'] = '${:,.2f}'
                                                if f'{nombre_precio_comp_i} {i_b}' in precio_peso_comp_i.columns:
                                                    format_precio_peso_i[f'{nombre_precio_comp_i} {i_b}'] = '${:,.2f}'
                                                
                                                st.dataframe(
                                                    precio_peso_comp_i.style.format(format_precio_peso_i),
                                                    hide_index=True, 
                                                    use_container_width=True
                                                )
                                            
                                            st.markdown("##### 📈 Evolución de Unidades por Rango de Peso")
                                            
                                            # ✅ CORREGIDO: Usar 'año' (minúscula)
                                            evol_peso_ia = df_ia_seg.groupby(['año', COL_PESO]).size().reset_index(name='Unidades')
                                            evol_peso_ia = evol_peso_ia.pivot(index='año', columns=COL_PESO, values='Unidades').fillna(0).astype(int)
                                            evol_peso_ia = evol_peso_ia.reset_index()
                                            evol_peso_ia.columns = ['año'] + [str(col) for col in evol_peso_ia.columns if col != 'año']
                                            
                                            evol_peso_ib = df_ib_seg.groupby(['año', COL_PESO]).size().reset_index(name='Unidades')
                                            evol_peso_ib = evol_peso_ib.pivot(index='año', columns=COL_PESO, values='Unidades').fillna(0).astype(int)
                                            evol_peso_ib = evol_peso_ib.reset_index()
                                            evol_peso_ib.columns = ['año'] + [str(col) for col in evol_peso_ib.columns if col != 'año']
                                            
                                            col_evol_ia, col_evol_ib = st.columns(2)
                                            
                                            with col_evol_ia:
                                                st.markdown(f"**{i_a}**")
                                                st.dataframe(evol_peso_ia, hide_index=True, use_container_width=True)
                                            
                                            with col_evol_ib:
                                                st.markdown(f"**{i_b}**")
                                                st.dataframe(evol_peso_ib, hide_index=True, use_container_width=True)
                                else:
                                    st.info(f"No hay modelos en el segmento {seg_seleccionado_comp_i} para los importadores seleccionados.")
                            else:
                                st.info("No hay segmentos disponibles para los importadores seleccionados.")
                        
                        # ---- EVOLUCIÓN DE PRECIOS EN COMPARATIVA ----
                        if col_precio_comp_i and col_precio_comp_i in df_ia.columns and col_precio_comp_i in df_ib.columns:
                            with st.expander("📈 Ver evolución de precios en el tiempo", expanded=False):
                                st.markdown(f"##### Evolución de {nombre_precio_comp_i} Promedio")
                                
                                evol_ia_comp = df_ia.groupby(['año', 'mes', 'mes_nombre'])[col_precio_comp_i].mean().reset_index()
                                evol_ia_comp['periodo'] = evol_ia_comp['mes_nombre'] + ' ' + evol_ia_comp['año'].astype(str)
                                evol_ia_comp = evol_ia_comp.sort_values(['año', 'mes'])
                                evol_ia_comp['Importador'] = i_a
                                
                                evol_ib_comp = df_ib.groupby(['año', 'mes', 'mes_nombre'])[col_precio_comp_i].mean().reset_index()
                                evol_ib_comp['periodo'] = evol_ib_comp['mes_nombre'] + ' ' + evol_ib_comp['año'].astype(str)
                                evol_ib_comp = evol_ib_comp.sort_values(['año', 'mes'])
                                evol_ib_comp['Importador'] = i_b
                                
                                evol_combined_i = pd.concat([evol_ia_comp, evol_ib_comp])
                                
                                if not evol_combined_i.empty:
                                    fig_evol_comp_i = px.line(
                                        evol_combined_i,
                                        x='periodo',
                                        y=col_precio_comp_i,
                                        color='Importador',
                                        markers=True,
                                        title=f"Evolución de {nombre_precio_comp_i} Promedio",
                                        color_discrete_sequence=COLOR_PALETTE
                                    )
                                    fig_evol_comp_i.update_layout(
                                        plot_bgcolor='white',
                                        height=300,
                                        margin=dict(t=40, b=10, l=10, r=10),
                                        xaxis_title="Período",
                                        yaxis_title=f"{nombre_precio_comp_i} ($)"
                                    )
                                    fig_evol_comp_i.update_traces(
                                        hovertemplate=f"{nombre_precio_comp_i}: $%{{y:,.2f}}<br>Periodo: %{{x}}<br>Importador: %{{fullData.name}}<extra></extra>"
                                    )
                                    st.plotly_chart(fig_evol_comp_i, use_container_width=True)
                                else:
                                    st.info("No hay datos suficientes para mostrar la evolución de precios.")
                else:
                    st.warning("⚠️ No hay suficientes importadores para comparar en el período seleccionado.")
# ============================================================
# TAB 3: NEW HOLLAND
# ============================================================
with tab3:
    # ✅ Usar df_actual que ya tiene los filtros globales aplicados (fechas + categorías)
    if COL_MARCA in df_actual.columns and MARCA_PROPIA in df_actual[COL_MARCA].unique():
        nh_act = df_actual[df_actual[COL_MARCA] == MARCA_PROPIA]
        st.markdown(f"## 🟡 {MARCA_PROPIA}")
        
        # --- MÉTRICAS GENERALES ---
        col_n1, col_n2, col_n3 = st.columns(3)
        with col_n1: 
            st.metric("📦 Unidades Totales", f"{len(nh_act):,}")
        with col_n2: 
            st.metric("📊 Market Share Total", f"{((len(nh_act)/total_actual*100) if total_actual>0 else 0):.1f}%")
        with col_n3: 
            num_importadores = nh_act['grupo_importador'].nunique() if 'grupo_importador' in nh_act.columns else 0
            st.metric("🏢 Importadores", f"{num_importadores}")
        
        st.divider()
        
        # --- 1. TODOS LOS IMPORTADORES (DEALERS) DE NEW HOLLAND ---
        st.markdown("### 🏢 Distribución por Importador")
        
        if 'grupo_importador' in nh_act.columns:
            importadores_nh = nh_act['grupo_importador'].value_counts().reset_index()
            importadores_nh.columns = ['Importador', 'Unidades']
            importadores_nh = importadores_nh[importadores_nh['Unidades'] > 0]
            importadores_nh['% Share'] = (importadores_nh['Unidades'] / importadores_nh['Unidades'].sum() * 100).round(1)
            importadores_nh = importadores_nh.sort_values('Unidades', ascending=False)
            
            if not importadores_nh.empty:
                fig_importadores = px.bar(
                    importadores_nh,
                    x='Importador',
                    y='Unidades',
                    text_auto=True,
                    color='Importador',
                    color_discrete_sequence=COLOR_PALETTE,
                    title=f"Distribución de {MARCA_PROPIA} por Importador"
                )
                fig_importadores.update_layout(
                    plot_bgcolor='white',
                    height=300,
                    margin=dict(t=30, b=5, l=5, r=5),
                    showlegend=False
                )
                st.plotly_chart(fig_importadores, use_container_width=True)
                
                st.dataframe(
                    importadores_nh,
                    hide_index=True,
                    use_container_width=True
                )
                
                # --- 2. DESGLOSE POR IMPORTADOR ---
                st.markdown("### 🔍 Detalle por Importador")
                
                importador_seleccionado = st.selectbox(
                    "Selecciona un importador para ver su detalle:",
                    importadores_nh['Importador'].tolist(),
                    key="importador_nh_sel"
                )
                
                if importador_seleccionado:
                    df_importador = nh_act[nh_act['grupo_importador'] == importador_seleccionado]
                    
                    col_imp1, col_imp2, col_imp3 = st.columns(3)
                    with col_imp1:
                        st.metric("📦 Unidades", f"{len(df_importador):,}")
                    with col_imp2:
                        num_segmentos = df_importador['categoria_maquinaria'].nunique()
                        st.metric("📂 Segmentos", f"{num_segmentos}")
                    with col_imp3:
                        num_modelos = df_importador[COL_MODELO].nunique() if COL_MODELO in df_importador.columns else 0
                        st.metric("🏗️ Modelos", f"{num_modelos}")
                    
                    if COL_FOB and COL_FOB in df_importador.columns:
                        st.markdown("##### 💰 Precios")
                        col_fob, col_cif = st.columns(2)
                        with col_fob:
                            fob_prom = df_importador[COL_FOB].mean()
                            st.metric("FOB Promedio", f"${fob_prom:,.2f}")
                        with col_cif:
                            if COL_CIF and COL_CIF in df_importador.columns:
                                cif_prom = df_importador[COL_CIF].mean()
                                st.metric("CIF Promedio", f"${cif_prom:,.2f}")
                    
                    st.markdown("##### 🏗️ Top Modelos")
                    if COL_MODELO in df_importador.columns:
                        top_modelos_imp = df_importador.groupby([COL_MODELO, 'categoria_maquinaria']).size().reset_index(name='Unidades')
                        top_modelos_imp = top_modelos_imp.sort_values('Unidades', ascending=False).head(10)
                        top_modelos_imp = top_modelos_imp.rename(columns={COL_MODELO: 'Modelo', 'categoria_maquinaria': 'Segmento'})
                        st.dataframe(top_modelos_imp, hide_index=True, use_container_width=True)
                    
                    st.markdown("##### 📈 Evolución de Unidades")
                    evol_importador = df_importador.groupby(['año', 'mes', 'mes_nombre']).size().reset_index(name='Unidades')
                    evol_importador['periodo'] = evol_importador['mes_nombre'] + ' ' + evol_importador['año'].astype(str)
                    evol_importador = evol_importador.sort_values(['año', 'mes'])
                    
                    if not evol_importador.empty:
                        fig_evol_imp = px.line(
                            evol_importador,
                            x='periodo',
                            y='Unidades',
                            markers=True,
                            title=f"Evolución de Unidades - {importador_seleccionado}",
                            color_discrete_sequence=['#FF8C00']
                        )
                        fig_evol_imp.update_layout(
                            plot_bgcolor='white',
                            height=250,
                            margin=dict(t=30, b=5, l=5, r=5),
                            xaxis_title="Período",
                            yaxis_title="Unidades"
                        )
                        st.plotly_chart(fig_evol_imp, use_container_width=True)
            else:
                st.info(f"No hay importadores registrados para {MARCA_PROPIA} en el período seleccionado.")
        else:
            st.info("No hay información de importadores para NEW HOLLAND.")
        
        st.divider()
        
        # --- 3. DISTRIBUCIÓN POR SEGMENTO (SOLO CON UNIDADES > 0) ---
        st.markdown("### 📊 Distribución por Segmento")
        
        # ✅ Filtrar solo segmentos con unidades > 0
        seg_nh = nh_act['categoria_maquinaria'].value_counts().reset_index()
        seg_nh.columns = ['Segmento', 'Unidades']
        seg_nh = seg_nh[seg_nh['Unidades'] > 0]  # <--- FILTRO CRÍTICO
        seg_nh['% Share'] = (seg_nh['Unidades'] / seg_nh['Unidades'].sum() * 100).round(1)
        seg_nh = seg_nh.sort_values('Unidades', ascending=False)
        
        if not seg_nh.empty:
            fig_seg_nh = px.pie(
                seg_nh,
                values='Unidades',
                names='Segmento',
                hole=0.4,
                title=f"Distribución de {MARCA_PROPIA} por Segmento",
                color_discrete_sequence=COLOR_PALETTE
            )
            fig_seg_nh.update_layout(height=350)
            st.plotly_chart(fig_seg_nh, use_container_width=True)
            
            st.dataframe(seg_nh, hide_index=True, use_container_width=True)
        else:
            st.info(f"No hay datos de segmentos para {MARCA_PROPIA} en el período seleccionado.")
        
        st.divider()
        
        # --- 4. TOP MODELOS DE NEW HOLLAND ---
        st.markdown("### 🏗️ Top Modelos de NEW HOLLAND")
        
        if COL_MODELO in nh_act.columns and not nh_act.empty:
            top_modelos_nh = nh_act.groupby([COL_MODELO, 'categoria_maquinaria']).size().reset_index(name='Unidades')
            top_modelos_nh = top_modelos_nh.sort_values('Unidades', ascending=False).head(15)
            top_modelos_nh = top_modelos_nh.rename(columns={COL_MODELO: 'Modelo', 'categoria_maquinaria': 'Segmento'})
            
            # Selector FOB/CIF para top modelos
            if COL_FOB and COL_FOB in nh_act.columns:
                tiene_cif_nh = COL_CIF and COL_CIF in nh_act.columns
                
                if tiene_cif_nh:
                    st.markdown("##### 💰 Selecciona el valor aduanero:")
                    tipo_precio_nh = st.radio(
                        "Tipo de precio:",
                        ["📦 FOB", "🚢 CIF"],
                        horizontal=True,
                        key="tipo_precio_nh",
                        label_visibility="collapsed"
                    )
                    col_precio_nh = COL_FOB if "FOB" in tipo_precio_nh else COL_CIF
                    nombre_precio_nh = "FOB" if "FOB" in tipo_precio_nh else "CIF"
                else:
                    col_precio_nh = COL_FOB
                    nombre_precio_nh = "FOB"
                
                if col_precio_nh and col_precio_nh in nh_act.columns:
                    precio_nh = nh_act.groupby([COL_MODELO])[col_precio_nh].mean().reset_index()
                    precio_nh.columns = ['Modelo', f'{nombre_precio_nh} Promedio']
                    top_modelos_nh = top_modelos_nh.merge(precio_nh, on='Modelo', how='left')
            
            format_nh = {}
            if f'{nombre_precio_nh} Promedio' in top_modelos_nh.columns:
                format_nh[f'{nombre_precio_nh} Promedio'] = '${:,.2f}'
            
            styled_nh = top_modelos_nh.style.format(format_nh)
            styled_nh = styled_nh.apply(lambda r: ['background-color: #FFE0B2; font-weight: bold;'] * len(r), axis=1)
            
            st.dataframe(styled_nh, hide_index=True, use_container_width=True)
            
            # --- GRÁFICO DE EVOLUCIÓN DE PRECIOS ---
            if col_precio_nh and col_precio_nh in nh_act.columns:
                with st.expander("📈 Evolución de Precios de NEW HOLLAND", expanded=False):
                    st.markdown(f"##### Evolución de {nombre_precio_nh} Promedio")
                    
                    evol_precio_nh = nh_act.groupby(['año', 'mes', 'mes_nombre', COL_MODELO])[col_precio_nh].mean().reset_index()
                    evol_precio_nh['periodo'] = evol_precio_nh['mes_nombre'] + ' ' + evol_precio_nh['año'].astype(str)
                    evol_precio_nh = evol_precio_nh.sort_values(['año', 'mes'])
                    
                    ver_todos_nh = st.checkbox("Mostrar todos los modelos", value=False, key="ver_todos_nh")
                    
                    if not ver_todos_nh:
                        top_5_nh = top_modelos_nh['Modelo'].head(5).tolist()
                        evol_precio_nh = evol_precio_nh[evol_precio_nh[COL_MODELO].isin(top_5_nh)]
                    
                    if not evol_precio_nh.empty:
                        fig_evol_precio_nh = px.line(
                            evol_precio_nh,
                            x='periodo',
                            y=col_precio_nh,
                            color=COL_MODELO,
                            markers=True,
                            title=f"Evolución de {nombre_precio_nh} por Modelo",
                            color_discrete_sequence=COLOR_PALETTE
                        )
                        fig_evol_precio_nh.update_layout(
                            plot_bgcolor='white',
                            height=350,
                            margin=dict(t=40, b=10, l=10, r=10),
                            xaxis_title="Período",
                            yaxis_title=f"{nombre_precio_nh} ($)",
                            legend=dict(title="Modelo", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                        st.plotly_chart(fig_evol_precio_nh, use_container_width=True)
                    else:
                        st.info("No hay suficientes datos para mostrar la evolución de precios.")
            
            # --- GRÁFICO DE EVOLUCIÓN DE UNIDADES ---
            with st.expander("📦 Evolución de Unidades de NEW HOLLAND", expanded=False):
                st.markdown(f"##### Evolución de Unidades Importadas")
                
                evol_unidades_nh = nh_act.groupby(['año', 'mes', 'mes_nombre', COL_MODELO]).size().reset_index(name='Unidades')
                evol_unidades_nh['periodo'] = evol_unidades_nh['mes_nombre'] + ' ' + evol_unidades_nh['año'].astype(str)
                evol_unidades_nh = evol_unidades_nh.sort_values(['año', 'mes'])
                
                ver_todos_unidades_nh = st.checkbox("Mostrar todos los modelos", value=False, key="ver_todos_unidades_nh")
                
                if not ver_todos_unidades_nh:
                    top_5_nh = top_modelos_nh['Modelo'].head(5).tolist()
                    evol_unidades_nh = evol_unidades_nh[evol_unidades_nh[COL_MODELO].isin(top_5_nh)]
                
                if not evol_unidades_nh.empty:
                    fig_evol_unidades_nh = px.line(
                        evol_unidades_nh,
                        x='periodo',
                        y='Unidades',
                        color=COL_MODELO,
                        markers=True,
                        title=f"Evolución de Unidades por Modelo",
                        color_discrete_sequence=COLOR_PALETTE
                    )
                    fig_evol_unidades_nh.update_layout(
                        plot_bgcolor='white',
                        height=350,
                        margin=dict(t=40, b=10, l=10, r=10),
                        xaxis_title="Período",
                        yaxis_title="Unidades",
                        legend=dict(title="Modelo", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig_evol_unidades_nh, use_container_width=True)
                else:
                    st.info("No hay suficientes datos para mostrar la evolución de unidades.")
    else:
        st.warning(f"No se encontraron datos para {MARCA_PROPIA} en el período seleccionado.")

# ============ FOOTER ============
st.divider()
f_datos = datetime.fromtimestamp(ULTIMA_ACTUALIZACION).strftime('%d/%m/%Y %H:%M') if ULTIMA_ACTUALIZACION else datetime.now().strftime('%d/%m/%Y %H:%M')
st.caption(f"Pipeline Gerencial v16.0 Clean Treemap | {len(df):,} registros auditados | Fuente: Veritrade | Sincronizado al: {f_datos}")