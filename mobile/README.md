# Mãouse Mobile - Guia Completo

## Visão Geral

**Mãouse Mobile** é um aplicativo React Native/Expo que permite controlar o telemóvel total usando gestos de mão detetados pela câmara frontal do dispositivo.

---

## Funcionalidades

### Gestos de Mão
| Gesto | Ação |
|-------|------|
| ✋ Mão aberta | Mover cursor |
| 🤏 Pinça (polegar+index) | Tap / Selecionar |
| 🤏🤞 Pinça (polegar+médio) | Clique direito |
| ✊ Punho | Arrastar |
| ✌️ Dois dedos | Scroll |
| ☝️ Um dedo | Mover (1D) |
| 👍 Polegar cima | Play/Pausa |
| 🤙 Shaka | Colar |
| ✋✊ Palmas | Voltar / Multitarefa |

### Ações de Sistema
- **Tap** → Selecionar item
- **Long Press** → Clique direito
- **Swipe** → Navegar
- **Scroll** → Rolar página
- **Volta** → Botão voltar
- **Início** → Ecrã inicial
- **Multitarefa** → Apps recentes
- **Notificações** → Barra de notificações
- **Volume** → Ajustar volume
- **Brightness** → Ajustar brilho

---

## Estrutura do Projeto

```
mobile/maouse-mobile/
├── App.tsx                          # Componente principal
├── src/
│   ├── engine/
│   │   ├── filters.ts               # One Euro Filter + AccelCurve
│   │   └── gestures.ts              # Deteção de 12+ gestos
│   ├── hooks/
│   │   ├── useProEntitlement.ts          # IAP + validação server-side + restore
│   │   └── useAccessibilityStatus.ts     # Estado do serviço de acessibilidade
│   ├── store/
│   │   ├── index.ts                 # Zustand store
│   │   ├── license.ts               # Zustand store de licença (free/mobile_pro)
│   │   └── remote.ts                # Zustand store do controlo remoto do PC
│   ├── components/
│   │   ├── ProGate.tsx              # Paywall Pro
│   │   └── RemoteScreen.tsx         # Ecrã de controlo remoto do PC
│   ├── services/
│   │   ├── licenseApi.ts            # Cliente do license-server
│   │   └── remoteClient.ts          # Cliente WebSocket do PC (handshake auth)
│   ├── utils/
│   │   └── deviceId.ts              # UUID persistente do dispositivo
│   ├── types/
│   │   └── gesture.ts               # Tipos TypeScript
│   ├── __tests__/
│   │   └── remoteClient.test.ts     # Contrato do protocolo remoto (Jest)
│   └── constants/
│       └── index.ts                 # Cores, labels, presets
├── android/                         # Gerado no prebuild (ver plugins/ abaixo)
├── ios/                             # Gerado no prebuild (ver plugins/ abaixo)
├── app.json                         # Config Expo
├── plugins/
│   └── with-maouse-native/
│       ├── index.js                 # Config plugin (copia os templates no prebuild)
│       └── templates/
│           ├── android/             # MaouseAccessibilityService + 3 módulos (Kotlin)
│           │   ├── MaouseAccessibilityService.kt  # Injeção de gestos/teclado (sem root)
│           │   ├── MaousePackage.kt                # Regista os 3 módulos no RN
│           │   ├── TouchControllerModule.kt        # tap, longPress, swipe, drag, moveCursor
│           │   ├── KeyboardControllerModule.kt     # typeText, pressKey, pressCombo
│           │   ├── SystemControllerModule.kt       # back/home/recents/notif, volume, brilho
│           │   └── accessibility_service_config.xml
│           └── ios/
│               └── KeyboardController.swift        # (só este: touch/system iOS não implementado)
├── eas.json                         # Config EAS Build
└── package.json                     # Dependências
```

> Este ficheiro é um resumo. A referência completa e correcta está em
> `maouse-mobile/README.md` — a estrutura acima é a real, mas evolve depressa.

> **O código nativo vive nos templates do plugin**, não em `android/`/`ios/` no
> repositório: essas pastas são geradas no prebuild. Editar o que o prebuild
> escreveu não sobrevive a `prebuild --clean`; tem de ser editado em
> `plugins/with-maouse-native/templates/`.

---

## Pré-requisitos

- **Node.js** 20+ (testado em 26; o Expo SDK 57 exige LTS moderno)
- **Expo CLI** — já vem no projecto: `npx expo`, sem instalação global
- **EAS CLI** (`npm install -g eas-cli`), só para builds na nuvem
- **Conta Expo** (para build)
- **Telemóvel** com Android 7+ ou iOS 14+

---

## Instalação

### 1. Navegar até à pasta
```bash
cd mobile/maouse-mobile
```

### 2. Instalar dependências
```bash
npm install
```

### 3. Verificar instalação
```bash
npx tsc --noEmit   # tipos
npm test           # protocolo remoto
```

> O `npm install --legacy-peer-deps` que constava antes aqui não é necessário —
> o `package.json` tem `allowScripts` e o lockfile resolve as peers. Se ainda
> precisares dele, é sinal de que o lockfile ficou dessincronizado.

---

## Configuração

### Variáveis de Ambiente (app.json)

O app já vem configurado com:
- **Câmara frontal** para deteção de gestos
- **MediaPipe** com 2 mãos
- **Confiança** 0.5 para deteção/tracking

### Parâmetros Ajustáveis (src/store/index.ts)

| Parâmetro | Default | Descrição |
|-----------|---------|-----------|
| `moveGain` | 2.0 | Velocidade do cursor |
| `filterMinCutoff` | 1.4 | Filtro One Euro (suavidade) |
| `filterBeta` | 0.028 | Aceleração do filtro |
| `pinchOnRatio` | 0.38 | Sensibilidade pinça |
| `pinchOffRatio` | 0.55 | Histerese pinça |
| `hapticEnabled` | true | Feedback háptico |

---

## Executar

### Opção 1: Expo Go (mais rápido, sem nativos)
```bash
npx expo start
```
Escaneia o QR code com o Expo Go.

### Opção 2: Expo Dev Client (com nativos)
```bash
# Login
eas login

# Build para Android
eas build --profile development --platform android

# Build para iOS
eas build --profile development --platform ios
```

### Opção 3: Local (com Android Studio/Xcode)
```bash
# Prebuild
npx expo prebuild --clean

# Android
npx expo run:android

# iOS
npx expo run:ios
```

---

## Módulos Nativos

> **Android requer o serviço de acessibilidade ativo** (para simular toques/gestos
> em outras apps sem root). Ativar em:
> `Definições > Acessibilidade > Mãouse`. Sem o serviço, os módulos não têm efeito.

> **Nota iOS:** tap/gestos em outras apps exigem APIs privadas — a implementação atual
> é um esboço funcional (clipboard + Accessibility), não garantida em todas as versões.

### Android (Kotlin — via MaouseAccessibilityService)

`MaousePackage` regista `TouchController`, `KeyboardController` e `SystemController`
no `MainApplication.kt` (lista de packages).

#### TouchController
```javascript
// Tap no ecrã
TouchController.tap(x, y);

// Long press
TouchController.longPress(x, y, duration); // duration em segundos

// Swipe
TouchController.swipe(x1, y1, x2, y2, duration);

// Drag
TouchController.dragStart(x, y);
TouchController.dragMove(x, y);
TouchController.dragEnd();

// Mover "cursor" continuamente
TouchController.moveCursor(x, y);
```

#### KeyboardController
```javascript
// Digitar texto (cola no campo focado)
KeyboardController.typeText("Hello");

// Pressionar tecla (66=Enter, 67=Backspace, 61=Tab)
KeyboardController.pressKey(66);

// Combinação de teclas (113=Ctrl)
KeyboardController.pressCombo([113, 31]); // Ctrl+C
KeyboardController.pressCombo([113, 50]); // Ctrl+V

// Toggle teclado
KeyboardController.toggleKeyboard();
```

#### SystemController
```javascript
// Voltar
SystemController.goBack();

// Ecrã inicial
SystemController.goHome();

// Apps recentes
SystemController.openRecents();

// Notificações
SystemController.openNotifications();

// Volume
SystemController.adjustVolume(1); // +1 = subir
SystemController.adjustVolume(-1); // -1 = descer

// Brilho
SystemController.setBrightness(128); // 0-255

// Screenshot (Android 11+)
SystemController.takeScreenshot();
```

### iOS (Swift)

#### TouchController
```swift
// Tap
TouchController.tap(x, y)

// Long press
TouchController.longPress(x, y, duration)

// Swipe
TouchController.swipe(x1, y1, x2, y2, duration)

// Drag
TouchController.dragStart(x, y)
TouchController.dragMove(x, y)
TouchController.dragEnd()
```

#### SystemController
```swift
// Voltar
SystemController.goBack()

// Ecrã inicial
SystemController.goHome()

// Apps recentes
SystemController.openRecents()

// Volume
SystemController.adjustVolume(1)

// Brilho
SystemController.setBrightness(128)
```

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                    Camera (Vision Camera)                │
│                         │                                │
│                         ▼                                │
│              ┌─────────────────────┐                    │
│              │   MediaPipe Hands   │                    │
│              │  (Kotlin/Swift nativo)│                    │
│              └──────────┬──────────┘                    │
│                         │ 21 landmarks                  │
│                         ▼                                │
│              ┌─────────────────────┐                    │
│              │   Gesture Engine    │                    │
│              │  (One Euro Filter)  │                    │
│              └──────────┬──────────┘                    │
│                         │ Gesture + Event               │
│                         ▼                                │
│              ┌─────────────────────┐                    │
│              │   Action Router     │                    │
│              └──────────┬──────────┘                    │
│                         │                                │
│         ┌───────────────┼───────────────┐               │
│         ▼               ▼               ▼               │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐          │
│   │  Touch   │   │ Keyboard │   │ System   │          │
│   │Controller│   │Controller│   │Controller│          │
│   └──────────┘   └──────────┘   └──────────┘          │
│         │               │               │               │
│         └───────────────┼───────────────┘               │
│                         ▼                                │
│              ┌─────────────────────┐                    │
│              │   Android / iOS     │                    │
│              │   (Ação no SO)      │                    │
│              └─────────────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

---

## Performance

| Métrica | Target |
|---------|--------|
| Latência gesto→ação | < 50ms |
| FPS deteção | 30+ fps |
| RAM usage | < 150MB |
| Battery drain | < 15%/hora |

---

## Troubleshooting

### Erro: "Cannot find module"
```bash
rm -rf node_modules
npm install
```

> Antes isto pedia `npm install --legacy-peer-deps`. Já não: o `package.json`
> declara `allowScripts` e o lockfile resolve as peers. Se precisares do
> `--legacy-peer-deps`, é sinal de que o lockfile ficou dessincronizado com o
> `package.json`.

### Erro: "Camera permission denied"
Verificar `app.json` → `expo.plugins` → `expo-camera`

### Erro: "MediaPipe not found"
Verificar se `hand_landmarker.task` está em `assets/`

### Erro: "Native module not found"
```bash
npx expo prebuild --clean
```

### Gestos não têm efeito no Android
Ativar o serviço de acessibilidade: `Definições > Acessibilidade > Mãouse`.
Sem isto, `TouchController`/`SystemController`/`KeyboardController` não conseguem
injetar ação noutras apps (o Android exige o serviço para gestos globais sem root).

### Build falha no EAS
```bash
# Limpar cache
eas build:configure
eas build --profile development --platform android --clear-cache
```

---

## Próximos Passos

- [x] Módulos nativos Android (gestos, teclado, sistema) via AccessibilityService
- [ ] Testar em dispositivo real
- [ ] Ativar/validar o serviço de acessibilidade em telemóveis reais
- [ ] Otimizar performance em devices low-end
- [ ] Adicionar controlo de voz (Whisper/Vosk)
- [ ] Implementar calibração automática
- [ ] Publicar na Play Store / App Store

---

## Licença

MIT
