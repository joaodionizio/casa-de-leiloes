// Testes de navegador da Story 2.5 (Playwright). Cobrem só o que `node --test`, o
// TypeScript e o build não provam: History API, foco, layout em viewports reais e
// imagem quebrada. A lógica pura segue em `npm test`.
//
// A API é simulada por interceptação de rede (`e2e/support/mockApi.ts`): nenhum banco,
// nenhuma AIC e nenhum dado persistente são tocados. O servidor é o `vite preview` do
// build de produção. O browser vem do comando documentado no README:
//   npx playwright install chromium

import { defineConfig, devices } from '@playwright/test'

const PORT = 4173

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.spec.ts',
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    // Artefatos só para depuração de uma falha; nenhum assert depende de imagem.
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `npm run build && npx vite preview --host 127.0.0.1 --port ${PORT} --strictPort`,
    url: `http://127.0.0.1:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
