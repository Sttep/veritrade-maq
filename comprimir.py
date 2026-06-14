import pandas as pd
import glob
from pathlib import Path

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
