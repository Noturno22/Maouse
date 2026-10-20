// Cliente RFCOMM/SPP do controlo remoto do PC.
//
// O PC serve este protocolo em `core/remote_rfcomm.py` (e no executável WinRT
// `maouse-bluetooth-host`), e este cliente liga-se a ele. O protocolo de
// mensagens é o **mesmo** do WebSocket e do BLE: os mesmos JSON, e o `auth`
// como primeira mensagem. É por isso que a interface é a mesma de
// `RemoteClient` — a `RemoteScreen` não muda.
//
// ## O que muda em relação ao BLE, e porque
//
// O `bleRemoteClient.ts` faz duas otimizações que aqui são **erradas**:
//
// 1. **`move` em binário.** No BLE o MTU é 20 bytes, e o JSON de um `move`
//    partir-se-ia em dois fragmentos a 60 Hz. O caminho binário são 7 bytes e
//    cabe numa. Num stream RFCOMM não há MTU: o JSON vai inteiro, e o caminho
//    binário só ganharia um `sendMove` a mais para aprender.
// 2. **`sendJson` com `withResponse: false`.** É `write-without-response` do
//    ATT, que ocupa a ligação sem confirmar. O RFCOMM é um stream com
//    controlo de fluxo e confirmação, e `sendJson` aqui é sempre com
//    resposta — o que também dá um erro de escrita em vez de um gesto
//    perdido em silêncio.
//
// O `move` continua a ser **acumulado**, mas por um motivo diferente do BLE:
// aqui não é para libertar a ligação, é para não atravessar a ponte do React
// Native uma vez por quadro de câmara. O mesmo valor a 30 Hz é uma conversa
// por segundo a mais com o outro lado sem ganhar nada.

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
import {
  CODE_LEN,
  authErrorMessage,
  codeCompleto,
  normalizeCode,
} from './pairingCode';

const MOVE_INTERVAL_MS = 24;
const PING_INTERVAL_MS = 15000;

interface NativeRfcomm {
  hasPermissions(): Promise<boolean>;
  // Exigidos pelo `NativeEventEmitter`; sem eles no lado Kotlin os eventos
  // nunca chegam e o JS não se queixa.
  addListener(event: string): void;
  removeListeners(count: number): void;
  isBluetoothEnabled(): Promise<boolean>;
  connect(address: string): Promise<boolean>;
  disconnect(): void;
  // Sem `withResponse`: no RFCOMM a escrita é sempre confirmada.
  sendJson(json: string): Promise<boolean>;
  isConnected(): Promise<boolean>;
  listBonded(): Promise<Array<{ address: string; name: string }>>;
}

export class RfcommRemoteClient {
  private native: NativeRfcomm | null;
  private emitter: NativeEventEmitter | null = null;
  private code = '';
  private ready = false;
  private cbs: RemoteClientCallbacks | null = null;
  private intentionalClose = false;
  private lastError = '';
  private moveTimer: ReturnType<typeof setInterval> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private pendingDx = 0;
  private pendingDy = 0;

  constructor(native: NativeRfcomm | undefined | null) {
    this.native = native ?? null;
  }

  get isConnected(): boolean {
    return this.ready;
  }

  /** `true` quando existe Classic Bluetooth utilizável (isto é, Android). */
  get isSupported(): boolean {
    return this.native !== null;
  }

  /**
   * Liga a um PC **já emparelhado** no Android, pelo endereço MAC, com o
   * código de 6 dígitos.
   *
   * O `address` não pode ser descoberto por varrimento: o RFCOMM não anuncia
   * nada, e o Android só liga a um dispositivo que já esteja emparelhado.
   * Vem das Definições do telefone.
   */
  connect(
    address: string,
    code: string,
    cbs: RemoteClientCallbacks
  ): void {
    const n = this.native;
    if (!n) {
      cbs.onError('Este dispositivo não tem Bluetooth Classic (só Android).');
      return;
    }
    this.close();
    this.cbs = cbs;
    this.code = normalizeCode(code);
    this.ready = false;
    this.intentionalClose = false;
    this.lastError = '';
    this.pendingDx = 0;
    this.pendingDy = 0;

    if (!codeCompleto(this.code)) {
      cbs.onError(
        `O código são ${CODE_LEN} dígitos — escreve-os antes de ligar por Bluetooth.`
      );
      return;
    }

    this.emitter = new NativeEventEmitter(NativeModules.RfcommRemote);
    this.emitter.addListener('connected', () => {
      // `auth` só depois de o socket estar aberto: antes disso o PC ainda não
      // tem stream por onde ler, e a mensagem ia-se ao ar.
      this.rawSend({ cmd: 'auth', code: this.code });
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
   * Pede a permissão de Bluetooth, se ainda não a houver.
   *
   * Só `BLUETOOTH_CONNECT`, ao contrário do BLE que também precisa de
   * `BLUETOOTH_SCAN`: aqui não há varrimento nenhum, o telefone é que já sabe
   * o endereço. Pedir `SCAN` sem necessidade faria o Android mostrar o diálogo
   * de localização, que é uma confusão que não ajuda ninguém.
   */
  async requestPermissions(): Promise<boolean> {
    const n = this.native;
    if (!n) return false;
    if (await n.hasPermissions()) return true;
    if (Platform.OS !== 'android' || Number(Platform.Version) < 31) {
      return false;
    }
    const res = await PermissionsAndroid.requestMultiple([
      PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT,
    ]);
    return Object.values(res).every(
      (v) => v === PermissionsAndroid.RESULTS.GRANTED
    );
  }

  /**
   * Os PCs já emparelhados com este telemóvel, para o utilizador escolher.
   *
   * Não há varrimento possível no RFCOMM, ao contrário do BLE: o Android só
   * liga a um dispositivo emparelhado, e a lista é a única forma de chegar
   * ao PC sem escrever um endereço MAC à mão.
   */
  async listBondedPeers(): Promise<Array<{ address: string; name: string }>> {
    const n = this.native;
    if (!n) return [];
    if (!(await this.requestPermissions())) return [];
    const list = await n.listBonded();
    return Array.isArray(list)
      ? list
          .map((d: any) => ({
            address: String(d?.address || ''),
            name: String(d?.name || ''),
          }))
          .filter((d: { address: string }) => d.address.length > 0)
      : [];
  }

  close(): void {
    this.intentionalClose = true;
    this.stopTimers();
    this.ready = false;
    this.pendingDx = 0;
    this.pendingDy = 0;
    if (this.emitter) {
      // Os listeners têm de sair antes do `NativeEventEmitter` ir para o lixo:
      // uma mensagem que chegue depois do `unmount` entra num componente que já
      // não existe.
      this.emitter.removeAllListeners('connected');
      this.emitter.removeAllListeners('disconnected');
      this.emitter.removeAllListeners('message');
      this.emitter.removeAllListeners('error');
      this.emitter = null;
    }
    this.native?.disconnect();
  }

  // ---- Comandos ----
  //
  // Idênticos aos do BLE e do WebSocket: o que muda é só como vão pelo fio.

  move(dx: number, dy: number): void {
    if (!this.ready) return;
    // Sem ganho, como nos outros transportes: o ganho vive no PC
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

  private rawSend(cmd: Record<string, unknown>): void {
    const n = this.native;
    if (!n) return;
    n.sendJson(JSON.stringify(cmd)).catch(() => {
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
        this.lastError = authErrorMessage(msg.error, msg.retry_after);
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

  /**
   * Envia o `move` acumulado, em JSON e em pixels arredondados.
   *
   * Não há caminho binário nem escala de décimos aqui: os dois existiam por
   * causa do MTU do BLE, e no RFCOMM o `{"cmd":"move","dx":..,"dy":..}` é o que
   * o PC já sabe ler — o mesmo formato do WebSocket.
   */
  private flushMoves(): void {
    if (!this.ready) return;
    const dx = Math.round(this.pendingDx);
    const dy = Math.round(this.pendingDy);
    this.pendingDx = 0;
    this.pendingDy = 0;
    if (dx === 0 && dy === 0) return;
    this.rawSend({ cmd: 'move', dx, dy });
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