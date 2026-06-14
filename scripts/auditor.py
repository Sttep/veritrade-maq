python -c "
import pandas as pd
import re
from collections import Counter

# Cargar archivo
df = pd.read_excel('inputs/Libro2-encontrados no categorizados.xlsx')

# Buscar columna de descripción
col = None
for c in df.columns:
    if 'descripcion' in str(c).lower():
        col = c
        break
if col is None:
    for c in df.columns:
        s = str(df[c].dropna().iloc[0]) if len(df[c].dropna()) > 0 else ''
        if 'CA:' in s or 'MARCA:' in s:
            col = c
            break

descs = df[col].astype(str)

# Extraer MARCA: y MODELO:
marcas = descs.str.extract(r'MARCA\s*:\s*([^,;]+)', expand=False).str.upper().str.strip()
modelos = descs.str.extract(r'MODELO\s*:\s*([^,;]+)', expand=False).str.upper().str.strip()

# Crear pares marca-modelo
pares = pd.DataFrame({'marca': marcas, 'modelo': modelos})
pares = pares.dropna(subset=['marca', 'modelo'])
pares = pares[pares['marca'] != '']

# Agrupar por marca
print('='*70)
print('  MARCAS Y MODELOS ENCONTRADOS')
print('='*70)

for marca in sorted(pares['marca'].unique()):
    modelos_marca = pares[pares['marca'] == marca]['modelo'].value_counts()
    print(f'\n  {marca}:')
    for mod, count in modelos_marca.head(15).items():
        print(f'    {mod:<45} {count:>5}')

# Guardar Excel
from openpyxl import Workbook
wb = Workbook()
ws = wb.active
ws.title = 'Marcas-Modelos'
ws.append(['Marca', 'Modelo', 'Cantidad'])

for (marca, modelo), count in pares.groupby(['marca', 'modelo']).size().items():
    ws.append([marca, modelo, count])

wb.save('analisis/marcas_modelos_libro2.xlsx')
print(f'\n  Guardado: analisis/marcas_modelos_libro2.xlsx')
"