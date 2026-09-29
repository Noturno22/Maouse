import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  PanResponder,
  Platform,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import { remote } from '../services/remoteClient';
import { useRemoteStore } from '../store/remote';

interface Props {
  onBack: () => void;
}

interface Size {
  w: number;
  h: number;
}

// O touchpad também sabe onde está na janela. Sem isto, o toque tinha de ser
// convertido com `locationX`, que é relativo à vista que recebeu o toque — e
// como o touchpad tem o texto de dica e o distintivo do ecrã por cima, tocar
// em cima deles mandava o cursor para outra direção.
interface PadRect extends Size {
  pageX: number;
  pageY: number;
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

export default function RemoteScreen({ onBack }: Props) {
  const {
    host,
    port,
    token,
    forwardGestures,
    status,
    screen,
    error,
    saveConfig,
    setForwardGestures,
    connect,
    disconnect,
  } = useRemoteStore();

  const [hostDraft, setHostDraft] = useState(host);
  const [portDraft, setPortDraft] = useState(port);
  const [tokenDraft, setTokenDraft] = useState(token);
  const kbBufRef = useRef('');
  const [kbText, setKbText] = useState('');

  const connected = status === 'connected';
  const busy = status === 'connecting';

  useEffect(() => {
    setHostDraft((v) => v || host);
    setPortDraft((v) => v || port);
    setTokenDraft((v) => v || token);
  }, [host, port, token]);

  const haptic = useCallback(() => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
  }, []);

  const onConnectPress = () => {
    saveConfig({
      host: hostDraft,
      port: portDraft,
      token: tokenDraft,
    });
    connect();
  };

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

  const layoutRef = useRef<PadRect>({ w: 1, h: 1, pageX: 0, pageY: 0 });
  const padRef = useRef<View>(null);

  // `measureInWindow` dá a posição do touchpad na janela, para depoisconverter
  // `pageX`/`pageY` (que são absolutos) em coordenadas relativas ao touchpad.
  const measurePad = useCallback(() => {
    const node = padRef.current;
    if (!node) return;
    node.measureInWindow((x, y, w, h) => {
      if (w > 0 && h > 0) {
        layoutRef.current = { w, h, pageX: x, pageY: y };
      }
    });
  }, []);
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
        // Remedir a cada toque: o teclado abrir/fechar ou o telefone rodar
        // mudam a posição do touchpad sem necessariamente mudar o tamanho, e o
        // `onLayout` só dispara quando o tamanho muda.
        measurePad();
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
            const all = evt.nativeEvent.touches as any[];
            const changed = (evt.nativeEvent as any).changedTouches;
            const touch = (changed && changed.length ? changed[0] : all[0]) as any;
            let x = 0.5;
            let y = 0.5;
            if (touch) {
              // `pageX`/`pageY` são absolutos e não dependem de qual vista
              // recebeu o toque. `locationX` depende — e o touchpad tem o texto
              // de dica e o distintivo do ecrã por cima, portanto tocar neles
              // mandava o cursor para outra direção.
              const pad = layoutRef.current;
              x = Math.max(0, Math.min(1, (touch.pageX - pad.pageX) / pad.w));
              y = Math.max(0, Math.min(1, (touch.pageY - pad.pageY) / pad.h));
            }
            remote.gesture('tap', x, y);
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
          onLayout={(e) => {
            const { width, height } = e.nativeEvent.layout;
            if (width > 0 && height > 0) {
              layoutRef.current = { ...layoutRef.current, w: width, h: height };
            }
            // A posição na janela só vem do `measureInWindow`, e é o que
            // permite acertar o ponto do toque.
            measurePad();
          }}
          accessible
          accessibilityRole="none"
          accessibilityLabel="Rato — área de toque"
          accessibilityHint="Um dedo move o cursor, toque faz clique, manter arrasta, dois dedos faz scroll."
          {...panResponder.panHandlers}
        >
          <Text style={styles.touchpadHint}>
            1 dedo = mover · toque = clique · manter = arrastar · 2 dedos = scroll · 2/3 dedos tocar = dir/meio
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
            onPress={disconnect}
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

  const renderConnectForm = () => (
    <View style={styles.form}>
      <Text style={styles.title}>Ligar ao PC</Text>
      <Text style={styles.subtitle}>
        No PC abre Definições → «Controlo remoto (mobile)» e copia o IP, a porta
        e o token que aparecem lá.
      </Text>

      <Text style={styles.label}>IP do PC</Text>
      <TextInput
        style={styles.input}
        value={hostDraft}
        onChangeText={setHostDraft}
        placeholder="ex.: 192.168.1.50"
        placeholderTextColor="#9E9E9E"
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType={Platform.OS === 'ios' ? 'numbers-and-punctuation' : 'default'}
      />

      <Text style={styles.label}>Porta</Text>
      <TextInput
        style={styles.input}
        value={portDraft}
        onChangeText={setPortDraft}
        placeholder="8765"
        placeholderTextColor="#9E9E9E"
        keyboardType="number-pad"
      />

      <Text style={styles.label}>Token</Text>
      <TextInput
        style={styles.input}
        value={tokenDraft}
        onChangeText={setTokenDraft}
        placeholder="Token mostrado no PC"
        placeholderTextColor="#9E9E9E"
        autoCapitalize="none"
        autoCorrect={false}
      />

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
      ) : (
        <TouchableOpacity style={styles.primaryButton} onPress={onConnectPress}>
          <Text style={styles.primaryButtonText}>LIGAR</Text>
        </TouchableOpacity>
      )}

      <Text style={styles.hint}>
        Para o WiFi externo / Internet: encaminha a porta {portDraft || '8765'} no
        router para este PC e liga a ws://IP-PÚBLICO:{portDraft || '8765'}.
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

      {connected ? renderConnected() : renderConnectForm()}
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

  form: {
    flex: 1,
    paddingHorizontal: 24,
    paddingTop: 8,
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
  primaryButton: {
    marginTop: 24,
    backgroundColor: ACCENT,
    borderRadius: 12,
    paddingVertical: 15,
    alignItems: 'center',
  },
  primaryButtonText: {
    color: '#003049',
    fontSize: 16,
    fontWeight: '700',
    letterSpacing: 1,
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