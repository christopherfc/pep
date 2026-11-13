# Demonstração do PEP

[Vídeo de 40 segundos](PEP%20-%20Demonstracao.mp4) com as telas do atendimento, o fechamento e os resultados dos testes.

## Fluxo funcional

1. Entre como médico e cadastre um horário futuro em **Minha agenda**.
2. Entre como atendente, selecione um paciente e reserve o horário. Use um paciente com carteirinha válida para demonstrar o fechamento de convênios. Os dados de exemplo incluem André Lucas Barbosa no plano Lagoa Essencial.
3. Como médico, inicie o atendimento, registre o procedimento, preencha o prontuário e inclua um anexo fictício. Salve, reabra pelo histórico e conclua a consulta.
4. Como atendente, abra **Faturamento** e gere o fechamento dos convênios para a data da consulta. Repita o fechamento e confira que só existe uma cobrança para o atendimento.

## Testes reproduzíveis

Suba o ambiente conforme o README e aplique o seed. Na pasta do projeto:

```powershell
docker compose exec api python -m app.check_auth
docker compose exec api python -m app.check_fluxo
docker compose exec api python -m app.benchmark carga
docker compose exec api python -m app.benchmark medir
```

O teste de fluxo cria um atendimento fictício e dispara duas reservas para o mesmo horário. Ele simula uma falha de escrita no MongoDB e confirma o bloqueio de conclusão e cobrança. Em seguida grava o prontuário, testa os acessos e o download, confere o Redis pelos cabeçalhos `X-Cache: MISS` e `X-Cache: HIT` e dispara dois fechamentos simultâneos. O resultado esperado é uma única reserva, uma cobrança de R$ 180,00 e três eventos na auditoria.

No teste com os contêineres, a API retornou 503 ao gravar com o MongoDB desligado e 409 ao tentar concluir ou faturar. Após religar o MongoDB, a mesma consulta aceitou o prontuário e pôde ser concluída. Com o Redis desligado, a leitura retornou 200 pelo MongoDB.

No navegador, foram conferidos o preenchimento do prontuário, a reabertura pelo histórico, o download e o fechamento. A tela de leitura foi testada com larguras de 390, 768 e 1.280 pixels.

A carga cria 100 mil consultas e 100 mil prontuários fictícios. Ela usa chaves determinísticas para poder ser repetida. Rode-a na base de demonstração.

## Resultados observados

Execução local em Docker da versão final, com 100 mil consultas no PostgreSQL e 100 mil prontuários no MongoDB. O vídeo registra uma execução anterior do mesmo benchmark.

| Consulta por data no PostgreSQL | Mediana de 10 execuções | Plano |
| --- | ---: | --- |
| Com índice | 0,024 ms | Index Scan |
| Sem índice | 6,671 ms | Seq Scan |

O teste mede `EXPLAIN ANALYZE` e desabilita os planos de acesso por índice apenas durante a comparação.

| Leitura de prontuários | p50 | p95 | Leituras/s | Acertos no cache |
| --- | ---: | ---: | ---: | ---: |
| Sem cache | 2,986 ms | 5,738 ms | 2.339,9 | 0 de 1.000 |
| Com cache | 1,494 ms | 3,136 ms | 4.676,4 | 1.000 de 1.000 |

O teste executa a rotina de leitura usada pela API, com oito trabalhadores e 1.000 leituras de 20 prontuários. O cenário com Redis usa cache aquecido. As medições cobrem o acesso aos dados. O teste funcional exercita também a API HTTP.
