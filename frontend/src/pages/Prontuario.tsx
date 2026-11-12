import { Link, useParams } from "react-router-dom";
import { useState } from "react";
import { AppLayout } from "../layouts/AppLayout";
import { Cadastro, EstadoDados } from "../components/Operacoes";
import { useDados } from "../hooks/useDados";
import { apiResponse } from "../services/api";
import { salvar } from "../services/operacoes";

type Registro = {
  evolucao: string;
  prescricoes: string | null;
  exames: string | null;
  dados_adicionais?: Record<string, string>;
  nome_anexo?: string;
};

type ProntuarioDaConsulta = {
  paciente: string;
  id_paciente: string;
  registro: Registro | null;
  pode_registrar: boolean;
};

export default function Prontuario() {
  const { consulta } = useParams();
  const [versao, setVersao] = useState(0);
  const [erroAnexo, setErroAnexo] = useState("");
  const caminho = "consultas/" + consulta + "/prontuario";
  const { data, loading, error } = useDados<ProntuarioDaConsulta>(consulta ? caminho : null, versao);
  const nomeAnexo = data?.registro?.nome_anexo;

  async function baixarAnexo(nome: string) {
    setErroAnexo("");
    try {
      const resposta = await apiResponse(caminho + "/anexo");
      const url = URL.createObjectURL(await resposta.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = nome;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      setErroAnexo(error instanceof Error ? error.message : "Não foi possível baixar o anexo.");
    }
  }

  return <AppLayout medical>
    <div className="page-heading"><h1>Prontuário da consulta</h1></div>
    <EstadoDados loading={loading} error={error} />
    <Link to="/painel-medico">Voltar à agenda</Link>
    {data && <section className="card">
      <h2>{data.paciente}</h2>
      <Link to={"/historico?paciente=" + data.id_paciente}>Ver histórico do paciente</Link>
      {data.registro ? <>
        <dl className="registro-clinico">
          <dt>Evolução clínica</dt><dd>{data.registro.evolucao}</dd>
          <dt>Prescrições</dt><dd>{data.registro.prescricoes || "Nenhuma registrada"}</dd>
          <dt>Exames</dt><dd>{data.registro.exames || "Nenhum registrado"}</dd>
          {Object.entries(data.registro.dados_adicionais ?? {}).map(([campo, valor]) =>
            <div key={campo}><dt>{campo}</dt><dd>{valor}</dd></div>)}
        </dl>
        {nomeAnexo && <button type="button" onClick={() => void baixarAnexo(nomeAnexo)}>
          Baixar {nomeAnexo}
        </button>}
        {erroAnexo && <p role="alert">{erroAnexo}</p>}
      </> : data.pode_registrar ? <>
        <p>Confira os dados antes de salvar. O registro fica disponível para consulta após o envio.</p>
        <Cadastro label="Salvar prontuário" concluido={() => setVersao(v => v + 1)}
          enviar={async campos => {
            const nome = String(campos.get("campo")).trim();
            const valor = String(campos.get("valor")).trim();
            if (Boolean(nome) !== Boolean(valor)) throw new Error("Preencha o nome e o valor do campo adicional.");
            return salvar(caminho, {
              evolucao: campos.get("evolucao"),
              prescricoes: String(campos.get("prescricoes")).trim() || null,
              exames: String(campos.get("exames")).trim() || null,
              dados_adicionais: nome ? { [nome]: valor } : {},
              anexo: await prepararAnexo(campos.get("anexo")),
            }, "PUT");
          }}>
          <label>Evolução clínica<textarea name="evolucao" maxLength={10000} required /></label>
          <label>Prescrições<textarea name="prescricoes" maxLength={5000} /></label>
          <label>Exames solicitados ou resultados<textarea name="exames" maxLength={5000} /></label>
          <label>Campo adicional<input name="campo" maxLength={80} placeholder="Ex.: Escala de dor" /></label>
          <label>Valor do campo adicional<input name="valor" maxLength={1000} /></label>
          <label>Anexo de até 2 MB<input name="anexo" type="file" /></label>
        </Cadastro>
      </> : <p>Prontuário ainda pendente.</p>}
    </section>}
  </AppLayout>;
}

async function prepararAnexo(arquivo: FormDataEntryValue | null) {
  if (!(arquivo instanceof File) || !arquivo.size) return null;
  if (arquivo.size > 2 * 1024 * 1024) throw new Error("Selecione um arquivo de até 2 MB.");
  const base64 = await new Promise<string>((resolve, reject) => {
    const leitor = new FileReader();
    leitor.onload = () => resolve(String(leitor.result).split(",")[1]);
    leitor.onerror = () => reject(new Error("Não foi possível ler o arquivo."));
    leitor.readAsDataURL(arquivo);
  });
  return { nome: arquivo.name, base64 };
}
