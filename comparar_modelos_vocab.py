import pandas as pd, json

with open('data/vocab_extra.json', 'r', encoding='utf-8') as f:
    vocab = json.load(f)

modelos = pd.read_excel('data/diccionario_maquinaria.xlsx', sheet_name='modelos')
modelos['modelo'] = modelos['modelo'].str.strip().str.upper()
modelos_dict = set(modelos['modelo'])

model_aliases = vocab.get('model_aliases', {})
total_aliases = 0
faltantes = 0

print('MODELOS EN VOCAB_EXTRA QUE NO ESTAN EN DICCIONARIO:')
for marca, aliases in model_aliases.items():
    for alias, canon in aliases.items():
        total_aliases += 1
        if canon.upper() not in modelos_dict:
            faltantes += 1
            print(f'  {marca}: {alias} -> {canon}')

print()
print(f'Total model_aliases: {total_aliases}')
print(f'Faltantes en diccionario: {faltantes}')
print(f'Modelos en diccionario: {len(modelos_dict)}')
