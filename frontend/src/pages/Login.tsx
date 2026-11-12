import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import type { FormEvent } from "react";
import { apiRequest } from "../services/api";
export default function Login() {
  const navigate = useNavigate();
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function entrar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const campos = new FormData(event.currentTarget);
    setErro("");
    setEnviando(true);
    try {
      const sessao = await apiRequest<{ access_token: string; usuario: { perfil: string } }>("auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: campos.get("email"), senha: campos.get("senha") }),
      });
      sessionStorage.setItem("pep_token", sessao.access_token);
      navigate(sessao.usuario.perfil === "medico" ? "/painel-medico" : "/painel", { replace: true });
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível entrar.");
    } finally {
      setEnviando(false);
    }
  }
  return (
    <>
      <main className="login">
        <section className="login-story">
          <Link to="/" className="brand">
            <img src="/pep_logo_fundo_verde.png" alt="PEP - Prontuário Eletrônico do Paciente" />
          </Link>
          <p className="eyebrow remove-eyebrow" style={{ color: "#b9d9cd" }}>
            Prontuário eletrônico do paciente
          </p>
          <h1>
            Mais conexão.
            <br />
            Mais cuidado.
          </h1>
          <p>
            Uma rotina mais leve para a clínica. Uma história de cuidado mais
            completa para cada paciente.
          </p>
        </section>
        <section className="login-form" aria-labelledby="login-title">
          <form onSubmit={entrar}>
            <p className="eyebrow">Faça login</p>
            <h1 id="login-title">Bem-vindo ao PEP</h1>
            <label>
              E-mail
              <input
                type="email"
                name="email"
                autoComplete="username"
                placeholder="voce@clinica.com.br"
                required
              />
            </label>
            <label>
              Senha
              <input
                type="password"
                name="senha"
                autoComplete="current-password"

                required
              />
            </label>
            <button type="submit" disabled={enviando}>{enviando ? "Entrando…" : "Entrar"}</button>
            {erro && <p className="feedback" role="alert">{erro}</p>}
          </form>
        </section>
      </main>
    </>
  );
}
