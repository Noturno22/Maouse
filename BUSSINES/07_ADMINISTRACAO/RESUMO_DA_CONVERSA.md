# Resumo da Conversa — 2026-09-13

> Registo resumido da sessão de trabalho sobre investidores e administração.
> Autor: Luar Studio Angola · Data: 2026-09-13 · Confidencial.

---

## 1. Pitch de investidores — versão simples

- Criado **`06_INVESTIDORES/PITCH_INVESTIDOR_SIMPLES.md`** — versão de 1 página, linguagem simples.
- **Reposicionado:** foco principal no **público em geral** (consumer primeiro); institucional
  passa a **acelerador**, não alvo inicial.

## 2. Área administrativa criada

- Criada **`07_ADMINISTRACAO/`** — nova área de controlo da empresa.
- **`HISTORICO_DA_EMPRESA.md`** — registo oficial de marcos (empresa **pré-fundada, ainda sem papel**).
- **`ESTRUTURA_DA_EMPRESA.md`** — controlo total da estrutura: **sócios, funcionários, investidores**.

## 3. 1.º investimento recebido

- **Roberto Almeida** (Rotterdam 🇳🇱) — apoio inicial de **260.000 Kz (≈ US$222)**.
- Registado como o **primeiro investimento externo** da empresa.

## 4. Comissão / equity (será definida com ele)

- Opções avaliadas: A) convertível · B) equity fixo · C) doação + reconhecimento.
- Escolhida **Opção B — equity fixo de 3%** (+ papel de parceiro UE em Roterdão).
- **Em reavaliação:** o fundador acha o 3% pouco → discussão pendente.

## 5. Fase B — Roberto poderá assumir a "Pista B" (marketing)

- Roberto pode tratar **fundos + execução da Fase B**: marca EUIPO/USPTO, entidade UE, landing
  `maouse.app`, vídeos demo, criadores (**orçada €1.900–3.700**).
- Com isso a contribuição dele sobe para ~$2.500–4.500 → **equity proposto: 8–15% com vesting**.

## 6. Previsão de caixa — lucros e novo capital

- Criado **`03_FINANCAS/PREVISAO_DE_CAIXA.md`** — fases, cash flow mensal, break-even e capital.
- Conclusões:
  - **Depois da Fase B NÃO há lucros** — é fase de investimento.
  - **Break-even: mês 14–18 (cenário base)**, ~fim do ano 1 (EBITDA ~€7k vs €45k receita).
  - **Pic de caixa negativo ~€8k nos meses 3–5** → **capital adicional leve (€3–7k)** provável,
    de preferência por receita/piloto/subsídio, não por equity.

## 7. Sessão — revisão do investimento e uso do capital

> Sessão de trabalho (opencode) — recapitulação do investimento e priorização do uso de fundos.

- **Recapitulado o 1.º investimento:** Roberto Almeida, 260.000 Kz (≈ US$222), equity 3% (reavaliação p/ 8–15% com vesting).
- **Recomendação de equity:** **8–15% só com execução real da Fase B e vesting ligado à entrega** (milestones), não à promessa. ~3% se o Roberto continuar apenas como anjo.
- **Uso do investimento — Pista A em primeiro:** ~$225–235 cobre o **bloqueador n.º 1** (Paddle `vendor_id` real, domínio, servidor pago, assinatura de código, Play) → produto **"pronto a vender"**.
- **Pistas seguintes:** Pista B (€1.900–3.700) = Fase B do Roberto · meses 3–5 (pico negativo ~€8k) = €3–7k por receita/piloto/subsídio, **não equity**.
- **Leitura:** o investimento serve de **ignição**, não de combustível.
- **Guião criado:** `03_FINANCAS/SETUP_PADDLE.md` — passo-a-passo do portal de pagamento (conta/KYC, 5 produtos+preços, Pay Links → `.env`, webhook/secret, SMTP, deploy Render pago, teste e2e sandbox, go-live). Tudo manual; código já pronto e suite verde.

---

## Decisões pendentes (follow-up)

| # | Pendência | Onde se regista |
|---|---|---|
| 1 | Fechar % de equity do Roberto (8–15% com vesting?) | `ESTRUTURA_DA_EMPRESA.md` §3.1 |
| 2 | Confirmar se a Fase B fica mesmo com o Roberto | `ESTRUTURA_DA_EMPRESA.md` §3.1 |
| 3 | Formalização legal ("sem papel" → contratos) | `ESTRUTURA_DA_EMPRESA.md` / `HISTORICO_DA_EMPRESA.md` |
| 4 | Plano de capital para os meses 3–5 (pic negativo) | `PREVISAO_DE_CAIXA.md` §6 |
| 5 | Executar **Pista A** com o 1.º investimento (Paddle real + checkout + webhook) | `RESUMO_DA_CONVERSA.md` §7 |

---

*Resumo de sessão — Luar Studio Angola · 2026. Confidencial.*