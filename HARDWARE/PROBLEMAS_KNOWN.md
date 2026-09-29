# Problemas Conhecidos de Hardware — Mãouse (Maouse)

> **Registo de conhecimento acumulado** do `HARDWARE/` LAB. Cada linha é uma falha,
> limitação ou comportamento observado em dispositivo real — para **não re-testar** e para
> **informar a matriz** (Validado/Aceite/Não-validado) e os bloqueadores técnicos.
> **Data:** 2026-09-01 · Autor: Luar Studio Angola · Estado: **EM REGISTO.**
> *Actualizado 2026-09-28:* §1.4 (SHAKA) — único defeito aquí que **não** veio do
> hardware, mas da medição automática do classificador de gestos. **Corrigido na
> Onda 1 §1.3** (build `fix/onda1-shaka`); §1.4 passa a ✅ com o evidence da
> correcção.

---

## 0. Legenda

| Marcador | Significado |
|---|---|
| 🔴 Bloqueador | Impede a venda numa categoria |
| 🟠 Limitação | Funciona, mas com ressalvas documentadas |
| ✅ Resolvido | Corrigido em build; registar o build fix |
| ❓ A investigar | Observado, causa ainda por determinar |

---

## 1. Desktop (Windows)

### 1.1. CPU sem GPU/NPU → FPS abaixo do alvo 🟠 Limitação

| Campo | Valor |
|---|---|
| **Sintoma** | FPS ≤15 em CPU de baixo custo sem acelerador de IA |
| **Dispositivo (confirmado)** | HP Notebook · Intel Core i3-5005U (2.0 GHz) · sem GPU dedicada · 8GB · Win10 Home |
| **Dados** | 14.6 fps · inferência 48.3 ms · 0 glitches · câmara 640×480@30 (1ª volta 2026-09-01). Re-teste noite: 11.9 fps / 78.5 ms (variação por luz/carga) |
| **Impacto matriz** | 🟡 **Aceite** (funciona, mas abaixo dos 25 fps) |
| **Causa provável** | Inferência MediaPipe em CPU (TFLite XNNPACK sem GPU) + pipeline de frame |
| **Mitigação** | `--no-gui` (liberta CPU do render); reduzir resolução da câmara; futuro: usar NPU/GPU se disponível |
| **Ação comercial** | Vender com aviso "requer bom CPU"; **não** ✅ em parcos 100% sem GPU |
| **Para validar** | Repetir em outro CPU fraco | ✅ testado `--gpu` → indisponível (ver §1.3) |

### 1.2. Nenhum dispositivo de GPU dedicada/NPU testado ainda 🔴 A investigar

- Falta medir se **desktop com GPU/NPU dedicada** sobe aos 25+ fps (categoria ✅ para
  marketing/contratos). Prioridade nº1 do LAB (`LAB.md` §4).

### 1.3. Integrada antiga (Intel HD 5500): delegado GPU indisponível 🟠 Limitação

| Campo | Valor |
|---|---|
| **Sintoma** | `main.py --gpu` falha ao criar o delegate e cai para CPU (`NotImplementedError`); FPS ≈ CPU (13.4 fps) |
| **Dispositivo** | HP Notebook · Intel HD Graphics 5500 (iGPU, chip Broadwell 2015) · Win10 Home |
| **Dados** | `--gpu`: inferência 67.3 ms · 13.4 fps (≈ baseline CPU); aviso "GPU indisponivel; a usar CPU" |
| **Impacto matriz** | A HD 5500 **não** conta como "GPU dedicada" — continua na categoria CPU fraco |
| **Causa provável** | MediaPipe Tasks GPU (OpenCL) sem suporte nesta iGPU antiga/drivers |
| **Mitigação** | Não prometer aceleração em integradas antigas; medir sempre com/sem `--gpu` |
| **Ação comercial** | Categoria ✅ exige GPU/NPU dedicada real (não iGPU antiga) |
| **Para validar** | Testar `--gpu` em iGPU nova (Intel 12ª+, AMD Ryzen APU) e GPU dedicada |

### 1.4. Gesto `SHAKA` (Ctrl+V) nunca era reconhecido ✅ Resolvido

> Descoberto pela Onda 0 (2026-09-28) ao medir a matriz de confusão, não por
> observação manual. Era a única confusão que existia no corpus de regressão.
> **Corrigido na Onda 1 §1.3** (2026-09-28) — a Predicado passou a medir a
> ponta do polegar contra a **base do indicador**, como o `thumb_out` da Meta.

| Campo | Valor |
|---|---|
| **Sintoma** | O "hang loose" (mindinho esticado + polegar para o lado) produzia sempre **Ctrl+C** (PINKY) em vez de **Ctrl+V** (SHAKA). Medido: **8 de 8** `SHAKA` classificados como `PINKY`, F1 = 0.000 |
| **Dispositivo** | Qualquer — não era dependente de hardware. Era geometria do predicado |
| **Causa** | `core/gestures.py`, predicado `thumb_out`: media o deslocamento da ponta do polegar contra `landmark 3` e exigia `dx > 0.30 × escala` ou `dy > 0.25 × escala`. A falange distal mede ~0.28 de uma escala de 1.10 — em mãos reais, ~30 mm contra ~95 mm de palma. O limiar estava **no limite físico do gesto**: media **anatomia, não intenção**, e variava por utilizador. Pior: `dx > 0.30 × escala` é geometricamente impossível — a falange distal é ~0.28 —, por isso a condição horizontal nunca podia ser satisfeita e a porta de entrada do SHAKA ficava fechada por construção |
| **Correcção** | `thumb_out` passou a medir a **distância da ponta do polegar à base do indicador (landmark 5), normalizada pela escala** (pulso → landmark 9): ~1.23 com o polegar para o lado, ~0.85 recolhido sobre a palma. Limiar 1.05 separa os dois gestos. É a mesma medida do `thumb_out` da Meta, e a mesma que o `core/gesture_ai.py` já usava |
| **Dados (depois)** | `python main.py --replay tests/fixtures/corpus_regressao_v1.npz` → F1 macro **1.0000**, exactidão **1.0000**, `SHAKA` F1 1.000 (P = R = 1.0), `PINKY` F1 1.000 (recuperou a precisão de 0.600), **zero confusões**, 0 cliques fantasma. `ACEITE: todos os alvos cumpridos` (min_f1 0.97) |
| **Impacto matriz** | ✅ Deixou de ser bloqueador: o Ctrl+V chega ao sítio certo. Sai da lista de "não anunciar" |
| **Limite honesto** | Isto é a **fixture sintética** (paramétrica, determinística). Prova que a medição deixou de estar no limite físico e que a distinção existe; **não** substitui um corpus gravado em mãos reais por demografia — esse é o objectivo da Onda 3 §3.1. Aimed: SHAKA F1 ≥ 0.9 cumpre-se na fixture, mas continua por provar no hardware |

Evidência em código: `tests/test_corpus_fixture.py::TestShakaIsRecognised`
(porta sobre a fixture real) e `tests/test_shaka_thumb_out.py` (predicado isolado,
sintético, sem câmara). Análise em `docs/RECONHECIMENTO_MAOS.md` §1.16 (limitação
11) e §3.2 Onda 1 §1.3.

---

## 2. Mobile (Android)

### 2.1. Ações nativas NÃO funcionam em device real 🔴 Bloqueador

| Campo | Valor |
|---|---|
| **Sintoma** | `NativeModules.TouchController?.tap()` faz **no-op silencioso** (via optional chaining) |
| **Causa** | Falta implementar módulos Touch/Keyboard/System + `AccessibilityService` no Manifest (`mobile/android`) |
| **Estado** | Auditar: bloquear nº4 de `PRONTIDAO_PARA_VENDA` — **por implementar** |
| **Impacto** | O core valor "controlar o telemóvel com a mão" não funciona em device real |
| **Plano** | Implementar no S2 do `PLANO_DE_EXECUCAO_90_DIAS` |

### 2.2. Permissões sensíveis declaradas sem uso ⚠️ Risco de rejeição Play

| Campo | Valor |
|---|---|
| **Sintoma** | `WRITE_SETTINGS` / `SYSTEM_ALERT_WINDOW` declaradas em `app.json`, sem código que as justifique |
| **Impacto** | Risco de rejeição Google Play (policy) |
| **Ação** | Remover se não usadas, ou justificar/documentar quando servirem |

### 2.3. Low-end: risco de tela preta/performance ❓ a investigar

- Já foram corrigidos múltiplos crashes do frame processor (`PROGRESSO.md`). **Otimização em
  low-end ainda pendente.** Falta testar em 5+ telemóveis low/mid-end (LAB prioridade 🔴 2).

---

## 3. Registo para novas observações

> Ao registar uma nova falha: copiar o template, preencher, e **etiquetar com a prioridade do
> impacto em vendas** (bloqueador/limitação/resolvido). Depois atualizar a
> `BUSSINES/MATRIZ_DE_DISPOSITIVOS.md` e, se afetar contratos, o `ANTIPADROES_E_RISCOS.md`.

```
### X.Y. <Título> <marcador>
| Campo | Valor |
|---|---|
| **Sintoma** |  |
| **Dispositivo** |  |
| **Dados** |  |
| **Impacto matriz** | ✅/🟡/❌/⚠️ |
| **Causa** |  |
| **Mitigação** |  |
| **Ação comercial** |  |
| **Para validar** |  |
```

---

*Registo de conhecimento — Luar Studio Angola · 2026. Área dedicada ao gargalo de compatibilidade.*
