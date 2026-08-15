import requests
import json
import os

url = "https://servicodados.ibge.gov.br/api/v3/agregados/4093/periodos/201201-202601/variaveis/4099|4096|12466?localidades=N3[26]&classificacao=2[6794,4,5]"

print("Buscando dados na API do IBGE...")
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    
    diretorio_atual = os.getcwd()
    
    for item in data:
        id_variavel = item['id']
        nome_variavel = item['variavel']
        
        for resultado in item.get('resultados', []):
            
          
            categoria_dict = resultado['classificacoes'][0]['categoria']
            
            nome_sexo = list(categoria_dict.values())[0]
            
            nome_arquivo = f"variavel_{id_variavel}_{nome_sexo}.json"
            caminho_arquivo = os.path.join(diretorio_atual, nome_arquivo)
            
            dados_para_salvar = {
                "id_variavel": id_variavel,
                "nome_variavel": nome_variavel,
                "categoria_sexo": nome_sexo,
                "dados": resultado
            }
            
            with open(caminho_arquivo, 'w', encoding='utf-8') as f:
                json.dump(dados_para_salvar, f, ensure_ascii=False, indent=4)
           
            
    print(f"\nTodos os 9 arquivos foram gerados com sucesso na pasta:\n{diretorio_atual}")

else:
    print(f"Erro ao acessar a API. Status Code: {response.status_code}")