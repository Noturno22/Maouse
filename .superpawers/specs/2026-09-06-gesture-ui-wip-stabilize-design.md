# Estabilização do WIP Gestos/UI — Design

**Data:** 2026-09-06
**Branch:** `feature/license-dialog-modernize`
**Tipo:** Estabilização (commit cirúrgico de trabalho-em-progresso já desenhado e testado; sem alteração de comportamento).
**Estado:** Design aprovado pelo utilizador (2026-09-06).

## 1. Contexto e problema

A branch contém, para além dos sub-sistemas já comitados, um **segundo conjunto de mudanças em working-tree** (WIP) que:

- implementa uma **nova onda de features** já desenhadas pelo utilizador: gesto punho-em-hold para ações destrutivas (Alt+F4), menu com `set_locked` (estado grey + tooltip PRO), toast com `danger=True`, tema com borda vermelha `[locked="true"]`, gate dinâmico `commands_ok` (comandos de 2 mãos exigem as **duas mãos presentes**), anti-falso-positivo da palma no alternador, e **trial 30 min → 5 min** (decisão final de produto confirmada);
- está **parcialmente já referenciada por código comitado**: `_flash_locked`/`set_locked` em `ui/main_window.py` (commit `3cebb23`) chama `MenuButton.set_locked()` que **só existe no WIP** (`ui/menu_panel.py`) → **HEAD sozinho rebenta com `AttributeError`** assim que `_sync_license_ui` corre. O WIP não é opcional: tem de entrar na branch para que o estado comitado seja consistente.

Descobertas da exploração (2026-09-06):

| Item | Estado |
|---|---|
| Trial (client `core/licensing.py` `TRIAL_DEFAULT_SECONDS=30*60`) | comitado em 30 min; WIP reduz para **5 min** em client, server, badge e testes |
| FistHoldDetector, anti-drift palma, `commands_ok` | só em WIP (`core/twohand.py`, `core/engine.py`) |
| `MenuButton.set_locked`, toast danger, tema `[locked]` | só em WIP (`ui/menu_panel.py`, `ui/toast.py`, `ui/theme.py`) |
| Testes untracked (fist_hold ×5, move ×10, open_switch ×5, toast) | não estão no git |
| `assets/brand/logo-look.png` (usado por `_flash_locked`) e `assets/brand/icon.png` | não trackeados → clone sem eles quebra o fundo do flash silenciosamente |
| `build.bat`/`airmouse.spec` | só empacotam `models` e `assets/fonts`; `assets/brand/*` fica de fora do exe |
| `tests/test_licensing.py::test_active_license_defaults_to_free` | falha por ambiente (`%APPDATA%\AirMouse\license.json` com lease PRO válida até 2026-09-12) → única falha da suite |
| `settings.json` (trackeado) | WIP altera calibrações da máquina dev (suavidade REACTIVO→NORMAL, `*_enabled` false) — **não é decisão de produto**, fica fora dos commits |

## 2. Objetivo

Tirar a branch do estado inconsistente com **commits cirúrgicos por onda**, cada onda com os seus testes verdes, e deixar a **suite 100% verde** (eliminando a única falha ambiental por isolamento de store path).

**Sem alteração de comportamento** do WIP — estabiliza-se o que está desenhado e já testado ao nível de unidade.

## 3. Baseline verde (antes de tudo)

Isolar `tests/test_licensing.py` do ambiente:

- Os testes que constroem `LicenseManager`/`LicenseClient` passam a usar um **`store_path` de teste** (via `tmp_path`/monkeypatch) em vez de ler a `%APPDATA%\AirMouse\license.json`.
- Objetivo: remover a dependência da máquina dev (lease PRO ativa) e tornar o teste determinístico.
- Commit dedicado e cirúrgico (ex.: `fix(tests): isola store de licensing do ambiente`) — valida-se primeiro, depois correm-se as ondas.

Critério de aceitação: suite completa (219+ items) com **0 falhas**.

## 4. Ondas de commit (uma commit por wave)

| Wave | Conteúdo | Ficheiros | Verificação local |
|---|---|---|---|
| **W1 Trial 5 min** | Decisão final confirmada; trial 5 min em client+server; normalize nome do teste | `core/licensing.py`, `license-server/storage.py`, `tests/test_trial_30min.py` → `tests/test_trial.py` (rewrite 5 min) | `pytest tests/test_trial.py tests/test_licensing.py` |
| **W2 Gestos** | Hold=punho, anti-drift, `commands_ok=len(results)==2`; testes untracked adicionados ao git; docs atualizadas | `core/twohand.py`, `core/engine.py`, `GESTOS.md`, `tests/test_fist_hold.py`, `tests/test_move_gesture.py`, `tests/test_open_switch_move.py` | `pytest tests/test_gesture_ai.py tests/test_gesture_ai_integration.py tests/test_move_gesture.py tests/test_open_switch_move.py tests/test_fist_hold.py` (46) |
| **W3 UI lock** | Toast danger, borda locked, `MenuButton.set_locked`; desbloqueia `_flash_locked` já comitado | `ui/toast.py`, `ui/theme.py`, `ui/menu_panel.py` | `pytest tests/test_toast.py tests/test_theme.py tests/test_i18n.py tests/test_gui_imports.py tests/test_license_dialog_free_ui.py tests/test_license_dialog_pro_ui.py` |
| **W4 Docs/assets** | amendment do spec já feito alinhado ao código; assets referenciados; misc dev | `mm.md`, `.easignore`, `.superpawers/specs/2026-09-05-license-dialog-modernize-design.md` (amendment em WIP), `assets/brand/logo-look.png`, `assets/brand/icon.png` | `git show --stat` contém só estes ficheiros; `logo-look.png`/`icon.png` lidos por `QPixmap` sem null |

Regra de conteúdo adicional:
- **`settings.json` fica FORA de todos os commits** (calibração local). Se for produto pretender tornar alguns valores default, fica registado no sub-projecto "config hygiene" (deferido).
- Nunca `git add .`/`-A`; cada wave faz `git add <ficheiros da wave>` explícito.

## 5. Packaging

- `build.bat`: acrescentar cópia de `assets/brand/*` (inclui `logo.png`, `logo-off.png`, `logo-look.png`, `icon.png`) para o diretório de build, ao lado de `models` e `assets/fonts`.
- `airmouse.spec`: acrescentar `datas` para `assets/brand`, `assets/fonts` e `assets/models` (o que existir) correspondente ao comportamento do build.bat.
- Commit dedicado de build; verificação = spec parseável (`PyInstaller`/YAML parse) + dry-run de `build.bat` (sem executar empacotamento pesado).

## 6. Verificação final

- Suite completa: **0 falhas** (verificar contagem de dots + `$LASTEXITCODE`).
- `py_compile` nos ficheiros tocados por cada wave.
- `ruff check` nos ficheiros tocados (só os nossos; as E501 pré-existentes do i18n são do sub-projecto "polimento voz", deferido).
- **Revisão por wave** (batida, como no plano voz): reviewer cruza spec↔commit, com re-review se necessário.

## 7. Fora do âmbito (deferido para sub-projectos seguintes)

- **Gaps de teste do engine**: hold→Alt+F4 end-to-end, gate `commands_ok` no engine, swipe/scroll off com 1 mão. (Os detetores já têm unit tests; o wiring no engine fica sem teste nesta fase.)
- **Countdown do trial** no license dialog (gap spec-vs-impl: `license.trial_remaining` existe mas a label é estática).
- **Paddle D2** (`PADDLE_VENDOR_ID=0` em `ui/license_dlg.py:38` — precisa do vendor_id real do utilizador; dependência externa).
- **Polimento voz**: 21×E501 no `i18n.py` + bug do `tools/test_voice_llm.py` (leak do `.env` de `core/llm._load_api_key`).
- **Config hygiene**: decidir se `settings.json` deixa de ser committable (`.gitignore` + `git rm --cached`) e que valores são defaults de fábrica.

## 8. Definições de sucesso

- Todos os commits do WIP em ondas coerentes, cada uma com testes verdes.
- Suite completa 100% verde (0 falhadas), portável para outra máquina (teste de licensing determinístico).
- Os assets referenciados por código comitado estão no git e no build.
- Estado comitado da branch é consistente (sem referências a código que ainda não existe no HEAD).
- Nada de `settings.json` nem de outros ficheiros de outra autoria incluídos por engano.

## 9. Referências

- Exploração (2026-09-06): researchers "License dialog / splash / trial" e "Gestures WIP & Voice polish".
- Spec pré-existente: `.superpawers/specs/2026-09-05-license-dialog-modernize-design.md`.
- Commit quebrado sem WIP: `3cebb23` (`_flash_locked` + `set_locked`).
- Config keys de gesto em `config.py` (comitadas em `a60ca13`): `left_hand_open_switch_max_move_px`, `left_hand_fist_close_hold_s`, `left_hand_fist_close_cooldown_s`.