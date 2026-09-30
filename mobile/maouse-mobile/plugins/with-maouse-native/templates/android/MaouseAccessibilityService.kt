package com.maouse.mobile

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.os.Handler
import android.os.Looper
import android.view.accessibility.AccessibilityEvent

/**
 * MaouseAccessibilityService: serviço de acessibilidade que permite ao Mãouse
 * injetar gestos (tap, longPress, swipe, drag) e ações globais (back, home,
 * recents, notificações) em qualquer app — sem root.
 *
 * Utilizadores têm de ativar o serviço em:
 *   Definições > Acessibilidade > Maouse (Maouse Accessibility)
 *
 * O serviço é referenciado estaticamente pelos módulos nativos
 * (TouchControllerModule / SystemControllerModule) para despachar gestos.
 *
 * NOTA — drag contínuo: o Android só executa UM gesto de cada vez
 * (dispatchGesture devolve false se já houver um ativo). Por isso o arrastar
 * usa a API de continuação de strokes (StrokeDescription willContinue +
 * continueStroke): o toque é mantido "em baixo" entre movimentos, em vez de
 * levantar o dedo a cada dragMove.
 */
class MaouseAccessibilityService : AccessibilityService() {

    companion object {
        @Volatile
        var instance: MaouseAccessibilityService? = null
    }

    private val main = Handler(Looper.getMainLooper())

    @Volatile
    private var isDragging = false

    // Estado do drag — confinado à thread main.
    private var dragStroke: GestureDescription.StrokeDescription? = null
    private var dragLastX = 0f
    private var dragLastY = 0f
    private var dragPendingX = 0f
    private var dragPendingY = 0f
    private var dragTime = 0L

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // Sem lógica de eventos por agora — apenas despachamos gestos on-demand.
    }

    override fun onInterrupt() {
        // Nada a interromper.
    }

    override fun onDestroy() {
        instance = null
        super.onDestroy()
    }

    fun isReady(): Boolean = true

    /** Tap simples: toque rápido num ponto do ecrã. */
    fun tap(x: Float, y: Float) {
        val path = Path().apply { moveTo(x, y) }
        val stroke = GestureDescription.StrokeDescription(path, 0, 80L)
        dispatchGesture(GestureDescription.Builder().addStroke(stroke).build(), null, null)
    }

    /** Long press: manter o dedo num ponto durante `durationMs`. */
    fun longPress(x: Float, y: Float, durationMs: Long) {
        val path = Path().apply { moveTo(x, y) }
        val stroke = GestureDescription.StrokeDescription(path, 0, durationMs)
        dispatchGesture(GestureDescription.Builder().addStroke(stroke).build(), null, null)
    }

    /** Swipe linear de (x1,y1) para (x2,y2) em `durationMs`. */
    fun swipe(x1: Float, y1: Float, x2: Float, y2: Float, durationMs: Long) {
        val path = Path().apply {
            moveTo(x1, y1)
            lineTo(x2, y2)
        }
        val stroke = GestureDescription.StrokeDescription(path, 0, durationMs)
        dispatchGesture(GestureDescription.Builder().addStroke(stroke).build(), null, null)
    }

    /**
     * Início de drag. Despacha um stroke curto com willContinue=true: o sistema
     * mantém o toque "em baixo" e deixa-nos continuá-lo nos dragMove seguintes.
     */
    fun dragStart(x: Float, y: Float, holdMs: Long = 120L) {
        main.post {
            dragLastX = x
            dragLastY = y
            dragPendingX = x
            dragPendingY = y
            val hold = holdMs.coerceAtLeast(60L)
            dragTime = hold
            val path = Path().apply { moveTo(x, y) }
            val stroke = GestureDescription.StrokeDescription(path, 0, hold, true)
            isDragging = true
            dragStroke = stroke
            dispatchGesture(GestureDescription.Builder().addStroke(stroke).build(), null, null)
        }
    }

    /** Continuação do drag: desloca o dedo para o novo ponto. */
    fun dragMove(x: Float, y: Float, durationMs: Long = 34L) {
        main.post { dispatchMove(x, y, durationMs) }
    }

    private fun dispatchMove(x: Float, y: Float, durationMs: Long) {
        dragPendingX = x
        dragPendingY = y
        if (!isDragging) {
            dragStart(x, y)
            return
        }
        val prev = dragStroke ?: return
        val duration = durationMs.coerceAtLeast(30L)
        val path = Path().apply {
            moveTo(dragLastX, dragLastY)
            lineTo(x, y)
        }
        val start = dragTime
        dragTime = start + duration
        val continued = prev.continueStroke(path, start, duration, true)
        if (dispatchGesture(
                GestureDescription.Builder().addStroke(continued).build(), null, null)
        ) {
            dragStroke = continued
            dragLastX = x
            dragLastY = y
        }
        // Se o dispatch falhar (sistema ocupado), mantemos o dragStroke anterior
        // e o próximo dragMove volta a tentar a partir do último ponto válido.
    }

    /** Fim do drag: ultimo segmento curto sem willContinue — o dedo levanta. */
    fun dragEnd() {
        main.post {
            if (!isDragging) return@post
            isDragging = false
            val prev = dragStroke
            dragStroke = null
            if (prev == null) return@post
            val path = Path().apply { moveTo(dragPendingX, dragPendingY) }
            val start = dragTime
            dragTime = start + 60L
            val finalStroke = prev.continueStroke(path, start, 60L, false)
            dispatchGesture(GestureDescription.Builder().addStroke(finalStroke).build(), null, null)
        }
    }

    fun performGlobalActionCompat(action: Int): Boolean =
        performGlobalAction(action)
}