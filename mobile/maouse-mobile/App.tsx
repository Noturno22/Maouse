import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  Dimensions,
  Platform,
  StatusBar,
  NativeModules,
} from 'react-native';
import { Camera, useCameraDevice, useFrameProcessor, useCameraPermission, VisionCameraProxy } from 'react-native-vision-camera';
import { Worklets } from 'react-native-worklets-core';
import type { HandDetectionResult } from 'expo-vision-camera-v4-mediapipe';
import { useSettingsStore, useGestureStore } from './src/store';
import { GESTURE_LABELS, GESTURE_COLORS, HAND_CONNECTIONS } from './src/constants';
import { HandLandmarks } from './src/types/gesture';
import { GestureEngine, GestureResult } from './src/engine/gestures';
import { FilterPair2D, AccelCurve } from './src/engine/filters';
import { useProEntitlement } from './src/hooks/useProEntitlement';
import ProGate from './src/components/ProGate';
import RemoteScreen from './src/components/RemoteScreen';
import { useRemoteStore } from './src/store/remote';
import { remote } from './src/services/remoteClient';

const { TouchController, KeyboardController, SystemController } = NativeModules;

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

const MOVE_INTERVAL_MS = 33;
const TAP_THRESHOLD_MS = 450;
const PALM_BACK_FRAMES = 5;

function palmScale(lm: any[]): number {
  if (!lm || lm.length < 21) return 0;
  const wrist = lm[0];
  const mcp = lm[9];
  const dx = (wrist?.x ?? 0) - (mcp?.x ?? 0);
  const dy = (wrist?.y ?? 0) - (mcp?.y ?? 0);
  return Math.hypot(dx, dy);
}

function isOpenPalm(lm: any[]): boolean {
  if (!lm || lm.length < 21) return false;
  const pts: [number, number][] = lm.map((p: any) => [p.x, p.y]);
  const wrist = pts[0];
  const dist = (a: [number, number], b: [number, number]) =>
    Math.hypot(a[0] - b[0], a[1] - b[1]);
  if (dist(wrist, pts[9]) < 0.05) return false;
  const pairs: [number, number][] = [
    [8, 6],
    [12, 10],
    [16, 14],
    [20, 18],
  ];
  return pairs.every(([tip, pip]) => dist(pts[tip], wrist) > dist(pts[pip], wrist));
}

export default function App() {
const [landmarks, setLandmarks] = useState<HandLandmarks | null>(null);
  const [showHelp, setShowHelp] = useState(false);
  const [frameDims, setFrameDims] = useState<{ w: number; h: number } | null>(null);
  const [debugInfo, setDebugInfo] = useState<{
    plugin: boolean;
    hands: number;
    error?: string | null;
  } | null>(null);

  const device = useCameraDevice('front');
  const { hasPermission, requestPermission } = useCameraPermission();
  const [cameraError, setCameraError] = useState<string | null>(null);

  const detectHandLandmarks = useMemo(
    () => VisionCameraProxy.initFrameProcessorPlugin('handLandmarker', {}),
    []
  );
  const hasPlugin = detectHandLandmarks != null;

  const {
    currentGesture,
    fps,
    isPaused,
    togglePaused,
    setGesture,
    incrementGestureCount,
    setFps,
  } = useGestureStore();

  const { moveGain, filterMinCutoff, filterBeta } = useSettingsStore();

  const proEntitlement = useProEntitlement();
  const [showPro, setShowPro] = useState(false);

  const [mode, setMode] = useState<'camera' | 'remote'>('camera');
  const remoteStatus = useRemoteStore((s) => s.status);
  const forwardGestures = useRemoteStore((s) => s.forwardGestures);

  useEffect(() => {
    useRemoteStore.getState().hydrate();
  }, []);

  const engineRef = useRef<GestureEngine | null>(null);
  const filtersRef = useRef<FilterPair2D | null>(null);
  const curveRef = useRef<AccelCurve | null>(null);
  const lastFrameTime = useRef(performance.now());
  const frameCount = useRef(0);
  const viewMappingRef = useRef<{
    ox: number;
    oy: number;
    dispW: number;
    dispH: number;
  } | null>(null);
  const frameDimsRef = useRef<{ w: number; h: number } | null>(frameDims);
  const filteredPalmRef = useRef<[number, number]>([0, 0]);
  const lastDragPosRef = useRef<[number, number]>([0, 0]);
  const pointerRef = useRef<{
    button: 'left' | 'right' | 'middle';
    x: number;
    y: number;
    pressedAt: number;
  } | null>(null);
  const lastMoveSentRef = useRef(0);
  const palmsFramesRef = useRef(0);
  const palmsSentRef = useRef(false);

  // Initialize gesture engine
  useEffect(() => {
    engineRef.current = new GestureEngine();
    filtersRef.current = new FilterPair2D(filterMinCutoff, filterBeta);
    curveRef.current = new AccelCurve(1.2, 3.0, 1400.0, 1.7);
  }, [filterMinCutoff, filterBeta]);

  const toScreen = useCallback(
    (px: number, py: number): [number, number] => {
      const vm = viewMappingRef.current;
      const fd = frameDimsRef.current;
      if (!vm || !fd || fd.w <= 0 || fd.h <= 0) {
        return [Math.round(px), Math.round(py)];
      }
      const x = vm.ox + vm.dispW - (vm.dispW / fd.w) * px;
      const y = vm.oy + (vm.dispH / fd.h) * py;
      return [
        Math.round(Math.max(0, Math.min(SCREEN_WIDTH, x))),
        Math.round(Math.max(0, Math.min(SCREEN_HEIGHT, y))),
      ];
    },
    []
  );

  // Rota de ações: transição de gesto -> comando nativo / PC remoto.
  const handleAction = useCallback(
    async (event: string, value: number | null) => {
      if (!proEntitlement.isPro) {
        // Versão gratuita: apenas pré-visualiza gestos, não envia comandos.
        setShowPro(true);
        return;
      }

      const [palmX, palmY] = filteredPalmRef.current;

      if (remoteStatus === 'connected' && forwardGestures) {
        // Modo "PC remoto": os gestos da câmara comandam o PC via WebSocket.
        remote.gesture(
          event,
          Math.max(0, Math.min(1, palmX / SCREEN_WIDTH)),
          Math.max(0, Math.min(1, palmY / SCREEN_HEIGHT)),
          value === null ? undefined : value ?? 0
        );
        return;
      }

      try {
        switch (event) {
          case 'left_down':
            // Pinça/punho pressiona: inicia toque/arrasto na posição da palma.
            if (TouchController) {
              pointerRef.current = {
                button: 'left',
                x: palmX,
                y: palmY,
                pressedAt: Date.now(),
              };
              lastDragPosRef.current = [palmX, palmY];
              await TouchController.dragStart(palmX, palmY);
            }
            break;
          case 'left_up': {
            const held = pointerRef.current;
            pointerRef.current = null;
            if (!held || held.button !== 'left' || !TouchController) break;
            if (Date.now() - held.pressedAt < TAP_THRESHOLD_MS) {
              // Pinça rápida = clique esquerdo.
              await TouchController.tap(held.x, held.y);
            } else {
              // Pinça/punho prolongado = solta o arrasto.
              await TouchController.dragEnd();
            }
            break;
          }
          case 'right_click':
            if (TouchController) {
              await TouchController.longPress(palmX, palmY, 0.5);
            }
            break;
          case 'scroll':
            if (value !== null && TouchController) {
              await TouchController.swipe(
                SCREEN_WIDTH / 2,
                SCREEN_HEIGHT / 2,
                SCREEN_WIDTH / 2,
                SCREEN_HEIGHT / 2 - value * 10,
                0.1
              );
            }
            break;
          case 'volume':
            if (SystemController && typeof value === 'number' && value !== 0) {
              await SystemController.adjustVolume(value > 0 ? 1 : -1);
            }
            break;
          case 'goBack':
            await SystemController?.goBack();
            break;
          case 'goHome':
            await SystemController?.goHome();
            break;
          case 'openRecents':
            await SystemController?.openRecents();
            break;
          case 'openNotifications':
            await SystemController?.openNotifications();
            break;
          case 'minimize':
            await KeyboardController?.pressCombo([113, 40]); // Ctrl+D
            break;
          case 'copy':
            await KeyboardController?.pressCombo([113, 31]); // Ctrl+C
            break;
          case 'paste':
            await KeyboardController?.pressCombo([113, 50]); // Ctrl+V
            break;
          default:
            break;
        }
      } catch (error) {
        console.error('Action error:', error);
      }
    },
    [proEntitlement.isPro, remoteStatus, forwardGestures]
  );

  // Processa o resultado da deteção (mão dominante + gestos + ações).
  const processHands = useCallback(
    (hands: any[], handedness: any[], imgW: number, imgH: number) => {
      if (!engineRef.current || !filtersRef.current || !curveRef.current) return;
      if (imgW <= 0 || imgH <= 0) return;

      try {
        // Duas mãos abertas (palmas) sustentadas -> voltar.
        if (hands.length >= 2 && hands.every(isOpenPalm)) {
          palmsFramesRef.current += 1;
          if (palmsFramesRef.current >= PALM_BACK_FRAMES && !palmsSentRef.current) {
            palmsSentRef.current = true;
            handleAction('goBack', null);
          }
        } else {
          palmsFramesRef.current = 0;
          palmsSentRef.current = false;
        }

        // Mão dominante: a de maior palma (mais próxima da câmara).
        let bestRaw = hands[0];
        for (const raw of hands) {
          if (palmScale(raw) > palmScale(bestRaw)) bestRaw = raw;
        }
        const points: [number, number, number][] = bestRaw.map((p: any) => [
          p.x,
          p.y,
          p.z,
        ]);
        const result = engineRef.current.update(points, imgW, imgH);

        // Filtra e mapeia a palma para coordenadas de ecrã (espelhado + aspect-fit).
        const [fx, fy] = filtersRef.current.filter(
          result.landmarks.palmCenter[0],
          result.landmarks.palmCenter[1]
        );
        filteredPalmRef.current = toScreen(fx, fy);

        // Atualiza estado
        setGesture(result.landmarks.gesture);
        incrementGestureCount();
        setLandmarks(result.landmarks);

        // Ações de transição
        if (result.event) {
          handleAction(result.event, result.value);
        }

        // Deslocamento contínuo enquanto o botão está pressionado (arrastar).
        if (
          proEntitlement.isPro &&
          !isPaused &&
          pointerRef.current?.button === 'left'
        ) {
          const now = Date.now();
          const dtMs = Math.max(now - lastMoveSentRef.current, 16);
          if (dtMs >= MOVE_INTERVAL_MS) {
            const target = filteredPalmRef.current;
            const prev = lastDragPosRef.current;
            const g =
              curveRef.current.apply(
                (target[0] - prev[0]) / (dtMs / 1000),
                (target[1] - prev[1]) / (dtMs / 1000)
              ) *
              (moveGain / 2);
            const nx = Math.max(0, Math.min(SCREEN_WIDTH, prev[0] + (target[0] - prev[0]) * g));
            const ny = Math.max(0, Math.min(SCREEN_HEIGHT, prev[1] + (target[1] - prev[1]) * g));
            TouchController?.dragMove(nx, ny);
            lastDragPosRef.current = [nx, ny];
            lastMoveSentRef.current = now;
          }
        } else {
          lastMoveSentRef.current = Date.now();
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        setDebugInfo((prev) =>
          prev && prev.error === msg ? prev : { plugin: true, hands: 0, error: `JS: ${msg}` }
        );
        console.error('processHands error:', e);
      }
    },
    [
      toScreen,
      handleAction,
      setGesture,
      incrementGestureCount,
      proEntitlement.isPro,
      isPaused,
      moveGain,
      setDebugInfo,
    ]
  );

  // Update FPS from the worklet via runOnJS (no React functions/refs are shared into the worklet)
  const updateFps = useRef(
    Worklets.createRunOnJS(() => {
      frameCount.current++;
      const now = Date.now();
      if (now - lastFrameTime.current >= 1000) {
        const fps = (frameCount.current * 1000) / (now - lastFrameTime.current);
        setFps(fps);
        frameCount.current = 0;
        lastFrameTime.current = now;
      }
    })
  );

  const emptyFrames = useRef(0);
  const clearAfterEmptyFrames = 6;

  const handleFramePayload = useCallback(
    (payload: {
      hands?: any[];
      handedness?: any[];
      imgW: number;
      imgH: number;
      handsCount: number;
    }) => {
      if (payload.handsCount > 0 && payload.hands && payload.hands.length > 0) {
        emptyFrames.current = 0;
        setFrameDims((prev) =>
          prev && prev.w === payload.imgW && prev.h === payload.imgH
            ? prev
            : { w: payload.imgW, h: payload.imgH }
        );
        processHands(payload.hands, payload.handedness || [], payload.imgW, payload.imgH);
      } else {
        emptyFrames.current += 1;
        if (emptyFrames.current >= clearAfterEmptyFrames) {
          setLandmarks(null);
        }
      }
    },
    [processHands]
  );

  const framePayloadRef = useRef(handleFramePayload);
  useEffect(() => {
    framePayloadRef.current = handleFramePayload;
  }, [handleFramePayload]);

  const bridgeFrame = useRef(
    Worklets.createRunOnJS(
      (payload: {
        hands?: any[];
        handedness?: any[];
        imgW: number;
        imgH: number;
        handsCount: number;
      }) => {
        framePayloadRef.current(payload);
      }
    )
  );

  const updateDebug = useRef(
    Worklets.createRunOnJS(
      (info: { plugin: boolean; hands: number; error?: string | null }) => {
        setDebugInfo((prev) => {
          if (
            prev &&
            prev.plugin === info.plugin &&
            prev.hands === info.hands &&
            prev.error === info.error
          ) {
            return prev;
          }
          return info;
        });
      }
    )
  );

  // Frame processor for real-time hand detection
  const frameProcessor = useFrameProcessor(
    (frame) => {
      'worklet';

      // Read frame dimensions BEFORE the slow MediaPipe call, while the frame is
      // guaranteed valid. Accessing frame props after heavy native work can throw
      // FrameInvalidError, and reading them first is the documented safe pattern.
      const imgW = frame.width;
      const imgH = frame.height;

      let hands: any[] | undefined;
      let handedness: any[] | undefined;
      let handsCount = 0;
      let errorMsg: string | null = null;

      try {
        const result = detectHandLandmarks?.call(frame) as HandDetectionResult | undefined;
        hands = result?.hands;
        handedness = result?.handedness;
        handsCount = result?.hands?.length ?? 0;
        errorMsg = result?.error ?? null;
      } catch (e: any) {
        errorMsg = e?.message ? String(e.message) : 'Frame processor error';
      }

      bridgeFrame.current({
        hands,
        handedness,
        imgW,
        imgH,
        handsCount,
      });

      updateDebug.current({ plugin: hasPlugin, hands: handsCount, error: errorMsg });

      // Update FPS on the JS thread
      updateFps.current();
    },
    [detectHandLandmarks, hasPlugin]
  );

  const viewMapping = useMemo(() => {
    if (!frameDims) return null;
    const scale = Math.max(SCREEN_WIDTH / frameDims.w, SCREEN_HEIGHT / frameDims.h);
    const dispW = frameDims.w * scale;
    const dispH = frameDims.h * scale;
    return {
      ox: (SCREEN_WIDTH - dispW) / 2,
      oy: (SCREEN_HEIGHT - dispH) / 2,
      dispW,
      dispH,
    };
  }, [frameDims]);

  useEffect(() => {
    viewMappingRef.current = viewMapping;
    frameDimsRef.current = frameDims;
  }, [viewMapping, frameDims]);

  // Render hand overlay
  const renderHandOverlay = () => {
    if (!landmarks) return null;

    const color = GESTURE_COLORS[landmarks.gesture] || '#969696';

    const mapX = (nx: number) =>
      viewMapping ? viewMapping.ox + (1 - nx) * viewMapping.dispW : nx * SCREEN_WIDTH;
    const mapY = (ny: number) =>
      viewMapping ? viewMapping.oy + ny * viewMapping.dispH : ny * SCREEN_HEIGHT;
    const toScreenX = (ix: number) =>
      viewMapping && frameDims
        ? viewMapping.ox + viewMapping.dispW - (viewMapping.dispW / frameDims.w) * ix
        : ix;
    const toScreenY = (iy: number) =>
      viewMapping && frameDims
        ? viewMapping.oy + (viewMapping.dispH / frameDims.h) * iy
        : iy;

    return (
      <View style={styles.overlay}>
        {/* Draw hand connections */}
        {HAND_CONNECTIONS.map(([a, b], index) => {
          const pa = landmarks.points[a];
          const pb = landmarks.points[b];
          if (!pa || !pb) return null;

          const x1 = mapX(pa[0]);
          const y1 = mapY(pa[1]);
          const x2 = mapX(pb[0]);
          const y2 = mapY(pb[1]);

          return (
            <View
              key={index}
              style={[
                styles.connectionLine,
                {
                  left: x1,
                  top: y1,
                  width: Math.hypot(x2 - x1, y2 - y1),
                  transform: [
                    {
                      rotate: `${Math.atan2(y2 - y1, x2 - x1)}rad`,
                    },
                  ],
                  backgroundColor: color,
                },
              ]}
            />
          );
        })}

        {/* Draw palm center */}
        <View
          style={[
            styles.palmCenter,
            {
              left: toScreenX(landmarks.palmCenterPx[0]) - 15,
              top: toScreenY(landmarks.palmCenterPx[1]) - 15,
              borderColor: color,
            },
          ]}
        />

        {/* Gesture badge */}
        <View style={[styles.gestureBadge, { backgroundColor: color + '80' }]}>
          <Text style={styles.gestureText}>
            {GESTURE_LABELS[landmarks.gesture]}
          </Text>
        </View>
      </View>
    );
  };

  if (mode === 'remote') {
    return (
      <View style={styles.container}>
        <StatusBar barStyle="light-content" />
        <RemoteScreen onBack={() => setMode('camera')} />
      </View>
    );
  }

  if (cameraError) {
    return (
      <View style={styles.permissionContainer}>
        <Text style={styles.permissionText}>Câmara indisponível</Text>
        <Text style={[styles.permissionText, { fontSize: 14 }]}>{cameraError}</Text>
        <Text style={[styles.permissionText, { fontSize: 14 }]}>
          A câmara está restrita pelo sistema (política de dispositivo ou
          restrição parental). Ative-a em Definições e reinicie a app.
        </Text>
      </View>
    );
  }

  if (!hasPermission) {
    return (
      <View style={styles.permissionContainer}>
        <Text style={styles.permissionText}>
          Mãouse precisa de acesso à câmara para detetar gestos de mão
        </Text>
        <TouchableOpacity style={styles.permissionButton} onPress={requestPermission}>
          <Text style={styles.permissionButtonText}>Permitir Câmara</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      {device && (
        <Camera
          style={StyleSheet.absoluteFill}
          device={device}
          isActive={mode === 'camera' && !cameraError}
          frameProcessor={frameProcessor}
          onError={(error) => {
            console.error('Camera error:', error.message);
            setCameraError(error.message);
          }}
        />
      )}

      {renderHandOverlay()}

      {/* Debug overlay */}
      {debugInfo && (
        <View style={styles.debugOverlay}>
          <Text style={styles.debugText}>
            plugin:{debugInfo.plugin ? 'Y' : 'N'} hands:{debugInfo.hands}
            {debugInfo.error ? ` err:${debugInfo.error}` : ''}
          </Text>
        </View>
      )}

      {/* Top bar */}
      <View style={styles.topBar}>
        <View style={styles.statusBadge}>
          <Text style={styles.statusText}>
            {isPaused ? 'PAUSA' : GESTURE_LABELS[currentGesture]}
          </Text>
        </View>

        <View style={styles.statsContainer}>
          <Text style={styles.statsText}>{fps.toFixed(0)} fps</Text>
          <Text style={styles.statsText}>G: {moveGain.toFixed(1)}</Text>
          {remoteStatus === 'connected' && forwardGestures ? (
            <Text style={[styles.statsText, { color: '#5ADC5A' }]}>REMOTO</Text>
          ) : null}
        </View>
      </View>

      {/* Bottom controls */}
      <View style={styles.bottomBar}>
        <TouchableOpacity
          style={styles.controlButton}
          onPress={togglePaused}
        >
          <Text style={styles.controlButtonText}>
            {isPaused ? '▶' : '⏸'}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.controlButton}
          onPress={() => setShowHelp(!showHelp)}
        >
          <Text style={styles.controlButtonText}>?</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.controlButton}
          onPress={() => setMode('remote')}
        >
          <Text style={[styles.controlButtonText, { fontSize: 16 }]}>PC</Text>
        </TouchableOpacity>
      </View>

      {/* Help overlay */}
      {showHelp && (
        <View style={styles.helpOverlay}>
          <View style={styles.helpContent}>
            <Text style={styles.helpTitle}>Gestos</Text>
            <Text style={styles.helpItem}>✋ Mão aberta = Mover cursor</Text>
            <Text style={styles.helpItem}>🤏 Pinça = Clique esquerdo</Text>
            <Text style={styles.helpItem}>🤏🤞 Pinça+médio = Clique direito</Text>
            <Text style={styles.helpItem}>✊ Punho = Arrastar</Text>
            <Text style={styles.helpItem}>✌️ Dois dedos = Scroll</Text>
            <Text style={styles.helpItem}>☝️ Um dedo = Mover (1D)</Text>
            <Text style={styles.helpItem}>👍 Polegar = Play/Pausa</Text>
            <Text style={styles.helpItem}>🤙 Shaka = Colar</Text>
            <Text style={styles.helpItem}>✋✋ Duas mãos abertas = Voltar</Text>
            <TouchableOpacity
              style={styles.helpCloseButton}
              onPress={() => setShowHelp(false)}
            >
              <Text style={styles.helpCloseText}>Fechar</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {showPro && !proEntitlement.isPro ? (
        <ProGate
          entitlement={proEntitlement}
          onClose={() => setShowPro(false)}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  overlay: {
    ...StyleSheet.absoluteFill,
  },
  connectionLine: {
    position: 'absolute',
    height: 2,
    transformOrigin: 'left',
  },
  palmCenter: {
    position: 'absolute',
    width: 30,
    height: 30,
    borderRadius: 15,
    borderWidth: 2,
  },
  gestureBadge: {
    position: 'absolute',
    top: 50,
    left: 20,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  gestureText: {
    color: '#FFF',
    fontSize: 18,
    fontWeight: 'bold',
  },
  topBar: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    paddingTop: 50,
  },
  statusBadge: {
    backgroundColor: 'rgba(0,0,0,0.6)',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  statusText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '600',
  },
  statsContainer: {
    backgroundColor: 'rgba(0,0,0,0.6)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  statsText: {
    color: '#FFF',
    fontSize: 14,
    marginLeft: 8,
  },
  debugOverlay: {
    position: 'absolute',
    bottom: 110,
    left: 20,
    right: 20,
    backgroundColor: 'rgba(0,0,0,0.7)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  debugText: {
    color: '#FFE066',
    fontSize: 13,
  },
  bottomBar: {
    position: 'absolute',
    bottom: 40,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 20,
  },
  controlButton: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  controlButtonText: {
    color: '#FFF',
    fontSize: 24,
  },
  permissionContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    padding: 40,
  },
  permissionText: {
    color: '#FFF',
    fontSize: 18,
    textAlign: 'center',
    marginBottom: 20,
  },
  permissionButton: {
    backgroundColor: '#50C8FF',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  permissionButtonText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '600',
  },
  helpOverlay: {
    ...StyleSheet.absoluteFill,
    backgroundColor: 'rgba(0,0,0,0.8)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  helpContent: {
    backgroundColor: '#2a2a2a',
    borderRadius: 16,
    padding: 24,
    maxWidth: SCREEN_WIDTH * 0.9,
  },
  helpTitle: {
    color: '#FFF',
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  helpItem: {
    color: '#DDD',
    fontSize: 16,
    marginBottom: 8,
  },
  helpCloseButton: {
    marginTop: 20,
    backgroundColor: '#50C8FF',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    alignItems: 'center',
  },
  helpCloseText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '600',
  },
});
