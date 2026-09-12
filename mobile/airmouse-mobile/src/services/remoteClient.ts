// Cliente WebSocket para o controlo remoto do PC (Rato + Teclado).
//
// Protocolo (PC: core/remote.py):
//   1. Primeira mensagem é sempre o auth:
//       {"cmd":"auth","token":"..."}  ->  {"ok":true,"w":1920,"h":1080}
//      Token errado -> {"ok":false,"error":"auth_required"} + ligação fechada.
//   2. Depois, comandos JSON; todos respondem {"ok":true,...}:
//       ping | move{dx,dy} | move_to{x,y} | click{button,count}
//       press{button} | release{button} | scroll{dx,dy} | key{key}
//       combo{mods,key} | text{text} | media{action} | gesture{event,x,y,value}

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
const MOVE_INTERVAL_MS = 24;
const MOVE_GAIN = 1.8;

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
  private token = '';
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

  connect(url: string, token: string, cbs: RemoteClientCallbacks): void {
    this.close();
    this.ready = false;
    this.intentionalClose = false;
    this.lastError = '';
    this.pendingDx = 0;
    this.pendingDy = 0;
    this.cbs = cbs;
    this.token = (token || '').trim();

    if (!this.token) {
      this.emitError('Falta o token — vê-o em Definições no PC.');
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
    ws.onopen = () => this.sendRaw({ cmd: 'auth', token: this.token });
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
    this.pendingDx += Math.round(MOVE_GAIN * dx);
    this.pendingDy += Math.round(MOVE_GAIN * dy);
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

  private sendRaw(cmd: Record<string, unknown>): void {
    const ws = this.ws;
    if (!this.ready || !ws || ws.readyState !== 1) return;
    ws.send(JSON.stringify(cmd));
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
      this.sendRaw({ cmd: 'move', dx, dy });
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