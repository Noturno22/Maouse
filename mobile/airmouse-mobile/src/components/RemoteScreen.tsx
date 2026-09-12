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

interface TouchPos {
  x: number;
  y: number;
}

const ACCENT = '#50C8FF';
const PANEL = '#1f1f1f';
const KEY_BG = '#2a2a2a';
const BORDER = '#333333';

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
  const [draftText, setDraftText] = useState('');

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

  const onSendText = () => {
    const text = draftText.trim();
    if (!text) return;
    remote.text(text);
    setDraftText('');
    haptic();
  };

  const layoutRef = useRef<Size>({ w: 1, h: 1 });
  const touchState = useRef({
    count: 0,
    last: new Map<number, TouchPos>(),
    startTime: 0,
    moved: false,
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
        ts.scrollAcc = 0;
        ts.last.clear();
        for (const touch of evt.nativeEvent.touches as any[]) {
          ts.last.set(touch.identifier, { x: touch.pageX, y: touch.pageY });
        }
      },
      onPanResponderMove: (evt) => {
        const touches = evt.nativeEvent.touches as any[];
        const ts = touchState.current;
        const count = touches.length;

        if (count !== ts.count) {
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
            if (Math.abs(dx) > 1 || Math.abs(dy) > 1) ts.moved = true;
            if (ts.moved && (dx !== 0 || dy !== 0)) remote.move(dx, dy);
          }
        } else if (count > 1) {
          // Scroll vertical com dois dedos: média das deltas de cada dedo.
          let dy = 0;
          for (const touch of touches) {
            const prev = ts.last.get(touch.identifier);
            const cur = { x: touch.pageX, y: touch.pageY };
            ts.last.set(touch.identifier, cur);
            if (prev) dy += cur.y - prev.y;
          }
          dy /= count;
          if (Math.abs(dy) > 0.5) ts.moved = true;
          if (ts.moved && dy !== 0) {
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
        const dur = Date.now() - ts.startTime;
        if (ts.count === 1 && !ts.moved && dur < 260) {
          const all = evt.nativeEvent.touches as any[];
          const changed = (evt.nativeEvent as any).changedTouches;
          const touch = (changed && changed.length ? changed[0] : all[0]) as any;
          let x = 0.5;
          let y = 0.5;
          if (touch) {
            x = Math.max(0, Math.min(1, touch.locationX / layoutRef.current.w));
            y = Math.max(0, Math.min(1, touch.locationY / layoutRef.current.h));
          }
          remote.gesture('tap', x, y);
          haptic();
        }
        ts.last.clear();
        ts.count = 0;
        ts.moved = false;
        ts.scrollAcc = 0;
      },
      onPanResponderTerminate: () => {
        const ts = touchState.current;
        ts.last.clear();
        ts.count = 0;
        ts.moved = false;
        ts.scrollAcc = 0;
      },
    })
  ).current;

  const keyBtn = (label: string, onPress: () => void) => (
    <TouchableOpacity key={label} style={styles.keyButton} onPress={onPress}>
      <Text style={styles.keyButtonText}>{label}</Text>
    </TouchableOpacity>
  );

  const renderConnected = () => (
    <View style={styles.connectedWrap}>
      <View style={styles.touchpadWrap}>
        <View
          style={styles.touchpad}
          onLayout={(e) => {
            layoutRef.current = { w: e.nativeEvent.layout.width, h: e.nativeEvent.layout.height };
          }}
          {...panResponder.panHandlers}
        >
          <Text style={styles.touchpadHint}>1 dedo = mover · toque = clique · 2 dedos = scroll</Text>
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
            value={draftText}
            onChangeText={setDraftText}
            placeholder="Escrever no PC…"
            placeholderTextColor="#777"
            autoCapitalize="none"
            autoCorrect={false}
            returnKeyType="send"
            onSubmitEditing={onSendText}
          />
          <TouchableOpacity style={styles.actionButton} onPress={onSendText}>
            <Text style={styles.actionButtonText}>↵</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.keyRow}>
          {keyBtn('ESC', () => remote.key('esc'))}
          {keyBtn('WIN', () => remote.key('win'))}
          {keyBtn('TAB', () => remote.key('tab'))}
          {keyBtn('ENTER', () => remote.key('enter'))}
          {keyBtn('⌫', () => remote.key('backspace'))}
        </View>

        <View style={styles.keyRow}>
          {keyBtn('←', () => remote.key('arrow_left'))}
          {keyBtn('↑', () => remote.key('arrow_up'))}
          {keyBtn('↓', () => remote.key('arrow_down'))}
          {keyBtn('→', () => remote.key('arrow_right'))}
          {keyBtn('␣', () => remote.key('space'))}
        </View>

        <View style={styles.keyRow}>
          {keyBtn('↩', () => remote.click('left', 1))}
          {keyBtn('Duplo', () => remote.click('left', 2))}
          {keyBtn('Dir', () => remote.click('right', 1))}
          {keyBtn('Med', () => remote.click('middle', 1))}
          <TouchableOpacity
            style={styles.stateButton}
            onPress={disconnect}
          >
            <Text style={styles.stateButtonText}>DESLIGAR</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.keyRow}>
          {keyBtn('🔉', () => remote.media('volume_down'))}
          {keyBtn('🔊', () => remote.media('volume_up'))}
          {keyBtn('🔇', () => remote.media('mute'))}
          {keyBtn('⏯', () => remote.media('play_pause'))}
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
        placeholderTextColor="#777"
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
        placeholderTextColor="#777"
        keyboardType="number-pad"
      />

      <Text style={styles.label}>Token</Text>
      <TextInput
        style={styles.input}
        value={tokenDraft}
        onChangeText={setTokenDraft}
        placeholder="Token mostrado no PC"
        placeholderTextColor="#777"
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
        <TouchableOpacity style={styles.headerButton} onPress={onBack}>
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
    width: 40,
    height: 40,
    borderRadius: 20,
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
    color: '#FFF',
    fontSize: 16,
    fontWeight: '700',
    letterSpacing: 1,
  },
  hint: {
    color: '#777',
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
    color: '#777',
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
  keyRow: {
    flexDirection: 'row',
    marginBottom: 8,
    gap: 8,
  },
  keyButton: {
    flex: 1,
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