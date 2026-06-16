import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
from calendar import monthrange
from pathlib import Path
from html import escape
import io
import re

# ============ CONFIGURACIÓN DE PÁGINA ============
st.set_page_config(
    page_title="Dashboard Gerencial - Maquinaria",
    page_icon="🚜",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============ CONSTANTES ============
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

# Mapeo y separación estricta de las métricas FOB y CIF
MAPEO_COLUMNAS = {
    'marca_norm': ['marca_norm', 'marca_normalizada'],
    'modelo': ['modelo_match', 'modelo'],
    'categoria_peso': ['categoria_peso', 'rango_peso', 'capacidad'],
    'grupo_importador': ['grupo_importador', 'importador_grupo', 'importador'],
    'valor_fob': ['valor_fob', 'fob', 'fob_usd'],
    'valor_cif': ['valor_cif', 'cif', 'cif_usd']
}

# ============ ESTILOS CSS ============
def cargar_css():
    st.markdown("""
    <style>
        .block-container { padding-left: 1rem !important; padding-right: 1rem !important; max-width: 100% !important; }
        .main { background-color: #F8F9FA; }
        .kpi-container {
            display: flex; justify-content: space-between; background-color: white;
            padding: 15px 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            margin-bottom: 20px; align-items: center; text-align: center;
        }
        .kpi-box { flex: 1; border-right: 1px solid #eee; }
        .kpi-box:last-child { border-right: none; }
        .kpi-title { font-size: 0.95rem; color: #4A5568; font-weight: 700; text-transform: uppercase; }
        .kpi-subtitle { font-size: 0.75rem; color: #888; display: block; margin-top: -2px; }
        .kpi-value { font-size: 1.9rem; color: #1F2937; font-weight: 800; margin-top: 5px; }
        .kpi-var-up { color: #2E8B57; font-weight: 800; font-size: 1.9rem; margin-top: 5px; }
        .kpi-var-down { color: #E74C3C; font-weight: 800; font-size: 1.9rem; margin-top: 5px; }
        .chart-header { 
            display: flex; justify-content: space-between; align-items: center; 
            background-color: #4A5568; color: white; padding: 5px 12px; 
            border-radius: 4px; margin-bottom: 12px; 
        }
        .chart-title-text { font-size: 0.9rem; font-weight: bold; margin: 0; }
    </style>
    """, unsafe_allow_html=True)

cargar_css()

# ============ HELPERS VISUALES Y DE ORDENACIÓN ============
def destacar_fila_nh(row):
    """Pinta la fila de New Holland para fácil ubicación gerencial."""
    if COL_MARCA in row.index and row[COL_MARCA] == MARCA_PROPIA:
        return ['background-color: #FFE0B2; font-weight: bold;'] * len(row)
    if 'Actor Comercial' in row.index and row['Actor Comercial'] == MARCA_PROPIA:
        return ['background-color: #FFE0B2; font-weight: bold;'] * len(row)
    if 'Marca' in row.index and row['Marca'] == MARCA_PROPIA:
        return ['background-color: #FFE0B2; font-weight: bold;'] * len(row)
    if 'mes_nombre' in row.index and row['mes_nombre'] == 'TOTAL YTD':
        return ['background-color: #E2E8F0; font-weight: bold;'] * len(row)
    return [''] * len(row)

def extraer_peso_numerico(val):
    """Helper para ordenar lógicamente rangos de tonelaje de menor a mayor."""
    nums = re.findall(r'\d+', str(val))
    return float(nums[0]) if nums else 0.0

# ============ FUNCIONES UTILITARIAS ============
def normalizar_columnas(df, mapeo):
    df = df.copy()
    for nombre_estandar, posibles_nombres in mapeo.items():
        for nombre in posibles_nombres:
            if nombre in df.columns:
                if nombre != nombre_estandar:
                    df = df.rename(columns={nombre: nombre_estandar})
                break
    return df

def aplicar_filtros(df, cat_sel, marcas_sel, imp_sel, col_marca):
    if cat_sel: df = df[df['categoria_maquinaria'].isin(cat_sel)]
    if marcas_sel: df = df[df[col_marca].isin(marcas_sel)]
    if imp_sel: df = df[df['grupo_importador'].isin(imp_sel)]
    return df

def calc_var(row, col_act, col_ant):
    ant = row[col_ant]
    act = row[col_act]
    if ant == 0: return "+100%" if act > 0 else "0%"
    return f"{((act - ant) / ant * 100):+.1f}%"

@st.cache_data
def descargar_excel_cache(df_tuple, nombre_hoja="Datos"):
    df = pd.DataFrame(df_tuple)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=nombre_hoja, index=False)
    return output.getvalue()

def descargar_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def render_bloque(titulo, fig, df_tabla, key_toggle, key_descarga, nombre_descarga="datos", col_config_table=None):
    """Renderiza Tablas y Gráficos con soporte para descargas y Stylers."""
    raw_df = df_tabla.data if hasattr(df_tabla, 'data') else df_tabla
    
    col_t1, col_t2, col_t3 = st.columns([4, 1, 1])
    with col_t1: st.markdown(f'<div class="chart-header"><p class="chart-title-text">{titulo}</p></div>', unsafe_allow_html=True)
    with col_t2: ver_grafico = st.toggle("📈 Gráfico", key=key_toggle)
    with col_t3:
        with st.popover("📥", use_container_width=True):
            col_xlsx, col_csv = st.columns(2)
            with col_xlsx:
                excel_data = descargar_excel_cache(tuple(raw_df.itertuples(index=False)), key_descarga[:30])
                st.download_button("Excel", data=excel_data, file_name=f"{nombre_descarga}.xlsx", key=f"xlsx_{key_descarga}", use_container_width=True)
            with col_csv:
                st.download_button("CSV", data=descargar_csv(raw_df), file_name=f"{nombre_descarga}.csv", key=f"csv_{key_descarga}", use_container_width=True)
    
    if col_config_table:
        st.dataframe(df_tabla, hide_index=True, use_container_width=True, column_config=col_config_table)
    else:
        st.dataframe(df_tabla, hide_index=True, use_container_width=True)
        
    if ver_grafico and fig is not None: 
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})

# ============ CARGA DE DATOS ============
@st.cache_data(ttl=3600)
def cargar_y_transformar_datos():
    ruta_parquet = Path(__file__).parent / 'datos_maquinaria.parquet'
    if ruta_parquet.exists():
        df = pd.read_parquet(ruta_parquet)
        ultima_actualizacion = ruta_parquet.stat().st_mtime
    else:
        ruta_outputs = Path(__file__).parent / 'outputs'
        files = sorted(ruta_outputs.glob('*_normalizado.xlsx'))
        if not files: return pd.DataFrame(), None, False
        dfs = []
        for f in files:
            try: dfs.append(pd.read_excel(f, sheet_name='normalizado_final'))
            except Exception: pass
        if not dfs: return pd.DataFrame(), None, False
        df = pd.concat(dfs)
        ultima_actualizacion = max(f.stat().st_mtime for f in files)
    
    if 'fecha_dua' not in df.columns: return pd.DataFrame(), None, True
    
    df['fecha'] = pd.to_datetime(df['fecha_dua'])
    df['año'] = df['fecha'].dt.year
    df['mes'] = df['fecha'].dt.month
    df['mes_nombre'] = df['mes'].map({i+1: m for i, m in enumerate(MESES_NOMBRES)})
    df = normalizar_columnas(df, MAPEO_COLUMNAS)
    if df.columns.duplicated().any(): df = df.loc[:, ~df.columns.duplicated()]
    
    columnas_texto = ['categoria_maquinaria', 'marca_norm', 'modelo', 'grupo_importador', 'categoria_peso']
    for col in columnas_texto:
        if col in df.columns:
            try:
                serie = df[col].iloc[:, 0] if isinstance(df[col], pd.DataFrame) else df[col]
                df[col] = serie.astype(str).str.upper().str.strip()
                df[col] = df[col].replace(['NAN', 'NONE', 'NULL', '', ' '], pd.NA)
            except Exception: pass
            
    if 'valor_fob' in df.columns:
        df['valor_fob'] = pd.to_numeric(df['valor_fob'], errors='coerce').fillna(0)
    
    if 'valor_cif' in df.columns:
        df['valor_cif'] = pd.to_numeric(df['valor_cif'], errors='coerce').fillna(0)
        
    for col in ['categoria_maquinaria', 'marca_norm', 'grupo_importador']:
        if col in df.columns: df[col] = df[col].astype('category')
    return df, ultima_actualizacion, False

df, ULTIMA_ACTUALIZACION, falta_columna = cargar_y_transformar_datos()
if df.empty:
    st.error("No se encontraron datos procesables.")
    st.stop()

COL_MARCA = 'marca_norm' if 'marca_norm' in df.columns else 'marca'
COL_MODELO = 'modelo'
COL_PESO = 'categoria_peso' if 'categoria_peso' in df.columns else None
COL_FOB = 'valor_fob' if 'valor_fob' in df.columns else None
COL_CIF = 'valor_cif' if 'valor_cif' in df.columns else None

# ============ CALLBACKS DE PESO ============
def seleccionar_todos_pesos():
    for p in st.session_state.get('pesos_disp', []): st.session_state[f"peso_{p}"] = True
def limpiar_pesos():
    for p in st.session_state.get('pesos_disp', []): st.session_state[f"peso_{p}"] = False

# ============ SIDEBAR ============
with st.sidebar:
    st.markdown("## ⚙️ Parámetros")
    años_disp = sorted(df['año'].dropna().unique())
    año_actual = st.selectbox("📅 Año Base", años_disp, index=len(años_disp)-1)
    
    st.markdown("### 📆 Periodo de Análisis")
    col1, col2 = st.columns(2)
    with col1: mes_ini = st.selectbox("Mes Inicio", MESES_NOMBRES, index=0)
    with col2: mes_fin = st.selectbox("Mes Fin", MESES_NOMBRES, index=len(MESES_NOMBRES)-1)
    
    mes_ini_num = MESES_NOMBRES.index(mes_ini) + 1
    mes_fin_num = MESES_NOMBRES.index(mes_fin) + 1
    año_limite_inf = st.selectbox("📜 Histórico desde", [a for a in años_disp if a <= año_actual], index=0)
    
    _, last_day = monthrange(año_actual, mes_fin_num)
    f_inicio = pd.Timestamp(año_actual, mes_ini_num, 1, 0, 0, 0)
    f_fin = pd.Timestamp(año_actual, mes_fin_num, last_day, 23, 59, 59)
    
    _, last_day_ant = monthrange(año_actual - 1, mes_fin_num)
    f_inicio_ant = pd.Timestamp(año_actual - 1, mes_ini_num, 1, 0, 0, 0)
    f_fin_ant = pd.Timestamp(año_actual - 1, mes_fin_num, last_day_ant, 23, 59, 59)
    
    st.markdown("---")
    cats_disp = sorted([c for c in df['categoria_maquinaria'].unique() if c in CAT_REQUERIDAS])
    cat_sel = st.multiselect("🏗️ Segmentos", cats_disp, default=cats_disp)
    
    with st.expander("🏢 Importadores & 🎯 Marcas"):
        imp_sel = []
        if 'grupo_importador' in df.columns:
            imp_sel = st.multiselect("Importadores", sorted(df['grupo_importador'].dropna().unique()), default=[])
        marcas_sel = st.multiselect("Marcas", sorted(df[COL_MARCA].dropna().unique()), default=[])
    
    st.toggle("🎥 Modo Presentación", key="modo_presentacion")
    if st.button("🔄 Refrescar datos", use_container_width=True):
        st.cache_data.clear(); st.rerun()

if st.session_state.get("modo_presentacion"):
    st.markdown("<style>[data-testid='stSidebar'] { display: none; } [data-testid='collapsedControl'] { display: none; }</style>", unsafe_allow_html=True)

# ============ FILTROS GLOBALES ============
df_actual = df[(df['fecha'] >= f_inicio) & (df['fecha'] <= f_fin)]
df_anterior = df[(df['fecha'] >= f_inicio_ant) & (df['fecha'] <= f_fin_ant)]
df_base = df[(df['año'] >= año_limite_inf) & (df['año'] <= año_actual)]

df_actual = aplicar_filtros(df_actual, cat_sel, marcas_sel, imp_sel, COL_MARCA)
df_anterior = aplicar_filtros(df_anterior, cat_sel, marcas_sel, imp_sel, COL_MARCA)
df_base = aplicar_filtros(df_base, cat_sel, marcas_sel, imp_sel, COL_MARCA)

total_actual = len(df_actual)
total_anterior = len(df_anterior)
var_pct = ((total_actual - total_anterior) / total_anterior * 100) if total_anterior > 0 else None

df_año_ant = aplicar_filtros(df[df['año'] == año_actual - 1], cat_sel, marcas_sel, imp_sel, COL_MARCA)
mes_real = min(mes_fin_num, date.today().month if año_actual == date.today().year else 12)
proyeccion = (total_actual / mes_real * 12) if mes_real > 0 else 0
cierre_anterior = len(df_año_ant)
var_proy = ((proyeccion - cierre_anterior) / cierre_anterior * 100) if cierre_anterior > 0 else 0

# ============ HEADER METRICS ============
var_str = f"{'▲' if var_pct >= 0 else '▼'} {abs(var_pct):.1f}%" if var_pct is not None else "N/D"
var_class = 'kpi-var-up' if (var_pct is not None and var_pct >= 0) else 'kpi-var-down'

st.markdown(f"""
<div class="kpi-container">
    <div style="flex: 2; text-align: left; padding-left: 10px;">
        <h2 style="margin:0; color:#1E448A; font-weight:800;">Reporte Gerencial de Maquinaria</h2>
        <span style="color:#666;">{mes_ini} - {mes_fin} {año_actual} | vs {año_actual-1}</span>
    </div>
    <div class="kpi-box"><div class="kpi-title">{año_actual-1}<span class="kpi-subtitle">Unidades</span></div><div class="kpi-value">{total_anterior:,}</div></div>
    <div class="kpi-box"><div class="kpi-title">{año_actual}<span class="kpi-subtitle">Unidades</span></div><div class="kpi-value">{total_actual:,}</div></div>
    <div class="kpi-box"><div class="kpi-title">Variación Periodo</div><div class="{var_class}">{var_str}</div></div>
    <div class="kpi-box"><div class="kpi-title">Proy. Cierre {año_actual}</div><div class="kpi-value">{proyeccion:,.0f}</div><span style="font-size:0.8rem; color:{'#2E8B57' if var_proy >=0 else '#E74C3C'}">{var_proy:+.1f}% vs {año_actual-1}</span></div>
</div>
""", unsafe_allow_html=True)

# ============ ALERTA DE CRECIMIENTO CRÍTICO ============
with st.expander("🚀 Radar de Aceleración y Crecimiento Crítico", expanded=True):
    modo_radar = st.radio("Evaluar aceleración táctica por:", ["🏆 Marcas Competidoras", "🏢 Importadores Logísticos"], horizontal=True, key="rad_radar")
    
    if "Marcas" in modo_radar:
        if not df_actual.empty and not df_anterior.empty:
            act_grp = df_actual.groupby([COL_MARCA, 'categoria_maquinaria']).size().reset_index(name='Actual')
            ant_grp = df_anterior.groupby([COL_MARCA, 'categoria_maquinaria']).size().reset_index(name='Anterior')
            
            crec = pd.merge(act_grp, ant_grp, on=[COL_MARCA, 'categoria_maquinaria'], how='outer').fillna(0)
            crec = crec[(crec['Actual'] >= 15) & (crec['Actual'] > crec['Anterior'])]
            
            def calc_crecimiento(row):
                if row['Anterior'] == 0: return 100.0 
                return ((row['Actual'] - row['Anterior']) / row['Anterior']) * 100
            
            crec['%_Crecimiento'] = crec.apply(calc_crecimiento, axis=1)
            alertas = crec[crec['%_Crecimiento'] >= 50].sort_values('%_Crecimiento', ascending=False).reset_index(drop=True)
            
            if alertas.empty:
                st.info("🟢 Sin crecimientos críticos detectados en Marcas frente al año anterior (Filtro base: Mínimo 15 unidades).")
            else:
                st.markdown("🚨 **Marcas con salto significativo en volumen YTD**")
                alertas_view = alertas.copy()
                alertas_view.rename(columns={
                    COL_MARCA: 'Actor Comercial',
                    'categoria_maquinaria': 'Segmento',
                    'Anterior': 'Unid. (Año Ant.)',
                    'Actual': 'Unid. (Año Act.)',
                    '%_Crecimiento': 'Crecimiento (%)'
                }, inplace=True)
                
                alertas_view['Estado'] = alertas_view.apply(lambda r: "🔥 NUEVO INGRESO RELEVANTE" if r['Unid. (Año Ant.)'] == 0 else "🚀 ACELERACIÓN", axis=1)
                
                st.dataframe(
                    alertas_view.style.apply(destacar_fila_nh, axis=1), 
                    hide_index=True, 
                    use_container_width=True,
                    column_config={
                        "Unid. (Año Ant.)": st.column_config.NumberColumn(format="%d"),
                        "Unid. (Año Act.)": st.column_config.NumberColumn(format="%d"),
                        "Crecimiento (%)": st.column_config.NumberColumn(format="+%.1f%%")
                    }
                )
        else:
            st.write("⚪ Faltan datos para calcular crecimientos interanuales.")
            
    else:
        if not df_actual.empty and not df_anterior.empty and 'grupo_importador' in df_actual.columns:
            patron_excluir = 'INDEPENDIENTE|OTROS|ESPECIFICADO'
            df_act_imp_limpio = df_actual[~df_actual['grupo_importador'].str.contains(patron_excluir, na=False, case=False)]
            df_ant_imp_limpio = df_anterior[~df_anterior['grupo_importador'].str.contains(patron_excluir, na=False, case=False)]
            
            act_grp_i = df_act_imp_limpio.groupby(['grupo_importador', 'categoria_maquinaria']).size().reset_index(name='Actual')
            ant_grp_i = df_ant_imp_limpio.groupby(['grupo_importador', 'categoria_maquinaria']).size().reset_index(name='Anterior')
            
            crec_i = pd.merge(act_grp_i, ant_grp_i, on=['grupo_importador', 'categoria_maquinaria'], how='outer').fillna(0)
            crec_i = crec_i[(crec_i['Actual'] >= 15) & (crec_i['Actual'] > crec_i['Anterior'])]
            
            def calc_crecimiento_i(row):
                if row['Anterior'] == 0: return 100.0 
                return ((row['Actual'] - row['Anterior']) / row['Anterior']) * 100
            
            crec_i['%_Crecimiento'] = crec_i.apply(calc_crecimiento_i, axis=1)
            alertas_i = crec_i[crec_i['%_Crecimiento'] >= 50].sort_values('%_Crecimiento', ascending=False).reset_index(drop=True)
            
            if alertas_i.empty:
                st.info("🟢 Sin crecimientos críticos detectados en Importadores Logísticos (excluyendo independientes/no especificados).")
            else:
                st.markdown("🚨 **Importadores con salto significativo en volumen YTD**")
                alertas_view_i = alertas_i.copy()
                alertas_view_i.rename(columns={
                    'grupo_importador': 'Actor Comercial',
                    'categoria_maquinaria': 'Segmento',
                    'Anterior': 'Unid. (Año Ant.)',
                    'Actual': 'Unid. (Año Act.)',
                    '%_Crecimiento': 'Crecimiento (%)'
                }, inplace=True)
                
                alertas_view_i['Estado'] = alertas_view_i.apply(lambda r: "🔥 NUEVO INGRESO RELEVANTE" if r['Unid. (Año Ant.)'] == 0 else "🚀 ACELERACIÓN", axis=1)
                
                st.dataframe(
                    alertas_view_i, 
                    hide_index=True, 
                    use_container_width=True,
                    column_config={
                        "Unid. (Año Ant.)": st.column_config.NumberColumn(format="%d"),
                        "Unid. (Año Act.)": st.column_config.NumberColumn(format="%d"),
                        "Crecimiento (%)": st.column_config.NumberColumn(format="+%.1f%%")
                    }
                )
        else:
            st.write("⚪ Faltan datos o columna de importadores para calcular crecimientos interanuales.")

if df_actual.empty: st.warning("Sin datos para el periodo seleccionado."); st.stop()

# ============ CREACIÓN DE PESTAÑAS ============
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Market Share", "🏆 Marcas & Importadores", "⚖️ Por Peso", "💰 Precios FOB / CIF", "🟡 Inteligencia New Holland"
])

# ============================================================
# TAB 1: MARKET SHARE
# ============================================================
with tab1:
    st.markdown('<div class="chart-header"><p class="chart-title-text">📈 Tendencia Mensual Histórica (Con Totales)</p></div>', unsafe_allow_html=True)
    df_tend = df_base[df_base['categoria_maquinaria'].isin(cat_sel if cat_sel else cats_disp)]
    tend_all = df_tend.groupby(['año','mes','mes_nombre']).size().reset_index(name='Unidades')
    tend_all['Año'] = tend_all['año'].astype(str)
    
    tend_tabla = tend_all.pivot_table(index='mes_nombre', columns='Año', values='Unidades', aggfunc='sum').fillna(0)
    tend_tabla = tend_tabla.astype(int).reset_index()
    tend_tabla['mes_nombre'] = pd.Categorical(tend_tabla['mes_nombre'], categories=MESES_NOMBRES, ordered=True)
    tend_tabla = tend_tabla.sort_values('mes_nombre').reset_index(drop=True)
    
    # Agregar Columnas de Totales a la Tabla
    tend_tabla['Total Mes'] = tend_tabla.iloc[:, 1:].sum(axis=1).astype(int)
    
    # Agregar Fila Inferior de Totales Generales
    total_dict = {col: (tend_tabla[col].sum() if col != 'mes_nombre' else 'TOTAL YTD') for col in tend_tabla.columns}
    tend_tabla = pd.concat([tend_tabla, pd.DataFrame([total_dict])], ignore_index=True)
    
    meses_ord = [m for m in MESES_NOMBRES if m in tend_all['mes_nombre'].unique()]
    fig_tend = px.line(tend_all, x='mes_nombre', y='Unidades', color='Año', markers=True, color_discrete_sequence=COLOR_PALETTE)
    fig_tend.update_layout(plot_bgcolor='white', height=450, xaxis={'categoryorder':'array','categoryarray':meses_ord})
    
    render_bloque("", fig_tend, tend_tabla.style.apply(destacar_fila_nh, axis=1), "tgl_tend", "desc_tend", "tendencia_mensual")
    
    st.divider()
    st.markdown('<div class="chart-header"><p class="chart-title-text">📋 Variación Anual por Segmento (De Lado a Lado)</p></div>', unsafe_allow_html=True)
    años_lista = sorted(df_base['año'].unique()) 
    resumen = []
    for cat in (cat_sel if cat_sel else cats_disp):
        fila = {'Segmento': cat}
        prev = None
        for a in años_lista:
            val = len(df_base[(df_base['año']==a) & (df_base['mes'].between(mes_ini_num, mes_fin_num)) & (df_base['categoria_maquinaria']==cat)])
            fila[f"{a}"] = val
            if prev is not None and prev > 0: fila[f"VAR {a}"] = f"{((val-prev)/prev*100):+.1f}%"
            prev = val
        if any(fila[f"{a}"] > 0 for a in años_lista): resumen.append(fila)
    st.dataframe(pd.DataFrame(resumen), hide_index=True, use_container_width=True)

    st.divider()
    col_sh_l, col_sh_r = st.columns(2)
    with col_sh_l:
        share = df_actual['categoria_maquinaria'].value_counts().reset_index()
        share.columns = ['Categoria', 'Unidades']
        share = share[(share['Categoria'].isin(cat_sel if cat_sel else cats_disp)) & (share['Unidades'] > 0)]
        share['% Share'] = (share['Unidades'] / share['Unidades'].sum() * 100).round(1)
        fig_pie = px.pie(share, values='Unidades', names='Categoria', hole=0.4, color_discrete_sequence=COLOR_PALETTE)
        render_bloque("🥧 Desglose de Market Share", fig_pie, share, "tgl_share", "desc_share", "market_share")

# ============================================================
# 🏆 TAB 2: MARCAS & IMPORTADORES
# ============================================================
with tab2:
    modo_actor = st.radio("Ver por:", ["🏆 Marcas", "🏢 Importadores"], horizontal=True, key="radial_modo_actor")
    
    if "Marcas" in modo_actor:
        st.markdown("### 📊 Inteligencia Competitiva de Marcas")
        col_ctrl1, col_ctrl2 = st.columns(2)
        with col_ctrl1: top_n = st.number_input("👁️ Profundidad del Ranking (Top N):", min_value=5, max_value=100, value=10, step=5, key="top_n_m")
        with col_ctrl2:
            segmentos_disponibles = ["TODOS LOS SEGMENTOS"] + sorted(list(cat_sel if cat_sel else cats_disp))
            seg_local_sel = st.selectbox("🏗️ Auditar marcas en el segmento:", segmentos_disponibles, index=0, key="seg_local_m")
            
        st.divider()
        df_act_rank = df_actual[df_actual['categoria_maquinaria'] == seg_local_sel] if seg_local_sel != "TODOS LOS SEGMENTOS" else df_actual.copy()
        df_ant_rank = df_anterior[df_anterior['categoria_maquinaria'] == seg_local_sel] if seg_local_sel != "TODOS LOS SEGMENTOS" else df_anterior.copy()

        rank_act = df_act_rank[COL_MARCA].value_counts().reset_index(name=str(año_actual))
        rank_ant = df_ant_rank[COL_MARCA].value_counts().reset_index(name=str(año_actual-1))
        ranking = rank_act.merge(rank_ant, on=COL_MARCA, how='outer').fillna(0).sort_values(str(año_actual), ascending=False).head(top_n).reset_index(drop=True)
        ranking[[str(año_actual), str(año_actual-1)]] = ranking[[str(año_actual), str(año_actual-1)]].astype(int)
        ranking.insert(0, 'N°', ranking.index + 1)
        ranking['Market Share'] = (ranking[str(año_actual)] / (ranking[str(año_actual)].sum() if ranking[str(año_actual)].sum() > 0 else 1) * 100).round(1).astype(str) + '%'
        ranking['Var Anual'] = ranking.apply(lambda r: calc_var(r, str(año_actual), str(año_actual-1)), axis=1)
        ranking_view = ranking[['N°', COL_MARCA, str(año_actual-1), str(año_actual), 'Var Anual', 'Market Share']]
        
        col_split_l, col_split_r = st.columns([3, 2])
        with col_split_l:
            st.markdown("##### 📋 Tabla de Posiciones de Importación")
            event_marcas = st.dataframe(
                ranking_view.style.apply(destacar_fila_nh, axis=1), 
                hide_index=True, 
                use_container_width=True, 
                on_select="rerun", 
                selection_mode="single-row"
            )
        
        with col_split_r:
            filas_m = event_marcas.selection.rows
            if filas_m:
                marca_unica = ranking_view.iloc[filas_m[0]][COL_MARCA]
                st.markdown(f"#### 🔎 Radiografía: **{marca_unica}**")
                df_fichas = df_act_rank[df_act_rank[COL_MARCA] == marca_unica]
                
                imp_d = df_fichas['grupo_importador'].value_counts().reset_index(name='Unidades')
                imp_d = imp_d[imp_d['Unidades'] > 0]
                fig_imp_d = px.bar(imp_d, x='grupo_importador', y='Unidades', text_auto=True, color_discrete_sequence=['#4A90E2'])
                fig_imp_d.update_layout(plot_bgcolor='white', height=240, margin=dict(t=5, b=5, l=5, r=5))
                render_bloque("🏢 Canales Logísticos", fig_imp_d, imp_d, "tgl_split_imp", "d_split_imp", "importadores_marca")
                
                if COL_MODELO in df_fichas.columns:
                    mod_d = df_fichas.groupby([COL_MODELO, 'categoria_maquinaria']).size().reset_index(name='Unidades')
                    mod_d = mod_d[mod_d['Unidades'] > 0].sort_values('Unidades', ascending=False).head(5)
                    mod_d.rename(columns={'categoria_maquinaria': 'Segmento'}, inplace=True)
                    
                    fig_mod_d = px.bar(mod_d, x=COL_MODELO, y='Unidades', color='Segmento', text_auto=True, color_discrete_sequence=COLOR_PALETTE)
                    fig_mod_d.update_layout(plot_bgcolor='white', height=240, margin=dict(t=5, b=5, l=5, r=5), legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                    render_bloque("🔧 Mix de Modelos", fig_mod_d, mod_d, "tgl_split_mod", "d_split_mod", "modelos_marca")
            else:
                st.info("💡 *Haz clic directamente sobre cualquier celda o palabra del ranking izquierdo para cargar su ficha analítica aquí en tiempo real.*")

        st.divider()
        st.markdown("### ⚔️ Comparador Head-to-Head Estratégico")
        marcas_h2h = sorted(df_actual[COL_MARCA].dropna().unique())
        c_h1, c_h2 = st.columns(2)
        with c_h1: m_a = st.selectbox("Marca Referencia A", marcas_h2h, index=0, key="h2h_ma")
        with c_h2: m_b = st.selectbox("Marca Rival B", marcas_h2h, index=min(1, len(marcas_h2h)-1), key="h2h_mb")
        if m_a != m_b:
            df_ma, df_mb = df_actual[df_actual[COL_MARCA] == m_a], df_actual[df_actual[COL_MARCA] == m_b]
            h2h_trends = pd.merge(df_ma.groupby('mes_nombre').size().reset_index(name=m_a), df_mb.groupby('mes_nombre').size().reset_index(name=m_b), on='mes_nombre', how='outer').fillna(0)
            h2h_trends[[m_a, m_b]] = h2h_trends[[m_a, m_b]].astype(int)
            h2h_trends['mes_nombre'] = pd.Categorical(h2h_trends['mes_nombre'], categories=MESES_NOMBRES, ordered=True)
            h2h_trends = h2h_trends.sort_values('mes_nombre').reset_index(drop=True)
            
            fig_h2h_m = px.line(h2h_trends.melt(id_vars='mes_nombre', var_name='Marca', value_name='Unidades'), x='mes_nombre', y='Unidades', color='Marca', markers=True, color_discrete_map={MARCA_PROPIA: COLOR_NH}, color_discrete_sequence=COLOR_PALETTE)
            fig_h2h_m.update_layout(plot_bgcolor='white', height=350)
            render_bloque("📈 Curva Comparativa Mensual", fig_h2h_m, h2h_trends, "tgl_h2h_m", "d_h2h_m")
            
            st.markdown(f"##### 🩻 Desglose Táctico de Modelos Comercializados YTD")
            col_h2h_l, col_h2h_r = st.columns(2)
            with col_h2h_l:
                st.markdown(f"**Top 5 Modelos — {m_a}**")
                m_a_mods = df_ma.groupby([COL_MODELO, 'categoria_maquinaria']).size().reset_index(name='Unidades').sort_values('Unidades', ascending=False).head(5).reset_index(drop=True)
                m_a_mods.rename(columns={'categoria_maquinaria': 'Segmento'}, inplace=True)
                m_a_mods['Unidades'] = m_a_mods['Unidades'].astype(int)
                st.dataframe(m_a_mods.style.apply(destacar_fila_nh, axis=1) if m_a == MARCA_PROPIA else m_a_mods, hide_index=True, use_container_width=True)
            with col_h2h_r:
                st.markdown(f"**Top 5 Modelos — {m_b}**")
                m_b_mods = df_mb.groupby([COL_MODELO, 'categoria_maquinaria']).size().reset_index(name='Unidades').sort_values('Unidades', ascending=False).head(5).reset_index(drop=True)
                m_b_mods.rename(columns={'categoria_maquinaria': 'Segmento'}, inplace=True)
                m_b_mods['Unidades'] = m_b_mods['Unidades'].astype(int)
                st.dataframe(m_b_mods.style.apply(destacar_fila_nh, axis=1) if m_b == MARCA_PROPIA else m_b_mods, hide_index=True, use_container_width=True)

    else:
        st.markdown("### 🏢 Inteligencia Competitiva de Importadores")
        col_ctrl_i1, col_ctrl_i2 = st.columns(2)
        with col_ctrl_i1: top_n_imp = st.number_input("👁️ Profundidad del Ranking (Top N):", min_value=5, max_value=100, value=10, step=5, key="top_n_i")
        with col_ctrl_i2:
            seg_imp_disp = ["TODOS LOS SEGMENTOS"] + sorted(list(cat_sel if cat_sel else cats_disp))
            seg_local_imp_sel = st.selectbox("🏗️ Auditar importadores en el segmento:", seg_imp_disp, index=0, key="seg_local_i")
            
        st.divider()
        df_act_imp = df_actual[df_actual['categoria_maquinaria'] == seg_local_imp_sel] if seg_local_imp_sel != "TODOS LOS SEGMENTOS" else df_actual.copy()
        df_ant_imp = df_anterior[df_anterior['categoria_maquinaria'] == seg_local_imp_sel] if seg_local_imp_sel != "TODOS LOS SEGMENTOS" else df_anterior.copy()

        rank_imp_act = df_act_imp['grupo_importador'].value_counts().reset_index(name=str(año_actual))
        rank_imp_ant = df_ant_imp['grupo_importador'].value_counts().reset_index(name=str(año_actual-1))
        ranking_imp = rank_imp_act.merge(rank_imp_ant, on='grupo_importador', how='outer').fillna(0).sort_values(str(año_actual), ascending=False).head(top_n_imp).reset_index(drop=True)
        ranking_imp[[str(año_actual), str(año_actual-1)]] = ranking_imp[[str(año_actual), str(año_actual-1)]].astype(int)
        ranking_imp.insert(0, 'N°', ranking_imp.index + 1)
        ranking_imp['Market Share'] = (ranking_imp[str(año_actual)] / (ranking_imp[str(año_actual)].sum() if ranking_imp[str(año_actual)].sum() > 0 else 1) * 100).round(1).astype(str) + '%'
        ranking_imp['Var Anual'] = ranking_imp.apply(lambda r: calc_var(r, str(año_actual), str(año_actual-1)), axis=1)
        ranking_imp_view = ranking_imp[['N°', 'grupo_importador', str(año_actual-1), str(año_actual), 'Var Anual', 'Market Share']]
        
        col_split_imp_l, col_split_imp_r = st.columns([3, 2])
        with col_split_imp_l:
            st.markdown("##### 📋 Distribución de Cuotas Aduaneras")
            event_imps = st.dataframe(ranking_imp_view, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row")
        
        with col_split_imp_r:
            filas_i = event_imps.selection.rows
            if filas_i:
                imp_unico = ranking_imp_view.iloc[filas_i[0]]['grupo_importador']
                st.markdown(f"#### 🏢 Carpeta Comercial: **{imp_unico}**")
                df_fichas_imp = df_act_imp[df_act_imp['grupo_importador'] == imp_unico]
                
                m_data = df_fichas_imp[COL_MARCA].value_counts().reset_index(name='Unidades')
                m_data = m_data[m_data['Unidades'] > 0]
                fig_m_data = px.bar(m_data, x=COL_MARCA, y='Unidades', text_auto=True, color_discrete_sequence=['#F39C12'])
                fig_m_data.update_layout(plot_bgcolor='white', height=240, margin=dict(t=5, b=5, l=5, r=5))
                render_bloque("🏗️ Portafolio de Marcas", fig_m_data, m_data, "tgl_split_mimp", "d_split_mimp", "marcas_importador")
                
                cat_d = df_fichas_imp['categoria_maquinaria'].value_counts().reset_index(name='Unidades')
                cat_d = cat_d[cat_d['Unidades'] > 0]
                fig_cat_d = px.pie(cat_d, values='Unidades', names='categoria_maquinaria', hole=0.3, color_discrete_sequence=COLOR_PALETTE)
                fig_cat_d.update_layout(height=240, margin=dict(t=5, b=5, l=5, r=5))
                render_bloque("⚖️ Core Business (Segmentos)", fig_cat_d, cat_d, "tgl_split_catimp", "d_split_catimp", "segmentos_importador")
            else:
                st.info("💡 *Haz clic encima de cualquier importador para auditar su mix de marcas y especialización de maquinaria de inmediato.*")

        st.divider()
        st.markdown("## ⚔️ Comparador Head-to-Head (Importadores)")
        if 'grupo_importador' in df_actual.columns:
            imps_h2h = sorted(df_actual['grupo_importador'].dropna().unique())
            ci_h1, ci_h2 = st.columns(2)
            with ci_h1: i_a = st.selectbox("Importador A", imps_h2h, index=0, key="h2h_ia")
            with ci_h2: i_b = st.selectbox("Importador B", imps_h2h, index=min(1, len(imps_h2h)-1), key="h2h_ib")
            if i_a != i_b:
                df_ia, df_ib = df_actual[df_actual['grupo_importador'] == i_a], df_actual[df_actual['grupo_importador'] == i_b]
                h2h_i_trends = pd.merge(df_ia.groupby('mes_nombre').size().reset_index(name=i_a), df_ib.groupby('mes_nombre').size().reset_index(name=i_b), on='mes_nombre', how='outer').fillna(0)
                h2h_i_trends[[i_a, i_b]] = h2h_i_trends[[i_a, i_b]].astype(int)
                h2h_i_trends['mes_nombre'] = pd.Categorical(h2h_i_trends['mes_nombre'], categories=MESES_NOMBRES, ordered=True)
                h2h_i_trends = h2h_i_trends.sort_values('mes_nombre').reset_index(drop=True)
                
                fig_h2h_i = px.line(h2h_i_trends.melt(id_vars='mes_nombre', var_name='Importador', value_name='Unidades'), x='mes_nombre', y='Unidades', color='Importador', markers=True)
                fig_h2h_i.update_layout(plot_bgcolor='white', height=350)
                render_bloque("📈 Comparativa Logística Mensual", fig_h2h_i, h2h_i_trends, "tgl_h2h_i", "d_h2h_i")

# ============================================================
# TAB 3: POR PESO (TREEMAP CLEAN)
# ============================================================
with tab3:
    if not COL_PESO: st.warning("No se localizó columna de pesos en el dataset.")
    else:
        seg_peso = st.selectbox("⚖️ Segmento para Evaluar Peso:", cat_sel if cat_sel else cats_disp)
        df_seg = df_actual[df_actual['categoria_maquinaria'] == seg_peso]
        if not df_seg.empty:
            pesos_disp = sorted(df_seg[COL_PESO].dropna().unique(), key=extraer_peso_numerico)
            st.session_state['pesos_disp'] = pesos_disp
            
            col_pa, col_pl = st.columns(2)
            with col_pa: st.button("✅ Todos", key="p_all_t3", on_click=seleccionar_todos_pesos)
            with col_pl: st.button("❌ Limpiar", key="p_none_t3", on_click=limpiar_pesos)
            
            cols_chk = st.columns(min(len(pesos_disp), 5))
            pesos_sel = [p for i, p in enumerate(pesos_disp) if cols_chk[i % len(cols_chk)].checkbox(str(p), value=True, key=f"peso_{p}")]
            
            if pesos_sel:
                df_peso = df_seg[df_seg[COL_PESO].isin(pesos_sel)].copy()
                p_cat = df_peso.groupby([COL_PESO, COL_MARCA]).size().reset_index(name='Unidades')
                p_cat = p_cat[p_cat['Unidades'] > 0]
                
                p_cat[COL_MARCA] = p_cat[COL_MARCA].astype(str)
                p_cat[COL_PESO] = p_cat[COL_PESO].astype(str)
                
                # 🟢 NUEVO: Colorear por categoría de peso, excepto New Holland
                p_cat['Color_Treemap'] = p_cat.apply(lambda r: MARCA_PROPIA if r[COL_MARCA] == MARCA_PROPIA else r[COL_PESO], axis=1)
                
                fig_pb = px.treemap(
                    p_cat,
                    path=[COL_PESO, COL_MARCA], 
                    values='Unidades',
                    color='Color_Treemap',            
                    color_discrete_map={MARCA_PROPIA: COLOR_NH},
                    color_discrete_sequence=COLOR_PALETTE
                )
                
                fig_pb.update_traces(textinfo="label+value", textfont=dict(size=12))
                fig_pb.update_layout(margin=dict(t=10, b=10, l=5, r=5), height=450)
                
                peso_tabla = p_cat.pivot(index=COL_MARCA, columns=COL_PESO, values='Unidades').fillna(0)
                peso_tabla = peso_tabla.astype(int).reset_index()
                
                cols_ordenadas = [COL_MARCA] + [p for p in pesos_disp if p in peso_tabla.columns]
                peso_tabla = peso_tabla[cols_ordenadas]
                
                render_bloque("⚖️ Distribución Estructural por Rango de Peso", fig_pb, peso_tabla.style.apply(destacar_fila_nh, axis=1), "tgl_peso_b", "d_peso_b")
                
                if COL_MODELO in df_peso.columns:
                    st.divider()
                    st.markdown("#### 🎯 Enfoque Láser: Anatomía de Modelos por Fabricante")
                    marcas_visibles = sorted(df_peso[COL_MARCA].dropna().unique())
                    
                    NH_default_idx = marcas_visibles.index(MARCA_PROPIA) if MARCA_PROPIA in marcas_visibles else 0
                    marca_laser = st.selectbox("🎯 Selecciona una marca del Treemap para desglosar sus modelos:", marcas_visibles, index=NH_default_idx)
                    
                    df_laser = df_peso[df_peso[COL_MARCA] == marca_laser]
                    
                    tabla_laser = df_laser.groupby([COL_MODELO, 'categoria_maquinaria', COL_PESO]).size().reset_index(name='Unidades')
                    tabla_laser = tabla_laser.sort_values('Unidades', ascending=False).reset_index(drop=True)
                    tabla_laser['Unidades'] = tabla_laser['Unidades'].astype(int)
                    tabla_laser.rename(columns={COL_MODELO: 'Modelo Comercial', 'categoria_maquinaria': 'Segmento', COL_PESO: 'Rango de Peso'}, inplace=True)
                    
                    if marca_laser == MARCA_PROPIA:
                        st.dataframe(tabla_laser.style.apply(lambda r: ['background-color: #FFE0B2; font-weight: bold;'] * len(r), axis=1), hide_index=True, use_container_width=True)
                    else:
                        st.dataframe(tabla_laser, hide_index=True, use_container_width=True)

# ============================================================
# TAB 4: FOB / CIF TREND
# ============================================================
with tab4:
    st.markdown("## 💰 Inteligencia de Precios (Trend FOB / CIF)")
    
    tipo_costo = st.radio("🔎 Selecciona el valor aduanero a auditar:", ["📦 Valor FOB (Origen)", "🚢 Valor CIF (Puesto en Puerto)"], horizontal=True)
    col_activa = COL_FOB if "FOB" in tipo_costo else COL_CIF
    metric_name = "FOB" if "FOB" in tipo_costo else "CIF"
    
    if col_activa and df_actual[col_activa].sum() > 0:
        df_val = df_actual[df_actual[col_activa] > 0].copy()
        val_trend = df_val.groupby(['año','mes','mes_nombre',COL_MARCA]).agg(val_prom=(col_activa, 'mean')).reset_index()
        val_trend['periodo'] = val_trend['mes_nombre'] + ' ' + val_trend['año'].astype(str)
        t5_val = [m for m in df_actual[COL_MARCA].value_counts().head(5).index if m in val_trend[COL_MARCA].unique()]
        
        marcas_val = st.multiselect(f"Selecciona marcas para costeo general ({metric_name}):", sorted(val_trend[COL_MARCA].unique()), default=t5_val)
        
        if marcas_val:
            df_f_plot = val_trend[val_trend[COL_MARCA].isin(marcas_val)].sort_values(['año','mes'])
            df_f_plot['periodo_ord'] = pd.to_datetime(df_f_plot['año'].astype(str) + '-' + df_f_plot['mes'].astype(str) + '-01')
            df_f_plot = df_f_plot.sort_values('periodo_ord')
            
            fig_f_trend = px.line(df_f_plot, x='periodo', y='val_prom', color=COL_MARCA, markers=True, color_discrete_map={MARCA_PROPIA: COLOR_NH}, color_discrete_sequence=COLOR_PALETTE, title=f"Evolución Histórica de Precios {metric_name} Promedio")
            fig_f_trend.update_layout(plot_bgcolor='white', height=400)
            
            tabla_f_trend = df_f_plot.pivot(index=COL_MARCA, columns='periodo', values='val_prom').fillna(0)
            periodos_ordenados = df_f_plot['periodo'].unique()
            tabla_f_trend = tabla_f_trend[periodos_ordenados].reset_index()
            
            for col in periodos_ordenados:
                tabla_f_trend[col] = tabla_f_trend[col].astype(int)
            
            render_bloque(f"📈 Evolución Histórica de Precios {metric_name} Promedio", fig_f_trend, tabla_f_trend.style.apply(destacar_fila_nh, axis=1), f"tgl_{metric_name.lower()}_top", f"d_{metric_name.lower()}_top")
            
            st.divider()
            st.markdown("#### 🎯 Análisis Táctico y Configuración de Precios por Modelo")
            
            marcas_sub = st.multiselect("Filtra las marcas a auditar al detalle (sub-selección):", marcas_val, default=marcas_val, key=f"ms_{metric_name.lower()}_sub")
            
            if marcas_sub:
                df_val_f = df_val[df_val[COL_MARCA].isin(marcas_sub)].copy()
                df_val_f['periodo_ord'] = pd.to_datetime(df_val_f['año'].astype(str) + '-' + df_val_f['mes'].astype(str) + '-01')
                df_val_f = df_val_f.sort_values('periodo_ord')
                df_val_f['periodo'] = df_val_f['mes_nombre'] + ' ' + df_val_f['año'].astype(str)

                df_scatter = df_val_f.groupby([COL_MARCA, COL_MODELO, 'periodo', 'periodo_ord']).agg(
                    val_unitario=(col_activa, 'mean'),
                    unidades=(col_activa, 'size')
                ).reset_index().sort_values('periodo_ord')
                
                fig_scatter = px.scatter(
                    df_scatter, x='periodo', y='val_unitario', size='unidades', color=COL_MARCA,
                    hover_data=[COL_MODELO], size_max=35, 
                    color_discrete_map={MARCA_PROPIA: COLOR_NH}, color_discrete_sequence=COLOR_PALETTE,
                    title=f"Dispersión de Costos Unitarios {metric_name} (Tamaño de burbuja = Volumen de lote)"
                )
                fig_scatter.update_layout(plot_bgcolor='white', height=400)
                st.plotly_chart(fig_scatter, use_container_width=True)
                
                st.markdown("##### 📋 Estructura de Banda Salarial y Configuración de Precios")
                banda_val = df_val_f.groupby([COL_MARCA, COL_MODELO, 'categoria_maquinaria']).agg(
                    min_val=(col_activa, 'min'),
                    avg_val=(col_activa, 'mean'),
                    max_val=(col_activa, 'max'),
                    unid=(col_activa, 'size')
                ).reset_index().sort_values([COL_MARCA, 'unid'], ascending=[True, False]).reset_index(drop=True)
                
                banda_val['unid'] = banda_val['unid'].astype(int)
                banda_val.rename(columns={
                    COL_MARCA: 'Marca', COL_MODELO: 'Modelo Comercial', 'categoria_maquinaria': 'Segmento',
                    'min_val': f'{metric_name} Mínimo ($)', 'avg_val': f'{metric_name} Promedio ($)',
                    'max_val': f'{metric_name} Máximo ($)', 'unid': 'Unidades'
                }, inplace=True)
                
                marcas_en_banda = sorted(banda_val['Marca'].unique())
                NH_banda_idx = marcas_en_banda.index(MARCA_PROPIA) if MARCA_PROPIA in marcas_en_banda else 0
                marca_banda_sel = st.selectbox("🎯 Selecciona una marca para desglosar sus precios por modelo:", marcas_en_banda, index=NH_banda_idx, key=f"sb_banda_{metric_name.lower()}")
                
                banda_val_filtrada = banda_val[banda_val['Marca'] == marca_banda_sel]
                
                st.dataframe(
                    banda_val_filtrada.style.apply(lambda r: ['background-color: #FFE0B2; font-weight: bold;'] * len(r) if r['Marca']==MARCA_PROPIA else ['']*len(r), axis=1).format({
                        f'{metric_name} Mínimo ($)': '{:,.0f}', f'{metric_name} Promedio ($)': '{:,.0f}', f'{metric_name} Máximo ($)': '{:,.0f}'
                    }),
                    hide_index=True, use_container_width=True
                )
    else:
        st.warning(f"No se detectaron datos válidos en la columna de costos {metric_name} para el periodo seleccionado.")

# ============================================================
# TAB 5: INTELIGENCIA NEW HOLLAND
# ============================================================
with tab5:
    if MARCA_PROPIA in df[COL_MARCA].unique():
        nh_act = df_actual[df_actual[COL_MARCA] == MARCA_PROPIA]
        st.markdown(f"## 🟡 Inteligencia Competitiva — {MARCA_PROPIA}")
        
        mask_propia = nh_act['grupo_importador'].str.contains(IMPORTADOR_PROPIO, na=False) if 'grupo_importador' in nh_act.columns else pd.Series(False, index=nh_act.index)
        df_w = nh_act[mask_propia]
        
        col_n1, col_n2, col_n3 = st.columns(3)
        with col_n1: st.metric("Mis Unidades YTD", f"{len(nh_act):,}")
        with col_n2: st.metric("Mi Market Share Total", f"{((len(nh_act)/total_actual*100) if total_actual>0 else 0):.1f}%")
        with col_n3: st.metric(f"Unidades {IMPORTADOR_PROPIO}", f"{len(df_w):,}")
        
        st.divider()
        st.markdown("### 🎯 Auditoría de Brecha Comercial")
        
        modo_brecha = st.radio("Medir brecha operativa frente a:", ["🏆 Marcas Competidoras", "🏢 Importadores Competidores"], horizontal=True, key="radial_modo_brecha")
        benchmark = []
        df_base_bench = df_actual.copy()
        
        if "Marcas" in modo_brecha:
            marcas_riv = sorted([m for m in df_base_bench[COL_MARCA].dropna().unique() if m != MARCA_PROPIA])
            if marcas_riv:
                rival_sel = st.selectbox("⚔️ Selecciona la marca para medir brecha directa:", marcas_riv, index=marcas_riv.index("CATERPILLAR") if "CATERPILLAR" in marcas_riv else 0, key="sb_rival_m")
                st.markdown(f"Analizando: **{MARCA_PROPIA}** vs **{rival_sel}** por segmento comercial.")
                
                for cat in (cat_sel if cat_sel else cats_disp):
                    df_cat = df_base_bench[df_base_bench['categoria_maquinaria'] == cat]
                    t_cat = len(df_cat)
                    if t_cat > 0:
                        nh_c = len(nh_act[nh_act['categoria_maquinaria'] == cat])
                        riv_c = len(df_cat[df_cat[COL_MARCA] == rival_sel])
                        sh_nh, sh_riv = (nh_c/t_cat*100), (riv_c/t_cat*100)
                        dif_u = nh_c - riv_c
                        estado = f"🟢 Ganando (+{dif_u})" if dif_u > 0 else (f"🔴 Perdiendo ({dif_u})" if dif_u < 0 else "⚪ Empate")
                        
                        benchmark.append({'Segmento Comercial': cat, 'Unid. NH': nh_c, 'Share NH': f"{sh_nh:.1f}%", f'Unid. {rival_sel}': riv_c, f'Share {rival_sel}': f"{sh_riv:.1f}%", 'Brecha (pp)': f"{(sh_nh - sh_riv):+.1f} pp", 'Situación Actual': estado, 'v_a': nh_c, 'v_b': riv_c})
                
                df_bench = pd.DataFrame(benchmark)
                if not df_bench.empty:
                    fig_b = go.Figure(data=[go.Bar(name='New Holland', x=df_bench['Segmento Comercial'], y=df_bench['v_a'], marker_color='#FF8C00'), go.Bar(name=str(rival_sel), x=df_bench['Segmento Comercial'], y=df_bench['v_b'], marker_color='#1E448A')])
                    fig_b.update_layout(barmode='group', plot_bgcolor='white', height=350)
                    df_tabla_b = df_bench.drop(columns=['v_a', 'v_b'])
                    
                    config_cols = {"Segmento Comercial": st.column_config.TextColumn("Segmento Comercial", width="medium"), "Unid. NH": st.column_config.NumberColumn("Unid. NH", format="%d"), f"Unid. {rival_sel}": st.column_config.NumberColumn(f"Unid. {rival_sel}", format="%d")}
                    render_bloque(f"📋 Matriz de Brecha vs {rival_sel}", fig_b, df_tabla_b, "tgl_b_m", "d_b_m", "brecha", col_config_table=config_cols)
        else:
            if 'grupo_importador' in df_base_bench.columns:
                imps_riv = sorted([i for i in df_base_bench['grupo_importador'].dropna().unique() if IMPORTADOR_PROPIO not in str(i)])
                if imps_riv:
                    rival_i_sel = st.selectbox("⚔️ Selecciona el canal importador para medir brecha:", imps_riv, index=0, key="sb_rival_i")
                    for cat in (cat_sel if cat_sel else cats_disp):
                        df_cat = df_base_bench[df_base_bench['categoria_maquinaria'] == cat]
                        t_cat = len(df_cat)
                        if t_cat > 0:
                            w_c = len(df_cat[df_cat['grupo_importador'].str.contains(IMPORTADOR_PROPIO, na=False)])
                            riv_i_c = len(df_cat[df_cat['grupo_importador'] == rival_i_sel])
                            sh_w, sh_rivi = (w_c/t_cat*100), (riv_i_c/t_cat*100)
                            dif_ui = w_c - riv_i_c
                            estado_i = f"🟢 Ganando (+{dif_ui})" if dif_ui > 0 else (f"🔴 Perdiendo ({dif_ui})" if dif_ui < 0 else "⚪ Empate")
                            
                            benchmark.append({'Segmento Comercial': cat, f'Unid. {IMPORTADOR_PROPIO}': w_c, f'Share {IMPORTADOR_PROPIO}': f"{sh_w:.1f}%", f'Unid. {rival_i_sel}': riv_i_c, f'Share {rival_i_sel}': f"{sh_rivi:.1f}%", 'Brecha (pp)': f"{(sh_w - sh_rivi):+.1f} pp", 'Situación Actual': estado_i, 'v_a': w_c, 'v_b': riv_i_c})
                            
                    df_bench_i = pd.DataFrame(benchmark)
                    if not df_bench_i.empty:
                        fig_bi = go.Figure(data=[go.Bar(name=IMPORTADOR_PROPIO, x=df_bench_i['Segmento Comercial'], y=df_bench_i['v_a'], marker_color='#2E8B57'), go.Bar(name=str(rival_i_sel), x=df_bench_i['Segmento Comercial'], y=df_bench_i['v_b'], marker_color='#34495E')])
                        fig_bi.update_layout(barmode='group', plot_bgcolor='white', height=350)
                        df_tabla_bi = df_bench_i.drop(columns=['v_a', 'v_b'])
                        
                        config_cols_i = {"Segmento Comercial": st.column_config.TextColumn("Segmento Comercial", width="medium"), f"Unid. {IMPORTADOR_PROPIO}": st.column_config.NumberColumn(f"Unid. {IMPORTADOR_PROPIO}", format="%d"), f"Unid. {rival_i_sel}": st.column_config.NumberColumn(f"Unid. {rival_i_sel}", format="%d")}
                        render_bloque(f"📋 Matriz Logística vs {rival_i_sel}", fig_bi, df_tabla_bi, "tgl_b_i", "d_b_i", "brecha_imp", col_config_table=config_cols_i)

# ============ FOOTER ============
st.divider()
f_datos = datetime.fromtimestamp(ULTIMA_ACTUALIZACION).strftime('%d/%m/%Y %H:%M') if ULTIMA_ACTUALIZACION else datetime.now().strftime('%d/%m/%Y %H:%M')
st.caption(f"Pipeline Gerencial v16.0 Clean Treemap | {len(df):,} registros auditados | Fuente: Veritrade | Sincronizado al: {f_datos}")