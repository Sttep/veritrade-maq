import pandas as pd, glob

files = glob.glob('outputs/*_estructurado.xlsx')

print('='*60)
print('FASE A - RESULTADOS POR ARCHIVO')
print('='*60)

for f in files:
    df = pd.read_excel(f, sheet_name='estructurado')
    total = len(df)
    con_marca = df['marca'].notna().sum()
    con_modelo = df['modelo'].notna().sum()
    sin_mod = len(df[df['modelo'].isna() & df['marca'].notna()])
    sin_nada = len(df[df['marca'].isna() & df['modelo'].isna()])
    
    nombre = f.split('\\')[-1][:60]
    print(f'\nARCHIVO: {nombre}')
    print(f'  Total:           {total:>8,}')
    print(f'  Con marca:       {con_marca:>8,}  ({100*con_marca/total:.1f}%)')
    print(f'  Con modelo:      {con_modelo:>8,}  ({100*con_modelo/total:.1f}%)')
    print(f'  Sin modelo (c/m): {sin_mod:>8,}')
    print(f'  Sin marca ni mod: {sin_nada:>8,}')

# Consolidado
df = pd.concat([pd.read_excel(f, sheet_name='estructurado') for f in files])
total = len(df)
print('\n' + '='*60)
print('CONSOLIDADO')
print('='*60)
print(f'  Total:           {total:>8,}')
print(f'  Con marca:       {df.marca.notna().sum():>8,}  ({100*df.marca.notna().sum()/total:.1f}%)')
print(f'  Con modelo:      {df.modelo.notna().sum():>8,}  ({100*df.modelo.notna().sum()/total:.1f}%)')
print(f'  Top categorias:')
for cat, n in df['categoria_maquinaria'].value_counts().head(10).items():
    print(f'    {cat:<30} {n:>6}')