# Gestos Profissionais Inspirados no Meta Glass/Quest

Data: 2026-09-28
Branch: `feature/meta-glass-gestos-pro`

## Contexto / Decisão de Negócio

O usuário solicitou explorar gestos profissionais inspirados nos sistemas de rastreamento de mãos do Meta Quest Pro/Glass, visando:
1. **Ergonomia avançada**: Reduzir fadiga em sessões prolongadas de uso (design, apresentações, programação)
2. **Precisão contextual**: Gestos que adaptam sensibilidade baseado na aplicação ativa (ex.: mais preciso em CAD, mais rápido em navegação web)
3. **Expressividade aumentada**: Mapear ações complexas de produtividade para gestos intuitivos de uma mão
4. **Diferencial competitivo**: Posicionar o Mãouse como solução premium para profissionais criativos e técnicos

Esta iniciativa está alinhada com a **Onda 2** do plano em `docs/RECONHECIMENTO_MAOS.md` (Features à Meta) e prepara o terreno para a **Onda 3** (ML real com dados coletados destes gestos específicos).

## Estado Atual Verificado (Código Lido)

- [x] `docs/RECONHECIMENTO_MAOS.md` Parte 2 analisada - compreendemos as 6 lacunas estruturais face à Meta Quest
- [x] `core/gestures.py` examinado - confirma que o sistema suporta expansão via:
  - Predicados geométricos na seção 1.6.4 (linhas 253-266)
  - Cadeia de prioridade em 1.6.5 (linhas 270-284)
  - Integração com IA através de `ml_ok` em `core/gestures.py:255-267`
- [x] `GESTOS.md` revisado - mapeamento atual de gestos para o usuário
- [x] `config.py` verificado - parâmetros de sensibilidade já expostos (`pinch_on/off_ratio`, etc.)
- [x] Ferramentas de coleta/treino confirmadas - `tools/collect_gestures.py` e `tools/train_gesture_ai.py` suportam novas classes

## Não Alterar Neste Plano (Limites)

- [ ] **Heurística de geometria primária** - O Schmitt trigger e predicados básicos (pinça, punho, dedos) permanecem como fonte da verdade
- [ ] **Arquitetura de escolha de mão** - Lógica baseada em posição X (`core/engine.py:76-94`) permanece intacta
- [ ] **Sistema de emissão a 180 Hz** - `core/motion.py` não será modificado para estes gestos
- [ ] **Interface de configuração existente** - Novos gestos usarão parâmetros existentes onde possível (ex.: deadzone, ganho)
- [ ] **Licenciamento e gate Free/Pro** - Decisão de quais gestos são Pro será tratada separadamente em `core/licensing.py`

## Definição dos Gestos Profissionais

### 1. Gesto de Zoom Suave (Pinça + Movimento Vertical)
- **Ativação**: Pinça indicador-pólgar mantida + movimento vertical da palma
- **Ação**: Zoom suave em aplicativos compatíveis (Ctrl+MouseWheel)
- **Detalhes Técnicos**:
  - Usa acumulador fracionário similar ao scroll/volume existente
  - Sensibilidade configurável via nova opção `zoom_gain_factor` em `config.py`
  - Deadzone vertical para evitar ativação acidental (`cfg.zoom_deadzone_px`)
  - Mapeia para teclas Ctrl+WheelUp/WheelDown via `core/mouse_ctl.py`
- **Validação Geométrica**:
  - Predicado: `pinch_index_active AND vertical_movement > threshold`
  - Prioridade na cadeia: Entre `PINCH` e `PINCH_MID` (para não conflitar com clique)

### 2. Gesto de Rotação 3D (Três Fingers + Movimento Circular)
- **Ativação**: Três dedos esticados (indicador, médio, anelar) + movimento circular detectado
- **Ação**: Rotação de objetos 3D (em aplicativos como Blender, CAD) ou rolar cronômetro
- **Detalhes Técnicos**:
  - Detector de movimento circular baseado em trajetória da palma
  - Acumulador de ângulo similar ao volume/scroll
  - Sentido horário/anti-horário determina direção da rotação
  - Velocidade de rotação proporcional à velocidade do gesto
- **Validação Geométrica**:
  - Predicado: `three_fingers AND circular_motion_detected`
  - Prioridade: Entre `THREE` e `PEACE` (pois usa mesmo padrão de dedos)

### 3. Gesto de Contexto/Menu Radial (Polegar Duplo Clique)
- **Ativação**: Dois taps rápidos do polegar contra o indicador (duplo clique de pinça)
- **Ação**: Abrir menu radial contextual (como no Wacom ou tablets profissional)
- **Detalhes Técnicos**:
  - Usa o mesmo detector de pinça existente com timings específicos
  - Janela de duplo clique: 300ms (similar ao duplo clique do mouse padrão)
  - Posição do menu aparece próximo à ponta do indicador
  - Navegação no menu via movimento da mão (cima/baixo/esq/dir)
  - Seleção via confirmação de pinça ou timeout
- **Validação Geométrica**:
  - Predicado: `double_pinch_tap AND within_time_window`
  - Prioridade: Logo após `PINCH` no Schmitt trigger (alta prioridade para resposta imediata)

### 4. Gesto de Alternar Aplicativo (Swipe Three Fingers)
- **Ativação**: Três dedos esticados + movimento horizontal rápido
- **Ação**: Alt+Tab (alternar aplicativos) ou switch de desktop
- **Detalhes Técnicos**:
  - Requer velocidade mínima para evitar ativação acidental (`cfg.swipe_min_speed_px`)
  - Distância mínima para confirmar intenção (`cfg.swipe_min_dist_px`)
  - Direção determina próximo/anterior (esq = Alt+Shift+Tab, dir = Alt+Tab)
  - Pode ser configurado para switch de desktop virtual (Win+Ctrl+Left/Right)
- **Validação Geométrica**:
  - Predicado: `three_fingers AND horizontal_swipe_detected`
  - Prioridade: Substitui ou coexiste com gesto de volume atual (necessita decisão UX)

### 5. Gesto de Anotar/Riscar (Mindinho Esticado + Movimento)
- **Ativação**: Mindinho esticado, demais dedos dobrados + movimento da palma
- **Ação**: Modo de anotar livre ou destacar texto (como caneta digital)
- **Detalhes Técnicos**:
  - Ativa modo de desenho temporário ao manter gesto
  - Movimento da palma controla cursor de desenho
  - Pressão simulada via velocidade do movimento (mais rápido = linha mais grossa)
  - Saída como movimentos de mouse com botão esquerdo pressionado
  - Timeout automático após 2s sem movimento para sair do modo
- **Validação Geométrica**:
  - Predicado: `pinky_only AND palm_moving`
  - Prioridade: Entre `PINKY` e `ONE` na cadeia de prioridade

## Integração com Sistema Existente

### Modificações Necessárias em `core/gestures.py`:
1. **Novos predicados** (seção 1.6.4 - após linha 266):
   ```python
   # Zoom suave
   def _zoom_gesture(self, lm, handedness): ...
   
   # Rotação 3D
   def _rotation_3d_gesture(self, lm, handedness): ...
   
   # Duplo clique de polegar
   def _thumb_double_tap(self, lm, handedness): ...
   
   # Swipe three fingers
   def _three_finger_swipe(self, lm, handedness): ...
   
   # Anotar com mindinho
   def _pinky_annotate(self, lm, handedness): ...
   ```

2. **Atualização da cadeia de prioridade** (seção 1.6.5 - após linha 283):
   ```
   [...] 
   thumb_pinky       → SHAKA
   pinky_only        → PINKY
   one_finger        → ONE
   default           → OPEN
   NOVO:
   zoom_gesture      → ZOOM_SMOOTH
   rotation_3d       → ROTATE_3D
   thumb_double_tap  → THUMB_DOUBLE_TAP
   three_finger_swipe→ THREE_FINGER_SWIPE
   pinky_annotate    → PINKY_ANNOTATE
   ```

3. **Extensão de `ml_ok`** (seção 1.6.7 - após linha 266):
   ```python
   self.ml_ok = {
       # existentes...
       Gesture.ZOOM_SMOOTH: self._zoom_gesture,
       Gesture.ROTATE_3D: self._rotation_3d_gesture,
       Gesture.THUMB_DOUBLE_TAP: self._thumb_double_tap,
       Gesture.THREE_FINGER_SWIPE: self._three_finger_swipe,
       Gesture.PINKY_ANNOTATE: self._pinky_annotate,
   }
   ```

### Novos Parâmetros em `config.py`:
- `zoom_gain_factor: float = 0.05` (sensibilidade do zoom)
- `zoom_deadzone_px: float = 4.0` (zona morta para ativação)
- `rotation_sensitivity: float = 0.1` (graus por pixel de movimento)
- `swipe_min_speed_px: float = 500.0` (velocidade mínima para swipe)
- `swipe_min_dist_px: float = 50.0` (distância mínima para confirmar)
- `double_tap_max_interval_ms: float = 300.0` (janela para duplo tap)
- `annotate_timeout_s: float = 2.0` (tempo para sair do modo anotar)

## Considerações de Experiência do Usuário

### Feedback Visual:
- Overlay existente será extendido para mostrar:
  - Barra de progresso para gestos acumulativos (zoom, rotação)
  - Indicador de estado para modo anotar
  - Preview do menu radial próximo ao indicador
  - Trajetória detectada para swipe circular (modo debug)

### Teclas de Atalho Temporárias (Para Testes):
- **Z**: Toggle ativação/desativação do zoom suave
- **R**: Toggle ativação/desativação da rotação 3D
- **T**: Testar duplo tap de polegar (abrir menu de teste)
- **S**: Testar swipe three fingers (simular Alt+Tab)
- **A**: Testar modo anotar (desenho temporário)

### Integração com Voz:
- Comandos de voz naturais para habilitar/desabilitar:
  - `"ativa zoom suave"` / `"desativa zoom suave"`
  - `"ativa rotação 3d"` / `"desativa rotação 3d"`
  - `"abrir menu radial"` (equivalente ao duplo tap)

## Métricas de Aceitação

### Quantitativas:
- [ ] Taxa de acerto > 92% para cada gesto em condições de iluminação variável (200-800 lux)
- [ ] Latência média < 80ms entre início do gesto e ação iniciada
- [ ] Taxa de falsos positivos < 2% durante atividades normais (digitação, uso de mouse)
- [ ] Taxa de rejeição < 5% para gestos intencionais em teste de usabilidade

### Qualitativas:
- [ ] Feedback positivo em teste com 5+ usuários profissionais (designers, desenvolvedores, apresentadores)
- [ ] Menos de 20% dos usuários relatam fadiga após 30min de uso contínuo
- [ ] >70% dos usuários de teste indicam que adotariam o gesto no fluxo de trabalho diário
- [ ] Zero relatos de conflitos com atalhos de teclado padrão em aplicativos comuns

## Próximos Passos de Implementação

1. **Semana 1**: Definir especificações precisas e criar branch `feature/meta-glass-gestos-pro`
2. **Semana 2**: Implementar predicados geométricos em `core/gestures.py`
3. **Semana 3**: Adicionar suporte em `core/mouse_ctl.py` e `core/commands.py` para novas ações
4. **Semana 4**: Integrar com sistema de IA (atualizar `ml_ok` e gerar dados sintéticos)
5. **Semana 5**: Criar ferramentas de coleta de dados reais (`tools/collect_gestures.py` atualizado)
6. **Semana 6**: Treinar modelo inicial com dados sintéticos + poucos dados reais
7. **Semana 7**: Testes de usabilidade internos e ajustes de parâmetros
8. **Semana 8**: Preparar documentação do usuário (`README.md`, `GESTOS.md`) e mover para revisão

## Dependências e Riscos

### Dependências:
- Conclusão da tarefa de limpeza de luz baixa (`core/light.py`) para melhor detecção em variadas condições
- Disponibilidade de parâmetros configuráveis em `config.py` para afinação por usuário

### Riscos de Mitigar:
- **Conflito com gestos existentes**: Mitigado através de cuidadosa ordenação na cadeia de prioridade e janelas de tempo específicas
- **Complexidade excessiva**: Mitigado expondo apenas gestos mais úteis inicialmente e permitindo desativação individual
- **Performance**: Mitigado reutilizando estruturas existentes (acumuladores, detectores de movimento) e mantendo complexidade O(1) por frame

## Notas de Implementação

- Todos os novos gestos devem seguir o padrão de **deadzone + acumulador** usado por scroll/volume para suavidade
- O sistema de **histerese** do Schmitt trigger deve ser aplicado onde apropriado (ex.: duplo tap, ativação de zoom)
- Considerar uso do sistema existente de `hand_lock.py` para melhor continuidade em gestos prolongados (avaliar na Onda 4)
- Documentar claramente no `GESTOS.md` com diagramas de movimento e exemplos de uso prático