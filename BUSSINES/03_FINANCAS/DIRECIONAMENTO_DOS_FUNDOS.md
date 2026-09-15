# Direcionamento dos Fundos — 1.º Investimento (Pista A)

> Divisão oficial do **1.º investimento recebido** (Roberto Almeida, Rotterdam 🇳🇱) —
> **260.000 Kz ≈ US$222** — nos direcionamentos de Pista A (destravar cobrança).
> Base: `CUSTOS_DE_LANCAMENTO.md`, `CHECKLIST_POS_PAGAMENTO.md`, `SETUP_PADDLE.md`.
> **Data:** 2026-09-14 · Autor: Luar Studio Angola · Confidencial.
> **Natureza:** divisão de alocação; valores de fornecedores a confirmar no checkout,
> diferenças reais absorvidas pela reserva (§4).

---

## 1. Princípio da divisão

> **O dinheiro é ignição, não combustível.** Só se gasta no que *destrava o primeiro euro*
> (Pista A). Tudo o que for "atrair" (Fase B), "crescer" (institucional) ou "sobreviver"
> (reserva de caixa) fica **fora** destes fundos — com prioridade acima noutras fontes.

| Direção | Incluído aqui? | Porquê |
|---|---|---|
| Pista A — destravar cobrança | ✅ **Sim (estes fundos)** | Remove o bloqueador n.º 1 (Paddle real) |
| Pista B / Fase B — marketing (marca, entidade UE, landing, vídeos, criadores) | ❌ Não | €1.900–3.700 — Fase B do Roberto (fundos + execução) |
| Cano institucional (WCAG + seguro RC) | ❌ Não | Só quando houver 1.º piloto pedido (€1.650–5.400) |
| Reserva de caixa operacional (2 meses) | ❌ Não | ~€4k — via receita/piloto/subsídio, não equity |

---

## 2. Divisão oficial (~US$222)

| # | Direção | Item | Custo | Prioridade | Quando | Estado |
|---|---|---|---|---|---|---|
| 1 | **Assinatura de código** | SSL.com IV (Individual) — pago | **US$129/ano** | 🔴 Não-negociável — bloqueador desktop n.º 1 | **Agora** | 🟡 **pago, em validação** (`SSLCOM_VALIDACAO.md`) |
| 2 | **Domínio da marca** | `maouse.app` — comprado | **US$14.342/ano** | 🔴 Não-negociável | **Agora** | ✅ |
| 3 | **License server** | Render **free tier** | **US$0** | 🟢 Hoje, zero | **Já** (validar fluxo) | ⬜ |
| 4 | **Email transacional** | Resend / SMTP free tier | **US$0** | 🟢 Hoje, zero | **Já** (entrega de chave `MAO-`) | ⬜ |
| 5 | **Pagamentos** | Paddle (Merchant of Record) | **US$0** (% por venda ~5%+$0,50) | 🟢 Hoje, zero | **Já** (checkout ativo) | ⬜ |
| 6 | **Loja mobile** | Play Developer (ativo — da reserva) | **US$25 (1x)** | 🟡 Decidido pelo Roberto | **Já** | ✅ |
| **Subtotal obrigatório** | | | **US$143.34** | | | |
| **Reserva de contingência** | | | **~US$53.66** | 🟡 Só aplicar com critério | §3 abaixo |

---

## 3. Reserva de contingência (~US$53.66) — ordem de aplicação

> Reserva inicial ~US$81, já com **US$25 gastos na Play Developer** (decisão de lançar
> mobile em paralelo) e **+US$2.342 do domínio** (real custou US$14.342 vs US$12 orçado)
> → resta **~US$53.66**.

| Ordem | Quando aplicar | Item | Custo | Critério |
|---|---|---|---|---|
| 1ª | Sempre que houver fees escondidas do signing | Buffer cloud/token/rees — re-emissão ou eSigner | **US$15–30** | Só se o fornecedor cobrar extra pelo signing |
| 2ª | Quando houver vendas recorrentes constantes | Render **instance paga** (1.º mês) | **US$7** (→ US$84/ano) | O free tier dorme (~15 min) e atrasa o webhook → só pago quando doer |
| 3ª | Reverter o resto para o fundo | Saldo retido (não gasto) | **US$16–38** | Não gastar sem decisão; devolver à tesouraria |

> **Regra:** nada na reserva é gasto "porque existe". Cada item dispara **só quando o critério
> da tabela acontecer** — se nenhum critério ocorrer, o saldo permanece guardado.

---

## 4. Controle de execução (vincular o gasto à entrega)

| Item | Critério de entrega | Evidência |
|---|---|---|
| Cert (US$129) | `Get-AuthenticodeSignature` → `Status: Valid`, Publisher "Luar Studio Angola", em `dist\AirMouse\AirMouse.exe` + instalador | Cmd output salvo no commit/build |
| Domínio (US$12) | `maouse.app` a resolver; usado na landing + Paddle App URL | `nslookup` + checkout Paddle a usar o domínio |
| Render free (US$0) | Blueprint deployado; `curl https://<service>.onrender.com/health` → `200 ok` | Log do health check |
| Email (US$0) | Uma compra real Paddle → email com chave `MAO-` chega ao comprador | Screenshot do email + licença ativada |
| Paddle (US$0) | `PADDLE_VENDOR_ID` real no `core/licensing.py` → checkout cobra | 1.ª transação `transaction.completed` no dashboard |

---

## 5. Resumo executivo

- **Total:** 260.000 Kz ≈ **US$222** — todo destinado à **Pista A (destravar cobrança)**.
- **Gasto até agora: US$168.34** (cert $129 + domínio $14.342 + Play $25) → **reserva ~US$53.66**.
- **Cert em validação na SSL.com** (ref# `co-3c1laihs7ca`); a entrega "pronto a vender" completa-se quando a validação aprovar e o `.exe` sair assinado.
- **Reserva restante: ~US$53.66** — eSigner/Render pago só quando os critérios §3 dispararem; evita pedir 2.ª ronda por despesa corrente.
- **Fora destes fundos:** Pista B (€1.900–3.700), cano institucional (€1.650–5.400), reserva de caixa (~€4k) — financiados por receita / Fase B do Roberto / piloto pago / subsídio, **não equity**.

---

*Planeamento financeiro — Luar Studio Angola · 2026. Confidencial. Valores de fornecedores sujeitos a confirmação no momento da compra; diferenças absorvidas pela reserva §3.*