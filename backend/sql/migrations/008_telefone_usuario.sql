-- O telefone cadastral pertence à conta, inclusive para médicos.
UPDATE usuario u SET telefone = m.telefone
FROM medico m
WHERE m.id_usuario = u.id_usuario AND u.telefone IS NULL AND m.telefone IS NOT NULL;

ALTER TABLE medico DROP COLUMN telefone;
