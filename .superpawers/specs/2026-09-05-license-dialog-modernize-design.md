# Redesign da Área de Subscrição — Design (Etapa A)

> Estado: aprovado pelo utilizador. Ramo: `feature/license-dialog-modernize`.
> Aprovado com base na Abordagem A (redesign focado); Etapa C (fontes embedded) fica como follow-up separado.

## Objetivo

Modernizar o diálogo de licença/subscrição do Mãouse (`ui/license_dlg.py`) para um estilo
**premium minimalista**: menos densidade, hierarquia clara, tipografia moderna e copy confiante.
Sem alterações de comportamento (seleção de plano, checkout Paddle, ativação de chave,
desativação, trial restante).

## Âmbito

| Ficheiro | Alteração |
|---|---|
| `ui/license_dlg.py` | Reconstrução da UI `LicenseDialog` (modo FREE e modo PRO ativo) |
| `ui/theme.py` | Novos tokens/object names no `MAIN_STYLESHEET`; remoção de estilos obsoletos |
| `i18n.py` | Reescrita dos valores `license.*` (chaves mantidas, tons alterados) |

Sem novos testes (não existem testes UI do diálogo). `tests/test_i18n.py` exige que as chaves
`license.*` continuem a existir — apenas os valores mudam, por isso o teste permanece verde.

## Layout (modo FREE)

Diálogo com largura fixa de **620px** (antes 700px). Ordem vertical:

1. **Linha de status fina** no topo: chip dourado pequeno «FREE · 5 MIN DE TESTE» + tempo restante
   (apenas se `trial_remaining_seconds() > 0`). **Sem glow nem animação de pulso** — remove o
   `FreeBanner`/`FreeBadge` e o respetivo `breathe_glow`.
2. **Hero sóbrio**: linha com título «Mãouse Pro» + badge PRO discreto; subtítulo curto numa linha.
   Sem badge gigante amarelo.
3. **Benefícios**: mantém o rótulo de secção `SectionTitle` («O QUE DESBLOQUEIA») em estilo slim
   (pequeno, espaçado) seguido de 4 linhas compactas (check verde + nome em bold + descrição curta
   em cinza), com espaçamento menor entre linhas.
4. **Planos**: grelha de 2 colunas com um cartão por produto em `_PRODUCTS` (cartões pequenos,
   ~84px de altura mínima), seleção por estado discreto (borda fina + fundo subtil, via property
   QSS `[selected="true"]`), badge «POPULAR» apenas no produto destacado (primeiro de `_PRODUCTS`).
5. **CTA único sem pulse**: «ATIVAR PRO · €39,90» (mantém o estilo `ProCta` dourado, sem `breathe_glow`).
6. **Chave em modo secundário**: divisor + legenda pequena «Já tem uma chave Pro?» + campo + botão,
   visualmente discretos (menos contraste que o resto).

Sem colapso/expansão animado: a linha de chave fica visível mas visualmente secundária.

## Layout (modo PRO ativo)

Diálogo com largura fixa de **560px** (altura 340px). Ordem vertical:

- Hero «Mãouse Pro» + badge discreto; subtítulo (1 linha).
- Espaço.
- Botão «Remover licença» em estilo secundário discreto (não o azul cheio `SettingsButton`).

## Tipografia (Etapa A — sem binários)

- Títulos e nomes de plano: `Segoe UI Variable Display` com fallback `Segoe UI`.
- Corpo: `Segoe UI`.
- Mono (preço, extra): `Cascadia Code` com fallback `Consolas`.

Fallbacks garantem funcionamento em Windows 10 (sem `Segoe UI Variable`) e Windows 11.

## Novos object names no stylesheet

- `StatusChip` — chip do estado FREE (fundo discreto, texto dourado, sem glow).
- `HeroChip` — badge discreto associado ao título.
- `PlanCard` (+ `:selected` + `:hover`) — cartões de plano menores, seleção por borda fina.
- `PlanPrice`, `PlanExtra` — preço e linha extra dos cartões.
- `BenefitText` — linha de benefício (check + nome + descrição).
- `KeyCaption` — legenda da linha de chave.
- `KeyField` — campo de chave discreto.

Estilos removidos: `FreeBanner`, `FreeBadge` (substituídos por `StatusChip`).

## Copy (i18n — valores alterados, chaves mantidas)

| Chave | PT (novo) | Motivo |
|---|---|---|
| `license.hero` | «Uma nova forma de trabalhar com a mão» (confiante) | remover «nova experiência tecnológica» |
| `license.hero_sub` | «Tudo o que já usa, agora com todo o potencial desbloqueado.» | remover «mágico» |
| `license.unlocks_title` | «O QUE DESBLOQUEIA» | remover «REVOLUCIONÁRIA» |
| `license.cta` | «ATIVAR PRO» | encurtar (o CTA junta o preço) |
| `license.pro_active_sub` | «Obrigado por apoiar o Mãouse.» (concisa) | menos floreado |
| `license.remove` | «Remover licença» | encurtar |
| `license.key_hint` (nova) | «Cole a chave aqui» | placeholder do campo de chave (sem duplicar o botão) |

Restantes chaves (trial_remaining, trial_ended, activate_now, has_key, activate_key, enter_key,
activate_failed, needs_connection) mantêm-se como estão.

## Comportamento preservado (invariantes)

- `LicenseDialog` decidido por `license_mgr.is_pro()`: PRO → UI ativa; senão → UI FREE.
- `_on_plan_selected` continua a atualizar o estado dos cartões e o texto do CTA com o preço.
- `_on_cta` → `_open_checkout(plan)`; mensagens de checkout mantidas.
- `_activate_key` / `_deactivate` mantêm a escrita em `cfg.license_tier` e `accept()`/mensagens.
- `BlockDialog` não é alterado nesta etapa (apenas se beneficia: o CTA já não usa ⭐).
- Larguras: FREE 620px, PRO ativo mantém-se funcional (redimensionar para hierarquia equivalente).

## Etapa C (follow-up, fora deste spec)

Bundling de Inter / Space Grotesk / JetBrains Mono em `assets/fonts/` com `QFontDatabase`,
e atualização das `font-family` do stylesheet. Decidida após validação da Etapa A.

## Critérios de aceitação

1. Diálogo FREE renderiza com a nova hierarquia (estado, hero, benefícios, planos, CTA, chave)
   e sem qualquer animação de pulso.
2. Seleção de plano continua a funcionar e atualiza o CTA.
3. Ativação/desativação de chave funcionam como antes.
4. Modo PRO ativo renderiza a UI simplificada.
5. `tests/test_i18n.py` verde; suíte completa sem novos falhanços além do
   `test_active_license_defaults_to_free` (dependente do ambiente — licença PRO ativa na máquina).
6. Nenhuma `font-family` referenciada pode ser uma fonte inexistente sem fallback.