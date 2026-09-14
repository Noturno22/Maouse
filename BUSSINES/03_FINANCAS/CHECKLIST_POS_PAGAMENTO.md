# Checklist Pós-Pagamento — Mãouse (AirMouse)

> Passos de **execução sem custo** que transformam "ingredientes comprados"
> (**Render pago: $225–235/ano**, ver `CUSTOS_DE_LANCAMENTO.md` e `MAPA_OPS_VS_MARKETING.md`)
> em "pronto para vender". Complementa `BUSSINES/02_EXECUCAO/PRONTIDAO_PARA_VENDA.md`
> (bloqueadores técnicos).

---

## 1. Assinatura do `.exe` — `docs/ASSINATURA_DIGITAL.md`

- [ ] Colocar `cert\maouse.pfx` na raiz do projeto (o `.gitignore` já ignora `*.pfx`)
- [ ] Definir a password via variável de ambiente `PFX_PASS` (não fica no histórico do shell)
- [ ] Correr `build.bat` (assina o `.exe` + o instalador Inno Setup automaticamente)
- [ ] Verificar com `Get-AuthenticodeSignature` → `Status: Valid` + Publisher "Luar Studio Angola"
      em `dist\AirMouse\AirMouse.exe` e `dist\Maouse-Setup-1.0.0.exe`

> Lembrar: certificados novos ainda podem mostrar SmartScreen até ganhar reputação —
> resolve-se com downloads legítimos e volume, não é bug da assinatura.

---

## 2. Deploy do license-server no Render — `license-server/DEPLOY_RENDER.md`

- [ ] Blueprint com `render.yaml` (código já está pronto)
- [ ] Definir as env vars **obrigatórias**:
  - `AIRMOUSE_LS_ADMIN_TOKEN` (ex.: `openssl rand -hex 24`)
  - `AIRMOUSE_LS_PRIVATE_KEY` / `AIRMOUSE_LS_PUBLIC_KEY` (PEM de `license-server/`)
- [ ] Métricas da conta de serviço Google: `AIRMOUSE_GOOGLE_PLAY_CREDENTIALS_JSON`
      (Android Publisher API) — sem isto o `mobile/entitle` só corre em modo dev
- [ ] Opcionais: `AIRMOUSE_PADDLE_*`, `AIRMOUSE_SMTP_*` + `AIRMOUSE_SMTP_ENABLED=1`
- [ ] Disco persistente **1 GB em `/data`** (`AIRMOUSE_LS_DB=/data/license.db`)
- [ ] Confirmar: `curl https://<service>.onrender.com/health` → `200 ok`

---

## 3. Gravar o URL real no build — `docs/DESKTOP_LICENSE_URL.md`

- [ ] Em `core/licensing.py`, `_default_endpoints()`: trocar o placeholder
      `https://licenses.maouse.example.com` pelo URL real `https://<service>.onrender.com`
- [ ] Igualar também `tools/issue_pro_key.py` (`AIRMOUSE_LS_URL` default) se usado
- [ ] Rebuildar e reassinar o `.exe` (`build.bat`)
- [ ] **Nunca** mudar o URL depois de distribuir sem rebuildar

> **Gap crítico:** sem isto o `.exe` assinado não ativa licenças no cliente
> (o trial local continua a funcionar, mas a chave `MAO-` falharia sempre).

---

## 4. Pagamento + email (Paddle/SMTP)

- [ ] Conta Paddle + criar o produto com `PADDLE_PRODUCT_URLS` do `core/licensing.py`
- [ ] Definir `AIRMOUSE_PADDLE_WEBHOOK_SECRET`, `AIRMOUSE_PADDLE_VENDOR_ID`, `AIRMOUSE_PADDLE_API_KEY`
- [ ] Conta de email transacional free tier (ex. Resend) + domínio `maouse.app`
      → `AIRMOUSE_SMTP_HOST/PORT/USER/PASSWORD/FROM`
- [ ] Testar **uma compra real** → webhook `transaction.completed` emite a chave
      `MAO-` e o email chega ao comprador

---

## 5. Mobile (Play Console)

- [ ] Conta dev Google Play ($25, pago 1 vez)
- [ ] Criar produto IAP `maouse_mobile_pro` (o code-side já está ✅: expo-iap +
      validação Google no license-server + paywall `ProGate`)
- [ ] Criar conta de serviço Google com permissão Android Publisher API
      → `AIRMOUSE_GOOGLE_PLAY_CREDENTIALS_JSON` no Render
- [ ] Desligar `AIRMOUSE_MOBILE_DEV_ALLOW=0` em produção
- [ ] Icons Mãouse + privacy policy URL + store listing (copy de acessibilidade)
- [ ] Upload do código com IAP (EAS Build/prebuild + `submit.production`)

---

## 6. LAB de hardware — `HARDWARE/`

- [ ] Preencher `HARDWARE/MATRIZ_DE_DISPOSITIVOS.md` com ≥5 devices por categoria crítica
      (desktop GPU, desktop CPU fraco, mobile low-end) usando `HARDWARE/LAB.md` +
      `HARDWARE/CHECKLIST_VALIDACAO.md`
- [ ] Registar falhas em `HARDWARE/PROBLEMAS_KNOWN.md`
- [ ] Critério de go: ≥1 ✅ validado por categoria crítica

> Sustenta promessas honestas e previne reembolsos (D7).

---

## 7. Pista B — Marketing & vendas (em paralelo, custo €1.900–3.700)

> Mapa completo e custos em `BUSSINES/04_MARKETING_E_VENDAS/MAPA_OPS_VS_MARKETING.md` e no
> `PLANO_DE_EXECUCAO_90_DIAS.md` §5. O plano orçou EV €300–500; com **OV ($129)** a Pista B
> aproxima-se do mínimo de €1.900.

- [ ] Registo de marca EUIPO + USPTO (€300–600, 1x — moat nº1)
- [ ] Domínios extra `.app/.io/.com` + anti-typosquatting (€50)
- [ ] Entidade UE + advogado (€600–1.500 — bloqueador B2B/B2G, Paddle, lojas)
- [ ] Landing `maouse.app` + 3–4 vídeos demo (€200–500, DIY/IA)
- [ ] Ferramentas Paddle/EAS/CI (€100–300)
- [ ] 5 criadores demo viral (€300, Sprint 3)
- [ ] Conferências/deslocações (€200, opcional)
- [ ] **Total Pista B** ≈ **€1.900–3.700**

### Custos NÃO orçamentados (Cano B institucional — só p/ vender a hospitais)

- [ ] **Auditoria WCAG independente** — €300–1.000 (agência) a €1.500–5.000 (manual
      especializada; recomendado p/ o Mãouse). Projeto EAA completo €4.000–15.000.
      Re-auditoria em cada mudança de UI.
- [ ] **Seguro RC profissional** — ~€150–400/ano (TI/digital, ex. exali desde €133/ano;
      escala com a faturação e capital seguro).

---

## Ordem sugerida

1. **2 → 3 → 1** (server → URL real → `.exe` assinado): destrava a venda desktop.
2. **4** em paralelo: pagamento + email (precisa do 2 para o webhook).
3. **5 e 6** podem andar atrás, sem bloquear a venda desktop.
4. **Pista B (7)** corre nos 90 dias; **Cano B** só quando: auditoria WCAG + seguro RC +
   entidade UE + matriz ≥1 ✅ por categoria crítica.

---

*Operacional · Luar Studio Angola · 2026. Complementa `CUSTOS_DE_LANCAMENTO.md`,
`PRONTIDAO_PARA_VENDA.md`, `docs/ASSINATURA_DIGITAL.md`, `license-server/DEPLOY_RENDER.md`,
`docs/DESKTOP_LICENSE_URL.md` e `MAPA_OPS_VS_MARKETING.md`.*