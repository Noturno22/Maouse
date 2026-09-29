import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  RemoteStatus,
  RemoteScreenInfo,
  buildWsUrl,
} from '../services/remoteClient';
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

// O `remote` que o resto da app usa é a **fachada** de
// `remoteTransport`, não o `RemoteClient` do WebSocket: são os dois que
// implementam a mesma interface e a fachada escolhe entre eles. Importar
// `remoteClient` aqui (como se fazia antes) dava o cliente WebSocket e o
// `connectBle` não existiria — que é o tipo de erro que só aparece em runtime,
// quando alguém toca no botão de Bluetooth.
export { remote } from '../services/remoteTransport';
export type { DiscoveredPeer } from '../services/mdnsDiscovery';

const STORAGE_KEY = '@maouse/remote';

interface RemoteConfig {
  host: string;
  port: string;
  token: string;
  forwardGestures: boolean;
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
  connectBle: (address: string) => Promise<void>;
  /** Liga ao PC escolhido na lista de mDNS. */
  connectPeer: (peer: DiscoveredPeer) => void;
}

export const useRemoteStore = create<RemoteState>((set, get) => ({
  host: '',
  port: '8765',
  token: '',
  forwardGestures: false,
  status: 'disconnected',
  screen: null,
  error: '',
  scanning: false,
  blePeers: [],
  peers: [],
  discovering: false,
  mdnsRunning: false,

  hydrate: async () => {
    try {
      const raw = await AsyncStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const cfg = JSON.parse(raw);
      set({
        host: typeof cfg.host === 'string' ? cfg.host : '',
        port: typeof cfg.port === 'string' ? cfg.port : '8765',
        token: typeof cfg.token === 'string' ? cfg.token : '',
        forwardGestures: cfg.forwardGestures === true,
      });
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
    const { host, port, token } = get();
    const h = String(host || '').trim();
    if (!h) {
      set({
        status: 'error',
        error: 'Introduz o IP do PC (mostrado nas definições no PC).',
      });
      return;
    }
    const url = buildWsUrl(h, port);
    set({ status: 'connecting', error: '', screen: null });
    remote.connect(url, token, {
      onOpen: (screen) => set({ status: 'connected', screen, error: '' }),
      onClose: (message) =>
        set((s) => ({
          status: message ? 'disconnected' : s.status,
          error: message || s.error,
        })),
      onError: (message) => set({ status: 'error', error: message }),
    });
  },

  disconnect: () => {
    remote.close();
    set({ status: 'disconnected', screen: null, error: '' });
  },

  discover: async () => {
    if (!mdnsSupported()) {
      set({ error: 'A descoberta automática só existe no Android.' });
      return;
    }
    set({ discovering: true, peers: [], error: '' });
    await mdns.start({
      onFound: (peer) =>
        set((s) => {
          // O mDNS re-anuncia o mesmo PC de 30 em 30 segundos. Sem esta
          // deduplicação, a lista cresce com cópias do mesmo endereço e o
          // utilizador tem de adivinhar qual é a boa.
          const others = s.peers.filter(
            (p) => !(p.host === peer.host && p.port === peer.port)
          );
          return { peers: [...others, peer] };
        }),
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
      });
    } catch (e: any) {
      set({ error: e?.message || 'A procura por Bluetooth falhou.' });
    } finally {
      set({ scanning: false });
    }
  },

  connectBle: async (address) => {
    const { token } = get();
    if (!token) {
      set({
        status: 'error',
        error: 'Falta o token — vê-lo em Definições no PC.',
      });
      return;
    }
    set({ status: 'connecting', error: '', screen: null });
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
      set({ status: 'error', error: e?.message || 'Falta a permissão de Bluetooth.' });
      return;
    }
    remote.connectBle(address, token, {
      onOpen: (screen) => set({ status: 'connected', screen, error: '' }),
      onClose: (message) =>
        set((s) => ({
          status: message ? 'disconnected' : s.status,
          error: message || s.error,
        })),
      onError: (message) => set({ status: 'error', error: message }),
    });
  },

  connectPeer: (peer) => {
    // Guardar o host e a porta é o que faz a ligação sobreviver a um restart
    // da app: da próxima vez, o botão "ligar" já sabe para onde ir, e o
    // utilizador não reescreve o IP.
    void get().saveConfig({ host: peer.host, port: String(peer.port) });
    get().connect();
  },
}));
