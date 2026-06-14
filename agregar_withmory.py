import pandas as pd
grupos = pd.read_excel('data/diccionario_maquinaria.xlsx', sheet_name='grupos_importador')
nueva = pd.DataFrame({
    'keyword': ['INVERSIONES Y NEGOCIOS GENERALES SELVA', 'NEGOCIOS GENERALES SELVA'],
    'grupo': ['GRUPO WITHMORY', 'GRUPO WITHMORY']
})
grupos = pd.concat([grupos, nueva], ignore_index=True)
grupos = grupos.drop_duplicates(subset=['keyword'], keep='first')
with pd.ExcelWriter('data/diccionario_maquinaria.xlsx', engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
    grupos.to_excel(writer, sheet_name='grupos_importador', index=False)
print('Razones sociales agregadas a GRUPO WITHMORY')
