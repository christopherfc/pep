# Frontend do PEP

Aplicação React com TypeScript e Vite. O Docker Compose do projeto inicia o frontend e encaminha as chamadas de `/api` para o FastAPI.

Para desenvolver o frontend fora do Docker, mantenha a API rodando na porta 8000 e execute nesta pasta:

```powershell
npm ci
npm run dev
```

O Vite informa a URL no terminal. Se a API usar outra porta, defina `API_TARGET` antes de iniciar o Vite. `npm run build` verifica os tipos e gera a pasta `dist`.

As telas ficam em `src/pages`, as rotas em `src/routes/App.tsx` e o cliente HTTP em `src/services/api.ts`. As contas de exemplo e o fluxo de demonstração estão no [README do projeto](../README.md).
