/**
 * Testes do contrato de rede do controlo remoto.
 *
 * Isto não é um nice-to-have: é a fronteira de segurança entre o telemóvel e o
 * PC. O `core/remote.py` do PC expoe um `RemoteServer` que aceita comandos que
 * mexem no rato e no teclado de quem esta a usar a maquina, e a unica coisa entre
 * um host qualquer na mesma rede e esse rato e o handshake `auth` da primeira
 * mensagem. Se este ficheiro deixar de passar, ou porque o `buildWsUrl` mudou de
 * forma inesperada, ou porque o cliente deixou de mandar o auth como primeira
 * mensagem, o buraco abre em silencio -- nao ha teste nenhum do outro lado que
 * apanhe isso.
 *
 * Por isso os testes aqui sao sobre *contrato*, nao sobre implementacao: o que
 * interessa e o que sai pela ligacao e o que o PC aceita, nao quantas vezes o
 * `handleMessage` foi chamado.
 */
import { buildWsUrl, RemoteClient } from '../services/remoteClient';

// ---------------------------------------------------------------------------
// Teia de WebSocket minima, so o suficiente para o cliente falar.
// ---------------------------------------------------------------------------

type SentFrame = { cmd: string; [k: string]: unknown };

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  static last(): FakeWebSocket {
    const ws = FakeWebSocket.instances[FakeWebSocket.instances.length - 1];
    if (!ws) throw new Error('nenhum WebSocket foi aberto');
    return ws;
  }
  static reset(): void {
    FakeWebSocket.instances = [];
  }

  sent: SentFrame[] = [];
  closed = false;
  // 0 CONNECTING, 1 OPEN, 3 CLOSED, como na WebSocket do browser. Sem isto o
  // `rawSend` engole tudo (so escreve com readyState 1) e os testes passam vazios.
  readyState = 0;

  onopen: (() => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: ((ev: { code: number; reason: string }) => void) | null = null;

  constructor(public url: string) {
    FakeWebSocket.instances.push(this);
  }

  send(raw: string): void {
    this.sent.push(JSON.parse(raw) as SentFrame);
  }

  close(): void {
    this.closed = true;
    this.readyState = 3;
    // A WebSocket real dispara `onclose` de forma assincrona. Se o fake
    // disparasse a sincrono, o caminho de fecho seria exercitado de outra
    // maneira e o teste passaria sem cobrir o que o browser faz.
    setTimeout(() => this.onclose?.({ code: 1000, reason: '' }), 0);
  }

  // --- ajuda para o teste conduzir a ligacao ---

  /** Simula a ligacao a abrir. Dispara o auth, como o cliente faz. */
  accept(): void {
    this.readyState = 1;
    this.onopen?.();
  }

  /** Entrega uma mensagem do PC. */
  deliver(payload: unknown): void {
    this.onmessage?.({ data: JSON.stringify(payload) });
  }

  /** Entrega uma mensagem invalida, tal e qual (nao um payload). */
  deliverRaw(data: string): void {
    this.onmessage?.({ data });
  }

  /** Simula o PC a fechar a ligacao. */
  serverClose(code = 1006, reason = ''): void {
    this.readyState = 3;
    this.onclose?.({ code, reason });
  }
}

function withFakeWebSocket<T>(fn: () => T): T {
  FakeWebSocket.reset();
  const original = (globalThis as any).WebSocket;
  (globalThis as any).WebSocket = FakeWebSocket;
  const restore = () => {
    (globalThis as any).WebSocket = original;
  };
  try {
    const out = fn();
    if (out && typeof (out as any).then === 'function') {
      return (out as unknown as Promise<unknown>).finally(restore) as T;
    }
    restore();
    return out;
  } catch (err) {
    restore();
    throw err;
  }
}

function makeCallbacks() {
  return {
    onOpen: jest.fn(),
    onClose: jest.fn(),
    onError: jest.fn(),
  };
}

// ---------------------------------------------------------------------------
// buildWsUrl
// ---------------------------------------------------------------------------

describe('buildWsUrl', () => {
  it('monta ws:// a partir de host e porta', () => {
    expect(buildWsUrl('192.168.1.20', 8765)).toBe('ws://192.168.1.20:8765');
  });

  it('aceita a porta como string (vem de um campo de texto)', () => {
    expect(buildWsUrl('192.168.1.20', '8765')).toBe('ws://192.168.1.20:8765');
  });

  it('normaliza um host que ja vem com ws://', () => {
    // O utilizador cola o que copiou do log do PC, e o log traz o URL inteiro.
    // Sem isto, o cliente mandaria `ws://ws://...` e a ligacao falhava sem
    // mensagem util.
    expect(buildWsUrl('ws://192.168.1.20', 8765)).toBe('ws://192.168.1.20:8765');
  });

  it('rebaixa wss:// para ws:// — limitação conhecida', () => {
    // Deliberado, não um deslize: `core/remote.py` arranca o servidor com
    // `websockets.serve(...)` sem `ssl=`, portanto só existe texto claro e
    // ignorar o esquema é o que funciona na LAN. QUANDO O PC GANHAR TLS este
    // teste tem de falhar de propósito — é o aviso de que o cliente continua a
    // deitar o esquema fora e a ligação segura não vai completar.
    expect(buildWsUrl('wss://192.168.1.20', 8765)).toBe('ws://192.168.1.20:8765');
  });

  it('limpa espacos e barras a mais', () => {
    expect(buildWsUrl('  192.168.1.20/  ', 8765)).toBe('ws://192.168.1.20:8765');
  });

  it('usa a porta do PC por omissao quando nao vem nenhuma', () => {
    // 8765 e' `remote_port` no config.py do PC. Se algum dia mudar, este teste
    // tem de mudar com ele -- e a falha e' o sinal, nao um silencio.
    expect(buildWsUrl('192.168.1.20', '')).toBe('ws://192.168.1.20:8765');
  });

  it('aceita um hostname em vez de IP', () => {
    // O mDNS anuncia o PC como nome de instancia, e o utilizador pode escrever
    // `Maouse-1f3a2b9c.local` em vez do IP.
    expect(buildWsUrl('Maouse-1f3a2b9c.local', 8765)).toBe(
      'ws://Maouse-1f3a2b9c.local:8765',
    );
  });

  it('mantem o token fora do URL', () => {
    // O token nao viaja na ligacao; viaja no corpo da primeira mensagem. Se
    // algum dia aparecer na URL, este teste falha -- e e' o que o impede.
    const url = buildWsUrl('192.168.1.20', 8765);
    expect(url).not.toMatch(/token/i);
    expect(url).not.toMatch(/[?]/);
  });
});

// ---------------------------------------------------------------------------
// O handshake: a primeira mensagem e sempre o auth
// ---------------------------------------------------------------------------

describe('RemoteClient — handshake de auth', () => {
  it('manda o auth como PRIMEIRA mensagem, sem nada antes', () => {
    withFakeWebSocket(() => {
      const cbs = makeCallbacks();
      const c = new RemoteClient();
      c.connect('ws://192.168.1.20:8765', 'tok-123', cbs);

      FakeWebSocket.last().accept();

      const ws = FakeWebSocket.last();
      expect(ws.sent).toHaveLength(1);
      expect(ws.sent[0]).toEqual({ cmd: 'auth', token: 'tok-123' });
    });
  });

  it('nao aceita comandos antes do servidor confirmar o auth', () => {
    // A raza de ser do `rawSend` no `onopen` e nao do `sendRaw`: `sendRaw` so
    // escreve quando `ready`, e `ready` so passa a true com o `ok` do PC. Sem
    // isto, um `move` que chegue cedo seria descartado com o rato parado.
    withFakeWebSocket(() => {
      const cbs = makeCallbacks();
      const c = new RemoteClient();
      c.connect('ws://192.168.1.20:8765', 'tok-123', cbs);

      const ws = FakeWebSocket.last();
      c.move(10, 20);
      c.click('left');

      ws.accept();
      // O flush dos moves pendentes corre no timer, e o timer so arranca
      // depois do auth. Aqui nao ha timer nenhum, logo o socket tem de estar
      // vazio: o `move` foi para o buffer, nao para a ligacao.
      expect(ws.sent).toHaveLength(1);
      expect(ws.sent[0].cmd).toBe('auth');
    });
  });

  it('fica pronto e anuncia o ecra quando o PC responde ok', () => {
    withFakeWebSocket(() => {
      const cbs = makeCallbacks();
      const c = new RemoteClient();
      c.connect('ws://192.168.1.20:8765', 'tok-123', cbs);

      const ws = FakeWebSocket.last();
      ws.accept();
      ws.deliver({ cmd: 'auth', ok: true, w: 2560, h: 1440 });

      expect(c.isConnected).toBe(true);
      expect(cbs.onOpen).toHaveBeenCalledWith({ w: 2560, h: 1440 });
      c.close();
    });
  });

  it('sobe o tamanho do ecra quando o PC manda algo invalido', () => {
    // Um `w: 0` faria o cursor ficar preso no canto. O default e' uma escolha
    // deliberada: e' melhor um ecra errado do que um cursor inutil.
    withFakeWebSocket(() => {
      const cbs = makeCallbacks();
      const c = new RemoteClient();
      c.connect('ws://192.168.1.20:8765', 'tok-123', cbs);

      const ws = FakeWebSocket.last();
      ws.accept();
      ws.deliver({ cmd: 'auth', ok: true, w: 0, h: -1 });

      expect(cbs.onOpen).toHaveBeenCalledWith({ w: 1920, h: 1080 });
      c.close();
    });
  });

  it('fecha e explica quando o token é recusado', () => {
    withFakeWebSocket(() => {
      const cbs = makeCallbacks();
      const c = new RemoteClient();
      c.connect('ws://192.168.1.20:8765', 'token-errado', cbs);

      const ws = FakeWebSocket.last();
      ws.accept();
      ws.deliver({ cmd: 'auth', ok: false, error: 'auth_required' });

      expect(c.isConnected).toBe(false);
      expect(ws.closed).toBe(true);
      expect(cbs.onError).toHaveBeenCalledWith(
        expect.stringContaining('Token recusado'),
      );
    });
  });

  it('recusa ligar sem token, sem sequer abrir a ligacao', () => {
    // O token vem de um campo que o utilizador pode deixar vazio. Abrir a
    // ligacao para a recusar a seguir gastaria uma ronda e mostraria um erro
    // de rede em vez do erro util.
    withFakeWebSocket(() => {
      const cbs = makeCallbacks();
      const c = new RemoteClient();

      c.connect('ws://192.168.1.20:8765', '   ', cbs);

      expect(FakeWebSocket.instances).toHaveLength(0);
      expect(cbs.onError).toHaveBeenCalledWith(
        expect.stringContaining('token'),
      );
    });
  });
});

// ---------------------------------------------------------------------------
// Robustez do que chega do PC
// ---------------------------------------------------------------------------

describe('RemoteClient — o que o PC manda', () => {
  it('ignora lixo sem rebentar', () => {
    withFakeWebSocket(() => {
      const cbs = makeCallbacks();
      const c = new RemoteClient();
      c.connect('ws://192.168.1.20:8765', 'tok-123', cbs);

      const ws = FakeWebSocket.last();
      ws.accept();

      expect(() => ws.deliverRaw('isto nao e json')).not.toThrow();
      expect(() => ws.deliverRaw('null')).not.toThrow();
      expect(() => ws.deliverRaw('{"sem_cmd": 1}')).not.toThrow();
      expect(() => ws.deliverRaw('')).not.toThrow();

      // Continua vivo e ainda nao pronto, porque nada disse que o auth passou.
      expect(c.isConnected).toBe(false);
      c.close();
    });
  });

  it('nao fica pronto so por receber JSON bem formado', () => {
    withFakeWebSocket(() => {
      const cbs = makeCallbacks();
      const c = new RemoteClient();
      c.connect('ws://192.168.1.20:8765', 'tok-123', cbs);

      const ws = FakeWebSocket.last();
      ws.accept();
      ws.deliver({ tipo: 'qualquer' });

      expect(c.isConnected).toBe(false);
      c.close();
    });
  });

  it('distingue "PC nao alcançavel" de "ligacao caiu depois de_auth"', () => {
    // As duas mensagens dizem coisas diferentes ao utilizador e a UI mostra-as
    // tal e qual. Um 1006 antes do auth e' o IP errado; um 1006 depois e' o PC
    // que adormeceu. Colapsar os dois deixaria o utilizador a mexer nas
    // definições sem hipótese de resolver.
    withFakeWebSocket(() => {
      const cbs = makeCallbacks();
      const c = new RemoteClient();
      c.connect('ws://192.168.1.20:8765', 'tok-123', cbs);

      FakeWebSocket.last().accept();
      FakeWebSocket.last().serverClose(1006);

      expect(cbs.onClose).toHaveBeenCalledWith(
        expect.stringContaining('IP'),
      );
    });
  });

  it('não mostra erro quando é o utilizador a desligar', async () => {
    // O `onclose` de um socket que o próprio cliente fecha é engolido pelo
    // `handleClose` (o `this.ws` já foi limpo), por isso `onClose` não chega a
    // correr. O que interesa travar é o que o utilizador vê: nada. Se alguém
    // corrigir a ordem um dia, `onClose('')` continua a não ser uma acusação.
    await withFakeWebSocket(async () => {
      const cbs = makeCallbacks();
      const c = new RemoteClient();
      c.connect('ws://192.168.1.20:8765', 'tok-123', cbs);

      FakeWebSocket.last().accept();
      FakeWebSocket.last().deliver({ cmd: 'auth', ok: true, w: 1920, h: 1080 });

      c.close();
      await new Promise((r) => setTimeout(r, 0));

      expect(c.isConnected).toBe(false);
      expect(cbs.onError).not.toHaveBeenCalled();
      const accused = cbs.onClose.mock.calls.filter(([m]) => m !== '');
      expect(accused).toHaveLength(0);
    });
  });
});
