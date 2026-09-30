import { useCallback, useEffect, useState } from 'react';
import { NativeModules, Platform } from 'react-native';

// Sem os módulos nativos (ex.: iOS stub, web) assumimos "ok".
const getCtrl = (): any => {
  const { SystemController } = NativeModules as Record<string, any>;
  return SystemController;
};

/**
 * Estado do serviço de Acessibilidade do Mãouse (Android).
 * Sem ele, TouchController/KeyboardController não têm efeito no telemóvel —
 * por isso a UI mostra um aviso/atalho quando está desligado.
 */
export function useAccessibilityStatus() {
  const [enabled, setEnabled] = useState<boolean | null>(null);

  const refresh = useCallback(() => {
    const ctrl = getCtrl();
    if (Platform.OS !== 'android' || !ctrl?.isAccessibilityEnabled) {
      setEnabled(true);
      return;
    }
    ctrl
      .isAccessibilityEnabled()
      .then((ok: boolean) => setEnabled(!!ok))
      .catch(() => setEnabled(false));
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 3000);
    return () => clearInterval(timer);
  }, [refresh]);

  const openSettings = useCallback(() => {
    getCtrl()?.openAccessibilitySettings?.();
  }, []);

  return { accessibilityEnabled: enabled, refreshAccessibility: refresh, openAccessibilitySettings: openSettings };
}