// Cliente WebSocket para o controlo remoto do PC (Rato + Teclado).
//
// Protocolo (PC: core/remote.py):
//   1. Primeira mensagem é sempre o auth, e exige code *e* lease:
//       {"cmd":"auth","code":"123456","lease":"..."}
//         -> {"cmd":"auth","ok":true,"w":1920,"h":1080}
//      Código errado -> {"cmd":"auth","ok":false,"error":"auth_required"} + ligação fechada.
//      Muitas tentativas -> {"cmd":"auth","ok":false,"error":"auth_locked"} + ligação fechada.
//      Lease ausente/expirada/tier não pago -> {"ok":false,"error":"pro_required"}.
//      A lease vem do license-server (`useProEntitlement`) e é o que impede um
//      telemóvel free de controlar o PC; o PC é quem valida a assinatura.
//   2. Depois, comandos JSON; todos respondem {"ok":true,...}:
//       ping | move{dx,dy} | move_to{x,y} | click{button,count}
//       press{button} | release{button} | scroll{dx,dy} | key{key}
//       combo{mods,key} | text{text} | media{action} | gesture{event,x,y,value}

import {
  CODE_LEN,
  authErrorMessage,
  codeCompleto,
  normalizeCode,
} from './pairingCode';

export type RemoteStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'error';

export interface RemoteScreenInfo {
  w: number;
  h: number;
}

export interface RemoteClientCallbacks {
  onOpen: (screen: RemoteScreenInfo) => void;
  onClose: (message: string) => void;
  onError: (message: string) => void;
}

const PING_INTERVAL_MS = 15000;
// Os `move` são acumulados e enviados de 24 em 24 ms. 24 ms é a taxa com que
// o Android entrega touch events, por isso isto não perde nada e reduz o
// número de comandos (e de respostas do servidor) por segundo.
const MOVE_INTERVAL_MS = 24;

// O ganho do movimento relativo NÃO é aplicado aqui: vive no PC, em
// `remote_move_gain` (config.py), e é afinável no ecrã das definições sem
// recompilar a app. Havia um `MOVE_GAIN = 1.8` TAMBÉM aqui, o que dava um
// ganho efectivo de 1.8 x 3.0 = 5.4: uma varredura do dedo na largura do
// touchpad (~330 px) atirava o cursor 1780 px, mais do que a largura do ecrã.
// Era o "clique salta": o cursor batia no limite do ecrã e o toque clicava
// no sítio onde ele tinha ficado, não onde o dedo tinha parado.
// `pendingDx`/`pendingDy` acumulam em vírgula flutuante e só se arredonda no
// flush, para não perder meio píxel a cada evento.

export function buildWsUrl(host: string, port: string | number): string {
  const h = String(host || '')
    .trim()
    .replace(/^wss:\/\//i, '')
    .replace(/^ws:\/\//i, '')
    .replace(/\/+$/, '');
  const p = String(port || '8765').trim();
  return `ws://${h}:${p}`;
}

export class RemoteClient {
  private ws: WebSocket | null = null;
  private code = '';
  private lease = '';
  private ready = false;
  private cbs: RemoteClientCallbacks | null = null;
  private intentionalClose = false;
  private lastError = '';
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private moveTimer: ReturnType<typeof setInterval> | null = null;
  private pendingDx = 0;
  private pendingDy = 0;

  get isConnected(): boolean {
    return this.ready;
  }

  connect(
    url: string,
    code: string,
    lease: string,
    cbs: RemoteClientCallbacks
  ): void {
    this.close();
    this.ready = false;
    this.intentionalClose = false;
    this.lastError = '';
    this.pendingDx = 0;
    this.pendingDy = 0;
    this.cbs = cbs;
    this.code = normalizeCode(code);
    this.lease = (lease || '').trim();

    if (!codeCompleto(this.code)) {
      this.emitError(
        `O código são ${CODE_LEN} dígitos — vê-os em Definições no PC.`
      );
      return;
    }

    if (!this.lease) {
      this.emitError('O controlo remoto do PC é Pro. Compra o Pro para ligar.');
      return;
    }

    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch {
      this.emitError('Endereço inválido.');
      return;
    }

    this.ws = ws;
    // Nota: o auth é enviado diretamente (rawSend) porque só passa a poder usar
    // sendRaw depois de ready=true, que depende do ok do servidor a esta mensagem.
    ws.onopen = () =>
      this.rawSend({ cmd: 'auth', code: this.code, lease: this.lease });
    ws.onmessage = (ev) => this.handleMessage(String(ev.data));
    ws.onerror = () => {
      this.lastError = 'Falha de ligação (rede inacessível?).';
    };
    ws.onclose = (ev) => this.handleClose(ws, ev.code, ev.reason);
  }

  close(): void {
    this.intentionalClose = true;
    this.stopTimers();
    this.ready = false;
    this.pendingDx = 0;
    this.pendingDy = 0;
    const ws = this.ws;
    this.ws = null;
    if (ws) {
      try {
        ws.close();
      } catch {
        // já fechada
      }
    }
  }

  // ---- Comandos ----

  move(dx: number, dy: number): void {
    if (!this.ready) return;
    // Acumula em vírgula flutuante, sem ganho: o ganho é do PC
    // (`remote_move_gain`) e o arredondamento só acontece no flush.
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

  gesture(
    event: string,
    x?: number,
    y?: number,
    value?: number
  ): void {
    const cmd: Record<string, unknown> = { cmd: 'gesture', event };
    if (typeof x === 'number' && Number.isFinite(x)) cmd.x = x;
    if (typeof y === 'number' && Number.isFinite(y)) cmd.y = y;
    if (typeof value === 'number' && Number.isFinite(value)) cmd.value = value;
    this.sendRaw(cmd);
  }

  // ---- Internos ----

  private rawSend(cmd: Record<string, unknown>): void {
    const ws = this.ws;
    if (!ws || ws.readyState !== 1) return;
    ws.send(JSON.stringify(cmd));
  }

  // Todo comando discreto (clique, pressão, tecla, gesto) passa por aqui, e
  // QUALQUER um deles tem de ser precedido pelo esvaziamento do buffer de
  // `move`. Sem isso a ordem chega trocada ao PC: os `move` ficam à espera do
  // flush de 24 ms, mas o clique vai imediato, e o servidor — que executa um
  // comando de cada vez, pela ordem de chegada — carrega o botão com o cursor
  // ainda no sítio anterior aos últimos 24 ms de dedo. O clique saía no sítio
  // errado e o cursor só avançava DEPOIS do clique, o que se lê exactamente
  // como "o clique salta".
  private sendRaw(cmd: Record<string, unknown>): void {
    if (!this.ready) return;
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
        this.emitError(this.lastError);
        this.close();
      }
    }
  }

  private handleClose(wsRef: WebSocket, code: number, reason: string): void {
    if (this.ws !== wsRef) return; // ligação antiga
    this.stopTimers();
    const wasReady = this.ready;
    const cb = this.cbs;
    this.ready = false;
    this.ws = null;
    if (!cb) return;
    if (this.intentionalClose) {
      cb.onClose('');
      return;
    }
    const message = wasReady
      ? reason || `Ligação ao PC terminada (${code})`
      : this.lastError ||
        (code === 1006
          ? 'Não foi possível ligar ao PC. Confere o IP e o mesmo WiFi.'
          : `Ligação fechada (${code})`);
    cb.onClose(message);
  }

  private emitError(message: string): void {
    this.cbs?.onError(message);
  }

  private flushMoves(): void {
    const dx = Math.round(this.pendingDx);
    const dy = Math.round(this.pendingDy);
    this.pendingDx = 0;
    this.pendingDy = 0;
    if (dx !== 0 || dy !== 0) {
      // `rawSend`, não `sendRaw`: um `sendRaw` aqui voltaria a chamar
      // `flushMoves` indefinidamente. É também o que garante a ordem — quem
      // chama o `flushMoves` já vai enviar o comando logo a seguir, e o
      // WebSocket preserva a ordem de escrita.
      if (this.ready) this.rawSend({ cmd: 'move', dx, dy });
    }
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

export const remote = new RemoteClient();