# PEP · Banco de Dados II

O PEP é um projeto acadêmico para a rotina de uma clínica. A equipe cadastra os pacientes e agenda os atendimentos. O médico registra o prontuário e os procedimentos. A equipe administrativa consulta o histórico de atendimentos e gera as cobranças.

O paciente é um registro cadastral. As contas de acesso são de administrador, atendente e médico.

## Executar

Abra o Docker Desktop e execute na pasta do projeto:

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build -d --wait
docker compose exec api python -m app.manage seed
```

- Aplicação: http://localhost:5173
- Documentação da API: http://localhost:8000/docs
- Verificação dos três bancos: http://localhost:8000/health/ready

Na inicialização, a API aplica as migrações PostgreSQL e cria a coleção `prontuarios` no MongoDB. A criação também pode ser executada com `docker compose exec api python -m app.manage init-mongo`. O seed é opcional e usa dados fictícios. As novas contas de exemplo usam a senha `PepDemo123!`.

O arquivo `002_uuid_ids.sql` serve apenas para converter bases antigas com IDs inteiros. Para uma instalação nova, siga os comandos acima.

| Acesso | Conta de exemplo |
| --- | --- |
| Atendente | `mariasilva@pep.com` |
| Médico | `joaosilva@pep.com` |

Para criar a primeira conta de administrador:

```powershell
docker compose exec api python -m app.manage create-admin
```

Use `docker compose stop` para pausar os serviços. PostgreSQL e MongoDB usam volumes persistentes. O Redis usa cache temporário. Use as credenciais do arquivo `.env.example` em um ambiente local com dados fictícios.

## Fluxo do atendimento

1. O médico oferece um horário futuro em **Minha agenda**. A recepção seleciona paciente, médico e horário em **Novo agendamento**.
2. Em **Minha agenda**, o médico inicia o atendimento, registra os procedimentos e abre o prontuário. A evolução clínica é obrigatória. Prescrição, exames, campo adicional e um anexo de até 2 MB são opcionais.
3. Depois de salvar o prontuário, o médico conclui a consulta. O registro fica disponível no histórico dos médicos que atendem aquele paciente.
4. A equipe administrativa gera a cobrança em **Faturamento**. Para convênios, o fechamento do período gera as cobranças elegíveis em lote. O sistema usa os valores registrados nos procedimentos.

Consultas antigas sem prontuário podem receber o registro do médico responsável. Cobranças já existentes continuam disponíveis no histórico financeiro.

## Onde está cada parte

| Pasta ou arquivo | Conteúdo |
| --- | --- |
| `backend/app/auth.py` | Login, sessão e perfis |
| `backend/app/operacoes.py` | Cadastros, agenda e faturamento |
| `backend/app/manutencao.py` | Manutenção de cadastros, cobertura e procedimentos |
| `backend/app/prontuario.py` | Autorização, gravação no MongoDB e cache Redis |
| `backend/sql` | Estrutura relacional, migrações e cargas de exemplo |
| `frontend/src/pages` | Telas React |
| [Arquitetura e modelagem](docs/arquitetura.md) | Diagramas, responsabilidades e consistência |
| [Demonstração e resultados](docs/demonstracao.md) | Roteiro, teste funcional e benchmark |
| [Roteiro da apresentação](docs/roteiro-apresentacao.md) | Falas, sequência de cliques, código e perguntas para estudar |

Para desenvolvimento do frontend fora do Docker, veja o [guia do frontend](frontend/README.md).
