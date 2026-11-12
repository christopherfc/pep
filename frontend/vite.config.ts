import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  return {
    server: {
      proxy: {
        "/api": {
          target: env.API_TARGET || "http://localhost:8000",
          changeOrigin: true,
          rewrite: path => path.replace(/^\/api/, ""),
        },
      },
    },
  };
});
