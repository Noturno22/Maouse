// Contrato do cliente RFCOMM.
//
// O que este ficheiro prende são as decisões que **só** o RFCOMM obriga, e que
// uma futura alteração feita a olho quebraria sem o-typescript dizer nada:
//
// - o `auth` é a primeira mensagem, e nada mais sai antes do `ok` do PC;
// - `move` vai em **JSON de pixels** (`{"cmd":"move","dx":3,"dy":-2}`) e não no
//   caminho binário de décimos do BLE, que ali existe só por causa do MTU de
//   20 bytes e aqui não tem razão de ser;
// - um `move` que não chegue a zero nem a 1 é arredondado no `flush`.
//
// Não se repete aqui o que `remoteClient.test.ts` já prende do protocolo
// (token, lease, `pro_required`, lixo JSON): é o mesmo protocolo, e duplicar
// isso só daria dois lugares para(actualizar e divergir.

import { DeviceEventEmitter, NativeModules } from 'react-native';
import { RfcommRemoteClient } from '../services/rfcommRemoteClient';

const CODE = '123456';

function fakeNative() {
  return {
    hasPermissions: jest.fn().mockResolvedValue(true),
    addListener: jest.fn(),
    removeListeners: jest.fn(),
    isBluetoothEnabled: jest.fn().mockResolvedValue(true),
    connect: jest.fn().mockResolvedValue(true),
    disconnect: jest.fn(),
    sendJson: jest.fn().mockResolvedValue(true),
    isConnected: jest.fn().mockResolvedValue(false),
    listBonded: jest.fn().mockResolvedValue([]),
  };
}

type Callbacks = {
  onOpen: jest.Mock;
  onClose: jest.Mock;
  onError: jest.Mock;
};

function cbs(): Callbacks {
  return { onOpen: jest.fn(), onClose: jest.fn(), onError: jest.fn() };
}

/** As mensagens que o cliente mandou, já deserializadas. */
function sent(n: ReturnType<typeof fakeNative>): Record<string, unknown>[] {
  return n.sendJson.mock.calls.map((c) => JSON.parse(c[0] as string));
}

let native: ReturnType<typeof fakeNative>;
let client: RfcommRemoteClient;

beforeEach(() => {
  jest.useFakeTimers();
  native = fakeNative();
  // O cliente tira o emitter de `NativeModules.RfcommRemote`, e o
  // `NativeEventEmitter` do RN exige um módulo não-nulo — por isso o falso é
  // registado aqui e não só injectado no construtor.
  (NativeModules as Record<string, unknown>).RfcommRemote = native;
  client = new RfcommRemoteClient(native);
});

afterEach(() => {
  client.close();
  jest.useRealTimers();
  delete (NativeModules as Record<string, unknown>).RfcommRemote;
});

/** Simula o PC a aceitar o socket: é o que autoriza o `auth`. */
function socketOpen() {
  DeviceEventEmitter.emit('connected', {});
}

/** Simula a resposta de `auth` do PC. */
function authOk(w = 1920, h = 1080) {
  DeviceEventEmitter.emit('message', {
    message: JSON.stringify({ cmd: 'auth', ok: true, w, h }),
  });
}

describe('RfcommRemoteClient — primeiro o auth', () => {
  it('não manda nada antes de o socket estar aberto', () => {
    const cb = cbs();
    client.connect('00:11:22:33:44:55', CODE, cb);

    expect(native.sendJson).not.toHaveBeenCalled();

    socketOpen();
    expect(sent(native)).toEqual([{ cmd: 'auth', code: CODE }]);
  });

  it('recusa o `auth` sem código de 6 dígitos e não abre o socket', () => {
    const cb = cbs();
    client.connect('00:11:22:33:44:55', '12', cb);

    expect(cb.onError).toHaveBeenCalledWith(expect.stringContaining('6 dígitos'));
    expect(native.connect).not.toHaveBeenCalled();
  });

  it('ignora comandos até o PC confirmar o `auth`', () => {
    const cb = cbs();
    client.connect('00:11:22:33:44:55', CODE, cb);
    socketOpen();

    // O socket está aberto mas o `auth` ainda não foi respondido: o PC pode
    // estar a rejeitar o código, e um clique aqui seria um comando a um rato
    // que ninguém autorizou.
    client.click('left');
    client.scroll(0, 120);
    client.move(10, 10);
    jest.advanceTimersByTime(50);

    expect(sent(native)).toEqual([{ cmd: 'auth', code: CODE }]);
  });

  it('dá aLigação como pronta só com o `ok` do PC', () => {
    const cb = cbs();
    client.connect('00:11:22:33:44:55', CODE, cb);
    socketOpen();

    expect(client.isConnected).toBe(false);

    authOk(2560, 1440);

    expect(client.isConnected).toBe(true);
    expect(cb.onOpen).toHaveBeenCalledWith({ w: 2560, h: 1440 });
  });
});

describe('RfcommRemoteClient — move em JSON', () => {
  it('envia `move` como JSON em pixels, não em binário de décimos', () => {
    const cb = cbs();
    client.connect('00:11:22:33:44:55', CODE, cb);
    socketOpen();
    authOk();

    client.move(3, -2);
    jest.advanceTimersByTime(24);

    expect(sent(native)).toEqual([
      { cmd: 'auth', code: CODE },
      { cmd: 'move', dx: 3, dy: -2 },
    ]);
    // O caminho binário do BLE (`sendMove` + `MOVE_SCALE`) não existe aqui:
    // um `move` de 3 px tinha de sair como `dx:3`, e não como `dx:30`.
    expect((native as unknown as { sendMove?: unknown }).sendMove).toBeUndefined();
  });

  it('acumula e arredonda no flush, em vez de enviar por `move`', () => {
    const cb = cbs();
    client.connect('00:11:22:33:44:55', CODE, cb);
    socketOpen();
    authOk();

    client.move(1.4, -2.4);
    client.move(1.4, -2.4);
    jest.advanceTimersByTime(24);

    // 2.8 -> 3, -4.8 -> -5: dois gestos num só comando.
    expect(sent(native)[1]).toEqual({ cmd: 'move', dx: 3, dy: -5 });
  });

  it('não manda `move` que se anula sozinho', () => {
    const cb = cbs();
    client.connect('00:11:22:33:44:55', CODE, cb);
    socketOpen();
    authOk();

    client.move(5, 5);
    client.move(-5, -5);
    jest.advanceTimersByTime(24);

    expect(sent(native)).toEqual([{ cmd: 'auth', code: CODE }]);
  });

  it('esvazia o `move` pendente antes de um comando que não seja `move`', () => {
    const cb = cbs();
    client.connect('00:11:22:33:44:55', CODE, cb);
    socketOpen();
    authOk();

    client.move(7, 0);
    client.click('left');

    // O `move` chega primeiro: se o clique chegasse antes, carregava o botão
    // no sítio onde o dedo ainda não tinha chegado.
    expect(sent(native)).toEqual([
      { cmd: 'auth', code: CODE },
      { cmd: 'move', dx: 7, dy: 0 },
      { cmd: 'click', button: 'left', count: 1 },
    ]);
  });
});

describe('RfcommRemoteClient — auth recusado', () => {
  it('não abre a ligação e reporta o erro do PC', () => {
    const cb = cbs();
    client.connect('00:11:22:33:44:55', CODE, cb);
    socketOpen();

    DeviceEventEmitter.emit('message', {
      message: JSON.stringify({ cmd: 'auth', ok: false, error: 'auth_failed' }),
    });

    expect(client.isConnected).toBe(false);
    expect(cb.onError).toHaveBeenCalledWith(expect.any(String));
    expect(native.disconnect).toHaveBeenCalled();
  });
});

describe('RfcommRemoteClient — queda da ligação', () => {
  it('deixa de aceitar comandos quando o PC fecha o socket', () => {
    const cb = cbs();
    client.connect('00:11:22:33:44:55', CODE, cb);
    socketOpen();
    authOk();
    expect(client.isConnected).toBe(true);

    DeviceEventEmitter.emit('disconnected', {});

    expect(client.isConnected).toBe(false);
    client.click('left');
    expect(sent(native)).toHaveLength(1); // só o `auth`
    expect(cb.onClose).toHaveBeenCalled();
  });

  it('reporta uma falha de ligação que o `auth` nunca chegou a confirmar', async () => {
    const cb = cbs();
    native.connect.mockRejectedValue(new Error('Ligação RFCOMM falhou'));
    client.connect('00:11:22:33:44:55', CODE, cb);

    // O `catch` do `connect` roda numa microtask, por isso a asserção tem de
    // esperar por ela — com `fakeTimers` isto continua a ser verdade: os
    // timers falsos não affectam a fila de promessas.
    await Promise.resolve();

    expect(cb.onError).toHaveBeenCalledWith('Ligação RFCOMM falhou');
  });
});

describe('RfcommRemoteClient — lista de emparelhados', () => {
  it('devolve vazio sem módulo nativo', async () => {
    const c = new RfcommRemoteClient(undefined);
    expect(await c.listBondedPeers()).toEqual([]);
  });

  it('filtra entradas sem endereço e normaliza o nome', async () => {
    native.listBonded.mockResolvedValue([
      { address: 'AA:BB:CC:DD:EE:FF', name: null },
      { address: '', name: 'Lixo' },
      { address: '11:22:33:44:55:66', name: 'Fortune' },
    ]);
    expect(await client.listBondedPeers()).toEqual([
      { address: 'AA:BB:CC:DD:EE:FF', name: '' },
      { address: '11:22:33:44:55:66', name: 'Fortune' },
    ]);
  });

  it('reporta a recusa de permissão como lista vazia', async () => {
    native.hasPermissions.mockResolvedValue(false);
    expect(await client.listBondedPeers()).toEqual([]);
  });
});