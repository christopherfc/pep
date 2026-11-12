-- Carga fictícia. As chaves fixas permitem repetir o comando.
INSERT INTO paciente (id_paciente, nome, cpf)
VALUES ('8a04cfed-8106-4819-9ab0-7d22d1fa3b78', 'Paciente de Benchmark', '00000099000')
ON CONFLICT (id_paciente) DO NOTHING;

INSERT INTO agendamento (id_agendamento, id_medico, id_paciente, data, horario, status)
SELECT md5('agenda-benchmark-' || n)::uuid, %s,
       '8a04cfed-8106-4819-9ab0-7d22d1fa3b78', DATE '1900-01-01' + n / 100,
       TIME '00:00' + (n %% 100) * INTERVAL '1 minute', 'realizado'
FROM generate_series(1, %s) AS n
ON CONFLICT (id_agendamento) DO NOTHING;

INSERT INTO consulta (id_consulta, id_agendamento, data, horario, status, id_prontuario)
SELECT md5('consulta-benchmark-' || n)::uuid, a.id_agendamento, a.data, a.horario,
       'realizada', md5('prontuario-benchmark-' || n)::uuid
FROM generate_series(1, %s) AS n
JOIN agendamento a ON a.id_agendamento = md5('agenda-benchmark-' || n)::uuid
ON CONFLICT (id_consulta) DO NOTHING;
