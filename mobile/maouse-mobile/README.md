# Mãouse — Mobile

Controle total do telemóvel usando gestos de mão detetados pela câmara frontal.
Controla também o rato e o teclado do PC a partir do telemóvel.

## Funcionalidades

- **Mover cursor** - Mão aberta ou indicador levantado
- **Tap/Selecionar** - Pinça polegar+indicador
- **Clique direito** - Pinça polegar+médio
- **Arrastar** - Punho fechado
- **Scroll** - Dois dedos (peace sign)
- **Volta/Início** - Atalhos de sistema
- **Acessibilidade** - Navegação por foco
- **Controlo remoto do PC** - Rato, clique, arrasto, scroll, teclado e media via
  WebSocket com token (ver "Controlo remoto do PC")

## Pré-requisitos

- Node.js 18+
- Expo CLI (`npm install -g expo-cli`)
- Telemóvel com Expo Go ou Android Studio/iOS Simulator

## Instalação

```bash
cd mobile/maouse-mobile
npm install
```

## Executar

```bash
# Development
npx expo start

# Android
npx expo start --android

# iOS
npx expo start --ios
```

## Estrutura do Projeto

```
maouse-mobile/
├── App.tsx                    # Componente principal + gate de gestos Pro
├── index.ts                   # Entry point registado no app.json
├── src/
│   ├── engine/
│   │   ├── filters.ts         # One Euro Filter + AccelCurve
│   │   └── gestures.ts        # Deteção de gestos
│   ├── hooks/
│   │   ├── useProEntitlement.ts     # IAP (expo-iap) + validação server-side + restore
│   │   └── useAccessibilityStatus.ts  # Estado do serviço de acessibilidade
│   ├── store/
│   │   ├── index.ts           # Zustand store
│   │   ├── license.ts         # Zustand store de licença (tier free/mobile_pro)
│   │   └── remote.ts          # Zustand store do controlo remoto (host/port/token)
│   ├── components/
│   │   ├── ProGate.tsx        # Paywall Pro (comprar/restaurar/continuar gratis)
│   │   └── RemoteScreen.tsx   # Ecrã de controlo remoto do PC (rato + teclado)
│   ├── services/
│   │   ├── licenseApi.ts      # Cliente do license-server (/api/v1/mobile/entitle)
│   │   └── remoteClient.ts    # Cliente WebSocket do PC (handshake auth)
│   ├── utils/
│   │   └── deviceId.ts        # UUID persistente do dispositivo
│   ├── types/
│   │   └── gesture.ts         # Tipos TypeScript
│   ├── constants/
│   │   └── index.ts           # Constantes
│   └── __tests__/
│       └── remoteClient.test.ts  # Contrato do protocolo remoto (Jest)
├── plugins/
│   └── with-maouse-native/    # Config plugin: injecta o código nativo no prebuild
│       ├── index.js
│       └── templates/
│           ├── android/       # MaouseAccessibilityService + 3 módulos (Kotlin)
│           │   ├── MaouseAccessibilityService.kt
│           │   ├── MaousePackage.kt
│           │   ├── TouchControllerModule.kt
│           │   ├── KeyboardControllerModule.kt
│           │   ├── SystemControllerModule.kt
│           │   └── accessibility_service_config.xml
│           └── ios/
│               └── KeyboardController.swift
├── conectar.bat               # Atalho de arranque em Windows
├── app.json                   # Configuração Expo (+ plugin with-maouse-native + expo-iap)
├── eas.json                   # Perfis de build EAS
└── AGENTS.md                  # Notas obrigatórias para agentes neste directório
```

> **Onde vive o código nativo.** Não existe `android/` nem `ios/` no repositório
> porque são gerados no prebuild. O código Kotlin/Swift é real, versionado, e
> vive em `plugins/with-maouse-native/templates/` — o config plugin copia-o para
> o projecto gerado durante `expo prebuild`. Editar `android/` local não
> sobrevive a um prebuild limpo: tem de ser editado no template.

## Testes

O único alvo com testes é o **protocolo remoto**, porque é a fronteira de
segurança entre o telemóvel e o PC: o `core/remote.py` do PC executa comandos que
mexem no rato e no teclado de quem está a usar a máquina, e a única coisa entre um
host qualquer da mesma rede e esse rato é o handshake `auth` da primeira mensagem.

```bash
npm test          # jest, uma passagem
npx tsc --noEmit  # tipos
```

Coberto: `buildWsUrl` (normalização de host, porta por omissão, token fora do
URL), o `auth` como primeira e única mensagem antes do servidor confirmar, o
cliente a ignorar comandos que chegam antes da hora, o token recusado, lixo JSON, e
a distinção entre «o PC não está alcançável» e «a ligação caiu». O preset é o
`jest-expo` do Expo SDK 57, com `@react-native/jest-preset` à parte desde o RN
0.86. Do lado do PC, `tests/test_remote_protocol_contract.py` prende o mesmo
contrato em Python — 28 testes que não precisam de toolchain TS.

> **`npm audit` — não corras `--force`.** O `audit` reporta ~16 avisos herdados do
> toolchain do Expo. O único *high* que tinha correção sem partir nada
> (`brace-expansion`) já foi resolvido. O que resta é dívida upstream sem versão
> corrigida: a advisory do `node-forge` afecta **todas** as versões, e o `npm`
> propõe como «solução» um downgrade a `expo@44.0.6` — três majors atrás. O mesmo
> vale para `decode-uri-component` via `expo-router`. Trocar uma vulnerabilidade
> transitiva do toolchain de build por um Expo partido é um mau negócio; o
> `node-forge` só corre na máquina de quem faz build, a verificar assinaturas.

## Controlo remoto do PC

O telemóvel pode substituir o rato e o teclado do PC. Ligar-se pelo IP mostrado
nas definições do PC, com o token que o PC apresenta.

- **Transporte** — WebSocket em texto claro (`ws://`). O PC arranca o servidor
  sem TLS (`core/remote.py`, `websockets.serve(...)` sem `ssl=`), por isso só
  existe `ws://`. Ver a nota de limitação no teste `buildWsUrl`.
- **Autenticação** — a primeira mensagem é sempre `{"cmd":"auth","token":"…"}`.
  Token errado → `{"cmd":"auth","ok":false,"error":"auth_required"}` e a ligação
  é fechada. Nenhum comando é aceite antes do servidor confirmar.
- **O token não viaja no URL**, só no corpo da primeira mensagem.

> O `ws://` em claro significa que o token e os comandos são legíveis por
> qualquer pessoa na mesma rede. É aceitável em LAN doméstica e é a razão pela
> qual o token é guardado no dispositivo e não interpolado no endereço.

## Próximos Passos

1. TLS no servidor remoto (e então `wss://` no `buildWsUrl`)
2. Testes de componentes com `@testing-library/react-native`
3. Testar o serviço de acessibilidade em telemóveis reais
4. Adicionar controlo de voz
5. Calibração automática

## Compras Pro (IAP)

A versão gratuita navega/pré-visualiza; o controlo de gestos completo desbloqueia com a **compra
única** `maouse_mobile_pro` (Google Play), validada server-side.

- **Compra** → `useProEntitlement().purchasePro()` (produto IAP `maouse_mobile_pro`).
- **Validação** → `POST {licenseServerUrl}/api/v1/mobile/entitle` valida o `purchaseToken` na
  Google Play Billing API e emite um lease JWT (`tier=mobile_pro`). Sem validação do servidor,
  a transação **não** é finalizada (replay seguro).
- **Restore** → `restorePro()` (getAvailablePurchases + revalidação).
- **Gate** → `App.tsx` só envia gestos nativos se `proEntitlement.isPro`; caso contrário mostra `ProGate`.

### Configuração (app.json -> extra)

| Chave | Valor | Descrição |
|-------|-------|-----------|
| `licenseServerUrl` | `https://license.maouse.app` | Base URL do license-server |
| `mobileProductId` | `maouse_mobile_pro` | Product ID do Pro (pago único) no Play Console |
| `androidPackage` | `com.maouse.mobile` | Package Android |

> **Builds nativos:** o `expo-iap` requer **custom dev client / prebuild**. Requer Android SDK:
> `npx expo prebuild --clean` antes de fazer build/upload para o Play Console.
> No license-server, define `MAOUSE_GOOGLE_PLAY_CREDENTIALS_JSON` (conta de serviço com permissão
> "Android Publisher") — sem isso a validação só corre em modo dev (`MAOUSE_MOBILE_DEV_ALLOW=1`, nunca em produção).

## Licença

MIT
