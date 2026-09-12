## Objetivo

Fortalecer a robustez do gesto "Mover" (cursor), mantendo o comportamento validado como “perfeito” e prevenindo regressões.

## Entregas esperadas

- Testes unitários dedicados ao fluxo de movimento (mover).
- Atualização mínima de documentação sinalizando a validação do gesto mover.

## Escopo técnico

- Foco em:
  - `core/engine.py` (via `process_frame`) — movimentação e gates.
  - `core/gestures.py` — mapeamento OPEN/ONE -> movimento.
  - `core/motion.py` — SmoothEmitter.
  - `core/mouse_ctl.py` — move_by.
  - `core/filters.py` — FilterPair2D.
- Evitar alterações comportamentais; objetivo é cobrir comportamento existente.

## Plano de testes

1. Criar suite em `tests/test_move_gesture.py`:
   - Cenário 1: mapeia `Gesture.OPEN` e `Gesture.ONE` como gestos de movimento.
   - Cenário 2: `Gesture.NONE` e gestos não-movimento não alteram posição.
   - Cenário 3: movimento é filtrado e escalado (proporcional à resolução câmara/ecrã).
   - Cenário 4: `SmoothEmitter` emite passos fracionários sem duplicar pixels.
   - Cenário 5: movimento respeita `deadzone_px` / `still_velocity_px`.
2. Mock:
   - `MouseCtl` (position, move_by) para validar incrementos.
   - `FilterPair2D`/`AccelCurve` conforme necessário.
3. Verificação:
   - Rodar testes com pytest e garantir 0 falhas.
   - Não alterar APIs públicas.

## Documentação

- Atualizar `PROGRESSO.md` com registro conciso:
  - Gesto mover validado e coberto por testes de robustez.
- Não alterar `GESTOS.md` (descrição já correta).

## Riscos/Restrições

- Não introduzir dependências novas.
- Manter compatibilidade com Windows (sendinput/pynput).
- Não alterar comportamento percecionado (latência/precisão).
