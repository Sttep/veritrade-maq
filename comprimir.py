import sys
import pandas as pd
import glob
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

def comprimir_datos():
    print("⏳ Leyendo archivos de la carpeta outputs/...")
    ruta_outputs = Path(__file__).parent / 'outputs'
    files = sorted(ruta_outputs.glob('*_normalizado.xlsx'))
    
    if not files:
        print("❌ No se encontraron archivos Excel normalizados.")
        return
        
    dfs = []
    for f in files:
        try:
            dfs.append(pd.read_excel(f, sheet_name='normalizado_final'))
            print(f"✅ Cargado: {f.name}")
        except Exception as e:
            print(f"❌ Error: {f.name} - {e}")
            
    if dfs:
        print("🔄 Unificando...")
        df_completo = pd.concat(dfs, ignore_index=True)

        # Excluir partes/accesorios: FOB positivo menor a $5,000
        if 'fob_usd' in df_completo.columns:
            fob_num = pd.to_numeric(df_completo['fob_usd'], errors='coerce').fillna(0)
            partes = (fob_num > 0) & (fob_num < 5_000)
            if partes.sum() > 0:
                print(f"🔧 Excluidos {partes.sum()} registros con FOB < $5,000 (partes/accesorios)")
            df_completo = df_completo[~partes].copy()

        # Marcar máquinas sin marca detectada como "SIN MARCA" cuando la descripción dice S/M
        desc_col = next((c for c in ['_descripcion', 'descripcion'] if c in df_completo.columns), None)
        if desc_col and 'marca_norm' in df_completo.columns:
            sin_marca_mask = (
                df_completo['marca_norm'].isna() | df_completo['marca_norm'].isin(['', 'nan', 'None'])
            ) & df_completo[desc_col].astype(str).str.contains(r'\bS/M\b', na=False, regex=True)
            count_sm = sin_marca_mask.sum()
            if count_sm > 0:
                df_completo.loc[sin_marca_mask, 'marca_norm'] = 'SIN MARCA'
                print(f"🏷️  {count_sm} registros etiquetados como 'SIN MARCA'")

        # ✅ Forzar TODAS las columnas de texto a string
        for col in df_completo.columns:
            if df_completo[col].dtype == 'object':
                df_completo[col] = df_completo[col].astype(str).replace(['nan','None','<NA>'], '')
        
        ruta_guardado = Path(__file__).parent / 'datos_maquinaria.parquet'
        df_completo.to_parquet(ruta_guardado, index=False, compression='snappy')
        
        print(f"🚀 ¡ÉXITO! Archivo: {ruta_guardado.name}")
        print(f"📦 Tamaño: {ruta_guardado.stat().st_size / 1024 / 1024:.1f} MB")

if __name__ == "__main__":
    comprimir_datos()
