import streamlit as st
import pandas as pd
import glob
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time

# ============ CONFIGURACIÓN DE PÁGINA ============
st.set_page_config(
    page_title="Dashboard Corporativo - Maquinaria",
    page_icon="🚜",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Paleta de colores
COLOR_ACTUAL = '#2E8B57'
COLOR_ANTERIOR = '#1E448A'
COLOR_PALETTE = ['#1E448A', '#2E8B57', '#4A90E2', '#34495E', '#50C878', '#D98880', '#A9CCE3']

st.markdown("""
<style>
    .main { background-color: #F8F9FA; }
    .kpi-container {
        display: flex; justify-content: space-between; background-color: white;
        padding: 15px 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 20px; align-items: center; text-align: center;
    }
    .kpi-box { flex: 1; border-right: 1px solid #eee; }
    .kpi-box:last-child { border-right: none; }
    .kpi-title { font-size: 0.85rem; color: #666; font-weight: 600; text-transform: uppercase; }
    .kpi-value { font-size: 1.8rem; color: #333; font-weight: bold; margin-top: 5px; }
    .kpi-var-up { color: #2E8B57; font-weight: bold; font-size: 1.8rem; }
    .kpi-var-down { color: #E74C3C; font-weight: bold; font-size: 1.8rem; }
    .chart-title { background-color: #4A5568; color: white; padding: 6px 12px; font-size: 0.9rem; font-weight: bold; border-radius: 4px; margin-bottom: 12px; }
    .loader-container {
        background-color: #1F1F2E; color: white; padding: 20px; border-radius: 10px;
        text-align: center; font-size: 35px; font-weight: bold; margin-bottom: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)

# ============ CARGA DE DATOS ============
@st.cache_data
def cargar_datos():
    time.sleep(1.5)
    files = glob.glob('outputs/*_normalizado.xlsx')
    if not files:
        return pd.DataFrame()
    df = pd.concat([pd.read_excel(f, sheet_name='normalizado_final') for f in files])
    df['fecha'] = pd.to_datetime(df['fecha_dua'])
    df['año'] = df['fecha'].dt.year
    df['mes'] = df['fecha'].dt.month
    meses_map = {1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'}
    df['mes_nombre'] = df['mes'].map(meses_map)
    for col in ['categoria_maquinaria', 'marca', 'marca_norm', 'modelo', 'grupo_importador', 'categoria_peso']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()
    return df

loader_placeholder = st.empty()
with loader_placeholder.container():
    st.markdown("""
    <div class="loader-container">
        <p style="font-size: 1rem; color: #86E3A2; margin-bottom: 5px;">Procesando bases de datos de Veritrade...</p>
        <p>🚜 💨 🏗️ 🚛 🚜</p>
    </div>
    """, unsafe_allow_html=True)

df = cargar_datos()
loader_placeholder.empty()

if df.empty:
    st.error("No se encontraron archivos de datos validos.")
    st.stop()

COL_MARCA = 'marca_norm' if 'marca_norm' in df.columns else 'marca'
COL_MODELO = 'modelo_match' if 'modelo_match' in df.columns else 'modelo'
COL_PESO = next((c for c in ['categoria_peso', 'rango_peso', 'capacidad'] if c in df.columns), None)

# ============ SIDEBAR ============
with st.sidebar:
    st.markdown("## 🗓️ Filtros")
    st.markdown("---")
    
    años_disp = sorted(df['año'].dropna().unique())
    año_actual = st.selectbox("📅 Año Base", años_disp, index=len(años_disp)-1)
    año_limite_inf = st.selectbox("⏳ Año Inicial", [a for a in años_disp if a <= año_actual], index=0)
    
    st.markdown("### 📆 Meses")
    meses_nombres = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
    col1, col2 = st.columns(2)
    with col1: mes_ini = st.selectbox("Desde", meses_nombres, index=0)
    with col2: mes_fin = st.selectbox("Hasta", meses_nombres, index=3)
    mes_ini_num = meses_nombres.index(mes_ini) + 1
    mes_fin_num = meses_nombres.index(mes_fin) + 1
    
    st.markdown("---")
    st.markdown("### 🏗️ Segmentos")
    cats_disp = sorted(df['categoria_maquinaria'].unique())
    CAT_DEFAULT = ["MINICARGADOR FRONTAL", "CARGADOR FRONTAL", "RETROEXCAVADORA", "EXCAVADORA", "MOTONIVELADORA", "BULLDOZER"]
    cat_sel = st.multiselect("Clases de Maquinaria", cats_disp, default=[c for c in CAT_DEFAULT if c in cats_disp])
    
    st.markdown("---")
    st.markdown("### 🎯 Marcas")
    marcas_disp = sorted(df[COL_MARCA].dropna().unique())
    marcas_sel = st.multiselect("Marcas", marcas_disp, default=[])
    
    imp_sel = []
    if 'grupo_importador' in df.columns:
        imp_disp = sorted(df['grupo_importador'].dropna().unique())
        imp_sel = st.multiselect("Importadores", imp_disp, default=[])
    
    st.markdown("---")
    st.markdown("### 👁️ Modo Vista")
    modo_vista = st.radio("Formato", ["📊 Gráficos", "📋 Tablas"], horizontal=True)
    
    st.markdown(f"*Total: {len(df):,} registros*")

# ============ FILTROS ============
df_base = df[(df['año'] >= año_limite_inf) & (df['año'] <= año_actual)].copy()
if mes_ini_num <= mes_fin_num:
    df_base = df_base[df_base['mes'].between(mes_ini_num, mes_fin_num)]
else:
    df_base = df_base[(df_base['mes'] >= mes_ini_num) | (df_base['mes'] <= mes_fin_num)]
if cat_sel: df_base = df_base[df_base['categoria_maquinaria'].isin(cat_sel)]
if marcas_sel: df_base = df_base[df_base[COL_MARCA].isin(marcas_sel)]
if imp_sel: df_base = df_base[df_base['grupo_importador'].isin(imp_sel)]

df_actual = df_base[df_base['año'] == año_actual]
df_anterior = df_base[df_base['año'] == (año_actual - 1)]

total_actual = len(df_actual)
total_anterior = len(df_anterior)
var_pct = ((total_actual - total_anterior) / total_anterior * 100) if total_anterior > 0 else 0

# ============ FUNCIONES ============
def renderizar(titulo, fig, df_tabla):
    st.markdown(f'<div class="chart-title">{titulo}</div>', unsafe_allow_html=True)
    if modo_vista == "📊 Gráficos":
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.dataframe(df_tabla, hide_index=True, use_container_width=True)

def crear_cuadro(df_eval, dimension, items):
    resumen = []
    años_lista = sorted(df_eval['año'].unique())
    for item in items:
        fila = {dimension: item}
        for a in años_lista:
            df_a = df_eval[df_eval['año'] == a]
            c_actual = len(df_a[df_a[dimension] == item])
            c_ant = len(df[(df['año'] == (a-1)) & (df['mes'].between(mes_ini_num, mes_fin_num)) & (df[dimension] == item)]) if marcas_sel or imp_sel else 0
            if not marcas_sel and not imp_sel:
                c_ant = len(df[(df['año'] == (a-1)) & (df['mes'].between(mes_ini_num, mes_fin_num)) & (df[dimension] == item)])
            tot = len(df_a)
            fila[f"{a} CANT"] = c_actual
            fila[f"{a} VAR%"] = f"{((c_actual-c_ant)/c_ant*100):+.1f}%" if c_ant > 0 else "N/A"
            fila[f"{a} MS%"] = f"{(c_actual/tot*100):.1f}%" if tot > 0 else "0%"
        resumen.append(fila)
    return pd.DataFrame(resumen), años_lista

# ============ KPIs ============
st.markdown(f"""
<div class="kpi-container">
    <div style="flex: 2; text-align: left; padding-left: 10px;">
        <h2 style="margin:0; color:#1E448A; font-weight:800;">Reporte Gerencial de Importaciones</h2>
        <span style="color:#666;">{mes_ini}-{mes_fin} | {año_limite_inf}-{año_actual}</span>
    </div>
    <div class="kpi-box"><div class="kpi-title">{año_actual-1}</div><div class="kpi-value">{total_anterior:,}</div></div>
    <div class="kpi-box"><div class="kpi-title">{año_actual}</div><div class="kpi-value">{total_actual:,}</div></div>
    <div class="kpi-box"><div class="kpi-title">Variacion</div><div class="{'kpi-var-up' if var_pct >= 0 else 'kpi-var-down'}">{'▲' if var_pct >= 0 else '▼'} {abs(var_pct):.1f}%</div></div>
</div>
""", unsafe_allow_html=True)

if df_actual.empty:
    st.warning("No hay datos para los filtros seleccionados.")
    st.stop()

# ============ TABS ============
tab1, tab2, tab3 = st.tabs(["📊 Market Share", "🏆 Marcas & Importadores", "⚖️ Por Peso"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        tend = df_base[df_base['año'].isin([año_actual-1, año_actual])].groupby(['mes','mes_nombre','año']).size().reset_index(name='Unidades')
        tend['año'] = tend['año'].astype(str)
        fig = px.bar(tend, y='mes_nombre', x='Unidades', color='año', orientation='h', barmode='group',
                     color_discrete_map={str(año_actual-1): COLOR_ANTERIOR, str(año_actual): COLOR_ACTUAL}, text_auto=True)
        fig.update_layout(plot_bgcolor='white', height=350, yaxis={'categoryorder':'array','categoryarray':meses_nombres[::-1]}, legend=dict(orientation='h', y=1.02))
        tend_tabla = tend.pivot(index='mes_nombre', columns='año', values='Unidades').fillna(0).reset_index()
        renderizar("📈 Tendencia Mensual", fig, tend_tabla)
    
    with col2:
        share = df_actual['categoria_maquinaria'].value_counts()
        fig = px.pie(values=share.values, names=share.index, hole=0.4, color_discrete_sequence=COLOR_PALETTE)
        fig.update_layout(height=350)
        share_tabla = share.reset_index()
        share_tabla.columns = ['Categoria', 'Unidades']
        share_tabla['%'] = (share_tabla['Unidades']/total_actual*100).round(1)
        renderizar("🥧 Market Share", fig, share_tabla)
    
    # Cuadro Resumen Oficial
    st.markdown('<div class="chart-title">📋 Cuadro Resumen por Segmento</div>', unsafe_allow_html=True)
    df_res, años_l = crear_cuadro(df_base, 'categoria_maquinaria', cat_sel)
    st.dataframe(df_res, hide_index=True, use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)
    
    with col1:
        top = df_actual[COL_MARCA].value_counts().head(15)
        fig = px.bar(x=top.values, y=top.index, orientation='h', text=top.values, color_discrete_sequence=[COLOR_ACTUAL])
        fig.update_traces(textposition='outside')
        fig.update_layout(plot_bgcolor='white', height=450, yaxis=dict(autorange="reversed"))
        top_tabla = top.reset_index(); top_tabla.columns = ['Marca','Unidades']
        renderizar(f"🏆 Top 15 Marcas ({año_actual})", fig, top_tabla)
    
    with col2:
        if 'grupo_importador' in df.columns:
            top_i = df_actual['grupo_importador'].value_counts().head(15)
            fig = px.bar(x=top_i.values, y=top_i.index, orientation='h', text=top_i.values, color_discrete_sequence=['#34495E'])
            fig.update_traces(textposition='outside')
            fig.update_layout(plot_bgcolor='white', height=450, yaxis=dict(autorange="reversed"))
            top_i_tabla = top_i.reset_index(); top_i_tabla.columns = ['Importador','Unidades']
            renderizar(f"🏢 Top 15 Importadores ({año_actual})", fig, top_i_tabla)
        else:
            st.info("Columna 'grupo_importador' no disponible.")
    
    # Modelos top
    if 'modelo' in df_actual.columns:
        st.markdown('<div class="chart-title">🔧 Top Modelos ({})</div>'.format(año_actual), unsafe_allow_html=True)
        df_mod = df_actual.copy()
        df_mod['Marca_Modelo'] = df_mod[COL_MARCA] + " - " + df_mod['modelo']
        top_mod = df_mod['Marca_Modelo'].value_counts().head(20).reset_index()
        top_mod.columns = ['Marca-Modelo','Unidades']
        if modo_vista == "📊 Gráficos":
            fig_mod = px.bar(top_mod.sort_values('Unidades'), x='Unidades', y='Marca-Modelo', orientation='h', text_auto=True, color_discrete_sequence=[COLOR_ACTUAL])
            fig_mod.update_traces(textposition='outside')
            fig_mod.update_layout(plot_bgcolor='white', height=500, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_mod, use_container_width=True)
        else:
            st.dataframe(top_mod, hide_index=True, use_container_width=True)

with tab3:
    if COL_PESO:
        col1, col2 = st.columns(2)
        orden = ['-14t','14-17t','17t-21t','21-27t','27t-33t','33t-38t','38-50t','50t+','100t+']
        
        with col1:
            peso_c = df_actual[COL_PESO].value_counts().reindex([p for p in orden if p in df_actual[COL_PESO].unique()])
            fig = px.bar(x=peso_c.index, y=peso_c.values, text=peso_c.values, color_discrete_sequence=[COLOR_ACTUAL])
            fig.update_traces(textposition='outside')
            fig.update_layout(plot_bgcolor='white', height=400)
            peso_tabla = peso_c.reset_index(); peso_tabla.columns = ['Rango','Unidades']
            renderizar(f"⚖️ Unidades por Peso ({año_actual})", fig, peso_tabla)
        
        with col2:
            peso_cat = df_actual.groupby([COL_PESO,'categoria_maquinaria']).size().reset_index(name='Unidades')
            fig = px.bar(peso_cat, x=COL_PESO, y='Unidades', color='categoria_maquinaria', color_discrete_sequence=COLOR_PALETTE)
            fig.update_layout(plot_bgcolor='white', height=400, legend=dict(orientation='h', y=1.02))
            peso_cat_tabla = peso_cat.pivot(index=COL_PESO, columns='categoria_maquinaria', values='Unidades').fillna(0).reset_index()
            renderizar(f"⚖️ Peso por Tipo ({año_actual})", fig, peso_cat_tabla)
        
        # Comparativa
        comp = []
        for p in orden:
            if p in df_actual[COL_PESO].unique() or p in df_anterior[COL_PESO].unique():
                comp.append({'Rango':p, f'{año_actual-1}':len(df_anterior[df_anterior[COL_PESO]==p]), f'{año_actual}':len(df_actual[df_actual[COL_PESO]==p])})
        df_comp = pd.DataFrame(comp)
        df_comp_m = df_comp.melt(id_vars='Rango', var_name='Año', value_name='Unidades')
        fig = px.bar(df_comp_m, x='Rango', y='Unidades', color='Año', barmode='group', color_discrete_sequence=[COLOR_ANTERIOR, COLOR_ACTUAL], text_auto=True)
        fig.update_layout(plot_bgcolor='white', height=400, legend=dict(orientation='h', y=1.02))
        renderizar(f"📊 Comparativa Peso ({año_actual-1} vs {año_actual})", fig, df_comp)
    else:
        st.info("Columna de peso no disponible.")

st.divider()
st.caption(f"Pipeline v1.1 | {len(df):,} registros | {datetime.now().strftime('%d/%m/%Y %H:%M')}")
