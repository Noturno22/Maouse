// Escolhe o transporte do controlo remoto: WebSocket (WiFi) ou BLE.
//
// A `RemoteScreen` chama `remote.move()`, `remote.click()` e companhia há
// centenas de linhas e não deve saber qual dos dois transportes está em uso.
// Por isso `remote` é esta fachada, e não o `RemoteClient` do WebSocket: os
// dois clientes implementam a mesma interface e aqui escolhe-se um.
//
// A interface é o `RemoteClient` original, com uma coisa a mais —
// `connectBle` / `disconnectBle` não fazem sentido num cliente WebSocket, e
// metê-los na interface comum obrigaria a um `if` inútil do outro lado.

import {
  NativeEventEmitter,
  NativeModules,
  PermissionsAndroid,
  Platform,
} from 'react-native';
import {
  RemoteClient,
  RemoteClientCallbacks,
  RemoteScreenInfo,
} from './remoteClient';
import { BleRemoteClient } from './bleRemoteClient';

export type RemoteTransport = 'wifi' | 'ble';

const { BleRemote } = NativeModules as {
  BleRemote?: {
    hasPermissions(): Promise<boolean>;
    isBluetoothEnabled(): Promise<boolean>;
    startScan(seconds: number): Promise<boolean>;
    stopScan(): void;
    connect(address: string): Promise<boolean>;
    disconnect(): void;
    sendJson(json: string, withResponse: boolean): Promise<boolean>;
    sendMove(dxTenths: number, dyTenths: number): Promise<boolean>;
    isConnected(): Promise<boolean>;
    // Exigidos pelo `NativeEventEmitter`; ver `mdnsDiscovery.ts`.
    addListener(event: string): void;
    removeListeners(count: number): void;
  };
};

/**
 * O módulo nativo só existe no Android.
 *
 * O `bleRemoteClient.ts` é importado em qualquer plataforma, e o
 * `NativeModules.BleRemote` é `undefined` no iOS e no web. Um `import` de um
 * módulo inexistente rebenta o bundle — por isso o `require` é feito aqui, e o
 * cliente BLE devolve sempre um objeto que sabe dizer "não há Bluetooth
 * aqui" em vez de rebentar.
 */
/** O cliente BLE, exposto para quem precisar de pedir permissões. */
export const ble: BleRemoteClient = new BleRemoteClient(
  Platform.OS === 'android' ? BleRemote : undefined
);

let transport: RemoteTransport = 'wifi';

export const remote = {
  get transport(): RemoteTransport {
    return transport;
  },

  get isConnected(): boolean {
    return transport === 'ble' ? ble.isConnected : ws.isConnected;
  },

  /** Liga por Bluetooth a um endereço MAC já descoberto, com o código de 6 dígitos. */
  connectBle(
    address: string,
    code: string,
    cbs: RemoteClientCallbacks
  ): void {
    transport = 'ble';
    ble.connect(address, code, cbs);
  },

  closeBle(): void {
    if (transport === 'ble') {
      ble.close();
      transport = 'wifi';
    }
  },

  connect(
    url: string,
    code: string,
    lease: string,
    cbs: RemoteClientCallbacks
  ): void {
    transport = 'wifi';
    ws.connect(url, code, lease, cbs);
  },

  close(): void {
    if (transport === 'ble') {
      ble.close();
      transport = 'wifi';
      return;
    }
    ws.close();
  },

  move: (dx: number, dy: number) =>
    transport === 'ble' ? ble.move(dx, dy) : ws.move(dx, dy),
  moveTo: (x: number, y: number) =>
    transport === 'ble' ? ble.moveTo(x, y) : ws.moveTo(x, y),
  click: (button?: 'left' | 'right' | 'middle', count?: number) =>
    transport === 'ble' ? ble.click(button, count) : ws.click(button, count),
  press: (button?: 'left' | 'right' | 'middle') =>
    transport === 'ble' ? ble.press(button) : ws.press(button),
  release: (button?: 'left' | 'right' | 'middle') =>
    transport === 'ble' ? ble.release(button) : ws.release(button),
  scroll: (dx?: number, dy?: number) =>
    transport === 'ble' ? ble.scroll(dx, dy) : ws.scroll(dx, dy),
  key: (key: string) => (transport === 'ble' ? ble.key(key) : ws.key(key)),
  combo: (mods: string[], key: string) =>
    transport === 'ble' ? ble.combo(mods, key) : ws.combo(mods, key),
  text: (text: string) =>
    transport === 'ble' ? ble.text(text) : ws.text(text),
  media: (action: string) =>
    transport === 'ble' ? ble.media(action) : ws.media(action),
  gesture: (
    event: string,
    x?: number,
    y?: number,
    value?: number
  ) =>
    transport === 'ble'
      ? ble.gesture(event, x, y, value)
      : ws.gesture(event, x, y, value),
};

export const ws = new RemoteClient();

export type { RemoteClientCallbacks, RemoteScreenInfo };

/** O módulo BLE, ou `null` onde não há (iOS, web). */
export function bleModule() {
  return BleRemote ?? null;
}

/**
 * Garante as permissões de Bluetooth, pedir-as ao utilizador se faltarem.
 *
 * Declarar `BLUETOOTH_SCAN`/`BLUETOOTH_CONNECT` no manifest **não** as dá: do
 * Android 12 em diante são permissões de runtime, e sem o pedido o `startScan`
 * morre com uma `SecurityException` a meio — cujo stack trace aponta para o
 * framework, não para o que faltou. É por isso que o pedido vive aqui e não
 * num `try/catch` em volta do scan.
 *
 * As duas pedem-se juntas: `PermissionsAndroid.requestMultiple` trata-as como
 * um único diálogo no Android 12+, e pedir uma de cada vez abre dois diálogos
 * para o mesmo assunto.
 */
async function ensureBleReady(m: NonNullable<ReturnType<typeof bleModule>>) {
  if (await m.hasPermissions()) return;
  // Abaixo do Android 12 as permissões são de instalação e não há o que pedir.
  if (Platform.OS === 'android' && Number(Platform.Version) >= 31) {
    const res = await PermissionsAndroid.requestMultiple([
      PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN,
      PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT,
    ]);
    const ok = Object.values(res).every(
      (v) => v === PermissionsAndroid.RESULTS.GRANTED
    );
    if (!ok) {
      throw new Error(
        'O telemóvel não deu permissão de Bluetooth. Ativa-a em Definições.'
      );
    }
    if (await m.hasPermissions()) return;
  }
  throw new Error('Falta a permissão de Bluetooth no telemóvel.');
}

/** Varre BLE durante `seconds` e devolve cada PC encontrado. */
export async function scanForPeers(
  seconds: number,
  onDevice: (address: string, name: string) => void
): Promise<void> {
  const m = bleModule();
  if (!m) return;
  await ensureBleReady(m);
  if (!(await m.isBluetoothEnabled())) {
    throw new Error('O Bluetooth está desligado.');
  }
  const sub = new NativeEventEmitter(NativeModules.BleRemote);
  const handler = (ev: { device?: { address?: string; name?: string } }) => {
    const d = ev?.device;
    if (d?.address) onDevice(d.address, d.name || '');
  };
  sub.addListener('device', handler);
  try {
    await m.startScan(seconds);
    // A promessa do `startScan` resolve-se antes de aparecerem resultados, e
    // os resultados é que interessam. A espera é aqui, no JS, e não no
    // módulo nativo, para o `unmount` poder cancelar sem callbacks pendentes.
    await new Promise((r) => setTimeout(r, seconds * 1000 + 200));
  } finally {
    // `removeListener` não existe no `NativeEventEmitter` do React Native.
    // A forma correcta é `removeAllListeners`, e cada varredura cria o seu
    // `sub`, por isso não fica nenhum listener antigo à espera.
    sub.removeAllListeners('device');
    try {
      m.stopScan();
    } catch {
      // já parado
    }
  }
}
