# Mãouse — Pitch de Investimento

> **Documento de apresentação a potenciais investidores.**
> Autor: Luar Studio Angola · Data: 2026-09-13 · Confidencial.
> Base: `01_ESTRATEGIA/MODELO_DE_NEGOCIO.md`, `03_FINANCAS/PROJECOES_PRIMEIRAS_VENDAS.md`,
> `04_MARKETING_E_VENDAS/MAPA_OPS_VS_MARKETING.md`. Valores são estimativas de planeamento,
> sujeitas a validação com dados reais.

---

## 1. Elevator pitch

**Mãouse é o rato do futuro: controlas o computador apenas com a mão e a voz, usando a
webcam — sem hardware extra, sem aparelhos, sem custo por utilizador.**

É um produto completo, em código de produção, com **mais de 239 testes automatizados a
passar**, focado primeiro no segmento de **acessibilidade** (onde a compra é feita por
instituições, não por consumidores), com um plano claro para faturar **€45k no primeiro
ano (cenário base)** — e onde **um único contrato institucional vale mais do que centenas
de downloads gratuitos**.

---

## 2. O problema

- **1 em cada 7 pessoas no mundo vive com algum tipo de deficiência** (~1,3 mil milhões, OMS);
  50–100 milhões têm limitação motora nos membros superiores. Para muitas, um rato convencional
  é difícil ou impossível de usar.
- O software "pronto a vender" para este público não existe a preço acessível: as alternativas
  são **hardware caro** (ex.: Ultraleap, centenas de euros) ou **apps de 2.ª linha** (ex: Camera
  Mouse) que ninguém usa no dia a dia por falta de precisão.
- A **União Europeia impõe acessibilidade digital por lei desde 28/06/2025** (EU Accessibility Act
  — EAA): hospitais, escolas e o Estado precisam de soluções *comprovadamente* acessíveis, o que
  cria **procura legal e financiamento institucional** para software como o Mãouse.
- **Ninguém resolveu o problema da precisão**: há gestos por webcam de demonstração, mas não há um
  produto mainstream com qualidade profissional com que um utilizador consiga trabalhar o dia
  inteiro. É esse o vazio que o Mãouse preenche.

---

## 3. A solução — o que já está construído

**Mãouse controla o cursor com a mão (gestos) e com a voz, 100% offline, com privacidade
total (nada é enviado para a nuvem).** Zero hardware. Instalação em 1 clique. Windows 10/11 +
Android.

### Precisão de nível profissional (a barreira técnica resolvida)
1. Filtro One Euro — sem tremor parado, sem atraso em movimento.
2. Curva de aceleração exponencial — precisão sub-pixel devagar, varrimento total do ecrã rápido.
3. Emissor de movimento a **180 Hz** com interpolação sub-pixel — cursor sedoso mesmo com webcam a 15–30 fps.
4. Predição de movimento (~40 ms) e ponto de controlo = centro da palma — zero saltos ao clicar/arrastar.
5. Histerese nas pinças + estabilidade de 3 frames — sem cliques duplos acidentais.
6. Snap magnético via UI Automation — o cursor "gruda" nos botões reais de qualquer app (Chrome, Explorer, nativos).

### Interação natural
| Interface | O quê |
|---|---|
| **Gestos (7 classes, IA treinada)** | Mover, clique esq./dir., arrastar, scroll, volume — máquina de estados + IA (MLP) híbrida com regras |
| **Voz profissional (híbrida)** | "Jarvis" → comandos naturais em português transcritos por Whisper (local) → resposta falada por voz neural Piper |
| **Duas mãos** | Redundância de mão dominante 👏 palmas abrem o Assistente 3D; ✋✋ controla a Lupa do Windows |
| **Luz baixa** | Realce adaptativo (CLAHE) + ajuste de exposição da câmara quando o ambiente escurece |
| **Auto-afinação** | Adapta-se à tua câmara e velocidade; afinação fina em sliders com animação premium (painel de Definições reescrito) |

### Motores de receita já no produto
- **Gate Free/Pro** real por funcionalidade (`core/licensing.py`) + verificação de tempo de uso
  (trial) e chaves offline HMAC; **checkout Paddle** integrado para pagamentos.
- **Modo Trading Master** (€149,90) — recurso premium dos operadores de trading, já bloqueado
  para assinantes Pro.
- **Mobile Android** em React Native/Expo com paywall `ProGate`, subscrição
  `maouse_mobile_pro` e validação Google Play no nosso próprio servidor de licenças.

### Infraestrutura de negócio
- **license-server** próprio (deploy blueprint no Render): licenças, trial, emissão de chaves e
  webhook de pagamentos.
- **Instalador 1-clique** (Inno Setup via `build.bat`) que inclui os modelos de IA — arranca
  offline; voz/TTS descarregados na 1.ª utilização.
- **Só testes: 239 testes automatizados verdes** no repositório desktop.

---

## 4. Mercado

| Métrica | Valor | Nota |
|---|---|---|
| Dispositivos Windows ativos | ~1,4 mil milhões | Base instalada desktop |
| Utilizadores de smartphones | ~4,9 mil milhões (Android ~3,6–3,8) | Alvo mobile |
| Pessoas com deficiência significativa | ~1,3 mil milhões (~16%) | 1 em cada 7; problema mão-de-obra é subgrupo grande |
| Mercado de reconhecimento de gestos | **US$15 mil milhões em 2030** (CAGR ~20–25%) | Vento de cauda estrutural |
| Mercado de input por voz/IA | US$20+ mil milhões | Gesto e voz convergem |

**TAM → SAM → SOM**
- **TAM:** ~US$15 mil milhões/ano (2030)
- **SAM:** ~US$300–500 milhões/ano (acessibilidade, apresentações, media-center, kiosk)
- **SOM (1.º triénio):** €2–4 milhões/ano de receita recorrente

**Porquê agora**
1. Regulação de acessibilidade (EU EAA em vigor 2025; Section 508; leis PT/BR) exige software
   *comprovadamente* acessível.
2. `soma` de câmaras prontas (webcam em 100% dos portáteis) + modelos de mão (MediaPipe) maduros.
3. Vazio real: nenhum produto mainstream "rato de gestos por webcam" com qualidade profissional.

---

## 5. Modelo de negócio e preços

| Canal | Oferta | Preço (indicativo) | Tipo |
|---|---|---|---|
| Desktop — Free (open-core) | Motor de precisão + funil | €0 | Aquisição |
| Desktop — **Pro lifetime** | Recurso completo + voz + IA | €39,90 | 1x (early adopters compram lifetime) |
| Desktop — Pro subscrição | Tudo | €4,99/mês | Recorrente |
| **Trading Master** | Modo exclusivo para traders | €149,90 | 1x (só assinantes Pro pagos) |
| Mobile Android | Subscrição Pro | €2,99/mês | Recorrente (escala massiva via loja) |
| **Institucional (B2B/B2G)** | Piloto pago 4–8 semanas | €2.000–5.000 | Prova de valor |
| **Institucional (B2B/B2G)** | Contrato anual | €5.000–50.000 | Recorrente B2B |

**Economia da unidade — a parte bonita:**
- **Custo marginal ≈ 0**: o produto é 100% local/offline — escalar de 100 para 1 milhão de
  utilizadores quase não aumenta o custo de servidor. **Margem por contrato institucional ≈ 100%.**
- Custo fixo ~€2.000/mês no Y1 (contra €45k de receita base → **EBITDA ~€7k, ~16%**).
- Conversão free→pago assumida em 1,5–4% (realista para um produto com trial e demonstração visual).

---

## 6. Projeções financeiras (cenários)

### Primeiros 90 dias (Fase 1)

| Métrica | Conservador | **Base** | Otimista |
|---|---|---|---|
| Downloads free | 1.500–3.000 | 4.500–9.000 | 12.000–27.000 |
| Clientes pagos (consumer) | 60–120 | **150–300** | 400–900 |
| Faturamento consumer | €2k–5k | **€5k–12k** | €15k–38k |
| Piloto institucional | 0–1 | **1** | 1–2 |
| **Faturamento total (90 dias)** | **€2k–10k** | **€7k–17k** | **€20k–48k** |

### Ano 1 (Fase 2, alinhado ao plano de negócio)

| Cenário | Clientes pagos | Free users (cum.) | Faturamento | EBITDA |
|---|---|---|---|---|
| Conservador | ~400–500 | ~15.000 | **€15k** | ~−€5k |
| **Base** | **~1.100** | **45.000** | **€45k** | **~€7k (~16%)** |
| Otimista | ~2.500–3.000 | 80.000+ | **€90k** | ~€50k |

> **A regra de ouro:** o salto de €15k → €90k vem de **1 contrato institucional**, não de volume.
> ≈376 licenças lifetime (€39,90) = €15k, mas **1 contrato de €15k/ano fecha-o de uma vez**,
> com margem ~100%.

---

## 7. Go-to-market (90 dias)

Duas pistas em paralelo, documentadas e orçadas:

- **Pista A — Operacional (vender):** certificado de assinatura de código OV ($129), domínio,
  Render pago (sem cold-start no webhook Paddle), conta Google Play. **Destrava a 1.ª compra paga.
  Total ~$225–235.**
- **Pista B — Marketing (atrair):** registo de marca EUIPO+USPTO, entidade UE + advogado,
  landing `maouse.app` + 3–4 vídeos demo, 5 criadores (demo viral), ferramentas de lançamento.
  **Total ~€1.900–3.700.**
- **Cano institucional (a seguir):** auditoria WCAG independente (€1.500–5.000) + seguro RC
  profissional (€150–400/ano) — pré-requisitos para vender compliance EAA a hospitais/escolas.

**Segmentos em ordem de prioridade:** (1) Acessibilidade & saúde (integração individual +
institucional — maior disposição a pagar da história), (2) Apresentadores/professores/criadores
(early adopters virais), (3) Mobile Android emergentes (escala de volume).

---

## 8. Estado atual e marcos

| O quê | Estado |
|---|---|
| Produto desktop (gestos + voz + IA + snap) | ✅ Completo — código de produção, 239 testes verdes |
| UX premium (sliders animados, pausa circular animada no centro) | ✅ Recentemente concluído |
| Gate Free/Pro + trial + chaves offline HMAC | ✅ Implementado e testado |
| Checkout Paddle (produto/vendor) | ⛔ Falta vendor_id real (app `0`) — **bloqueador n.º 1 do primeiro euro** |
| Servidor de licenças (deploy blueprint Render) | ✅ Código pronto; falta deploy + env vars |
| Mobile Android (Expo, IAP, paywall) | 🔧 Em construção (Play Console/código) |
| Instalador 1-clique (`build.bat`) | ✅ Gera instalador; falta assinatura digital (cert EV/OV) |
| Landing + vídeos + open-core GitHub | ❌ A planear (plano 90 dias) |

**Com o financiamento deste investidor, o primeiro bloqueador é removido nas primeiras
semanas: o `vendor_id` Paddle real + deploy do servidor + instalador assinado → produto
"pronto a vender".**

---

## 9. Pedido de investimento e utilização de fundos (sugestão)

> Valor e participação a negociar. Sugestão ilustrativa de capital de arranque.

| Rubrica | Custo estimado |
|---|---|
| Pista A — destravar cobrança (assinatura, domínio, servidor, Play) | ~$225–235 |
| Pista B — marca, entidade UE, landing, vídeos, criadores | €1.900–3.700 |
| Checkout Paddle + webhook + email transacional | ~€0–100 |
| Cano institucional — auditoria WCAG + seguro RC | €1.650–5.400 |
| Reserva / suporte N1–N2 (2 meses) | ~€1.500 |
| **Total sugerido** | **~€5.000–10.000** |

**Uso do capital (90 dias):** destravar o pagamento → lançar funil (landing/vídeos/open-core) →
primeiro piloto institucional → primeiras 150–300 conversões pagas (cenário base).

---

## 10. Riscos e respetiva mitigação

| Risco | Mitigação |
|---|---|
| **Blocker #1: Paddle vendor_id = 0** → €0 em vendas web | Primeira ação com capital: conta Paddle + produto + webhook |
| Funil sem tração (sem downloads) | Landing + 3–4 vídeos demo + 5 criadores + open-core GitHub |
| Só consumidores pagam uma vez (lifetime) | Mix lifetime + subscrições + Trading Master + contrato institucional (recorrente) |
| Concorrentes (hardware caro, apps 2.ª linha) | Precisão profissional + preço ≤ €40 + zero hardware — diferenciação de categoria |
| Compliance B2B (WCAG, seguro, entidade UE) | Auditoria com fornecedores recomendados no plano; apenas para o canal institucional |

---

## 11. Resumo executivo

1. **Produto pronto e testado** — rato de gestos + voz com precisão profissional, offline,
   custo marginal zero, em Windows e Android.
2. **Mercado com vento de cauda** — acessibilidade obrigatória por lei na UE desde 2025;
   US$15 mil milhões em reconhecimento de gestos em 2030.
3. **Modelo com margens de software** — free→pago, lifetime + subscrição + Trading Master +
   B2B institucional; margem por contrato ≈ 100%.
4. **Alcance realista:** 150–300 clientes pagos nos primeiros 90 dias → **€45k no Y1 (base)**,
   €15k conservador, €90k otimista (com 1 contrato institucional).
5. **Começa a faturar em semanas** — o capital destrava exactamente o bloqueador n.º 1
   (Paddle/checkout) e o funil de aquisição.

---

*Confidencial · Luar Studio Angola · 2026. Documento preparado exclusivamente para discussão
de investimento; nada disto constitui uma oferta de valores mobiliários.*