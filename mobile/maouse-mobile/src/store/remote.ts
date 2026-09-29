import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  RemoteStatus,
  RemoteScreenInfo,
  buildWsUrl,
  remote,
} from '../services/remoteClient';

export { remote } from '../services/remoteClient';

const STORAGE_KEY = '@maouse/remote';

interface RemoteConfig {
  host: string;
  port: string;
  token: string;
  forwardGestures: boolean;
}

interface RemoteState extends RemoteConfig {
  status: RemoteStatus;
  screen: RemoteScreenInfo | null;
  error: string;
  hydrate: () => Promise<void>;
  saveConfig: (cfg: Partial<RemoteConfig>) => Promise<void>;
  setForwardGestures: (value: boolean) => Promise<void>;
  connect: () => void;
  disconnect: () => void;
}

export const useRemoteStore = create<RemoteState>((set, get) => ({
  host: '',
  port: '8765',
  token: '',
  forwardGestures: false,
  status: 'disconnected',
  screen: null,
  error: '',

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
}));