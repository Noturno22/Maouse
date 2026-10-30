import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  PanResponder,
  Platform,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import { remote } from '../services/remoteTransport';
import { CODE_LEN, codeCompleto, normalizeCode } from '../services/pairingCode';
import {
  BlePeer,
  DiscoveredPeer,
  useRemoteStore,
} from '../store/remote';

type ConnectTarget =
  | { kind: 'wifi'; peer: DiscoveredPeer }
  | { kind: 'ble'; peer: BlePeer };

interface Props {
  onBack: () => void;
}

interface TouchPos {
  x: number;
  y: number;
}

const ACCENT = '#50C8FF';
const PANEL = '#1f1f1f';
const KEY_BG = '#2a2a2a';
const BORDER = '#333333';

const DRAG_HOLD_MS = 380;
// Deslocamento total, em píxeis de ecrã, a partir do qual o gesto passa a
// contar como arrasto. A tremedeira normal do dedo num toque fica abaixo
// disto, portanto não desloca o cursor nem descarta o clique.
const TAP_SLOP_PX = 12;
const TAP_DECISION_DEADZONE = 1.5;

export default function RemoteScreen({ onBack }: Props) {
  const {
    code,
    forwardGestures,
    status,
    screen,
    error,
    scanning,
    blePeers,
    peers,
    discovering,
    mdnsRunning,
    lastTransport,
    lastPeerHost,
    lastPeerPort,
    lastBleAddress,
    stopDiscover,
    saveConfig,
    setForwardGestures,
    disconnect,
    discover,
    scanBle,
    connectBle,
    connectPeer,
  } = useRemoteStore();

  const [codeDraft, setCodeDraft] = useState<string>(code);
  const kbBufRef = useRef('');
  const [kbText, setKbText] = useState('');
  const autoAttemptRef = useRef('');
  const manualStopRef = useRef(false);

  const connected = status === 'connected';
  const busy = status === 'connecting';
  const codeOk = codeCompleto(codeDraft);

  useEffect(() => {
    setCodeDraft((v: string) => v || code);
  }, [code]);

  // O código fica guardado assim que está completo, mesmo que ainda não haja
  // PC à vista: reabrir a app não obriga a escrevê-lo outra vez.
  useEffect(() => {
    if (codeOk) void saveConfig({ code: codeDraft });
  }, [codeOk, codeDraft, saveConfig]);

  // Sair da tela tem de parar a procura. O `NsdManager` é um registo nativo
  // que vive para sempre: sem isto, voltar a abrir a tela reencontra a procura
  // anterior a correr, os peers accumulate-se aos poucos entre visitas, e o
  // `NativeEventEmitter` continua a emitir para um componente que já não
  // existe — que em Android é uma `IllegalStateException` de acesso a um
  // CatalystInstance destruído, e só quando o utilizador abre a tela outra vez.
  // A procura arranca sozinha porque o ecrã só pede o código: exigir um toque
  // em "procurar" para o PC aparecer era um segundo passo escondido.
  useEffect(() => {
    void discover();
    return () => stopDiscover();
  }, [discover, stopDiscover]);

  const target = useMemo<ConnectTarget | null>(() => {
    const lastWifi = peers.find(
      (p: DiscoveredPeer) =>
        p.host === lastPeerHost && String(p.port) === String(lastPeerPort)
    );
    const lastBle = blePeers.find((p: BlePeer) => p.address === lastBleAddress);

    if (lastTransport === 'ble' && lastBle) return { kind: 'ble', peer: lastBle };
    if (lastTransport === 'wifi' && lastWifi) {
      return { kind: 'wifi', peer: lastWifi };
    }
    if (lastWifi) return { kind: 'wifi', peer: lastWifi };
    if (lastBle) return { kind: 'ble', peer: lastBle };
    // Sem histórico: só há escolha automática quando só um PC respondeu. Com
    // vários, escolher por conta própria podia ligar ao PC errado; nesse caso
    // o utilizador toca no nome do PC que quer.
    if (peers.length === 1) return { kind: 'wifi', peer: peers[0] };
    if (blePeers.length === 1) return { kind: 'ble', peer: blePeers[0] };
    return null;
  }, [
    peers,
    blePeers,
    lastTransport,
    lastPeerHost,
    lastPeerPort,
    lastBleAddress,
  ]);

  const connectTo = useCallback(
    (next: ConnectTarget) => {
      void (async () => {
        await saveConfig({ code: codeDraft });
        if (next.kind === 'wifi') connectPeer(next.peer);
        else await connectBle(next.peer.address, next.peer.name);
      })();
    },
    [codeDraft, saveConfig, connectPeer, connectBle]
  );

  // Liga sozinho quando o código está completo e há um PC encontrado. A chave
  // impede que o mesmo par (código, PC) seja tentado em ciclo: um código errado
  // não pode gastar tentativas a cada anúncio mDNS, e um PC inalcançável não
  // pode abrir uma ligação por segundo.
  useEffect(() => {
    if (!codeOk || !target || manualStopRef.current) return;
    if (status !== 'disconnected' && status !== 'error') return;
    const key = `${codeDraft}|${target.kind}|${
      target.kind === 'wifi'
        ? `${target.peer.host}:${target.peer.port}`
        : target.peer.address
    }`;
    if (autoAttemptRef.current === key) return;
    autoAttemptRef.current = key;
    connectTo(target);
  }, [codeOk, codeDraft, target, status, connectTo]);

  const resetAuto = useCallback(() => {
    manualStopRef.current = false;
    autoAttemptRef.current = '';
  }, []);

  const onPeerPress = useCallback(
    (next: ConnectTarget) => {
      resetAuto();
      connectTo(next);
    },
    [connectTo, resetAuto]
  );

  const onDisconnectPress = useCallback(() => {
    // Desligar à mão não pode ser desfeito no instante seguinte pelo auto-ligar:
    // o utilizador disse que não, e a lista de PCs ainda está em memória.
    manualStopRef.current = true;
    disconnect();
  }, [disconnect]);

  const haptic = useCallback(() => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
  }, []);

  const onKbChange = useCallback(
    (v: string) => {
      const prev = kbBufRef.current;
      kbBufRef.current = v;
      setKbText(v);
      if (!remote.isConnected) return;
      if (v.length < prev.length) {
        for (let i = prev.length - v.length; i > 0; i--) remote.key('backspace');
      } else if (v.length > prev.length) {
        const added = v.slice(prev.length);
        let batch = '';
        for (const ch of added) {
          if (ch === '\n') {
            if (batch) { remote.text(batch); batch = ''; }
            remote.key('enter');
          } else {
            batch += ch;
          }
        }
        if (batch) remote.text(batch);
      }
    },
    []
  );

  const clearKb = useCallback(() => {
    kbBufRef.current = '';
    setKbText('');
  }, []);

  const onKbEnter = useCallback(() => {
    if (remote.isConnected) remote.key('enter');
    clearKb();
  }, [clearKb]);

  const onKbBackspace = useCallback(() => {
    if (remote.isConnected) remote.key('backspace');
  }, []);

  const padRef = useRef<View>(null);

  const touchState = useRef({
    count: 0,
    last: new Map<number, TouchPos>(),
    startTime: 0,
    startX: 0,
    startY: 0,
    moved: false,
    holdArmed: false,
    dragging: false,
    scrollAcc: 0,
  });

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderTerminationRequest: () => false,
      onPanResponderGrant: (evt) => {
        const ts = touchState.current;
        ts.count = evt.nativeEvent.touches.length;
        ts.startTime = Date.now();
        ts.moved = false;
        ts.holdArmed = false;
        ts.dragging = false;
        ts.scrollAcc = 0;
        ts.last.clear();
        for (const touch of evt.nativeEvent.touches as any[]) {
          ts.last.set(touch.identifier, { x: touch.pageX, y: touch.pageY });
        }
        // Origem do gesto: o limiar de arrasto mede a distância a este ponto,
        // e não a distância entre dois eventos (que a tremedeira dispara).
        const first = evt.nativeEvent.touches[0] as any;
        if (first) {
          ts.startX = first.pageX;
          ts.startY = first.pageY;
        }
      },
      onPanResponderMove: (evt) => {
        const touches = evt.nativeEvent.touches as any[];
        const ts = touchState.current;
        const count = touches.length;

        if (count !== ts.count) {
          if (ts.dragging) {
            remote.release('left');
            ts.dragging = false;
          }
          ts.count = count;
          ts.last.clear();
          for (const touch of touches) {
            ts.last.set(touch.identifier, { x: touch.pageX, y: touch.pageY });
          }
          return;
        }

        if (count === 1) {
          const touch = touches[0];
          const prev = ts.last.get(touch.identifier);
          const cur = { x: touch.pageX, y: touch.pageY };
          ts.last.set(touch.identifier, cur);
          if (prev) {
            const dx = cur.x - prev.x;
            const dy = cur.y - prev.y;
            const now = Date.now();
            if (Math.hypot(cur.x - ts.startX, cur.y - ts.startY) > TAP_SLOP_PX) {
              ts.moved = true;
            }
            // Arrasto exige parar E depois mexer: armar ao fim de DRAG_HOLD_MS
            // sem sair do limiar, mas carregar o botão só quando o dedo começa
            // a mexer. Assim soltar sem ter mexido é um toque no ponto tocado, e
            // não um clique na posição em que o cursor por acaso estava.
            if (!ts.moved && !ts.holdArmed && now - ts.startTime > DRAG_HOLD_MS) {
              ts.holdArmed = true;
              haptic();
            }
            if (!ts.dragging && ts.holdArmed && ts.moved) {
              ts.dragging = true;
              remote.press('left');
            }
            // Dead zone: dentro do limiar não se mexe o cursor. `ts.last` já foi
            // reancorado acima, por isso a travessia do limiar não dá um salto.
            if ((ts.dragging || ts.moved) && (dx !== 0 || dy !== 0)) {
              remote.move(dx, dy);
            }
          }
        } else if (count > 1) {
          let dy = 0;
          for (const touch of touches) {
            const prev = ts.last.get(touch.identifier);
            const cur = { x: touch.pageX, y: touch.pageY };
            ts.last.set(touch.identifier, cur);
            if (prev) dy += cur.y - prev.y;
          }
          dy /= count;
          if (Math.abs(dy) > 0.5) ts.moved = true;
          if (dy !== 0) {
            ts.scrollAcc += dy;
            const step = Math.round(ts.scrollAcc);
            if (step !== 0) {
              ts.scrollAcc -= step;
              remote.scroll(0, step);
            }
          }
        }
      },
      onPanResponderRelease: (evt) => {
        const ts = touchState.current;
        if (ts.dragging) {
          remote.release('left');
          ts.dragging = false;
        } else if (!ts.moved) {
          // Sem limite de tempo: um toque deliberado e lento também é toque.
          if (ts.count === 1) {
            // O toque é RELATIVO, como num touchpad de portátil: clica onde o
            // cursor está, não onde o dedo toca. A versão anterior mandava as
            // coordenadas absolutas do toque (`gesture('tap', x, y)`), e o PC
            // fazia `move_to` antes de clicar — o cursor saltava do sítio onde
            // o dedo o tinha pousado para o ponto tocado no pad, que não tem
            // relação nenhuma com ele. O arrasto já era relativo; o toque
            // agora é-o também, e o clique fica onde o utilizador o deixou.
            remote.click('left', 1);
            haptic();
          } else if (ts.count === 2) {
            remote.click('right', 1);
            haptic();
          } else if (ts.count >= 3) {
            remote.click('middle', 1);
            haptic();
          }
        }
        ts.last.clear();
        ts.count = 0;
        ts.moved = false;
        ts.holdArmed = false;
        ts.scrollAcc = 0;
        ts.startX = 0;
        ts.startY = 0;
      },
      onPanResponderTerminate: () => {
        const ts = touchState.current;
        if (ts.dragging) {
          remote.release('left');
          ts.dragging = false;
        }
        ts.last.clear();
        ts.count = 0;
        ts.moved = false;
        ts.holdArmed = false;
        ts.scrollAcc = 0;
        ts.startX = 0;
        ts.startY = 0;
      },
    })
  ).current;

  const keyBtn = (label: string, onPress: () => void, a11y?: string) => (
    <TouchableOpacity
      key={label + (a11y ?? '')}
      accessibilityLabel={a11y ?? label}
      style={styles.keyButton}
      onPress={onPress}
    >
      <Text style={styles.keyButtonText}>{label}</Text>
    </TouchableOpacity>
  );

  const renderConnected = () => (
    <View style={styles.connectedWrap}>
      <View style={styles.touchpadWrap}>
        <View
          ref={padRef}
          style={styles.touchpad}
          accessible
          accessibilityRole="none"
          accessibilityLabel="Rato — área de toque"
          accessibilityHint="Um dedo move o cursor, toque clica onde o cursor está, manter arrasta, dois dedos faz scroll."
          {...panResponder.panHandlers}
        >
          <Text style={styles.touchpadHint}>
            1 dedo = mover · toque = clique no ponto · manter = arrastar · 2 dedos = scroll · 2/3 dedos tocar = dir/meio
          </Text>
          <View style={styles.screenPill}>
            <Text style={styles.screenPillText}>
              {screen ? `${screen.w}×${screen.h}` : '…'}
            </Text>
          </View>
        </View>
      </View>

      <View style={styles.kbdPanel}>
        <View style={styles.textRow}>
          <TextInput
            style={styles.textInput}
            value={kbText}
            onChangeText={onKbChange}
            onSubmitEditing={onKbEnter}
            placeholder="Escrever em tempo real no PC…"
            placeholderTextColor="#9E9E9E"
            autoCapitalize="none"
            autoCorrect={false}
            spellCheck={false}
            blurOnSubmit={false}
            returnKeyType="go"
          />
          <View style={styles.textActions}>
            <TouchableOpacity
              style={styles.actionSmall}
              onPress={onKbBackspace}
              accessibilityLabel="Apagar"
            >
              <Text style={styles.actionSmallText}>⌫</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.actionSmall}
              onPress={clearKb}
              accessibilityLabel="Limpar texto escrito"
            >
              <Text style={styles.actionSmallText}>✕</Text>
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.keyRow}>
          {keyBtn('ESC', () => remote.key('esc'), 'Tecla Esc')}
          {keyBtn('WIN', () => remote.key('win'), 'Tecla Windows')}
          {keyBtn('TAB', () => remote.key('tab'), 'Tecla Tab')}
          {keyBtn('ENTER', () => remote.key('enter'), 'Tecla Enter')}
          {keyBtn('⌫', () => remote.key('backspace'), 'Apagar')}
        </View>

        <View style={styles.keyRow}>
          {keyBtn('←', () => remote.key('arrow_left'), 'Seta esquerda')}
          {keyBtn('↑', () => remote.key('arrow_up'), 'Seta para cima')}
          {keyBtn('↓', () => remote.key('arrow_down'), 'Seta para baixo')}
          {keyBtn('→', () => remote.key('arrow_right'), 'Seta direita')}
          {keyBtn('␣', () => remote.key('space'), 'Barra de espaço')}
        </View>

        <View style={styles.keyRow}>
          {keyBtn('↩', () => remote.click('left', 1), 'Clique esquerdo')}
          {keyBtn('Duplo', () => remote.click('left', 2), 'Duplo clique')}
          {keyBtn('Dir', () => remote.click('right', 1), 'Clique direito')}
          {keyBtn('Med', () => remote.click('middle', 1), 'Clique do meio')}
          <TouchableOpacity
            style={styles.stateButton}
            onPress={onDisconnectPress}
            accessibilityLabel="Desligar do PC"
          >
            <Text style={styles.stateButtonText}>DESLIGAR</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.keyRow}>
          {keyBtn('🔉', () => remote.media('volume_down'), 'Diminuir volume')}
          {keyBtn('🔊', () => remote.media('volume_up'), 'Aumentar volume')}
          {keyBtn('🔇', () => remote.media('mute'), 'Silenciar')}
          {keyBtn('⏯', () => remote.media('play_pause'), 'Reproduzir ou pausar')}
        </View>
      </View>
    </View>
  );

  // Procura o PC por mDNS ou por Bluetooth.
  //
  // As duas vias ficam lado a lado porque resolvem problemas diferentes: o
  // mDNS acha o PC em qualquer rede onde circule, e o BLE funciona sem rede
  // nenhuma — que é o caso de uma rede de empresa onde o multicast está
  // bloqueado, ou de um telemóvel em dados móveis com o PC em Ethernet.
  const renderDiscoveryPanel = () => (
    <View style={styles.discoveryPanel}>
      <View style={styles.discoveryRow}>
        <TouchableOpacity
          style={styles.discoveryBtn}
          onPress={() => {
            manualStopRef.current = false;
            if (mdnsRunning || discovering) stopDiscover();
            else void discover();
          }}
        >
          {discovering ? (
            <ActivityIndicator color={ACCENT} />
          ) : (
            <Text style={styles.discoveryBtnText}>
              {mdnsRunning ? 'PARAR PROCURA' : 'PROCURAR NA REDE'}
            </Text>
          )}
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.discoveryBtn}
          onPress={() => {
            manualStopRef.current = false;
            void scanBle(8);
          }}
          disabled={scanning}
        >
          {scanning ? (
            <ActivityIndicator color={ACCENT} />
          ) : (
            <Text style={styles.discoveryBtnText}>PROCURAR POR BLUETOOTH</Text>
          )}
        </TouchableOpacity>
      </View>

      {peers.map((p: DiscoveredPeer) => (
        <TouchableOpacity
          key={`${p.host}:${p.port}`}
          style={[styles.peerRow, !codeOk && styles.peerRowDisabled]}
          disabled={!codeOk}
          onPress={() => onPeerPress({ kind: 'wifi', peer: p })}
        >
          <Text style={styles.peerName}>{p.name || 'PC Mãouse'}</Text>
        </TouchableOpacity>
      ))}

      {blePeers.map((p: BlePeer) => (
        <TouchableOpacity
          key={p.address}
          style={[styles.peerRow, !codeOk && styles.peerRowDisabled]}
          disabled={!codeOk}
          onPress={() => onPeerPress({ kind: 'ble', peer: p })}
        >
          <Text style={styles.peerName}>{p.name || 'PC Mãouse'}</Text>
        </TouchableOpacity>
      ))}

      {peers.length === 0 && blePeers.length === 0 && !scanning && !discovering ? (
        <Text style={styles.discoveryHint}>
          {codeOk
            ? 'Código completo. À procura do PC na mesma rede…'
            : 'O PC tem de estar na mesma rede Wi‑Fi. Se a rede bloquear a descoberta, procura por Bluetooth.'}
        </Text>
      ) : null}
    </View>
  );

  const renderConnectForm = () => (
    <View style={styles.form}>
      <Text style={styles.title}>Ligar ao PC</Text>
      <Text style={styles.subtitle}>
        Escreve o código de 6 dígitos que o Mãouse mostra no PC, em Definições
        → Controlo remoto. O telemóvel encontra o PC sozinho.
      </Text>

      <Text style={styles.label}>Código do PC</Text>
      <TextInput
        style={[styles.input, styles.codeInput, !codeOk && styles.inputCurto]}
        value={codeDraft}
        autoFocus
        // O teclado de números não tem '#', '%' nem '@', e num campo de
        // emparelhamento um símbolo não faz sentido: o teclado do telemóvel é
        // maior do que o campo, e é preciso ver o que se escreve.
        keyboardType="number-pad"
        inputMode="numeric"
        maxLength={CODE_LEN}
        placeholder={'·'.repeat(CODE_LEN)}
        placeholderTextColor="#4A4A4A"
        onChangeText={(v) => {
          const limpo = normalizeCode(v);
          setCodeDraft(limpo);
          // Um código novo é uma tentativa nova: rearma o auto-ligar e limpa o
          // "desligar à mão", senão o ecrã ficava a olhar para o PC sem ligar.
          resetAuto();
        }}
        autoCorrect={false}
        autoCapitalize="none"
      />
      <Text style={styles.codeHint}>
        {codeOk
          ? 'Código completo — a ligação é automática quando o PC aparecer.'
          : `São ${CODE_LEN} dígitos. Lê-os no PC, em Definições → Controlo remoto.`}
      </Text>

      <Text style={[styles.label, styles.labelDiscovery]}>PCs encontrados</Text>
      {renderDiscoveryPanel()}

      <View style={styles.switchRow}>
        <Text style={styles.switchLabel}>Gestos da câmara comandam o PC</Text>
        <Switch
          value={forwardGestures}
          onValueChange={(v) => setForwardGestures(v)}
          trackColor={{ false: BORDER, true: ACCENT }}
          thumbColor="#FFF"
        />
      </View>

      {error ? <Text style={styles.errorText}>{error}</Text> : null}

      {busy ? (
        <View style={styles.busyRow}>
          <ActivityIndicator color={ACCENT} />
          <Text style={styles.busyText}>A ligar…</Text>
        </View>
      ) : null}

      <Text style={styles.hint}>
        Telemóvel e PC têm de estar na mesma rede Wi‑Fi. O Bluetooth é a
        alternativa quando a rede bloqueia a descoberta.
      </Text>
    </View>
  );

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.header}>
        <TouchableOpacity
            style={styles.headerButton}
            onPress={onBack}
            accessibilityLabel="Voltar"
          >
            <Text style={styles.headerButtonText}>◀</Text>
          </TouchableOpacity>
        <Text style={styles.headerTitle}>PC Remoto</Text>
        <View
          style={[
            styles.statusPill,
            {
              backgroundColor: connected ? 'rgba(90,220,90,0.25)' : 'rgba(0,0,0,0.6)',
            },
          ]}
        >
          <Text
            style={[
              styles.statusText,
              { color: connected ? '#5ADC5A' : '#FFF' },
            ]}
          >
            {connected ? 'LIGADO' : busy ? 'A LIGAR…' : 'SEM LIGAÇÃO'}
          </Text>
        </View>
      </View>

      {connected ? (
        renderConnected()
      ) : (
        // O formulário ganhou o painel de descoberta, e a lista de PCs
        // encontrados cresce a cada anúncio. Num ecrã pequeno o formulário
        // passa do fundo — e o botão LIGAR, que é o que se quer alcançar,
        // é o último.
        <ScrollView
          style={styles.formScroll}
          contentContainerStyle={styles.form}
          keyboardShouldPersistTaps="handled"
        >
          {renderConnectForm()}
        </ScrollView>
      )}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
    paddingTop: 50,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingBottom: 12,
  },
  headerButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: PANEL,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerButtonText: {
    color: '#FFF',
    fontSize: 16,
  },
  headerTitle: {
    flex: 1,
    color: '#FFF',
    fontSize: 20,
    fontWeight: '700',
    marginLeft: 12,
  },
  statusPill: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  statusText: {
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 0.5,
  },

  formScroll: {
    flex: 1,
  },
  form: {
    flexGrow: 1,
    paddingHorizontal: 24,
    paddingTop: 8,
    paddingBottom: 32,
  },
  discoveryPanel: {
    marginBottom: 16,
    padding: 12,
    borderRadius: 10,
    backgroundColor: PANEL,
    borderWidth: 1,
    borderColor: BORDER,
  },
  discoveryRow: {
    flexDirection: 'row',
    gap: 8,
  },
  discoveryBtn: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: ACCENT,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 40,
  },
  discoveryBtnText: {
    color: ACCENT,
    fontSize: 11,
    fontWeight: '700',
    textAlign: 'center',
  },
  peerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    marginTop: 8,
    paddingHorizontal: 10,
    borderRadius: 8,
    backgroundColor: KEY_BG,
  },
  peerName: {
    color: '#FFF',
    fontSize: 14,
    fontWeight: '600',
    flexShrink: 1,
  },
  // Sem código completo não há o que ligar; a linha fica visível mas apagada,
  // para o PC encontrado não parecer um botão avariado.
  peerRowDisabled: {
    opacity: 0.4,
  },
  discoveryHint: {
    color: '#9E9E9E',
    fontSize: 11,
    lineHeight: 16,
    marginTop: 10,
  },
  title: {
    color: '#FFF',
    fontSize: 24,
    fontWeight: '700',
    marginBottom: 8,
  },
  subtitle: {
    color: '#AAA',
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 20,
  },
  label: {
    color: '#DDD',
    fontSize: 13,
    fontWeight: '600',
    marginBottom: 6,
    marginTop: 12,
  },
  input: {
    backgroundColor: PANEL,
    borderWidth: 1,
    borderColor: BORDER,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: '#FFF',
    fontSize: 16,
  },
  // O código lê-se à distância e à pressa: 28 px, mono, e o mesmo tamanho
  // para os seis dígitos, para não parecer um campo de texto qualquer.
  codeInput: {
    fontSize: 28,
    fontWeight: '700',
    letterSpacing: 14,
    textAlign: 'center',
    paddingVertical: 14,
    // A seguir à última letra: sem isto, o `letterSpacing` também entra no
    // fim e o último dígito fica a olhar para fora do meio do campo.
    paddingRight: 26,
  },
  labelDiscovery: {
    marginTop: 20,
  },
  inputCurto: {
    borderColor: '#4A4A4A',
  },
  codeHint: {
    color: '#9E9E9E',
    fontSize: 12,
    lineHeight: 17,
    marginTop: 8,
  },
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 20,
  },
  switchLabel: {
    color: '#DDD',
    fontSize: 14,
    flex: 1,
    marginRight: 12,
  },
  errorText: {
    color: '#FF6B6B',
    fontSize: 14,
    marginTop: 14,
  },
  busyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 24,
  },
  busyText: {
    color: '#AAA',
    fontSize: 15,
    marginLeft: 10,
  },
  hint: {
    color: '#9E9E9E',
    fontSize: 12,
    lineHeight: 17,
    marginTop: 20,
  },

  connectedWrap: {
    flex: 1,
  },
  touchpadWrap: {
    flex: 1,
    paddingHorizontal: 16,
    paddingBottom: 8,
  },
  touchpad: {
    flex: 1,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: ACCENT,
    backgroundColor: '#050505',
    justifyContent: 'center',
    alignItems: 'center',
  },
  touchpadHint: {
    color: '#9E9E9E',
    fontSize: 13,
    textAlign: 'center',
    paddingHorizontal: 20,
  },
  screenPill: {
    position: 'absolute',
    top: 12,
    right: 12,
    backgroundColor: PANEL,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  screenPillText: {
    color: '#DDD',
    fontSize: 12,
  },
  kbdPanel: {
    paddingHorizontal: 12,
    paddingBottom: 24,
  },
  textRow: {
    flexDirection: 'row',
    marginBottom: 10,
  },
  textInput: {
    flex: 1,
    backgroundColor: PANEL,
    borderWidth: 1,
    borderColor: BORDER,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    color: '#FFF',
    fontSize: 15,
    marginRight: 8,
  },
  actionButton: {
    width: 46,
    borderRadius: 10,
    backgroundColor: ACCENT,
    justifyContent: 'center',
    alignItems: 'center',
  },
  actionButtonText: {
    color: '#FFF',
    fontSize: 18,
    fontWeight: '700',
  },
  textActions: {
    flexDirection: 'row',
    marginLeft: 8,
  },
  actionSmall: {
    width: 44,
    height: 48,
    borderRadius: 10,
    backgroundColor: '#2a2a2a',
    borderWidth: 1,
    borderColor: BORDER,
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 6,
  },
  actionSmallText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '600',
  },
  keyRow: {
    flexDirection: 'row',
    marginBottom: 8,
    gap: 8,
  },
  keyButton: {
    flex: 1,
    minHeight: 48,
    backgroundColor: KEY_BG,
    borderWidth: 1,
    borderColor: BORDER,
    borderRadius: 10,
    paddingVertical: 11,
    justifyContent: 'center',
    alignItems: 'center',
  },
  keyButtonText: {
    color: '#FFF',
    fontSize: 14,
    fontWeight: '600',
  },
  stateButton: {
    flex: 1,
    minHeight: 48,
    backgroundColor: 'rgba(255,86,86,0.25)',
    borderWidth: 1,
    borderColor: '#FF5656',
    borderRadius: 10,
    paddingVertical: 11,
    justifyContent: 'center',
    alignItems: 'center',
  },
  stateButtonText: {
    color: '#FF8A8A',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
});