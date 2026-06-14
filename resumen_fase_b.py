import pandas as pd, glob

files = glob.glob('outputs/*_normalizado.xlsx')

print('='*60)
print('FASE B - RESULTADOS POR ARCHIVO')
print('='*60)

for f in files:
    df = pd.read_excel(f, sheet_name='normalizado_final')
    total = len(df)
    marca_col = 'marca_norm' if 'marca_norm' in df.columns else 'marca'
    modelo_col = 'modelo_match' if 'modelo_match' in df.columns else 'modelo'
    
    con_marca = df[marca_col].notna().sum()
    con_modelo = df[modelo_col].notna().sum()
    sin_mod = len(df[df[modelo_col].isna() & df[marca_col].notna()])
    sin_nada = len(df[df[marca_col].isna() & df[modelo_col].isna()])
    
    nombre = f.split('\\')[-1][:60]
    print(f'\nARCHIVO: {nombre}')
    print(f'  Total:           {total:>8,}')
    print(f'  Con marca:       {con_marca:>8,}  ({100*con_marca/total:.1f}%)')
    print(f'  Con modelo:      {con_modelo:>8,}  ({100*con_modelo/total:.1f}%)')
    print(f'  Sin modelo (c/m): {sin_mod:>8,}')
    print(f'  Sin marca ni mod: {sin_nada:>8,}')

# Consolidado
df = pd.concat([pd.read_excel(f, sheet_name='normalizado_final') for f in files])
marca_col = 'marca_norm' if 'marca_norm' in df.columns else 'marca'
modelo_col = 'modelo_match' if 'modelo_match' in df.columns else 'modelo'
total = len(df)

print('\n' + '='*60)
print('CONSOLIDADO FASE B')
print('='*60)
print(f'  Total:           {total:>8,}')
print(f'  Con marca:       {df[marca_col].notna().sum():>8,}  ({100*df[marca_col].notna().sum()/total:.1f}%)')
print(f'  Con modelo:      {df[modelo_col].notna().sum():>8,}  ({100*df[modelo_col].notna().sum()/total:.1f}%)')
print(f'  Top categorias:')
for cat, n in df['categoria_maquinaria'].value_counts().head(10).items():
    print(f'    {cat:<30} {n:>6}')
