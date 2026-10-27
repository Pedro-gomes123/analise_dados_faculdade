# VigiaClima-Recife

Pipeline de coleta e ingestão de dados meteorológicos,
arboviroses e desastres relacionados a Recife e Pernambuco.

## Arquitetura

- `src/main.py`: coordena a execução.
- `src/collectors/`: contém os coletores de dados.
- `src/database/mongodb.py`: gerencia a conexão e a persistência.
- `src/utils/helpers.py`: funções auxiliares.
- `src/config.py`: configurações gerais.
- `.github/workflows/pipeline.yml`: execução automática.

## Banco de dados

Banco: `operacional_db`

Coleções:

- `inmet_estacoes`
- `inmet_observacoes`
- `openmeteo_horario`
- `recife_arboviroses`
- `s2id_desastres`
- `sinan_animais_peconhentos`

## Instalação local

Instale as dependências:

    python -m pip install -r requirements.txt

Configure a variável de ambiente `MONGODB_URI`.

Execute:

    python -m src.main

## Execução automática

O GitHub Actions está configurado para executar a pipeline
a cada hora e permite execução manual.

Configure o segredo `MONGODB_URI` nas configurações
do repositório antes de executar o workflow.

## Dados locais

Cópias JSON podem ser salvas em `data/raw/` para depuração.
O armazenamento principal é o MongoDB Atlas.