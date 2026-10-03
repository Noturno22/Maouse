import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  RemoteStatus,
  RemoteScreenInfo,
  buildWsUrl,
} from '../services/remoteClient';
import { useLicenseStore } from './license';
import {
  DiscoveredPeer,
  isSupported as mdnsSupported,
  mdns,
} from '../services/mdnsDiscovery';
import {
  ble,
  bleModule,
  remote,
  scanForPeers,
} from '../services/remoteTransport';
import { CODE_LEN, codeCompleto, normalizeCode } from '../services/pairingCode';

// O `remote` que o resto da app usa é a **fachada** de
// `remoteTransport`, não o `RemoteClient` do WebSocket: são os dois que
// implementam a mesma interface e a fachada escolhe entre eles. Importar
// `remoteClient` aqui (como se fazia antes) dava o cliente WebSocket e o
// `connectBle` não existiria — que é o tipo de erro que só aparece em runtime,
// quando alguém toca no botão de Bluetooth.
export { remote } from '../services/remoteTransport';
export type { DiscoveredPeer } from '../services/mdnsDiscovery';

const STORAGE_KEY = '@maouse/remote';

// O auto-connect por descoberta não pode disparar a cada re-anúncio do mDNS
// (o PC re-anuncia de 30 em 30 s) nem a cada anúncio BLE repetido. Um único
// temporizador, reiniciado a cada evento correspondente, decide quando a lista
// sossegou e vale a pena ligar — e é a única coisa que impede uma tempestade
// de `connect` quando há dois alvos na mesma rede.
let autoConnectTimer: ReturnType<typeof setTimeout> | null = null;

// Reconexão: quando a ligação cai a meio do uso (não quando o utilizador
// carrega em "desligar"), tenta-se voltar ao último alvo com um atraso que
// cresce. Sem isto, uma oscilação de WiFi deixava o telemóvel parado num ecrã
// de erro e o utilizador tinha de voltar a escolher o PC à mão.
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectAttempts = 0;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;
const RECONNECT_MAX_ATTEMPTS = 10;

function clearAutoConnectTimer() {
  if (autoConnectTimer) {
    clearTimeout(autoConnectTimer);
    autoConnectTimer = null;
  }
}

interface RemoteConfig {
  host: string;
  port: string;
  /**
   * O código de 6 dígitos do PC. Antes era `token` (16 caracteres hex) e a
   * leitura do `@maouse/remote` é feita por baixo: um valor guardado que não
   * tenha 6 dígitos é deitado fora, para o campo começar vazio em vez de
   * mostrar meio token antigo que nunca seria aceite.
   */
  code: string;
  forwardGestures: boolean;
  /** Último transporte utilizado */
  lastTransport?: 'wifi' | 'ble';
  /** Último peer WiFi */
  lastPeerHost?: string;
  lastPeerPort?: string;
  /** Último peer BLE */
  lastBleAddress?: string;
  lastBleName?: string;
  /** Tentar ligar automaticamente ao último alvo */
  autoConnect?: boolean;
}

/** Um PC encontrado por BLE, à espera de o utilizador escolher. */
export interface BlePeer {
  address: string;
  name: string;
}

interface RemoteState extends RemoteConfig {
  status: RemoteStatus;
  screen: RemoteScreenInfo | null;
  error: string;
  /** A fazer scan de BLE? */
  scanning: boolean;
  /** PCs encontrados por BLE, com o primeiro a ser o mais recente. */
  blePeers: BlePeer[];
  /** PCs encontrados por mDNS. */
  peers: DiscoveredPeer[];
  /** A descoberta está a correr? */
  discovering: boolean;
  /** A procura mDNS está a correr? Distingue "nunca foi pedida" de "activa". */
  mdnsRunning: boolean;
  autoConnecting: boolean;
  hydrate: () => Promise<void>;
  saveConfig: (cfg: Partial<RemoteConfig>) => Promise<void>;
  setForwardGestures: (value: boolean) => Promise<void>;
  connect: () => void;
  disconnect: () => void;
  /** Procura PCs por mDNS e preenche `peers`. */
  discover: () => Promise<void>;
  stopDiscover: () => void;
  /** Procura PCs por BLE e preenche `blePeers`. */
  scanBle: (seconds?: number) => Promise<void>;
  /** Liga por BLE a um dos endereços de `blePeers`. */
  connectBle: (address: string, name?: string) => Promise<void>;
  /** Liga ao PC escolhido na lista de mDNS. */
  connectPeer: (peer: DiscoveredPeer) => void;
}

export const useRemoteStore = create<RemoteState>((set, get) => {
  /**
   * Tenta voltar ao último alvo conhecido, com atraso crescente.
   *
   * Só é chamada quando a ligação caiu **estando estabelecida**: uma falha de
   * autenticação ou um endereço errado não se resolvem sozinhos, e insistir
   * neles seria uma tempestade de ligações a um código que o PC recusa.
   */
  const scheduleReconnect = () => {
    if (reconnectTimer) return;
    if (reconnectAttempts >= RECONNECT_MAX_ATTEMPTS) return;
    const delay = Math.min(
      RECONNECT_BASE_MS * 2 ** reconnectAttempts,
      RECONNECT_MAX_MS
    );
    reconnectAttempts += 1;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      const st = get();
      if (st.status === 'connected' || st.status === 'connecting') return;
      if (st.autoConnect === false) return;
      if (!codeCompleto(st.code)) return;
      if (st.lastTransport === 'ble' && st.lastBleAddress) {
        set({ autoConnecting: true });
        st.connectBle(st.lastBleAddress, st.lastBleName).catch(() => {});
        return;
      }
      if (st.lastPeerHost && st.lastPeerPort) {
        set({ autoConnecting: true });
        st.connectPeer({
          name: '',
          host: st.lastPeerHost,
          port: Number(st.lastPeerPort),
        } as any);
        return;
      }
      if (st.host && st.port) {
        set({ autoConnecting: true });
        st.connect();
      }
    }, delay);
  };

  const resetReconnect = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    reconnectAttempts = 0;
  };

  return {
  host: '',
  port: '8765',
  code: '',
  forwardGestures: false,
  status: 'disconnected',
  screen: null,
  error: '',
  scanning: false,
  blePeers: [],
  peers: [],
  discovering: false,
  mdnsRunning: false,
  autoConnecting: false,

  hydrate: async () => {
    resetReconnect();
    try {
      const raw = await AsyncStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const cfg = JSON.parse(raw);
      // `code` é o nome actual; `token` é o de antes dos 6 dígitos. Um valor
      // guardado que não seja um código de 6 dígitos é deitado fora: mostrá-lo
      // num campo de 6 dígitos dava um código truncado, e o utilizador via
      // "código inválido" num código que ele tinha copiado e colado bem.
      const guardado = normalizeCode(cfg.code ?? cfg.token);
      set({
        host: typeof cfg.host === 'string' ? cfg.host : '',
        port: typeof cfg.port === 'string' ? cfg.port : '8765',
        code: codeCompleto(guardado) ? guardado : '',
        forwardGestures: cfg.forwardGestures === true,
        lastTransport:
          cfg.lastTransport === 'wifi' || cfg.lastTransport === 'ble'
            ? cfg.lastTransport
            : undefined,
        lastPeerHost:
          typeof cfg.lastPeerHost === 'string' ? cfg.lastPeerHost : undefined,
        lastPeerPort:
          typeof cfg.lastPeerPort === 'string' ? cfg.lastPeerPort : undefined,
        lastBleAddress:
          typeof cfg.lastBleAddress === 'string' ? cfg.lastBleAddress : undefined,
        lastBleName:
          typeof cfg.lastBleName === 'string' ? cfg.lastBleName : undefined,
        autoConnect: cfg.autoConnect !== false,
      });

      // Tenta ligação automática após hidratar a configuração
      setTimeout(async () => {
        const st = get();
        if (st.status !== 'disconnected' || st.autoConnecting) return;
        if (st.autoConnect === false) return;
        if (!codeCompleto(st.code)) return;

        // Tentar por último transporte, com fallback
        if (st.lastTransport === 'ble' && st.lastBleAddress) {
          set({ autoConnecting: true });
          ble.requestPermissions().catch(() => {});
          await st.connectBle(st.lastBleAddress, st.lastBleName).catch(() => {});
          return;
        }
        if (st.lastTransport === 'wifi' && st.lastPeerHost && st.lastPeerPort) {
          set({ autoConnecting: true });
          st.connectPeer({
            name: '',
            host: st.lastPeerHost,
            port: Number(st.lastPeerPort),
          } as any);
          return;
        }
        if (st.lastTransport === 'wifi' && st.host && st.port) {
          set({ autoConnecting: true });
          st.connect();
          return;
        }
        if (st.lastBleAddress) {
          set({ autoConnecting: true });
          ble.requestPermissions().catch(() => {});
          await st.connectBle(st.lastBleAddress, st.lastBleName).catch(() => {});
          return;
        }
        if (st.host && st.port) {
          set({ autoConnecting: true });
          st.connect();
          return;
        }
      }, 300);
    } catch {
      // config não persistida — seguimos com os valores atuais
    }
  },

  saveConfig: async (cfg) => {
    const next = { ...get(), ...cfg };
    set(next);
    try {
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // não-fatal: guardamos apenas em memória
    }
  },

  setForwardGestures: async (value) => {
    const next = { ...get(), forwardGestures: value };
    set(next);
    try {
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // não-fatal
    }
  },

  connect: () => {
    const { host, port, code } = get();
    const { lease } = useLicenseStore.getState();
    const h = String(host || '').trim();
    if (!h) {
      set({
        status: 'disconnected',
        error: 'Introduz o IP do PC.',
        autoConnecting: false,
      });
      return;
    }
    if (!codeCompleto(code)) {
      set({
        status: 'disconnected',
        error: `O código são ${CODE_LEN} dígitos.`,
        autoConnecting: false,
      });
      return;
    }
    const url = buildWsUrl(h, port);
    set({ status: 'connecting', error: '', screen: null, autoConnecting: false });
    remote.connect(url, code, lease, {
      onOpen: (screen) => {
        resetReconnect();
        set({ status: 'connected', screen, error: '', autoConnecting: false });
        const st = get();
        get().saveConfig({
          lastTransport: 'wifi',
          lastPeerHost: st.host,
          lastPeerPort: st.port,
        });
      },
      onError: (msg) => set({ status: 'disconnected', error: msg, autoConnecting: false }),
      onClose: (msg) => {
        const wasConnected = get().status === 'connected';
        if (msg) set({ status: 'disconnected', error: msg, autoConnecting: false });
        else set({ status: 'disconnected', error: '', autoConnecting: false });
        if (msg && wasConnected) scheduleReconnect();
      },
    });
  },

  disconnect: () => {
    remote.close();
    clearAutoConnectTimer();
    resetReconnect();
    set({ status: 'disconnected', screen: null, error: '', autoConnecting: false });
  },

  discover: async () => {
    if (!mdnsSupported()) {
      set({ error: 'A descoberta automática só existe no Android.' });
      return;
    }
    set({ discovering: true, peers: [], error: '' });
    await mdns.start({
      onFound: (peer) => {
        set((s) => {
          // O mDNS re-anuncia o mesmo PC de 30 em 30 segundos. Sem esta
          // deduplicação, a lista cresce com cópias do mesmo endereço e o
          // utilizador tem de adivinhar qual é a boa.
          const others = s.peers.filter(
            (p) => !(p.host === peer.host && p.port === peer.port)
          );
          return { peers: [...others, peer] };
        });

        const stNow = get();
        if (
          stNow.status === 'disconnected' &&
          !stNow.autoConnecting &&
          stNow.autoConnect !== false &&
          codeCompleto(stNow.code) &&
          stNow.lastPeerHost &&
          stNow.lastPeerPort &&
          peer.host === stNow.lastPeerHost &&
          peer.port === Number(stNow.lastPeerPort)
        ) {
          clearAutoConnectTimer();
          autoConnectTimer = setTimeout(() => {
            autoConnectTimer = null;
            const st = get();
            if (
              st.status === 'disconnected' &&
              !st.autoConnecting &&
              st.autoConnect !== false &&
              codeCompleto(st.code)
            ) {
              set({ autoConnecting: true });
              st.connectPeer(peer);
            }
          }, 700);
        }
      },
      onLost: (name) =>
        set((s) => ({ peers: s.peers.filter((p) => p.name !== name) })),
      onError: (message) => set({ error: message }),
    });
    // `mdns.start()` resolve assim que o `discoverServices` é pedido; os
    // resultados chegam por evento e continuam a chegar. Deixar
    // `discovering` a `true` aqui desligava o botão de procura para o resto da
    // sessão — e a procura do mDNS é contínua, não um scan com fim: o que
    // está a correr é o "procurar", não um "a procurar".
    set({ discovering: false, mdnsRunning: true });
  },

  stopDiscover: () => {
    mdns.stop();
    set({ discovering: false, mdnsRunning: false });
  },

  scanBle: async (seconds = 8) => {
    if (!bleModule()) {
      set({ error: 'O Bluetooth só está disponível no Android.' });
      return;
    }
    set({ scanning: true, blePeers: [], error: '' });
    try {
      const seen: BlePeer[] = [];
      await scanForPeers(seconds, (address, name) => {
        // `seen` é local e não o estado do store: o callback chega do nativo
        // fora do ciclo do React, e escrever no store a cada anúncio (o
        // Android repete o mesmo dispositivo) faria a lista piscar.
        if (seen.some((p) => p.address === address)) return;
        seen.push({ address, name });
        set({ blePeers: [...seen] });

        const stNow = get();
        if (
          stNow.status === 'disconnected' &&
          !stNow.autoConnecting &&
          stNow.autoConnect !== false &&
          codeCompleto(stNow.code) &&
          stNow.lastTransport === 'ble' &&
          stNow.lastBleAddress === address
        ) {
          clearAutoConnectTimer();
          autoConnectTimer = setTimeout(() => {
            autoConnectTimer = null;
            const st = get();
            if (
              st.status === 'disconnected' &&
              !st.autoConnecting &&
              st.autoConnect !== false &&
              codeCompleto(st.code)
            ) {
              set({ autoConnecting: true });
              st.connectBle(address, name);
            }
          }, 700);
        }
      });
    } catch (e: any) {
      set({ error: e?.message || 'A procura por Bluetooth falhou.' });
    } finally {
      set({ scanning: false });
    }
  },

  connectBle: async (address, name) => {
    const { code } = get();
    if (!codeCompleto(code)) {
      set({
        status: 'error',
        error: 'O código são 6 dígitos — escreve-os antes de ligar.',
      });
      return;
    }
    set({ status: 'connecting', error: '', screen: null, autoConnecting: false });
    // A permissão de Bluetooth é de runtime do Android 12 em diante, e o
    // pedido tem de acontecer **antes** do `connectBle`: o `connect` nativo
    // não pode abrir um diálogo a meio de uma ligação, e sem isto o que se
    // vê é um `SecurityException` sem pista nenhuma.
    try {
      if (!(await ble.requestPermissions())) {
        throw new Error(
          'O telemóvel não deu permissão de Bluetooth. Ativa-a em Definições.'
        );
      }
    } catch (e: any) {
      set({ status: 'error', error: e?.message || 'Falta a permissão de Bluetooth.', autoConnecting: false });
      return;
    }
    remote.connectBle(address, code, {
      onOpen: (screen) => {
        resetReconnect();
        set({ status: 'connected', screen, error: '', autoConnecting: false });
        get().saveConfig({
          lastTransport: 'ble',
          lastBleAddress: address,
          lastBleName: name,
        });
      },
      onClose: (message) => {
        const wasConnected = get().status === 'connected';
        set((s) => ({
          status: message ? 'disconnected' : s.status,
          error: message || s.error,
          autoConnecting: false,
        }));
        if (message && wasConnected) scheduleReconnect();
      },
      onError: (message) => set({ status: 'error', error: message, autoConnecting: false }),
    });
  },

  connectPeer: (peer) => {
    // Guardar o host e a porta é o que faz a ligação sobreviver a um restart
    // da app: da próxima vez, o botão "ligar" já sabe para onde ir, e o
    // utilizador não reescreve o IP.
    const { code } = get();
    if (!codeCompleto(code)) {
      set({
        status: 'error',
        error: 'O código são 6 dígitos — escreve-os antes de ligar.',
      });
      return;
    }
    const { lease } = useLicenseStore.getState();
    const url = buildWsUrl(peer.host, String(peer.port));
    set({ status: 'connecting', error: '', screen: null, autoConnecting: false });
    void get().saveConfig({ host: peer.host, port: String(peer.port) });
    remote.connect(url, code, lease, {
      onOpen: (screen) => {
        resetReconnect();
        set({ status: 'connected', screen, error: '', autoConnecting: false });
        get().saveConfig({
          lastTransport: 'wifi',
          lastPeerHost: peer.host,
          lastPeerPort: String(peer.port),
        });
      },
      onError: (msg) => set({ status: 'error', error: msg, autoConnecting: false }),
      onClose: (msg) => {
        const wasConnected = get().status === 'connected';
        set((s) => ({
          status: msg ? 'disconnected' : s.status,
          error: msg || s.error,
          autoConnecting: false,
        }));
        if (msg && wasConnected) scheduleReconnect();
      },
    });
  },
  };
});
