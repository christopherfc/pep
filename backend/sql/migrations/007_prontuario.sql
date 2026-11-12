ALTER TABLE consulta ADD COLUMN id_prontuario uuid UNIQUE;

CREATE INDEX agendamento_paciente_data_idx ON agendamento (id_paciente, data DESC);
CREATE INDEX agendamento_medico_data_idx ON agendamento (id_medico, data, horario);
CREATE INDEX consulta_procedimento_consulta_idx ON consulta_procedimento (id_consulta);
CREATE INDEX consulta_data_idx ON consulta (data);
CREATE UNIQUE INDEX agendamento_horario_ativo_idx
    ON agendamento (id_medico, data, horario) WHERE status <> 'cancelado';

CREATE VIEW agenda_clinica AS
SELECT a.*, p.nome AS paciente, u.name AS medico, m.id_usuario AS usuario_medico
FROM agendamento a
JOIN paciente p USING (id_paciente)
JOIN medico m USING (id_medico)
JOIN usuario u USING (id_usuario);

CREATE TABLE auditoria_agenda (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_agendamento uuid NOT NULL REFERENCES agendamento(id_agendamento),
    status_anterior text,
    novo_status text NOT NULL,
    registrado_em timestamptz NOT NULL DEFAULT now()
);

CREATE FUNCTION auditar_agenda() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' OR OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO auditoria_agenda (id_agendamento, status_anterior, novo_status)
        VALUES (NEW.id_agendamento, CASE WHEN TG_OP = 'UPDATE' THEN OLD.status END, NEW.status);
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER auditar_agenda
AFTER INSERT OR UPDATE OF status ON agendamento
FOR EACH ROW EXECUTE FUNCTION auditar_agenda();

CREATE PROCEDURE fechar_faturamento(IN inicio date, IN fim date, INOUT total integer)
LANGUAGE plpgsql AS $$
DECLARE
    consultas uuid[];
BEGIN
    SELECT array_agg(id_consulta) INTO consultas
    FROM (
        SELECT cs.id_consulta
        FROM consulta cs JOIN agendamento a USING (id_agendamento)
        WHERE cs.data BETWEEN inicio AND fim AND cs.status = 'realizada'
          AND cs.id_prontuario IS NOT NULL AND a.id_paciente_convenio IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM faturamento f WHERE f.id_consulta = cs.id_consulta)
        ORDER BY cs.id_consulta FOR UPDATE OF cs
    ) AS elegiveis;

    INSERT INTO faturamento (id_consulta, valor_total, forma_pagamento, status)
    SELECT cs.id_consulta, sum(cp.valor * cp.quantidade), 'convenio', 'pendente'
    FROM consulta cs JOIN consulta_procedimento cp USING (id_consulta)
    WHERE cs.id_consulta = ANY (consultas)
    GROUP BY cs.id_consulta
    HAVING sum(cp.valor * cp.quantidade) <= 9999999999.99
    ON CONFLICT (id_consulta) DO NOTHING;
    GET DIAGNOSTICS total = ROW_COUNT;
END;
$$;
