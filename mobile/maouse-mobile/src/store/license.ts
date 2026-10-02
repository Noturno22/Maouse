import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY = '@maouse/license';

export type LicenseTier = 'free' | 'mobile_pro';

interface StoredLicense {
  tier: LicenseTier;
  lease: string;
}

interface LicenseState {
  tier: LicenseTier;
  lease: string;
  status: 'loading' | 'ready' | 'error';
  hydrate: () => Promise<void>;
  grant: (lease: string) => Promise<void>;
  clear: () => Promise<void>;
}

export const useLicenseStore = create<LicenseState>((set) => ({
  tier: 'free',
  lease: '',
  status: 'loading',
  hydrate: async () => {
    try {
      const raw = await AsyncStorage.getItem(STORAGE_KEY);
      if (!raw) {
        set({ tier: 'free', lease: '', status: 'ready' });
        return;
      }
      // O `tier` local só pinta a UI. O que abre o remoto é o `lease`, porque o
      // PC valida a assinatura; por isso um tier sem lease cai para free em vez
      // de fingir Pro. Instalações antigas gravavam a string crua 'mobile_pro',
      // que não é JSON — o parse abaixo rebenta e cai para free, que é o
      // comportamento certo para um formato sem prova de compra.
      const parsed = JSON.parse(raw) as Partial<StoredLicense>;
      const lease = typeof parsed.lease === 'string' ? parsed.lease.trim() : '';
      const tier: LicenseTier =
        lease && parsed.tier === 'mobile_pro' ? 'mobile_pro' : 'free';
      set({ tier, lease, status: 'ready' });
    } catch {
      set({ tier: 'free', lease: '', status: 'ready' });
    }
  },
  grant: async (lease: string) => {
    const value = (lease || '').trim();
    if (!value) {
      set({ tier: 'free', lease: '', status: 'ready' });
      return;
    }
    try {
      const stored: StoredLicense = { tier: 'mobile_pro', lease: value };
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
    } catch {
      // non-fatal: fica só em memória para esta sessão
    }
    set({ tier: 'mobile_pro', lease: value, status: 'ready' });
  },
  clear: async () => {
    try {
      await AsyncStorage.removeItem(STORAGE_KEY);
    } catch {
      // non-fatal
    }
    set({ tier: 'free', lease: '', status: 'ready' });
  },
}));