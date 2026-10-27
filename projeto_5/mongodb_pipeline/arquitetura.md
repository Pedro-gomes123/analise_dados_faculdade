# Arquitetura VigiaClima-Recife

## Fluxo de dados

1. O GitHub Actions inicia a execução.
2. `src/main.py` coordena os coletores.
3. Os coletores consultam as respectivas fontes.
4. Os registros são normalizados.
5. `src/database/mongodb.py` grava os documentos.
6. A execução termina.

## Separação de responsabilidades

- Collectors: coleta de dados.
- Database: conexão e persistência.
- Utils: funções auxiliares.
- Config: configurações não secretas.
- Main: coordenação da execução.

## Armazenamento

O MongoDB Atlas é o destino principal dos dados.

Os arquivos JSON locais são opcionais e servem para depuração.
Eles não devem ser enviados ao repositório.