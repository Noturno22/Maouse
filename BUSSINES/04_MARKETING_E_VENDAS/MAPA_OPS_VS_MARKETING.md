# Mapa OPS vs Marketing — Mãouse (AirMouse)

> As duas pistas que transformam o produto em receita. **Pista A** = capacidade operacional
> de cobrar (bloqueada por pagamentos). **Pista B** = execução de marketing/atração
> (orçamento do plano de 90 dias). Complementa `CUSTOS_DE_LANCAMENTO.md`,
> `CHECKLIST_POS_PAGAMENTO.md`, `PLANO_DE_EXECUCAO_90_DIAS.md` e
> `MODELO_DE_MARKETING_E_VENDAS.md`.
> **Data:** 2026-09-05 · Autor: Luar Studio Angola.

---

## PISTA A — Operacional (destravar a capacidade de cobrar) — decisão: **$225–235**

| Item | Custo | Frequência | Nota |
|---|---|---|---|
| Certificado code-signing OV | $129 | 1x/ano | OV suficiente desde 2026 (EV não salta SmartScreen) |
| Domínio `.com/.pt` | ~$12 | 1x/ano | Página de produto + "App Publisher URL" |
| Render — instance paga ($7/mês) | $84 | 1x/ano | Sem cold-start no webhook Paddle (decisão: começar pago) |
| Google Play (opcional) | $25 | 1x | Só se lançar mobile |
| **Total** | **~$225–235** | | + checklist pós-pagamento (sem custo) |

**Resultado:** "desktop vendável" (OKR O2.1 do plano) — aceitar a 1ª compra paga.
**Prazo:** ~1–2 semanas após pagamento (ver `CHECKLIST_POS_PAGAMENTO.md`).

> Alternativa mais barata: free tier Render $0 → total ~$141–151/ano (mas com cold-start
> no webhook). Decisão tomada: começar pago.

---

## PISTA B — Marketing & vendas (atrair conversões) — orçamento 90 dias: **€1.900–3.700**

Fonte: `PLANO_DE_EXECUCAO_90_DIAS.md` §5 (orçamento indicativo). O plano orçou **EV
€300–500/ano**; escolhendo **OV ($129)** poupa-se ~€150–350/ano → aproxima o total do
**mínimo** de €1.900.

| Rubrica | Custo | Tipo | Nota |
|---|---|---|---|
| Registo de marca (EUIPO + USPTO) | €300–600 | 1x | Moat nº1 |
| Domínios extra (`.app/.io/.com` + anti-typosquatting) | €50 | 1x | Blindagem da marca |
| Entidade UE + advogado | €600–1.500 | 1x | Bloqueador B2B/B2G (Paddle, lojas) |
| Assinatura de código | (na Pista A: OV $129) | | Plano orçou EV €300–500; escolhido OV |
| Landing + 3–4 vídeos demo | €200–500 | 1x | Pode ser DIY/IA |
| Ferramentas (Paddle, EAS, CI) | €100–300 | 1x/ano | Near-zero na prática |
| 5 criadores (demo viral) | €300 | 1x | S3 do plano |
| Conferências/deslocações | €200 | 1x | Opcional |
| **Total** | **~€1.900–3.700** | | Dentro do custo fixo ~€2k/mês do modelo |

Para além do pagamento: **auditoria WCAG independente + seguro RC** (ver secção seguinte).

---

## Custos NÃO orçamentados no plano (custo real maior) — estimativas 2026

> Exigidos para vender **compliance a instituições/hospitais** (Cano B). Para a venda
> consumer troca desktop não são bloqueadores — só o Cano B os precisa.

### 1. Auditoria WCAG independente
Prova de terceiros (não auto-declaração) de conformidade com WCAG 2.1/2.2 AA — obrigatória
para vender "conformidade EU EAA" a hospitais. Mercado 2026:

| Nível | Preço | Quando usar |
|---|---|---|
| Scan automático (SaaS) | 99–499 €/mês | Monitorização; não é prova legal |
| Auditoria agência-level | 300–1.000 € | Relatório utilizável, sem pass manual completo |
| Auditoria especializada manual | 1.500–5.000 € | **Caminho recomendado p/ o Mãouse (desktop + mobile)** |
| Projeto EAA completo (auditoria + correção + re-scan) | 4.000–15.000 € | Antes de vender compliance |
| VPAT/ACR certificado | 10.000 €+ | Procurement governamental |

**Estimativa Mãouse: começar em €1.500–5.000** (auditoria manual com scope otimizado:
fluxos core do desktop + ecrãs principais do mobile). Re-auditoria em cada mudança de UI.

### 2. Seguro RC profissional (indemnização profissional)
Cobre reclamações por erros/omissões/negligência ("não cumpriu o prometido e o cliente
foi multado"). Mercado PT 2026:

- Exali (TI/digital): **desde ~€133/ano líquidos** (depende de volume de faturação e capital seguro)
- Hiscox / intermediários PT: ~€150–400/ano para TI/software

**Estimativa Mãouse: ~€150–400/ano** (a escalar com a faturação).

---

## Fornecedores a contactar (pendentes de decisão)

> Itens cujo valor é estimativa de mercado — escolher fornecedor antes de gastar.
> Regra: pedir sempre **3 orçamentos** e confirmar o scope no email.

### Auditoria WCAG

| Fornecedor | Perfil | Preço indicativo 2026 |
|---|---|---|
| **AccessiProof** (EU) | Auditoria agência-level, feita na EU | desde €399 |
| **EAAPass** (EU) | Scan automático grátis + planos agência | €0–499 |
| **Accessible.org** | Manual por página/ecrã (DHS Trusted Testers) | $100–250/ecrã |
| **Consultores independentes** | Manual completo; melhor custo-benefício | €2.000–20.000 |
| Deque Systems | Enterprise, referência do sector | $5.000–50.000+ |
| Level Access | Enterprise/retainer | $10.000–100.000+/ano |

> **Recomendado:** contactar **3** (AccessiProof + 2 consultores independentes). Pedir scope
> otimizado: fluxos core do desktop + ecrãs principais do mobile + 1 re-scan incluído.

### Seguro RC profissional (Portugal)

| Fornecedor | Nota |
|---|---|
| **exali** | RC digital desde ~€133/ano líquidos; cobertura mundial; simulação online rápida |
| **Hiscox** (via Medal) | RC profissional para empresas |
| **Protev Seguros** | Broker — compara várias seguradoras |
| **Chambel Seguros** | Broker |
| **Soma Future Seguros** | Broker |

> **Recomendado:** simulação online exali (€133–400/ano) + 2 cotações via broker PT.
> Confirmar: cobertura de erros/omissões + cibersegurança, capital ≥ €50k, e escala de
> prémio com o volume de faturação.

### Certificado code-signing (escolher a CA)

| Fornecedor | Preço |
|---|---|
| **SSL.com OV** | $129/ano (1º ano) |
| Certum Cloud OV | ~€209/ano |
| Sectigo OV | €211–288/ano |

> **Recomendado:** SSL.com OV ($129/ano) — o mais barato para empresa registada.

### Mini-checklist antes de gastar
- [ ] 3 orçamentos por item (auditoria, seguro, certificado)
- [ ] Scope claro por escrito (páginas/ecrãs, capital seguro, validade do cert)
- [ ] Registar a decisão em `DECISOES.md` (auditoria escolhida + seguro + CA)

---

## Sequência

1. **Pista A agora** (~$225–235, 1x) → destrava a 1ª venda desktop.
2. **Pista B em paralelo nos 90 dias** (€1.900–3.700) → atrai conversões.
3. **Cano B (institucional)** só quando: auditoria WCAG feita + seguro RC ativo + entidade
   UE em ordem + matriz de dispositivos ≥1 ✅ por categoria crítica
   (`MODELO_DE_MARKETING_E_VENDAS.md` §2.2).

## Resumo de custo total até à 1ª venda real

| Cenário | Total | "Sem/com institucional" |
|---|---|---|
| Só desktop vendável (Pista A) | **~$225–235** | — |
| **Sem institucional** — Pista A + Pista B (consumer) | **~€2.125–3.935** (~$2.3k–4.3k) | Sem Cano B |
| **Com institucional** — A + B + Cano B (auditoria WCAG €1.500–5.000 + seguro RC €150–400/ano) | **~€3.775–9.335** (~$4.1k–10.2k) | Com Cano B |

---

*Operacional · Luar Studio Angola · 2026. Preços de mercado 2026 — confirmar no
fornecedor antes de comprar.*