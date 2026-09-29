// Cliente BLE do controlo remoto do PC.
//
// O PC publica um peripheral GATT (`core/remote_ble.py`) e este cliente é o
// `central`. O protocolo é o **mesmo** do WebSocket: as mensagens são os mesmos
// JSON, e o `auth` é a primeira frame. A única diferença é o transporte, e é por
// isso que a interface é a mesma de `RemoteClient` — a `RemoteScreen` não muda.
//
// Duas otimizações que o BLE torna necessárias:
//
// 1. **`move` vai em binário, sem JSON.** O JSON de um `move` são ~30 bytes e
//    o valor de uma característica são 20 (MTU 23 - 3). Qualquer `move` ia
//    partir-se em dois fragmentos, e a 60 Hz isso é 120 escritas por segundo.
//    O caminho binário são 7 bytes com cabeçalho e cabe numa. O formato é
//    `0x01` e dois `int16` em décimos de pixel — `OP_MOVE` e `MOVE_SCALE` do
//    lado Python.
//
// 2. **Os `move` continuam a ser acumulados e enviados de 24 em 24 ms.** Não é
//    uma herança do WebSocket: é o mesmo motivo. Com `write-without-response`
//    cada escrita ocupa a ligação, e despejar 60 movimentos por segundo deixa o
//    resto dos comandos à espera. A 24 ms são ~42 comandos por segundo, que
//    continua a ser mais do que os olhos detectam.

import {
  NativeEventEmitter,
  NativeModules,
  PermissionsAndroid,
  Platform,
} from 'react-native';
import {
  RemoteClientCallbacks,
  RemoteScreenInfo,
} from './remoteClient';

const MOVE_INTERVAL_MS = 24;
const PING_INTERVAL_MS = 15000;

const OP_MOVE = 0x01;
const MOVE_SCALE = 10;

interface NativeBle {
  hasPermissions(): Promise<boolean>;
  // Exigidos pelo `NativeEventEmitter`; sem o override no lado Kotlin os
  // eventos nunca chegam e o JS nao se queixa.
  addListener(event: string): void;
  removeListeners(count: number): void;
  isBluetoothEnabled(): Promise<boolean>;
  startScan(seconds: number): Promise<boolean>;
  stopScan(): void;
  connect(address: string): Promise<boolean>;
  disconnect(): void;
  sendJson(json: string, withResponse: boolean): Promise<boolean>;
  sendMove(dxTenths: number, dyTenths: number): Promise<boolean>;
  isConnected(): Promise<boolean>;
}

export class BleRemoteClient {
  private native: NativeBle | null;
  private emitter: NativeEventEmitter | null = null;
  private token = '';
  private ready = false;
  private cbs: RemoteClientCallbacks | null = null;
  private intentionalClose = false;
  private lastError = '';
  private moveTimer: ReturnType<typeof setInterval> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private pendingDx = 0;
  private pendingDy = 0;

  constructor(native: NativeBle | undefined | null) {
    this.native = native ?? null;
  }

  get isConnected(): boolean {
    return this.ready;
  }

  /** `true` quando este dispositivo tem BLE utilizável (isto é, Android). */
  get isSupported(): boolean {
    return this.native !== null;
  }

  connect(
    address: string,
    token: string,
    cbs: RemoteClientCallbacks
  ): void {
    const n = this.native;
    if (!n) {
      cbs.onError('Este dispositivo não tem Bluetooth Low Energy (só Android).');
      return;
    }
    this.close();
    this.cbs = cbs;
    this.token = (token || '').trim();
    this.ready = false;
    this.intentionalClose = false;
    this.lastError = '';
    this.pendingDx = 0;
    this.pendingDy = 0;

    if (!this.token) {
      cbs.onError('Falta o token — vê-o em Definições no PC.');
      return;
    }

    this.emitter = new NativeEventEmitter(NativeModules.BleRemote);
    this.emitter.addListener('connected', () => {
      // A notificação é o que torna a ligação utilizável: o PC só responde a
      // quem tem `Notifying` ligado, e por isso o `auth` só é enviado depois
      // disto. Enviar antes chegava a um PC mudo.
      this.rawSend({ cmd: 'auth', token: this.token }, true);
    });
    this.emitter.addListener('disconnected', (ev: { error?: string }) => {
      this.handleClose(ev?.error || 'Ligação Bluetooth terminada.');
    });
    this.emitter.addListener('message', (ev: { message?: string }) => {
      this.handleMessage(String(ev?.message || ''));
    });
    this.emitter.addListener('error', (ev: { error?: string }) => {
      this.lastError = String(ev?.error || 'Erro de Bluetooth.');
      this.cbs?.onError(this.lastError);
    });

    n.connect(address).catch((e: Error) => {
      this.lastError = e?.message || 'Ligação Bluetooth falhou.';
      this.cbs?.onError(this.lastError);
    });
  }

  /**
   * Pede as permissões de Bluetooth, se ainda não as houver.
   *
   * O `connect` acima é síncrono e não pode pedir uma permissão a meio de uma
   * ligação — mas o `startScan` e o toque no botão "ligar por Bluetooth" são
   * os dois pontos assíncronos onde o pedido cabe, e é o `store` que os chama.
   */
  async requestPermissions(): Promise<boolean> {
    const n = this.native;
    if (!n) return false;
    if (await n.hasPermissions()) return true;
    if (Platform.OS !== 'android' || Number(Platform.Version) < 31) {
      return false;
    }
    const res = await PermissionsAndroid.requestMultiple([
      PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN,
      PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT,
    ]);
    return Object.values(res).every(
      (v) => v === PermissionsAndroid.RESULTS.GRANTED
    );
  }

  close(): void {
    this.intentionalClose = true;
    this.stopTimers();
    this.ready = false;
    this.pendingDx = 0;
    this.pendingDy = 0;
    if (this.emitter) {
      // Os listeners têm de sair antes de `NativeEventEmitter` ir para o lixo:
      // um `device` que chegue depois do `unmount` chama `onDevice` num
      // componente que já não existe.
      this.emitter.removeAllListeners('connected');
      this.emitter.removeAllListeners('disconnected');
      this.emitter.removeAllListeners('message');
      this.emitter.removeAllListeners('error');
      this.emitter = null;
    }
    this.native?.disconnect();
  }

  // ---- Comandos ----

  move(dx: number, dy: number): void {
    if (!this.ready) return;
    // Sem ganho, como no WebSocket: o ganho vive no PC
    // (`remote_move_gain`) e aplicá-lo aqui daria o ganho ao quadrado.
    this.pendingDx += dx;
    this.pendingDy += dy;
  }

  moveTo(x: number, y: number): void {
    this.sendRaw({ cmd: 'move_to', x, y });
  }

  click(button: 'left' | 'right' | 'middle' = 'left', count = 1): void {
    this.sendRaw({ cmd: 'click', button, count });
  }

  press(button: 'left' | 'right' | 'middle' = 'left'): void {
    this.sendRaw({ cmd: 'press', button });
  }

  release(button: 'left' | 'right' | 'middle' = 'left'): void {
    this.sendRaw({ cmd: 'release', button });
  }

  scroll(dx = 0, dy = 0): void {
    const rdx = Math.round(dx);
    const rdy = Math.round(dy);
    if (rdx !== 0 || rdy !== 0) {
      this.sendRaw({ cmd: 'scroll', dx: rdx, dy: rdy });
    }
  }

  key(key: string): void {
    if (key) this.sendRaw({ cmd: 'key', key });
  }

  combo(mods: string[], key: string): void {
    this.sendRaw({ cmd: 'combo', mods, key });
  }

  text(text: string): void {
    if (text) this.sendRaw({ cmd: 'text', text });
  }

  media(action: string): void {
    if (action) this.sendRaw({ cmd: 'media', action });
  }

  gesture(event: string, x?: number, y?: number, value?: number): void {
    const cmd: Record<string, unknown> = { cmd: 'gesture', event };
    if (typeof x === 'number' && Number.isFinite(x)) cmd.x = x;
    if (typeof y === 'number' && Number.isFinite(y)) cmd.y = y;
    if (typeof value === 'number' && Number.isFinite(value)) cmd.value = value;
    this.sendRaw(cmd);
  }

  // ---- Internos ----

  private rawSend(cmd: Record<string, unknown>, withResponse = false): void {
    const n = this.native;
    if (!n) return;
    n.sendJson(JSON.stringify(cmd), withResponse).catch(() => {
      // Um `send` que falha é um gesto perdido. O `ping` de 15 em 15 s descobre
      // se a ligação morreu, e é essa a altura certa de dizer ao utilizador.
    });
  }

  private sendRaw(cmd: Record<string, unknown>): void {
    if (!this.ready) return;
    // O buffer de `move` é esvaziado primeiro, pelo mesmo motivo do WebSocket:
    // a ordem de chegada ao PC é a ordem de execução, e um clique que chegue
    // antes dos últimos 24 ms de dedo carrega o botão no sítio errado.
    this.flushMoves();
    this.rawSend(cmd);
  }

  private handleMessage(raw: string): void {
    if (!raw) return;
    let msg: any;
    try {
      msg = JSON.parse(raw);
    } catch {
      return;
    }
    if (!msg || typeof msg.cmd !== 'string') return;

    if (msg.cmd === 'auth') {
      if (msg.ok === true) {
        this.ready = true;
        const screen: RemoteScreenInfo = {
          w: Number(msg.w) > 0 ? Number(msg.w) : 1920,
          h: Number(msg.h) > 0 ? Number(msg.h) : 1080,
        };
        this.startTimers();
        this.cbs?.onOpen(screen);
      } else {
        this.lastError =
          msg.error === 'auth_required'
            ? 'Token recusado. Confirma o token nas definições do PC.'
            : String(msg.error || 'Auth falhou.');
        this.cbs?.onError(this.lastError);
        this.close();
      }
    }
  }

  private handleClose(message: string): void {
    this.stopTimers();
    const wasReady = this.ready;
    const cb = this.cbs;
    this.ready = false;
    if (!cb) return;
    if (this.intentionalClose) {
      cb.onClose('');
      return;
    }
    cb.onClose(wasReady ? message : this.lastError || message);
  }

  private flushMoves(): void {
    if (!this.ready) return;
    const dx = Math.round(this.pendingDx);
    const dy = Math.round(this.pendingDy);
    this.pendingDx = 0;
    this.pendingDy = 0;
    if (dx === 0 && dy === 0) return;
    this.native
      ?.sendMove(
        Math.round(dx * MOVE_SCALE),
        Math.round(dy * MOVE_SCALE)
      )
      .catch(() => {
        // gesto perdido
      });
  }

  private startTimers(): void {
    this.stopTimers();
    this.pingTimer = setInterval(() => {
      this.sendRaw({ cmd: 'ping' });
    }, PING_INTERVAL_MS);
    this.moveTimer = setInterval(() => this.flushMoves(), MOVE_INTERVAL_MS);
  }

  private stopTimers(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
    if (this.moveTimer) {
      clearInterval(this.moveTimer);
      this.moveTimer = null;
    }
  }
}
