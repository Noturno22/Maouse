# Projeções das Primeiras Vendas — Mãouse (AirMouse)

> Estimativas de planeamento para o arranque comercial: alcance global realista
> (clientes pagos) e faturamento esperado nas primeiras vendas.
> Construído sobre `01_ESTRATEGIA/MODELO_DE_NEGOCIO.md` (sec. 13) e
> `01_ESTRATEGIA/ESTRATEGIA_GLOBAL.md` (sec. 2). **Data:** 2026-09-12 · Autor: Luar Studio Angola.
> **Natureza:** projeção, não previsão — assumir cenário BASE como referência de trabalho.

---

## 1. Método

Duas fases:

1. **Fase 1 — arranque**: primeiros **90 dias** após o lançamento pago (web checkout + lojas).
2. **Fase 2 — ano 1 (Y1)**: primeiro ano fiscal completo de vendas.

Três cenários por fase (Conservador / Base / Otimista), alinhados aos totais do plano
(€15k / €45k / €90k Y1). A Fase 1 equivale a ~10–15% do Y1 no cenário Base, refletindo a
curva de arranque de funil.

## 2. Pressupostos

| Pressuposto | Valor | Fonte |
|---|---|---|
| Conversão free→pago | 1,5–4% | modelo, sec. 21 |
| Receita média por pagante consumer (arranque) | ~€30–40 | mix lifetime (€39,90) + subs (€4,99/mês) — early adopters tendem a comprar lifetime |
| Preço de referência PRO desktop | €39,90 lifetime | `ui/license_dlg.py` `_PRODUCTS` |
| Piloto institucional pago | €2.000–5.000 (4–8 semanas) | ESTRATEGIA_GLOBAL, Ação 1 |
| Contrato institucional anual | €5.000–50.000 | modelo, sec. 11.3 |
| Free users necessários p/ 1.100 pagantes | ~45.000 | modelo, sec. 13.1 |
| Custo fixo mensal (Y1) | ~€2.000/mês | modelo, sec. 12 |

> **Aviso de dependência:** os clientes pagos da Fase 1 dependem de o **funil estar vivo**
> (landing page + vídeos + lojas + open-core). Sem funil, o cenário real é €0.

## 3. Fase 1 — Primeiros 90 dias

| Métrica | Conservador | **Base** | Otimista |
|---|---|---|---|
| Downloads free | 1.500–3.000 | 4.500–9.000 | 12.000–27.000 |
| Clientes pagos consumer | 60–120 | **150–300** | 400–900 |
| Faturamento consumer | €2k–5k | **€5k–12k** | €15k–38k |
| Pilotos institucionais | 0–1 | **1** | 1–2 |
| Faturamento institucional | €0–5k | **€2k–5k** | €5k–10k |
| **Faturamento total (90 dias)** | **€2k–10k** | **€7k–17k** | **€20k–48k** |

## 4. Fase 2 — Ano 1 (alinhado ao plano)

| Cenário | Clientes pagos globais | Free users (cum.) | Faturamento total | EBITDA |
|---|---|---|---|---|
| Conservador | ~400–500 | ~15.000 | **€15k** | ~−€5k |
| **Base** | **~1.100** | **45.000** | **€45k** | **~€7k (16%)** |
| Otimista | ~2.500–3.000 | 80.000+ | **€90k** | ~€50k |

Nota EBITDA: custos Y1 ≈ €38k (inclui ~€14k de custos de lançamento fase 0 — marca, landing,
vídeos, legal UE — recaindo para ~€2k/mês a partir do Y2).

## 5. Qual "mundo" nas primeiras vendas?

As primeiras vendas não são globais — são **concentradas**. Distribuição realista no Y1:

| Região | Peso estimado | Canal natural |
|---|---|---|
| PT + BR + AO | 50–60% | Mercado natal + língua + acessibilidade (regional pricing) |
| Resto UE (ES/FR/DE/IT) | ~25% | EU EAA (obrigação legal desde 28/06/2025) + i18n já no produto |
| EN global (acessibilidade/tech) | 15–25% | Comunidades de assistive technology + criadores |

O alcance global massivo chega nos **Y2–Y3** (lojas + criadores + OEM), não no Y1.

## 6. Alavanca nº 1: o contrato institucional

| Via | Esforço p/ €15k |
|---|---|
| Subscrições mobile (€2,99/mês) | ~420 subscrições/ano, churn contínuo |
| Licenças Pro lifetime (€39,90) | ~376 licenças, uma vez, não-recorrente |
| **Contrato institucional** | **1 contrato pequeno (€15k/ano)** |

Guia prático:
- Aproximar instituições com **piloto pago de €2–5k** (instalação + formação + relatório de
  compliance EU EAA), não com pedido de centenas de licenças.
- Validar procura com 10–15 conversas de descoberta (centros de reabilitação PT/BR, RH
  hospitalar, juristas de compliance) **antes** de investir em pilotos caros.
- **Margem por contrato ≈ 100%** (custo marginal ≈ 0 — produto offline).

## 7. Bloqueadores das primeiras vendas (checklist)

| # | Blocker | Estado | Impacto se não resolvido |
|---|---|---|---|
| 1 | **Paddle D2** — `PADDLE_VENDOR_ID = 0` em `ui/license_dlg.py:38` | ⛔ Pendente (dependência externa: vendor_id real) | Checkout não cobra → **€0 em vendas web** |
| 2 | Landing page + 3 vídeos demo + open-core GitHub | A planear (plano 90 dias) | Sem funil → sem downloads → sem conversão |
| 3 | Instalador `.exe` polido (EV signing / Microsoft Store) | Em curso | Bloqueia canal desktop massivo |
| 4 | Mobile Android na Play Store | Em construção | Faturamento mobile ≈ 0 no Y1 |

> O premier blocker é o **#1**: sem vendor_id Paddle real, não há primeiro euro.

## 8. Métricas de acompanhamento (definir OKRs no arranque)

| Métrica | Alvo dos primeiros 90 dias |
|---|---|
| Download free vs pagante | ≥ 2% de conversão |
| Clientes pagos | ≥ 1 (obviamente) · meta base 150 |
| Pilot track (contactos → pilotos) | ≥ 10 conversas · ≥ 1 piloto assinado |
| Ticket médio consumer | €30–40 |
| CAC | < €8 orgânico |
| Margem por contrato | ≥ 60% (ideal 100%) |

## 9. Resumo executivo

- **Alcance realista das primeiras vendas: 150–300 clientes pagos globalmente** (cenário base),
  concentrados em PT/BR/AO + UE.
- **Faturamento: €7–17k nos primeiros 90 dias → €45k no Y1** (base); €15k conservador;
  €90k otimista (com 1 contrato institucional).
- **Regra de ouro:** o salto de €15k → €90k vem de **1 contrato institucional**, não de volume.
- **Criticidade:** nada disto acontece enquanto o checkout Paddle estiver bloqueado (D2).

---

*Documento de planeamento — Luar Studio Angola · 2026. Valores são estimativas sujeitas a
validação com dados reais das primeiras vendas.*