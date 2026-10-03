/**
 * Testes do gate Pro do ecrã de controlo remoto do PC.
 *
 * O `core/remote.py` do PC aceita comandos que mexem no rato e no teclado de quem
 * está a usar a máquina. A protecção que importa mora lá -- a lease -- e não
 * aqui. Mas se este gate desaparecer numa refactorização, o que acontece é um
 * telemóvel free passar a ver o formulário, e a tentativa de ligar falhar só no
 * servidor: dois passos mais tarde, e sem nada neste repositório que diga o que
 * mudou.
 *
 * Por isso os testes são sobre o que está *visível* e não sobre implementação.
 * `renderBody` tem três ramos e a ordem deles é o contrato: `loading` antes de
 * `!isPro` antes de `connected`. Um ramo trocado passa num teste solto e falha
 * aqui.
 */
import React from 'react';
import { render } from '@testing-library/react-native';

import RemoteScreen from '../components/RemoteScreen';
import type { ProEntitlement } from '../hooks/useProEntitlement';

// O `ProGate` fica REAL de propósito. Assim o teste prova que o ecrã mostra a
// cópia do paywall do PC remoto e não a do controlo de gestos no telemóvel: um
// paywall certo no sítio errado continua a parecer paywall, e o teste tem de
// apanhar isso.
//
// O store e a fachada de transportes são simulados porque não há nada a testar
// aqui. O store puxa `mdnsDiscovery` e `remoteTransport`, que falam com módulos
// nativos (NsdManager, BLE) que não existem no Node. O que se prova é a decisão
// do gate, e essa depende só da prop `entitlement`.
//
// O `mock` do nome não é decorativo: o `jest.mock` é içado acima dos imports e o
// hoisting do Babel só deixa a factory referenciar variáveis que comecem por `mock`.
const mockStoreState = {
  host: '192.168.1.50',
  port: 8765,
  code: '314159',
  forwardGestures: true,
  status: 'disconnected' as const,
  screen: null,
  error: null,
  scanning: false,
  blePeers: [],
  peers: [],
  discovering: false,
  mdnsRunning: false,
  stopDiscover: jest.fn(),
  saveConfig: jest.fn(),
  setForwardGestures: jest.fn(),
  connect: jest.fn(),
  disconnect: jest.fn(),
  discover: jest.fn(),
  scanBle: jest.fn(),
  connectBle: jest.fn(),
  connectPeer: jest.fn(),
};

jest.mock('../store/remote', () => ({
  useRemoteStore: () => mockStoreState,
}));

jest.mock('../services/remoteTransport', () => ({
  remote: {
    isConnected: false,
    key: jest.fn(),
    text: jest.fn(),
    click: jest.fn(),
    press: jest.fn(),
    release: jest.fn(),
    move: jest.fn(),
    scroll: jest.fn(),
    media: jest.fn(),
  },
}));

// O default de 5 s do Jest é curto para a primeira render deste ecrã: o preset
// compila a árvore toda do RN e os tempos medidos vão de 20 ms a 15 s conforme o
// cache do Babel esteja frio ou quente. 30 s dá folga sem chegar a esconder um
// teste pendurado a sério.
jest.setTimeout(30_000);

const LOADING = 'remote-license-loading';
const PAYWALL_REMOTO = 'O PC remoto faz parte do Pro';
const PAYWALL_GESTOS = 'Desbloqueia o controlo completo';
const BOTAO_LIGAR = 'LIGAR';

function makeEntitlement(overrides: Partial<ProEntitlement> = {}): ProEntitlement {
  return {
    isPro: false,
    status: 'ready',
    product: null,
    purchasing: false,
    actionError: null,
    purchasePro: async () => {},
    restorePro: async () => {},
    clearActionError: () => {},
    ...overrides,
  };
}

describe('<RemoteScreen />', () => {
  describe('enquanto a licença ainda não hidratou', () => {
    it('mostra só o spinner a um Pro, sem o formulário', async () => {
      // Sem a guarda de `loading`, `isPro: true` cairia no formulário e o Pro
      // veria um frame do ecrã que ainda não devia estar lá.
      const t = await render(
        <RemoteScreen
          onBack={jest.fn()}
          entitlement={makeEntitlement({ status: 'loading', isPro: true })}
        />,
      );

      expect(t.getByTestId(LOADING)).toBeTruthy();
      expect(t.queryByText(BOTAO_LIGAR)).toBeNull();
    });

    it('mostra só o spinner a um Free, sem o paywall', async () => {
      // E o outro lado do mesmo frame: o Free não pode ver paywall antes da
      // licença responder, porque `status` ainda pode virar `ready` com Pro.
      const t = await render(
        <RemoteScreen
          onBack={jest.fn()}
          entitlement={makeEntitlement({ status: 'loading', isPro: false })}
        />,
      );

      expect(t.getByTestId(LOADING)).toBeTruthy();
      expect(t.queryByText(PAYWALL_REMOTO)).toBeNull();
      expect(t.queryByText(BOTAO_LIGAR)).toBeNull();
    });
  });

  describe('com a licença já carregada', () => {
    it('a um Free mostra o paywall do PC remoto e nenhum controlo de ligação', async () => {
      const t = await render(
        <RemoteScreen
          onBack={jest.fn()}
          entitlement={makeEntitlement({ status: 'ready', isPro: false })}
        />,
      );

      expect(t.getByText(PAYWALL_REMOTO)).toBeTruthy();
      // A cópia de gestos é a do outro paywall: se aparecer, o ecrã está a
      // mostrar a mensagem errada para o que está a ser bloqueado.
      expect(t.queryByText(PAYWALL_GESTOS)).toBeNull();
      // Zero controlos de ligação. Um `LIGAR` aqui seria o gate furado.
      expect(t.queryByText(BOTAO_LIGAR)).toBeNull();
    });

    it('a um Pro mostra o formulário e nenhum paywall', async () => {
      const t = await render(
        <RemoteScreen
          onBack={jest.fn()}
          entitlement={makeEntitlement({ status: 'ready', isPro: true })}
        />,
      );

      expect(t.getByText(BOTAO_LIGAR)).toBeTruthy();
      expect(t.queryByText(PAYWALL_REMOTO)).toBeNull();
      expect(t.queryByText(PAYWALL_GESTOS)).toBeNull();
    });
  });
});