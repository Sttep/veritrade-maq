import pandas as pd, json

# Cargar vocab_extra
with open('data/vocab_extra.json', 'r', encoding='utf-8') as f:
    vocab = json.load(f)

# Cargar diccionario
marcas = pd.read_excel('data/diccionario_maquinaria.xlsx', sheet_name='marcas')
marcas['marca_estandar'] = marcas['marca_estandar'].str.strip().str.upper()
marcas_dict = set(marcas['marca_estandar'])

# Verificar aliases
print('ALIASES QUE APUNTAN A MARCAS INEXISTENTES:')
for alias, canon in vocab.get('aliases', {}).items():
    if canon.upper() not in marcas_dict:
        print(f'  {alias} -> {canon} (NO EXISTE en diccionario)')

print()
print('MARCAS EN VOCAB_EXTRA QUE NO ESTAN EN DICCIONARIO:')
for marca in vocab.get('marcas', {}).keys():
    if marca.upper() not in marcas_dict:
        print(f'  {marca} (NO EXISTE en diccionario)')

print()
print('MARCAS EN DICCIONARIO QUE NO TIENEN ALIAS EN VOCAB:')
marcas_con_alias = set(c.upper() for c in vocab.get('aliases', {}).values())
sin_alias = marcas_dict - marcas_con_alias
print(f'  {len(sin_alias)} marcas sin alias (las principales)')
