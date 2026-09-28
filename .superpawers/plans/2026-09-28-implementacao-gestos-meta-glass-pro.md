# Implementação de Gestos Profissionais Meta Glass/Quest

Data: 2026-09-28
Branch: `feature/meta-glass-gestos-pro`

## Contexto

Este plano detalha a implementação dos gestos profissionais inspirados nos sistemas Meta Quest Pro/Glass, conforme especificado em `.superpawers\specs\2026-09-28-meta-glass-gestos-pro-design.md`.

Objetivo: Adicionar 5 novos gestos de produtividade que melhorem a experiência profissional em campos como design 3D, apresentações, programação e trabalho criativo.

## Ligação ao Roadmap Geral

Esta implementação está alinhada com:
- **Onda 2** (Features à Meta) do plano em `docs/RECONHECIMENTO_MAOS.md`
- Prepara o terreno para **Onda 3** (ML real) com coleta de dados específicos destes gestos
- Contribui para a **Onda 5** (Menos gestos, melhores) ao oferecer alternativas mais eficientes para tarefas comuns

## Estado Inicial Verificado

- [x] Spec de design concluída (`.superpawers\specs\2026-09-28-meta-glass-gestos-pro-design.md`)
- [x] Arquivo de gestos de usuário atualizado (`GESTOS.md` versão corrente revisada)
- [x] Ferramentas de coleta/treino prontas para extensão (`tools/collect_gestures.py`, `tools/train_gesture_ai.py`)
- [x] Arquitetura de extensão de gestos validada em `core/gestures.py`
- [x] Sistema de emissão a 180 Hz e acumuladores fracionários já implementados (para zoom/rotação)

## Plano de Implementação por Semana

### Semana 1: Fundamentos e Predicados Geométricos
**Objetivo**: Implementar a detecção básica dos 5 novos gestos em `core/gestures.py`

- [ ] Adicionar predicado `_zoom_gesture` (detecta pinça + movimento vertical)
- [ ] Adicionar predicado `_rotation_3d_gesture` (detecta três dedos + movimento circular)
- [ ] Adicionar predicado `_thumb_double_tap` (detecta dois taps rápidos de polegar)
- [ ] Adicionar predicado `_three_finger_swipe` (detecta três dedos + swipe horizontal)
- [ ] Adicionar predicado `_pinky_annotate` (detecta mindinho esticado + movimento)
- [ ] Atualizar cadeia de prioridade em `update()` para integrar os novos predicados
- [ ] Implementar lógica de débounce e estabilidade específica para cada gesto
- [ ] Testes unitários básicos em `tests/test_meta_glass_gestures_predicados.py`

**Critério de aceitação semana 1**: Todos os novos predicados retornam corretamente para gestos de teste sintético

### Semana 2: Integração com Sistema de Ação
**Objetivo**: Conectar a detecção de gestos às ações reais do sistema

- [ ] Estender `core/mouse_ctl.py` com novos métodos:
  - `zoom_in/out(fator)` - simula Ctrl+MouseWheel
  - `rotate_3d(graus, eixo)` - para aplicativos 3D
  - `show_radial_menu(posicao)` - placeholder para futuro desenvolvimento
  - `alternar_aplicativo(direcao)` - simula Alt+Tab ou Win+Ctrl+Setas
  - `modo_annotar(ativar)` - controla estado de desenho
- [ ] Implementar mapeamento de gesto → ação em `core/commands.py` ou similar
- [ ] Adicionar novos parâmetros de configuração em `config.py` com valores padrão sensatos
- [ ] Integrar com sistema de acumuladores existentes (reutilizar padrão de scroll/volume)
- [ ] Testes de integração em `tests/test_meta_glass_gestures_integracao.py`

**Critério de aceitação semana 2**: Gestos disparam as ações corretas em ambiente de teste sem câmera

### Semana 3: Feedback Visual e Experiência do Usuário
**Objetivo**: Melhorar a discoverabilidade e usabilidade dos novos gestos

- [ ] Estender overlay em `core/overlay.py` ou `ui/main_window.py` para mostrar:
  - Indicador de gesto ativo (ícone + texto)
  - Barra de progresso para gestos acumulativos (zoom, rotação)
  - Preview do menu radial (quando relevante)
  - Estado do modo anotar
- [ ] Implementar sistema de dicas contextuais (tooltips) na janela de preview
- [ ] Adicionar suporte para Sons de feedback suave (opcional, configurável)
- [ ] Criar página de ajuda específica para gestos profissionais (acessível via tecla H)
- [ ] Testes de usabilidade informal com 2-3 usuários internos

**Critério de aceitação semana 3**: Usuários conseguem identificar quando cada gesto está ativo sem precisar memorizar

### Semana 4: Integração com IA e Coleta de Dados Reais
**Objetivo**: Preparar para validação com ML e coletar dados para melhoria futura

- [ ] Atualizar `ml_ok` em `core/gesture_ai.py` para mapear novas classes da IA
- [ ] Estender `tools/collect_gestures.py` para suportar coleta dos novos gestos (teclas 8-0 ou similares)
- [ ] Gerar dataset sintético inicial para treino rápida validação
- [ ] Executar primeira rodada de treino com dados sintéticos + poucos dados reais
- [ ] Validar que a IA não reduz significativamente o desempenho (latência < 5ms overhead)
- [ ] Criar script de avaliação específica para estes gestos (`tools/eval_meta_glass.py`)

**Critério de aceitação semana 4**: Sistema híbrido (geometria + IA) funciona com acerto > 85% em dados de teste sintético

### Semana 5: Refinamento, Testes e Documentação
**Objetivo**: Preparar para lançamento e validação final

- [ ] Executar bateria completa de testes existentes para garantir não regressão
- [ ] Ajustar parâmetros padrão baseado em testes internos (deadzone, sensibilidades)
- [ ] Implementar opções de ativação/desativação individual por gesto (via config ou hotkeys)
- [ ] Atualizar documentação do usuário:
  - `README.md` (seção Gestos)
  - `GESTOS.md` (adicionar nova seção para gestos profissionais)
  - Comentários no código explicando uso e limitações
- [ ] Criar vídeo de demonstração interna (30-60s mostrando cada gesto em uso)
- [ ] Preparar plano de teste com usuários externos (se aplicável)

**Critério de aceitação semana 5**: Zero regressões em testes existentes + documentação completa atualizada

## Dependências Externas

- Nenhuma dependência de nova biblioteca necessária
- Reutiliza completamente a infraestrutura existente de:
  - Detecção de MediaPipe
  - Sistema de acumuladores fracionários
  - Arquitetura de predicados geométricos
  - Mecanismo de confirmação por IA
  - Sistema de configuração e hotkeys

## Riscos e Estratégias de Mitigação

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Conflito com gestos existentes | Médio | Alto | Ordenação cuidadosa na cadeia de prioridade; janelas de tempo específicas; teste exaustivo de combinações |
| Complexidade excessiva para usuário | Médio | Médio | Desativação por padrão; hotkeys de toggle; descoberta visual no overlay; documentação clara |
| Performance degradada | Baixo | Médio | Reutilização de estruturas existentes; complexidade O(1); testes de benchmark antes/depois |
| Baixa adotância por falta de descoberta | Médio | Alto | Sobreposição visual no overlay; dicas contextuais; modo de aprendizado integrado |
| Dados insuficientes para ML real | Médio | Médio | Começar com geometria pura; coletar dados ativamente via ferramenta de coleta; priorizar gestos com maior ROI |

## Métricas de Sucesso Pós-Implementação

Imediatas (após semana 5):
- [ ] Cobertura de testes ≥ 80% para novo código
- [ ] Zero regressões na suíte de testes existente
- [ ] Latência adicional < 10ms por frame processado
- [ ] Documentação 100% atualizada (README, GESTOS.md, comentários código)

De curto prazo (1-2 semanas pós-implementação):
- [ ] Taxa de acerto > 90% em teste controlado com gestos de validação
- [ ] < 5% de falsos positivos durante teste de uso normal (digitação, navegação web)
- [ ] Feedback positivo em teste informal com ≥3 usuários internos
- [ ] ≥70% dos testadores indicam que usariam pelo menos um gesto regularmente

De médio prazo (1 mês pós-implementação, com coleta de dados reais):
- [ ] Disponibilidade de dataset real com ≥30 amostras por gesto
- [ ] Melhoria de acerto com IA real para > 95% em dados de validação
- [ ] Identificação de 2-3 casos de uso específico onde os gestos aumentam produtividade mensurável

## Próximos Passos Pós-Implementação

Dependendo do sucesso desta fase, considerar:
1. **Coleta intensiva de dados reais** para treino de modelo específico (Onda 3)
2. **Gestos contextuais** que variam conforme aplicação ativa (ex.: mais preciso no Blender, mais rápido no Chrome)
3. **Integração com perfil de usuário** para sugerir gestos baseado em padrões de uso
4. **Expansão para controle de apresentações** (avançar slide, apontador laser virtual, etc.)
5. **Experimentos com feedback háptico** via dispositivos compatíveis (se disponíveis no ecossistema)

## Aprovação e Marco de Conclusão

Este plano será considerado completo quando:
1. Todos os critérios de aceitação da semana 5 forem atendidos
2. A branch `feature/meta-glass-gestos-pro` puder ser mergeada em `main` sem quebrar funcionalidade existente
3. Uma versão de teste estiver disponível para validação por usuários-chave (se houver)
4. A documentação estiver atualizada e revisada por pelo menos um membro da equipe não envolvido na implementação

---
*Este plano é um documento vivo e pode ser ajustado conforme descobertas durante a implementação. Qualquer mudança significativa no escopo deve ser documentada e comunicada claramente.*