"""Verifica o fluxo do PEP com o seed, em um ambiente de demonstração."""

import json
from base64 import b64encode
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import UUID

from fastapi import HTTPException
from pymongo.errors import ConnectionFailure

from .database import connect
from .prontuario import RegistroClinico, salvar_prontuario

API = "http://127.0.0.1:8000"
SENHA = "PepDemo123!"


def requisicao(rota, metodo="GET", dados=None, token=None, esperado=200):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    corpo = json.dumps(dados).encode() if dados is not None else None
    pedido = Request(API + rota, data=corpo, method=metodo, headers=headers)
    try:
        resposta = urlopen(pedido, timeout=15)
    except HTTPError as erro:
        resposta = erro
    with resposta:
        conteudo = resposta.read()
        aceitos = esperado if isinstance(esperado, tuple) else (esperado,)
        assert resposta.status in aceitos, (rota, resposta.status, esperado, conteudo)
        if resposta.headers.get_content_type() == "application/json":
            conteudo = json.loads(conteudo)
        return resposta.status, conteudo, resposta.headers


def login(email):
    _, sessao, _ = requisicao("/auth/login", "POST", {"email": email, "senha": SENHA})
    return sessao["access_token"], sessao["usuario"]


def main():
    medico, usuario = login("joaosilva@pep.com")
    outro_medico, _ = login("lauracosta@pep.com")
    atendente, _ = login("mariasilva@pep.com")

    agora = datetime.now(timezone(timedelta(hours=-3)))
    data = (agora.date() + timedelta(days=1)).isoformat()
    for tentativa in range(1440):
        minuto = (agora.hour * 60 + agora.minute + tentativa) % 1440
        status, horario, _ = requisicao("/disponibilidades", "POST", {
            "data": data, "horario": f"{minuto // 60:02d}:{minuto % 60:02d}",
        }, medico, esperado=(201, 409))
        if status == 201:
            break
    else:
        raise AssertionError("Nenhum horário livre para o teste.")

    _, pacientes, _ = requisicao("/pacientes?q=00000001400", token=atendente)
    paciente = pacientes[0]["id_paciente"]
    _, convenios, _ = requisicao(f"/pacientes/{paciente}/convenios?data={data}", token=atendente)
    assert convenios, "A carteirinha do seed deve estar válida na data do teste."
    agendamento = {
        "id_disponibilidade": horario["id_disponibilidade"],
        "id_paciente": paciente,
        "id_paciente_convenio": convenios[0]["id_paciente_convenio"],
    }
    with ThreadPoolExecutor(max_workers=2) as tarefas:
        tentativas = list(tarefas.map(
            lambda _: requisicao("/agendamentos", "POST", agendamento, atendente, esperado=(201, 409)),
            range(2),
        ))
    assert sorted(status for status, _, _ in tentativas) == [201, 409]
    id_agendamento = next(dados["id_agendamento"] for status, dados, _ in tentativas if status == 201)
    print("Agenda simultânea: uma reserva criada e a outra recusada.")

    rota_agenda = f"/agendamentos/{id_agendamento}"
    requisicao(rota_agenda, "PATCH", {"status": "em_atendimento"}, medico)
    _, agenda, _ = requisicao(f"/agendamentos?data={data}", token=medico)
    id_consulta = next(item["id_consulta"] for item in agenda if item["id_agendamento"] == id_agendamento)
    rota = f"/consultas/{id_consulta}/prontuario"

    requisicao(rota, token=atendente, esperado=403)
    requisicao(rota, token=outro_medico, esperado=404)
    requisicao(rota, esperado=401)

    with patch("app.prontuario.documentos", side_effect=ConnectionFailure("Falha simulada")):
        try:
            salvar_prontuario(UUID(id_consulta), RegistroClinico(evolucao="Falha de teste"), usuario)
        except HTTPException as erro:
            assert erro.status_code == 503
        else:
            raise AssertionError("A falha do MongoDB deveria impedir o salvamento.")
    _, consulta, _ = requisicao(rota, token=medico)
    assert consulta["registro"] is None
    requisicao(rota_agenda, "PATCH", {"status": "realizado"}, medico, esperado=409)
    requisicao("/faturamento", "POST", {
        "id_consulta": id_consulta, "forma_pagamento": "convenio",
    }, atendente, esperado=409)
    print("Falha de gravação simulada: prontuário ausente, conclusão e cobrança bloqueadas.")

    anexo = b"Exame ficticio do teste"
    requisicao(rota, "PUT", {
        "evolucao": "Registro fictício de integração.",
        "prescricoes": "Prescrição fictícia.",
        "exames": "Exame fictício.",
        "dados_adicionais": {"Escala de dor": "2"},
        "anexo": {"nome": "exame.txt", "base64": b64encode(anexo).decode()},
    }, medico)
    _, consulta, cabecalhos = requisicao(rota, token=medico)
    assert cabecalhos["X-Cache"] == "MISS" and consulta["registro"]["dados_adicionais"] == {"Escala de dor": "2"}
    _, _, cabecalhos = requisicao(rota, token=medico)
    assert cabecalhos["X-Cache"] == "HIT"
    _, arquivo, _ = requisicao(rota + "/anexo", token=medico)
    assert arquivo == anexo
    requisicao(rota + "/anexo", token=atendente, esperado=403)
    print("MongoDB e Redis: registro persistido, MISS seguido de HIT e anexo protegido.")

    requisicao(f"/consultas/{id_consulta}/procedimentos", "POST", {
        "id_procedimento": "2d45982b-75e1-43c8-b709-000000000031", "quantidade": 1,
    }, medico, esperado=201)
    requisicao(rota_agenda, "PATCH", {"status": "realizado"}, medico)
    with ThreadPoolExecutor(max_workers=2) as tarefas:
        fechamentos = list(tarefas.map(
            lambda _: requisicao("/faturamento/fechamento", "POST", {"inicio": data, "fim": data}, atendente),
            range(2),
        ))
    assert sum(resultado["total"] for _, resultado, _ in fechamentos) >= 1
    _, faturas, _ = requisicao(f"/faturamento?inicio={data}&fim={data}", token=atendente)
    consulta_faturada = [item for item in faturas if item["id_consulta"] == id_consulta]
    assert len(consulta_faturada) == 1 and float(consulta_faturada[0]["valor_total"]) == 180
    with connect() as conn:
        auditoria = conn.execute("""
            SELECT novo_status FROM auditoria_agenda WHERE id_agendamento = %s ORDER BY id
        """, (id_agendamento,)).fetchall()
    assert [evento["novo_status"] for evento in auditoria] == ["pendente", "em_atendimento", "realizado"]
    print(f"Fechamento simultâneo: uma cobrança de R$ 180,00. Auditoria OK. Consulta: {id_consulta}")


if __name__ == "__main__":
    main()
