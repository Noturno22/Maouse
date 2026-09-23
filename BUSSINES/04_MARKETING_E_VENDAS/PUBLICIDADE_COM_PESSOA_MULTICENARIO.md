# Publicidade com Pessoa — Roteiro Multi-Cenário (Higgsfield)

> **Conceito:** um spot onde **uma pessoa real controla o cursor com a mão em vários cenários do
> dia-a-dia**, com **transições cinematográficas** a ligar os cenários (match cut / whip pan /
> morph) — geradas no Higgsfield. Narrativa: "um dia inteiro sem tocar num rato físico".
> Formato: **16:9 · 30–45 s · 9:16 para vertical (TikTok/Reels)** · einmal pro peça-mestra, reutilizável
> em vídeo-ads e TV spots.
> Regra-mestra (inalterável): **cada cena do produto é gravação REAL** (a pessoa real a mover o
> cursor); Higgsfield gera apenas **transições e tratamentos de cenário/fundo**. Nunca gerar o
> gesto→cursor com IA (§5.1 — nunca mockup/estética sem produto).
> **Data:** 2026-09-23 · Autor: Luar Studio Angola · Estado: roteiro pronto; depende de gravar a
> pessoa real em cada cenário (lista abaixo).

---

## 1. O roteiro (30–40 s) — "O teu dia sem rato físico"

> Estrutura: **HOOK (a própria mão!) → 4 cenários → remate/CTA**. A mão é a constante criativa:
> cada transição é um **match cut da mão** — a mão entra em frame num cenário e, na transição,
> "vira" (morph) para o mesmo gesto noutro cenário.

| T | Cenário | Ação real (gravar) | Transição (IA) |
|---|---|---|---|
| 0–3 s | **Casa (sofá)** | Pessoa no sofá, mão no ar a mover o cursor no PC à frente | — (abre com a mão, HOOK) |
| 3–6 s | Transição | — | **Match cut da mão**: a mesma posição da mão "transforma" no cenário seguinte (morph/Whip pan) |
| 6–12 s | **Escritório/secretária** | Pessoa a clicar (pinça) e fazer scroll (2 dedos) no trabalho real | — |
| 12–15 s | Transição | — | **Whip pan** rápido (a câmara "varre" para o próximo cenário) |
| 15–20 s | **Sala de aula / apresentação** | Pessoa em pé a andar; slide/nota avança ao virar a mão | — |
| 20–23 s | Transição | — | **Match cut da mão** outra vez (luz muda: dia→noite) |
| 23–29 s | **Noite / lazer (telemóvel)** | Mão a mover o cursor do PC usando o telemóvel em modo remoto (ou gesto em frente ao telemóvel) | — |
| 29–33 s | Transição final | — | Câmara afasta; os 4 cenários colapsam num só frame filtrado |
| 33–37 s | Remate | Pessoa olha para a câmara e mostra a mão vazia | — |
| 37–40 s | CTA | Logo + "maouse.app" | — |

**Slow motion opcional:** em 1–2 momentos, a mão fica em slow-mo (real) e o cursor segue normal
(latência baixa visível) — prova de precisão sem cortar. *Número no canto: "latência <80 ms"*.

---

## 2. Cenários possíveis (escolher 4 por versão; rotação para remakes)

| # | Cenário | Tipo | Nota de captura |
|---|---|---|---|
| C1 | Casa / sofá (manhã) | Teletrabalho/ser no sofá | Luz natural, portátil no regaço |
| C2 | Secretária / escritório | Trabalho produtivo | Monitor + teclado, clique e scroll reais |
| C3 | Sala de aula / palestra | Apresentação em pé | Slides a avançar com a mão (Snap/UI automation) |
| C4 | Café / espaço público | Uso casual | Portátil + telemóvel |
| C5 | Noite / quarto | Lazer noturno | PC + telemóvel em modo remoto |
| C6 | Hospedeira da sala / living | Familiar/idoso (segmento acessibilidade) | Pessoa a realizar tarefa básica (e-mail) |
| C7 | Cozinha | Multitasking (instrução culinária no ecrã) | Mão em gestos rápidos |
| C8 | Reunião online | Videocall a apresentar ecrã | A mão a fazer gestos enquanto fala |

> **Em cada versão só mudam os cenários escolhidos e o match cut** — o mesmo esqueleto serve
> remakes, testes A/B e localizações (PT-BR/EN/EU).

---

## 3. Regras de produção (não negociáveis)

| Regra | Motivo |
|---|---|
| **A pessoa é REAL** (familiar, colaborador ou ator) — nunca avatar a fingir usar o produto | §5.1: demonstração real |
| **Nunca gerar a mão a mover o cursor com IA** | Seria mockup do produto |
| Higgsfield gera: **transições, tratamento de luz/cor, variação de fundo** entre cenários reais | Eficiência + consistência visual |
| Números verdadeiros e datados no canto (latência ≤ alvo · ≥ fps da matriz) | §3.3 regra 5 |
| Legendas PT-BR + EN; badge do gesto (pinça → clique, 2 dedos → scroll) | §5.1/§3.3 |
| Sem locução obrigatória — música + texto de ecrã (ou VO opcional nos remakes) | Formato universal |
| CTA único no fim: "Download grátis — maouse.app" | §3.4 regra de ouro |

---

## 4. Workflow no Higgsfield (transições + cenário)

| Passo | Ação |
|---|---|
| 1 | Gravar os 4 cenários reais (OBS 16:9 60 fps) + os cortes de mão por transição (2 s cada). |
| 2 | Criar produto/perfil no Higgsfield (logo Mãouse + screenshot + foto webcam); Brand Kit ativo. |
| 3 | Para cada **transição**: usar ref-to-video / clip (o corte da mão de 2 s) e pedir o match cut/morph ou whip pan entre os dois cenários. |
| 4 | Gerar variações de **tratamento de cenário** (luz, cor, fundo) SEM alterar a mão/o gesto (prompt cuido: manter mão/cursor intactos). |
| 5 | Montar no editor: cenário real → transição IA → cenário real → ... → remate → CTA. |
| 6 | Exportar 16:9 (hero/YouTube) + 9:16 (TikTok/Reels); watermark discreto na versão Free. |

> ⚠ **Atenção crítica na etapa 4:** pedir ao Higgsfield "tornar mais bonito" pode **reescrever a mão
> e o cursor** — invalidando a prova. Prompt padrão: *"keep hand and cursor exactly as in the input;
> only regrade color, lighting and background of the scene."* Verificar **plano a plano** que o cursor
> e a mão não mudaram.

---

## 5. Checklist de entrega (spot multi-cenário)

- [ ] Desktop compilado + clipes reais dos 4 cenários (bloqueador nº1).
- [ ] Pessoa real escolhida (familiar/criador/ator) + gravação 60 fps.
- [ ] Transições IA geradas (match cut ×2 + whip pan + colapso final).
- [ ] Números reais da matriz inseridos com data.
- [ ] Versões PT-BR + EN e 9:16.
- [ ] Landing a cobrar antes de qualquer anúncio pago.

---

*Alinhado a `MODELO_DE_MARKETING_E_VENDAS.md` §3.4 (peça-mestra de narrativa), §3.3 (regras de copy e
números) e `ESTRATEGIA_DE_CONTEUDO_E_REDES_SOCIAIS.md` §5 (demo real, formatos). Complementa
`PUBLICIDADES_VIDEO_ADS.md`, `PUBLICIDADES_CINEMATOGRAFICAS_HIGGSFIELD.md` e
`PUBLICIDADES_HYPERMOTION_HIGGSFIELD.md`.*