"""Carga e comparação de desempenho usando dados fictícios."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from math import ceil
from statistics import median
from time import perf_counter

from psycopg import ClientCursor
from pymongo import UpdateOne

from .database import connect
from .manage import SQL
from .prontuario import ler_registro, documentos

PACIENTE = "8a04cfed-8106-4819-9ab0-7d22d1fa3b78"
TOTAL = 100_000
LOTE = 1000


def carregar():
    with connect() as conn:
        medico = conn.execute("""
            SELECT id_medico FROM medico JOIN usuario USING (id_usuario)
            WHERE email = 'joaosilva@pep.com'
        """).fetchone()
        if not medico:
            raise SystemExit("Execute python -m app.manage seed antes da carga.")
        with ClientCursor(conn) as cursor:
            cursor.execute((SQL / "carga.sql").read_text(encoding="utf-8"),
                           (medico["id_medico"], TOTAL, TOTAL))
        with conn.cursor(name="consulta_da_carga") as cursor:
            cursor.execute("""
                SELECT cs.id_consulta, cs.id_prontuario FROM consulta cs
                JOIN agendamento a USING (id_agendamento)
                WHERE a.id_paciente = %s
            """, (PACIENTE,))
            gravados = 0
            while registros := cursor.fetchmany(LOTE):
                operacoes = [
                    UpdateOne(
                        {"_id": str(registro["id_prontuario"])},
                        {"$setOnInsert": {
                            "id_consulta": str(registro["id_consulta"]),
                            "id_paciente": PACIENTE,
                            "evolucao": "Atendimento fictício para teste de carga.",
                        }},
                        upsert=True,
                    )
                    for registro in registros
                ]
                documentos().bulk_write(operacoes, ordered=False)
                gravados += len(operacoes)
    print(f"Consultas e prontuários disponíveis para o teste: {gravados:,}.")


def comparar_indice():
    consulta = "SELECT id_consulta FROM consulta WHERE data = DATE '1901-01-01'"
    with connect() as conn:
        conn.execute("ANALYZE consulta")
        for usar_indice in (True, False):
            if not usar_indice:
                conn.execute("SET LOCAL enable_indexscan = off")
                conn.execute("SET LOCAL enable_indexonlyscan = off")
                conn.execute("SET LOCAL enable_bitmapscan = off")
            tempos = []
            for _ in range(10):
                plano = conn.execute("EXPLAIN (ANALYZE, FORMAT JSON) " + consulta).fetchone()
                resultado = plano["QUERY PLAN"][0]
                tempos.append(resultado["Execution Time"])
            rotulo = "Com índice" if usar_indice else "Sem índice"
            print(f'{rotulo}: mediana {median(tempos):.3f} ms ({resultado["Plan"]["Node Type"]})')


def comparar_cache():
    with connect() as conn:
        ids = conn.execute("""
            SELECT cs.id_prontuario FROM consulta cs JOIN agendamento a USING (id_agendamento)
            WHERE a.id_paciente = %s ORDER BY cs.id_consulta LIMIT 20
        """, (PACIENTE,)).fetchall()
    if not ids:
        raise SystemExit("Execute python -m app.benchmark carga antes da comparação.")
    amostra = [registro["id_prontuario"] for registro in ids]
    for id_prontuario in amostra:
        ler_registro(id_prontuario)

    for usar_cache in (False, True):
        def medir(id_prontuario):
            inicio = perf_counter()
            _, origem = ler_registro(id_prontuario, usar_cache)
            return (perf_counter() - inicio) * 1000, origem

        inicio = perf_counter()
        with ThreadPoolExecutor(max_workers=8) as trabalhadores:
            resultados = list(trabalhadores.map(medir, amostra * 50))
        duracao = perf_counter() - inicio
        tempos = sorted(tempo for tempo, _ in resultados)
        p95 = tempos[ceil(len(tempos) * 0.95) - 1]
        acertos = sum(origem == "HIT" for _, origem in resultados)
        rotulo = "Com cache" if usar_cache else "Sem cache"
        print(f"{rotulo}: p50 {median(tempos):.3f} ms, p95 {p95:.3f} ms, "
              f"{len(tempos) / duracao:.1f} leituras/s, {acertos}/{len(tempos)} acertos no cache")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("acao", choices=["carga", "medir"])
    if parser.parse_args().acao == "carga":
        carregar()
    else:
        comparar_indice()
        comparar_cache()


if __name__ == "__main__":
    main()
