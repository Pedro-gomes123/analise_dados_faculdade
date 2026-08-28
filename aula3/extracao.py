import io
import requests
import pandas as pd

url = "https://servicodados.ibge.gov.br/api/v3/agregados/4093/periodos/201201-202602/variaveis/4099?localidades=N3[26]&classificacao=2[all]"

#resposta = requests.get(url)
data = pd.read_json(url)

resultados = data["resultados"][0]
sexos = {"Total": 0, "Homens": 1, "Mulheres": 2}

partes = []
for sexo, i in sexos.items():
    serie = resultados[i]["series"][0]["serie"]
    parte = pd.DataFrame.from_dict(serie, orient="index", columns=["valor"])
    parte.index.name = "periodo"
    parte = parte.reset_index()
    parte["sexo"] = sexo
    partes.append(parte)

df = pd.concat(partes, ignore_index=True)

df['valor'] = df['valor'].replace('...', '0')
df['valor'] = df['valor'].astype(float)

df['ano'] = df['periodo'].str[:4]
df['tri'] = df['periodo'].str[-2:].astype(int)

df.info()

df_ano = df.groupby(['sexo', 'ano'])['valor'].mean().reset_index()
print(df_ano)

for sexo in sexos:
    valores = df_ano.loc[(df_ano['sexo'] == sexo) & (df_ano['valor'] != 0), 'valor']
    moda = valores.mode()[0]
    mediana = valores.median()
    media = valores.mean()
    print(f"\n{sexo}")
    print("Moda:", moda)
    print("Mediana:", mediana)
    print("Média:", media)