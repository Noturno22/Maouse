// Descobre o PC por mDNS, para o telefone não escrever um IP à mão.
//
// O outro lado é `core/discovery.py`, que anuncia `_maouse._tcp`. Aqui o
// `NsdManager` do Android faz o papel do `zeroconf`.
//
// Dois motivos para isto não ser um `require` de um pacote de mDNS qualquer:
// o `NsdManager` é a API do sistema (e o Android 12+ exige `NEARBY_WIFI_DEVICES`
// em vez de localização), e o resultado é um `{name, host, port}` que se liga
// logo ao `RemoteClient` sem conversão.
//
// O que se perde, e é preciso saber: o mDNS **não** atravessa sub-redes. Um
// PC em Ethernet e um telefone em dados móveis nunca se encontram, e a
// consequência disso é o telefone dizer "não encontrei nada", o que é
// indistinguível de "o PC está desligado". Por isso o `start` avisa logo se o
// WiFi do telefone está desligado: dizer isso vale mais do que uma lista
// vazia.

import { NativeEventEmitter, NativeModules, Platform } from 'react-native';

export interface DiscoveredPeer {
  name: string;
  host: string;
  port: number;
  /** Versão do protocolo, dos TXT (`v`). */
  version?: string;
  /** Id do dispositivo, dos TXT (`id`). */
  id?: string;
}

export interface DiscoveryCallbacks {
  onFound: (peer: DiscoveredPeer) => void;
  onLost: (name: string) => void;
  onError: (message: string) => void;
}

// O nome do módulo nativo e o nome desta classe não podem ser o mesmo: o
// `const` de baixo tapa a classe que vem a seguir, e `new MdnsDiscovery()` passa
// a ser `new {start, stop}()` — um erro que só aparece em `tsc`, e em runtime
// como "MdnsDiscovery is not a constructor" na app.
const { MdnsDiscovery: nativeMdns } = NativeModules as {
  MdnsDiscovery?: {
    isSupported(): Promise<boolean>;
    start(): Promise<boolean>;
    stop(): void;
    hasWifi(): Promise<boolean>;
    // O `NativeEventEmitter` exige-os no tipo: sem eles, os eventos nunca são
    // registados e o JS não dá erro nenhum — é o mesmo motivo do override
    // `addListener` no lado Kotlin.
    addListener(event: string): void;
    removeListeners(count: number): void;
  };
};

/** `true` onde há `NsdManager` (isto é, Android). */
export function isSupported(): boolean {
  return Platform.OS === 'android' && !!nativeMdns;
}

export class MdnsDiscovery {
  private emitter: NativeEventEmitter | null = null;
  private cbs: DiscoveryCallbacks | null = null;
  private running = false;

  get isRunning(): boolean {
    return this.running;
  }

  async start(cbs: DiscoveryCallbacks): Promise<void> {
    if (!nativeMdns) {
      cbs.onError('Descoberta por mDNS só existe no Android.');
      return;
    }
    this.stop();
    this.cbs = cbs;

    // O aviso do WiFi vem **antes** de arrancar. Um `NsdManager` sem multicast
    // não dá erro: devolve uma lista silenciosamente vazia, e o utilizador
    // fica a olhar para "nenhum PC encontrado" sem nenhuma pista de porquê.
    const wifi = await nativeMdns.hasWifi().catch(() => false);
    if (!wifi) {
      cbs.onError(
        'O WiFi do telemóvel está desligado. O mDNS precisa dele para ' +
          'multicast — liga o WiFi, mesmo que o PC esteja noutra máquina.'
      );
    }

    this.emitter = new NativeEventEmitter(nativeMdns);
    this.emitter.addListener('found', (ev: { service?: any }) => {
      const s = ev?.service;
      if (!s || !s.host) return;
      const peer: DiscoveredPeer = {
        name: String(s.name || ''),
        host: String(s.host),
        port: Number(s.port) || 8765,
      };
      if (s.txt_v) peer.version = String(s.txt_v);
      if (s.txt_id) peer.id = String(s.txt_id);
      cbs.onFound(peer);
    });
    this.emitter.addListener('lost', (ev: { name?: string }) => {
      if (ev?.name) cbs.onLost(String(ev.name));
    });
    this.emitter.addListener('error', (ev: { error?: string }) => {
      cbs.onError(String(ev?.error || 'Erro na descoberta mDNS.'));
    });
    this.emitter.addListener('state', (ev: { state?: string }) => {
      this.running = ev?.state === 'running';
    });

    try {
      await nativeMdns.start();
      this.running = true;
    } catch (e: any) {
      cbs.onError(e?.message || 'A descoberta mDNS não arrancou.');
    }
  }

  stop(): void {
    if (this.emitter) {
      this.emitter.removeAllListeners('found');
      this.emitter.removeAllListeners('lost');
      this.emitter.removeAllListeners('error');
      this.emitter.removeAllListeners('state');
      this.emitter = null;
    }
    nativeMdns?.stop();
    this.running = false;
    this.cbs = null;
  }
}

export const mdns = new MdnsDiscovery();
