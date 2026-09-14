# Setup Paddle — Portal de Pagamento (Pista A)

> Guia operacional para destravar o pagamento automático (bloqueador n.º 1 da
> `PRONTIDAO_PARA_VENDA.md`). O investimento de arranque (≈ US$222) cobre **esta**
> etapa: conta Paddle + serviço pago no Render + domínio.
> **Natureza:** execução 100% manual (conta bancária/fiscal da empresa) — o código
> já está pronto e testado.
> **Data:** 2026-09-13 · Autor: Luar Studio Angola · Complementa
> `license-server/DEPLOY_RENDER.md`.

---

## 0. O que já está pronto (NÃO repetir)

| Peça | Estado |
|---|---|
| `POST /webhooks/paddle` (verifica HMAC → emite chave `MAO-` → dedup por `event_id` → email) | ✅ `license-server/app.py` |
| `paddle.py` (assinatura + parsing) · `emailer.py` (SMTP stdlib) · tabela `purchases` | ✅ |
| Cliente abre checkout (5 produtos) via env `AIRMOUSE_PADDLE_*_URL` | ✅ `core/licensing.py` |
| Suite de testes `license-server/` verde + testes de checkout do cliente verdes | ✅ | 

**O que falta é só dados reais da conta Paddle** para preencher o `.env` / Render.

---

## 1. Conta e entidade (KYC)

> ⚠️ **BLOQUEIO COMERCIAL REAL:** o Paddle é *Merchant of Record* — exige entidade
> verificada (KYC de negócio) para distribuir dinheiro. A empresa está
> **pré-fundada, sem papel legal**. O caminho recomendado:

1. **Hoje — Sandbox:** não exige KYC. Cria a conta em
   **https://sandbox-vendors.paddle.com** e monta tudo, para testar de ponta a ponta.
2. **Para Live — Entidade UE (Fase B):** o Paddle paga para contas bancárias
   verificadas da entidade. A **entidade EU** prevista para a Fase B (idealmente via
   Roberto/Roterdão) é o que destrava o live em condições. Só avançar para live
   depois da entidade ou de o Paddle aceitar a estrutura Luar Studio Angola.
3. **Conta live:** **https://vendors.paddle.com** (mesma conta, modo live).

> Até lá, o plano de execução: **sandbox completo** (esta semana) + **entidade** no
> horizonte da Fase B.

---

## 2. Catálogo — 5 produtos a criar

No dashboard: **Catalog → Products → + New product**. Cria os 5; depois **Prices**
dentro de cada produto (o Paddle separa *Product* do *Price*).

| Produto Luar | Preço (UI) | Tipo de preço | Chave de produto (exemplo interno) |
|---|---|---|---|
| **Mãouse Pro — Lifetime** | €39,90 | pago único | `maouse-pro-lifetime` |
| **Mãouse Pro — Subscrição** | €4,99/mês (ou €3,49/mês anual) | recorrente | `maouse-pro-subscription` |
| **Mãouse Família** | €59,90 (3 dispositivos) | pago único | `maouse-family` |
| **Mãouse Acessibilidade** | €19,95 (50% sob validação) | pago único | `maouse-pro-access` |
| **Trading Master** | €149,90 | pago único | `maouse-trading-master` |

> Nota: os IDs internos de produto/preço **não precisam de bater certo com o código** —
> o webhook emite a mesma chave Pro `MAO-` para qualquer produto. Mantém só nomes
> legíveis para o vosso controlo.

---

## 3. Checkout Links (Pay Links) → `.env`

> ⚠️ O formato antigo `checkout.paddle.com/{vendor_id}?product=...` (Paddle Classic)
> está deprecated. Usa o formato **Billing moderno** dos Pay Links.

1. No dashboard: **Checkout Links** (ou **Checkouts → Create checkout**).
2. Escolhe o *Price* do produto (ex.: Lifetime €39,90) → gera o link
   `https://checkout.paddle.com/<ID>`.
3. Repete para os 5 produtos e cola cada URL no `.env` (nunca nos `*.py`):

```bash
AIRMOUSE_PADDLE_LIFETIME_URL=https://checkout.paddle.com/xxx
AIRMOUSE_PADDLE_SUBSCRIPTION_URL=https://checkout.paddle.com/xxx
AIRMOUSE_PADDLE_FAMILY_URL=https://checkout.paddle.com/xxx
AIRMOUSE_PADDLE_ACCESS_URL=https://checkout.paddle.com/xxx
AIRMOUSE_PADDLE_TRADING_MASTER_URL=https://checkout.paddle.com/xxx
```

4. **Vendor ID:** no dashboard (perfil/Developer tools) copia o *Vendor ID* e
   preenche os dois sitios:
   - `ui/license_dlg.py` → `PADDLE_VENDOR_ID = 0` (o TODO do bloqueador #1) — é o
     fallback Classic; fica certo por higiene.
   - `AIRMOUSE_PADDLE_VENDOR_ID` no `.env` (referido no `DEPLOY_RENDER.md`).

---

## 4. Webhook → notificações (secret)

1. **Developer tools → Notifications → Add destination:**
   - **URL:** `https://<SEU-SERVIDOR>.onrender.com/webhooks/paddle`
   - **Secret:** gera um valor forte e **guarda-o** (não é mostrado outra vez):
     ```bash
     openssl rand -hex 24   # ou PowerShell: [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(24))
     ```
2. **Eventos a subscrever:**
   - `transaction.completed` → **obrigatório** (é o que o webhook processa)
   - `transaction.refunded` / `transaction.updated` → opcionais (o servidor ignora, mas fica registado para o futuro)
3. Cola o secret em `AIRMOUSE_PADDLE_WEBHOOK_SECRET` no `.env` (dev) e no painel do Render (prod).

---

## 5. Email da chave (SMTP)

O webhook envia a chave por email (`emailer.py`, SMTP puro — sem dependências).

```bash
AIRMOUSE_SMTP_ENABLED=1
AIRMOUSE_SMTP_HOST=smtp.seu-provedor.com
AIRMOUSE_SMTP_PORT=587
AIRMOUSE_SMTP_USER=seu-usuario
AIRMOUSE_SMTP_PASSWORD=sua-senha
AIRMOUSE_SMTP_FROM=sales@maouse.app
```

- **Dev/primeiro teste:** usa SMTP real barato (ex.: Brevo/Resend/SMTP2GO) ou a app-password do Gmail.
- Em produção **nunca** deixar `AIRMOUSE_SMTP_ENABLED=0` (o comprador ficaria sem chave).

---

## 6. Deploy do license-server no Render

Seguir **`license-server/DEPLOY_RENDER.md`** (v1.1). Pontos-chave:

- **Plano pago Starter (~US$7/mês)** — o Free tem cold-start e sleep que quebram o webhook em horas de silêncio. Este custo está dentro do investimento (~$225).
- Variáveis obrigatórias do Render: `AIRMOUSE_LS_ADMIN_TOKEN`, `AIRMOUSE_LS_PRIVATE_KEY` (PEM completo), `AIRMOUSE_LS_PUBLIC_KEY` (PEM completo).
- Juntar: `AIRMOUSE_PADDLE_WEBHOOK_SECRET`, `AIRMOUSE_SMTP_*` (`ENABLED=1`).
- Disco: `AIRMOUSE_LS_DB=/data/license.db` (já no `render.yaml`).
- Confirmar: `curl https://<servico>.onrender.com/health` → `{"status":"ok"}`.

> Depois do deploy, gravar o URL real em `core/licensing.py`:
> `PROD_LICENSE_SERVER_URL = "https://<servico>.onrender.com"` — sem isto o `.exe`
> não ativa licenças (gap de produção da `PRONTIDAO_PARA_VENDA.md` §1).

---

## 7. Teste de ponta a ponta (sandbox)

1. `.env` preenchido (URLs + secret) e servidor a correr localmente.
2. **Paddle sandbox:** *Checkout Links →* abre o link de teste → compra simulada, OU
   no webhook usa **“Send test notification”** com `transaction.completed`.
3. Verifica o servidor: `/webhooks/paddle` responde `200` + `{"ok":true,"handled":true,"key":"MAO-..."}`.
4. Confirma na DB: tabela `purchases` com o `event_id` (envia o mesmo evento 2× → mesma chave, sem duplicar).
5. Se SMTP ligado: chega o email com a chave.
6. **Cliente:** cola a chave no diálogo Pro → ativa → tier Pro.

---

## 8. Go-live

- [ ] Entidade validada no Paddle (KYC) — condição para live
- [ ] Produtos + Pay Links criados no **live**
- [ ] `.env`/Render com URLs live + secret live
- [ ] Render pago + `/health` ok + URL real gravado em `core/licensing.py`
- [ ] SMTP ligado e testado
- [ ] Compra de teste real (cartão) → chave por email → ativação no cliente
- [ ] Registar a primeira venda em `CHECKLIST_POS_PAGAMENTO.md`
- [ ] Após as primeiras vendas: atualizar `RESUMO_DA_CONVERSA.md` e a `PREVISAO_DE_CAIXA.md` com dados reais

---

## 9. Limitações atuais (conhecidas)

- **Family (3 dispositivos):** o webhook emite **uma** chave Pro por compra — as 3
  ativações da Família requerem emissão manual extra via `/admin/keys`. (Simplificação
  aceite; rever quando houver volume.)
- **Accessibilidade (€19,95):** o cupão de 50% já previsto no produto (sem workflow
  automático ainda — a verificação é manual e emite cupão/código).
- **Vendor ID Classic:** as URLs env têm prioridade; só o fallback web deprecado usa o
  `vendor_id`. Preencher por higiene, não como via principal.

---

*Execução · Luar Studio Angola · 2026. Passos manuais (conta/moeda/entidade) são responsabilidade da empresa.*