"""Registro clínico por consulta. A autorização sempre é consultada no PostgreSQL."""

import json
import os
from base64 import b64decode
from binascii import Error as Base64Error
from functools import lru_cache
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import Field, StringConstraints
from typing import Annotated
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid, OperationFailure, PyMongoError
from redis import Redis
from redis.exceptions import RedisError

from .auth import current_user
from .database import connect
from .operacoes import Dados, medico_atende_paciente

router = APIRouter(tags=["Prontuário"])


class Anexo(Dados):
    nome: str = Field(max_length=150)
    base64: str = Field(max_length=2_796_204)


class RegistroClinico(Dados):
    evolucao: str = Field(max_length=10000)
    prescricoes: str | None = Field(default=None, max_length=5000)
    exames: str | None = Field(default=None, max_length=5000)
    dados_adicionais: dict[
        Annotated[str, StringConstraints(min_length=1, max_length=80)],
        Annotated[str, StringConstraints(min_length=1, max_length=1000)],
    ] = Field(default_factory=dict, max_length=10)
    anexo: Anexo | None = None


@lru_cache
def documentos():
    cliente = MongoClient(
        host=os.environ["MONGO_HOST"], username=os.environ["MONGO_USER"],
        password=os.environ["MONGO_PASSWORD"], authSource="admin",
        timeoutMS=3000,
    )
    return cliente[os.environ["MONGO_DB"]].prontuarios


def inicializar_colecao():
    colecao = documentos()
    try:
        colecao.database.create_collection(colecao.name)
    except CollectionInvalid:
        return
    except OperationFailure as exc:
        if exc.code != 48:  # A coleção pode ter sido criada por outro processo.
            raise


@lru_cache
def cache():
    return Redis(
        host=os.environ["REDIS_HOST"], password=os.environ["REDIS_PASSWORD"],
        socket_connect_timeout=1, socket_timeout=1, decode_responses=True,
    )


def consulta_autorizada(conn, id_consulta, usuario, para_gravar=False):
    if usuario["perfil"] != "medico":
        raise HTTPException(403, "O prontuário é restrito à equipe médica")
    sql = """
        SELECT cs.id_prontuario, cs.status, a.id_paciente, p.nome AS paciente,
               m.id_usuario = %s AS responsavel
        FROM consulta cs JOIN agendamento a USING (id_agendamento)
        JOIN medico m USING (id_medico) JOIN paciente p USING (id_paciente)
        WHERE cs.id_consulta = %s
    """
    if para_gravar:
        sql += " FOR UPDATE OF cs"
    consulta = conn.execute(sql, (usuario["id_usuario"], id_consulta)).fetchone()
    if not consulta:
        raise HTTPException(404, "Consulta não encontrada")
    if not consulta["responsavel"] and (
        para_gravar or not medico_atende_paciente(conn, consulta["id_paciente"], usuario["id_usuario"])
    ):
        raise HTTPException(404, "Consulta não encontrada")
    return consulta


def ler_registro(id_prontuario, usar_cache=True):
    chave = f"pep:prontuario:{id_prontuario}"
    if usar_cache:
        try:
            registro = cache().get(chave)
            if registro:
                return json.loads(registro), "HIT"
        except (RedisError, ValueError):
            pass

    try:
        registro = documentos().find_one({"_id": str(id_prontuario)}, {"_id": 0, "arquivo": 0})
    except PyMongoError as exc:
        raise HTTPException(503, "Prontuário indisponível. Tente novamente.") from exc
    if registro is None:
        raise HTTPException(503, "Registro clínico indisponível")

    if usar_cache:
        try:
            cache().set(chave, json.dumps(registro), ex=60)
        except RedisError:
            pass
    return registro, "MISS" if usar_cache else "BYPASS"


@router.get("/consultas/{id_consulta}/prontuario")
def consultar_prontuario(id_consulta: UUID, response: Response, usuario=Depends(current_user)):
    with connect() as conn:
        consulta = consulta_autorizada(conn, id_consulta, usuario)
    registro = None
    if consulta["id_prontuario"]:
        registro, origem = ler_registro(consulta["id_prontuario"])
        response.headers["X-Cache"] = origem
    response.headers["Cache-Control"] = "no-store"
    return {
        "paciente": consulta["paciente"],
        "id_paciente": consulta["id_paciente"],
        "registro": registro,
        "pode_registrar": consulta["responsavel"] and consulta["status"] in ("em_atendimento", "realizada"),
    }


@router.put("/consultas/{id_consulta}/prontuario")
def salvar_prontuario(id_consulta: UUID, dados: RegistroClinico, usuario=Depends(current_user)):
    with connect() as conn:
        consulta = consulta_autorizada(conn, id_consulta, usuario, para_gravar=True)
        if consulta["id_prontuario"]:
            raise HTTPException(409, "Esta consulta já tem um prontuário registrado")
        if consulta["status"] not in ("em_atendimento", "realizada"):
            raise HTTPException(409, "Inicie a consulta antes de registrar o prontuário")

        id_prontuario = id_consulta
        documento = {
            "_id": str(id_prontuario),
            "id_consulta": str(id_consulta),
            "id_paciente": str(consulta["id_paciente"]),
            **dados.model_dump(exclude={"anexo"}),
        }
        if dados.anexo:
            try:
                arquivo = b64decode(dados.anexo.base64, validate=True)
            except Base64Error as exc:
                raise HTTPException(422, "Anexo inválido") from exc
            if not arquivo or len(arquivo) > 2 * 1024 * 1024:
                raise HTTPException(422, "Selecione um arquivo de até 2 MB")
            documento["nome_anexo"] = dados.anexo.nome
            documento["arquivo"] = arquivo
        try:
            documentos().replace_one({"_id": str(id_prontuario)}, documento, upsert=True)
        except PyMongoError as exc:
            raise HTTPException(503, "Não foi possível gravar o prontuário. Tente novamente.") from exc

        # Só fica visível depois que o PostgreSQL confirma a referência.
        conn.execute("UPDATE consulta SET id_prontuario = %s WHERE id_consulta = %s",
                     (id_prontuario, id_consulta))
    return {"id_prontuario": id_prontuario}


@router.get("/consultas/{id_consulta}/prontuario/anexo")
def baixar_anexo(id_consulta: UUID, usuario=Depends(current_user)):
    with connect() as conn:
        consulta = consulta_autorizada(conn, id_consulta, usuario)
    if not consulta["id_prontuario"]:
        raise HTTPException(404, "Anexo não encontrado")
    try:
        registro = documentos().find_one(
            {"_id": str(consulta["id_prontuario"])}, {"arquivo": 1, "nome_anexo": 1},
        )
    except PyMongoError as exc:
        raise HTTPException(503, "Anexo indisponível. Tente novamente.") from exc
    if not registro or "arquivo" not in registro:
        raise HTTPException(404, "Anexo não encontrado")
    return Response(
        registro["arquivo"], media_type="application/octet-stream",
        headers={
            "Content-Disposition": "attachment; filename*=UTF-8''" + quote(registro["nome_anexo"], safe=""),
            "Cache-Control": "no-store",
        },
    )
