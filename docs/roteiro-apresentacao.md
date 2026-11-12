# PEP · Roteiro completo de apresentação e estudo

**Tempo sugerido: 15 minutos de apresentação, mais perguntas.** O roteiro assume cinco integrantes. Troquem os números pelos nomes do grupo e ajustem o tempo ao que o professor der.

## Se vocês só tiverem 20 minutos para estudar hoje

1. Leiam as cinco falas de abertura de cada parte e combinem quem controla a tela.
2. Façam uma vez o caminho **liberar horário → agendar → iniciar → adicionar procedimento → salvar prontuário → concluir → faturar**.
3. Abram no editor as funções `agendar`, `salvar_prontuario`, `ler_registro` e a procedure `fechar_faturamento`.
4. Guardem esta explicação: **PostgreSQL guarda a operação da clínica, MongoDB guarda o prontuário, Redis acelera a leitura. O ID da consulta une o SQL ao documento.**

## 1. Divisão do tempo

| Tempo | Quem | O que mostra | O que precisa ficar claro |
|---|---|---|---|
| 0:00–2:30 | Integrante 1 | Problema, diagrama e aplicação aberta | Por que existem três bancos e qual o papel da API |
| 2:30–5:00 | Integrante 2 | Agenda, paciente, reserva e código SQL | Como a reserva evita dois agendamentos para o mesmo horário |
| 5:00–9:00 | Integrante 3 | Atendimento, prontuário, histórico e código Python | Como o prontuário é ligado à consulta e como o Redis entra na leitura |
| 9:00–11:30 | Integrante 4 | Fechamento dos convênios, view e trigger | Como a cobrança é calculada e protegida contra duplicidade |
| 11:30–15:00 | Integrante 5 | Testes, carga e resultados | O que foi medido, o que aconteceu nas falhas e o que o MVP entrega |

Uma pessoa pode controlar o computador enquanto as outras falam. Deixem abertas duas sessões do navegador, uma como médico e outra como atendente. Usem duas janelas com perfis diferentes ou uma normal e uma anônima.

## 2. Preparação antes de apresentar

Na pasta **Projeto**, com o Docker Desktop aberto, rodem no PowerShell:

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build -d --wait
docker compose exec api python -m app.manage seed
docker compose ps
```

Abram `http://localhost:5173` para as telas, `http://localhost:8000/docs` para as rotas da API e `http://localhost:8000/health/ready` para conferir as três conexões. Se já existe uma base local, façam o ensaio com dados fictícios. O seed cria exemplos, e contas de exemplo já existentes mantêm suas senhas.

| Papel | Conta de exemplo | Senha de um seed novo |
|---|---|---|
| Médico | `joaosilva@pep.com` | `PepDemo123!` |
| Atendente | `mariasilva@pep.com` | `PepDemo123!` |

- **Ensaio e apresentação:** escolham dois horários livres em uma data futura e anotem qual foi usado em cada rodada. O prontuário do ensaio fica salvo e a cobrança já gerada não volta a aparecer como pendente de geração.
- **Exemplo para o convênio:** André Lucas Barbosa, João Silva, plano **Lagoa Essencial** e procedimento **Consulta de clínica médica**, de **R$ 180,00**. Escolham o convênio na reserva e confirmem que aparece no formulário.
- **Arquivos na ordem:** [arquitetura](arquitetura.md), [operacoes.py](../backend/app/operacoes.py), [prontuario.py](../backend/app/prontuario.py), [migração SQL](../backend/sql/migrations/007_prontuario.sql), [benchmark.py](../backend/app/benchmark.py) e [resultados](demonstracao.md).
- **Plano de apoio:** baixem ou abram previamente o [vídeo de 40 segundos](PEP%20-%20Demonstracao.mp4). Deixem também um atendimento de ensaio já concluído para mostrar o resultado se um clique atrasar.
- **Se o tempo apertar:** mostrem ao vivo a reserva, o salvamento e a cobrança. Expliquem a falha e a carga com os resultados registrados. Rodem a carga antes de apresentar.

## 3. Integrante 1 · Abertura e arquitetura

**Fala sugerida**

> Nosso projeto é o PEP, um prontuário eletrônico para a rotina de uma clínica. A equipe da clínica cadastra o paciente e agenda o atendimento. O médico registra o prontuário, e a equipe administrativa gera a cobrança. Escolhemos um banco para os dados que precisam de regras fortes de integridade e outro para o documento clínico, que pode variar conforme o atendimento.

Mostrem o [diagrama de arquitetura e o modelo ER](arquitetura.md). Apontem o caminho **React → API FastAPI → bancos**. Expliquem as três responsabilidades:

- **PostgreSQL:** paciente, médico, agenda, consulta, procedimentos e faturamento. As tabelas se conectam por IDs e chaves estrangeiras.
- **MongoDB:** o documento clínico da consulta. Evolução, prescrições, exames e campos adicionais podem ficar juntos no mesmo documento.
- **Redis:** uma cópia temporária da parte textual do prontuário, com duração de 60 segundos. Em uma leitura repetida, o sistema pode usar essa cópia.

**Como ler o diagrama em 30 segundos:** sigam `PACIENTE → AGENDAMENTO → CONSULTA → FATURAMENTO`. Um paciente pode ter vários agendamentos. Cada agendamento pode originar uma consulta, e cada consulta pode gerar uma cobrança. A relação com procedimentos passa pela tabela `consulta_procedimento`, que guarda a quantidade e o preço usado naquele atendimento. Se perguntarem sobre normalização, apontem que paciente, médico e procedimento têm cadastros próprios, referenciados por IDs.

**Se quiserem mostrar o código de entrada:** abram [compose.yaml](../compose.yaml) e localizem `frontend`, `api`, `postgres`, `mongo` e `redis`. O Compose sobe esses serviços. Na API, [main.py](../backend/app/main.py#L35) verifica as conexões em `readiness`. A resposta de saúde é uma checagem do momento.

**Transição:** “Agora vamos mostrar o caminho de uma consulta, começando pela agenda.”

## 4. Integrante 2 · Da agenda à consulta

### O que clicar

1. Na sessão de **médico**, abram **Minha agenda**. Em **Disponibilidade de horários**, preencham a data futura e o horário e cliquem em **Liberar horário**.
2. Na sessão de **atendente**, abram **Agenda → Agendar consulta**. Busquem André Lucas Barbosa e selecionem o paciente, João Silva, a mesma data, o horário liberado e **Saúde Lagoa · Lagoa Essencial**.
3. Cliquem em **Salvar agendamento**. Mostrem a consulta na agenda. Se quiserem mostrar a situação do horário, voltem ao formulário e verifiquem que o horário reservado saiu da lista de livres.
4. Se perguntarem pelo cadastro, mostrem **Pacientes → Novo paciente** e expliquem que é uma ação interna da clínica. Para o fluxo completo, usem o paciente já preparado com a carteirinha de exemplo.

### O que mostrar no código

Abram [operacoes.py, função agendar](../backend/app/operacoes.py#L229). Procurem estas duas instruções dentro do mesmo `with connect() as conn`:

```sql
-- Trechos da reserva, com outras condições omitidas para a explicação.
UPDATE disponibilidade_agenda d SET status = 'ocupado'
-- O UPDATE exige que o horário ainda esteja disponível.
-- Ele devolve médico, data e horário para o INSERT.
INSERT INTO agendamento (id_medico, id_paciente, data, horario, status, id_paciente_convenio, observacoes)
```

Em seguida, abram [007_prontuario.sql](../backend/sql/migrations/007_prontuario.sql#L7):

```sql
CREATE UNIQUE INDEX agendamento_horario_ativo_idx
    ON agendamento (id_medico, data, horario) WHERE status <> 'cancelado';
```

**Fala sugerida**

> A API tenta marcar o horário como ocupado somente se ele ainda está disponível. Em seguida cria o agendamento, dentro da mesma transação. Se der erro no cadastro da reserva, a mudança do horário também é revertida. O índice único parcial é uma segunda garantia no banco: para um médico, data e horário, só pode existir um agendamento ativo.

**Pergunta provável:** “Se duas pessoas clicarem ao mesmo tempo?” Uma consegue reservar. A outra recebe conflito, HTTP **409**. O teste realmente dispara as duas tentativas em paralelo.

**Transição:** “O agendamento está no PostgreSQL. Agora o médico vai iniciar a consulta e gravar o documento clínico.”

## 5. Integrante 3 · Prontuário, histórico e integração

### O que clicar

1. Na sessão de **médico**, voltem a **Minha agenda** e escolham a data da reserva. Na linha de André, cliquem em **Iniciar**. A consulta passa para **Em atendimento**.
2. Cliquem em **Adicionar procedimento**, escolham **Consulta de clínica médica**, deixem quantidade **1** e cliquem em **Adicionar**.
3. Cliquem em **Registrar prontuário**. Preencham uma evolução fictícia, por exemplo, “Paciente relata melhora dos sintomas em atendimento de demonstração.” Se quiserem, preencham exame e campo adicional, como **Escala de dor** com valor **2**.
4. Cliquem em **Salvar prontuário**. Mostrem o resultado em leitura. Se usarem anexo, usem um arquivo fictício de até 2 MB e mostrem o botão de download.
5. Cliquem em **Ver histórico do paciente → Ler registro clínico** na consulta certa. Voltem à agenda, selecionem novamente a data da demonstração e cliquem em **Concluir**.

### Sigam uma ação da tela ao banco

| Passo | Onde apontar | O que dizer |
|---|---|---|
| 1. O formulário envia | [Prontuario.tsx](../frontend/src/pages/Prontuario.tsx#L73) | O React pega os campos e faz um `PUT` para `/consultas/{id_consulta}/prontuario`. |
| 2. A API confere acesso | [auth.py](../backend/app/auth.py#L44) e [prontuario.py](../backend/app/prontuario.py#L60) | O token identifica a sessão. A API confere no SQL a relação do médico com a consulta ou com o paciente. A gravação exige o médico responsável. |
| 3. O MongoDB recebe o documento | [salvar_prontuario](../backend/app/prontuario.py#L125) | O `_id` do documento usa o ID da consulta. O documento inclui o ID do paciente e o conteúdo clínico. |
| 4. O SQL confirma o vínculo | [salvar_prontuario, atualização SQL](../backend/app/prontuario.py#L155) | Só depois de gravar o documento a API atualiza `consulta.id_prontuario`. |
| 5. A API lê o histórico | [ler_registro](../backend/app/prontuario.py#L82) | Depois de verificar o acesso, ela tenta o Redis. Se precisar, lê o MongoDB e guarda uma cópia temporária. |

**Trecho para projetar** de [prontuario.py](../backend/app/prontuario.py#L149):

```python
try:
    documentos().replace_one({"_id": str(id_prontuario)}, documento, upsert=True)
except PyMongoError as exc:
    raise HTTPException(503, "Não foi possível gravar o prontuário. Tente novamente.") from exc

conn.execute("UPDATE consulta SET id_prontuario = %s WHERE id_consulta = %s",
             (id_prontuario, id_consulta))
```

**Como explicar linha por linha**

1. `replace_one(..., upsert=True)` grava o documento pela chave da consulta. Se precisar repetir uma tentativa que falhou antes da confirmação no SQL, a chave é a mesma.
2. `except PyMongoError` devolve **503** se o MongoDB falhar. O código sai antes de atualizar o vínculo no PostgreSQL.
3. `UPDATE consulta` registra a referência quando a escrita do documento deu certo. A conclusão e o faturamento dependem dessa referência.

**Cache em 20 segundos:** “O primeiro acesso sem cópia é um **MISS**. O sistema lê o MongoDB e põe o conteúdo textual no Redis por 60 segundos. Se a próxima leitura encontrar a chave, é um **HIT**. Esse padrão se chama *cache-aside*.” Apontem `cache().get(chave)` e `cache().set(..., ex=60)`. O anexo é baixado do MongoDB.

**Se o professor perguntar sobre falha entre os bancos:** “A transação do PostgreSQL cobre o lado SQL. Se o MongoDB gravar e o SQL falhar depois, o documento fica sem referência visível pela API. A tentativa seguinte usa a mesma chave. São dois bancos com uma regra de publicação coordenada pela API.”

**Transição:** “A consulta foi concluída com prontuário e procedimento. Agora o administrativo pode gerar a cobrança.”

## 6. Integrante 4 · Faturamento e recursos do PostgreSQL

### O que clicar

1. Na sessão de **atendente**, abram **Faturamento**. No **Período de referência**, coloquem a data da consulta nos dois campos e cliquem em **Consultar período**.
2. Em **Fechamento dos convênios**, coloquem a mesma data nos dois campos e cliquem em **Gerar cobranças**. Em uma rodada isolada com um atendimento elegível, o retorno é **Cobranças geradas: 1**. Mostrem a linha de **R$ 180,00**, com **Aguardando pagamento**.
3. Se houver tempo, repitam o fechamento do mesmo período. Com a mesma massa de dados, o retorno é **0** novas cobranças.

### O que mostrar no código

Abram [operacoes.py, fechar_periodo](../backend/app/operacoes.py#L451). A tela chama `POST /faturamento/fechamento` e a API executa `CALL fechar_faturamento(...)`. Em seguida, mostrem na [migração SQL](../backend/sql/migrations/007_prontuario.sql#L39):

```sql
-- Trecho do INSERT da procedure, com filtros intermediários omitidos.
SELECT cs.id_consulta, sum(cp.valor * cp.quantidade), 'convenio', 'pendente'
FROM consulta cs JOIN consulta_procedimento cp USING (id_consulta)
-- ...
ON CONFLICT (id_consulta) DO NOTHING;
```

**Fala sugerida**

> O fechamento procura consultas realizadas, com prontuário e convênio, dentro do período. Ele soma o valor de cada procedimento vezes a quantidade. A procedure bloqueia as consultas selecionadas e existe uma restrição de uma fatura por consulta. Por isso repetir o fechamento mantém uma cobrança por atendimento.

Voltem ao início do mesmo arquivo e mostrem mais dois recursos pedidos na disciplina:

- [View `agenda_clinica`](../backend/sql/migrations/007_prontuario.sql#L10). É uma consulta salva que junta agendamento, paciente e médico. A API a usa para ler a agenda.
- [Trigger `auditar_agenda`](../backend/sql/migrations/007_prontuario.sql#L35). O banco registra automaticamente a criação ou mudança de status do agendamento, com o status e a data do evento.

**Jeito fácil de lembrar:** a *view* ajuda a ler, a *trigger* reage a uma alteração e a *procedure* é chamada para executar uma operação.

## 7. Integrante 5 · Testes, carga e encerramento

### O que abrir

Abram [resultados e comandos](demonstracao.md). Mostrem [carga.sql](../backend/sql/carga.sql#L10), que usa `generate_series` para gerar dados, e [benchmark.py](../backend/app/benchmark.py#L21), que usa lotes para povoar o MongoDB.

Para ensaiar, rodem estes comandos antes da apresentação:

```powershell
docker compose exec api python -m app.check_auth
docker compose exec api python -m app.check_fluxo
docker compose exec api python -m app.benchmark carga
docker compose exec api python -m app.benchmark medir
```

- `check_auth` verifica login, permissões, inativação e logout.
- `check_fluxo` exercita a API, incluindo concorrência, falha simulada na escrita, acesso ao anexo, cache e fechamento.
- `benchmark carga` cria **100 mil consultas e 100 mil prontuários fictícios**. A carga é para a base de demonstração.
- `benchmark medir` compara consulta por data no PostgreSQL e leitura clínica com e sem cache. Mostrem uma saída já salva, ou rodem apenas a medição se a base já estiver carregada e houver tempo.

### Números para falar

| Cenário medido | Sem | Com |
|---|---:|---:|
| Índice no PostgreSQL · mediana da consulta por data | 4,591 ms | 0,017 ms |
| Redis · p95 da leitura de prontuário | 4,815 ms | 3,048 ms |
| Redis · leituras por segundo | 2.609,5 | 5.025,2 |

**Fala sugerida**

> Esses números vêm de uma execução local com dados fictícios. No teste SQL, o plano mudou de uma varredura da tabela para uma busca pelo índice. No teste do Redis, fizemos mil leituras com oito trabalhadores e com o cache já aquecido no cenário com Redis. O p95 mostra o tempo dentro do qual ficaram aproximadamente 95% das leituras. As leituras por segundo medem a rotina de acesso aos dados, e o teste funcional também passa pela API HTTP.

**Se perguntarem sobre falha real:** “Também desligamos o MongoDB na cópia de teste. A gravação retornou **503**, e concluir ou faturar retornou **409**. Depois que o MongoDB voltou, salvamos e concluímos. Com o Redis desligado, a leitura seguiu pelo MongoDB.” Mostrem essa evidência no [relato dos testes](demonstracao.md).

**Encerramento sugerido**

> Mostramos uma consulta desde a agenda até a cobrança. O PostgreSQL protege as operações da clínica, o MongoDB guarda o prontuário e o Redis acelera sua leitura. Os testes mostram como o sistema reage a concorrência e falhas, e a carga permite comparar índice e cache. O repositório inclui os diagramas, o vídeo e os comandos para repetir os testes. Obrigado. Podemos responder às perguntas.

## 8. Perguntas que a equipe inteira deve saber responder

| Pergunta | Resposta curta |
|---|---|
| Onde o paciente se cadastra? | A equipe da clínica faz o cadastro. Os perfis de acesso são administrador, atendente e médico. |
| Por que guardar prontuário em MongoDB? | O registro reúne campos que variam entre atendimentos. Um documento pode conter evolução, exames, prescrições e dados adicionais juntos. |
| Qual é o vínculo entre os bancos? | `consulta.id_prontuario` aponta para o `_id` do documento. No fluxo normal, esse ID é o da consulta. |
| Como sabem que o médico pode ler? | A API valida a sessão e o vínculo do médico com o paciente ou consulta antes de consultar o cache. A gravação fica com o responsável pela consulta. |
| O que acontece se o Redis ficar fora? | A API consulta o MongoDB. O Redis é uma cópia de leitura com expiração. |
| Como evitam duas cobranças? | A consulta é bloqueada no fechamento e a tabela de faturamento aceita uma cobrança por consulta. |
| O CPF é consultado na Receita? | A validação do MVP verifica o formato e a unicidade no cadastro local. A consulta cadastral exigiria uma integração externa. |
| Vocês comprovaram 99% de disponibilidade? | Testamos falhas e recuperação em ambiente local. A taxa de disponibilidade exigiria medição durante um período real de operação. |
| Posso editar um prontuário salvo? | No fluxo atual, o médico revisa antes de salvar e o registro publicado fica disponível para leitura. Edição e versionamento ficam como evolução do MVP. |
| Os números valem para qualquer computador? | São os resultados da nossa execução local. Hardware, volume de dados e perfil das consultas influenciam as medidas. |

## 9. Cartão rápido para o dia

- **Aplicação:** `localhost:5173` · **API:** `localhost:8000/docs`.
- **Paciente:** André Lucas Barbosa · **Médico:** João Silva · **Convênio:** Lagoa Essencial.
- **Valor esperado:** R$ 180,00 com uma consulta de clínica médica e quantidade 1.
- **A ordem do caso:** liberar horário → reservar → iniciar → procedimento → prontuário → concluir → gerar cobrança.
- **A ordem do código:** reserva SQL → gravação MongoDB e vínculo SQL → leitura Redis/MongoDB → fechamento SQL.
- **A evidência final:** concorrência, falha e recuperação, 100 mil consultas e 100 mil prontuários, índice e cache.

