# Arquitetura MongoDB — VigiaClima-Recife

1. `mongo/main.py` conecta ao Atlas e executa cada fonte; falhas de fonte ou de
   conexão resultam em código de saída diferente de zero.
2. INMET e Open-Meteo gravam séries horárias com instante UTC, ponto/estação e
   variáveis padronizadas (`precipitacao_mm`, `temperatura_c`, `umidade_pct` e
   `pressao_hpa`), mantendo também os campos recebidos da origem.
3. Dados Abertos Recife e SINAN são reduzidos a contagens agregadas antes de
   persistir. O SINAN é filtrado para Pernambuco; Recife exige município,
   agravo, semana e bairro identificáveis. Nenhuma notificação individual é
   escrita pelo fluxo novo.
4. S2ID só aceita recursos com UF explícita e grava apenas linhas de PE.
   Recursos que não permitem confirmar a geografia são ignorados e, se nenhum
   recurso válido existir, a fonte falha explicitamente.
5. `mongo/database/mongodb.py` grava documentos idempotentes: medições usam
   chaves naturais estáveis e atualizam o mesmo documento em reexecuções.
6. `mongo/data/raw/` contém cópias JSON de depuração dos dados produzidos e
   permanece fora do Git; para saúde, são gravadas apenas as agregações novas.
7. A etapa Bronze é independente e pode ser executada por `bronze/main.py`.

Os JSONs de depuração ficam em `mongo/data/raw/` e não são enviados ao Git.
