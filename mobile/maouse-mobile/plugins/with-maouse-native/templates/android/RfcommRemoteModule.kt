package com.maouse.mobile

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothSocket
import android.content.Context
import android.content.pm.PackageManager
import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.bridge.WritableMap
import com.facebook.react.modules.core.DeviceEventManagerModule
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.io.OutputStream
import java.util.UUID
import java.util.concurrent.atomic.AtomicBoolean

/**
 * RfcommRemoteModule: cliente RFCOMM/SPP do protocolo que o PC serve
 * (core/remote_rfcomm.py, e o executavel WinRT `maouse-bluetooth-host`).
 *
 * O telefone e o **cliente**: liga-se ao servico que o PC announce no SDP. E o
 * inverso do `BleRemoteModule` em dois sentidos que interessam — aqui o PC e o
 * servidor, e o transporte e Classic e nao LE.
 *
 * ## As diferencas em relacao ao BLE, e porque cada uma obriga a codigo diferente
 *
 * **O RFCOMM e um stream; o BLE nao.** Uma escrita ATT e exactamente um fragmento e
 * o link layer nunca junta dois, por isso o BLE pode meter o tamanho no cabecalho de
 * cada pedaco e o PC sabe sempre onde esta a fronteira. Num stream nao ha essa
 * garantia: uma leitura pode trazer meio cabecalho, tres mensagens, ou o fim de uma
 * e o todo de outra. Por isso aqui o tamanho vai **uma vez por mensagem**, e o
 * receptor acumula ate ter a mensagem inteira. Reusar o `split_frame` do BLE aqui
 * corromperia os comandos — e a falha apareceria como "o rato nao obedece".
 *
 * **Nao ha MTU.** O valor maximo e o que o outro lado conseguir ler, e nao 20 bytes.
 * Nao ha fragmentacao a gerir, nem fila de escritas com um pendente por ligacao: e
 * um `OutputStream`. E o `move` vai em **JSON**, nao no caminho binario de 5 bytes
 * do BLE — aquele existe para caber numa caracteristica de 20 bytes, e aqui o ganho
 * seria zero para bytes que o stream leva na mesma.
 *
 * **`connect()` e bloqueante.** Chama-lo na thread do bridge rebenta com
 * `NetworkOnMainThreadException`, por isso a ligacao corre numa thread dedicada e a
 * promessa resolve-se de la.
 *
 * ## Protocolo (tem de bater certo com o PC, byte a byte)
 *
 *     [tam:4 big-endian][a mensagem inteira]
 *
 * `tam` e o tamanho da mensagem em bytes, uma vez por mensagem. Little-endian daria
 * ao PC um tamanho de ~500 MB e ele descartaria a ligacao. O tecto e
 * `MAX_FRAME`, o mesmo do lado Python.
 */
class RfcommRemoteModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    override fun getName(): String = "RfcommRemote"

    private val context: ReactApplicationContext = reactContext

    /**
     * O mesmo UUID dos outros transportes, de proposito: o namespace de UUIDs do
     * BLE e o do SDP do RFCOMM nao se cruzam, e o mesmo valor da ao telefone uma so
     * identidade para "isto e um Maouse" em vez de duas para aprender.
     */
    private val serviceUuid: UUID = UUID.fromString(
        "D9905F51-F497-49A4-88DF-784D82249EFD"
    )

    private val adapter: BluetoothAdapter? by lazy {
        val mgr = context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
        mgr?.adapter
    }

    /**
     * Escrito na thread de ligacao e lido nas threads do bridge e do leitor.
     * Sem `@Volatile`, a escrita da thread de ligacao nao tem happens-before com
     * o `sendJson` do bridge e o leitor podia ver o socket anterior, ja fechado.
     */
    @Volatile
    private var socket: BluetoothSocket? = null

    /** `Socket.connect()` e `InputStream.read()` bloqueiam; esta flag e o unico jeito de os parar. */
    private val closed = AtomicBoolean(false)

    /** Bytes a espera de virar mensagem. Nunca um `String`: um acento UTF-8 parte-se ao meio. */
    private val rx = ByteArrayOutputStream()

    // ── Ciclo de vida ──────────────────────────────────────────────────

    @SuppressLint("MissingPermission")
    @ReactMethod
    fun connect(address: String, promise: Promise) {
        val a = adapter
        if (a == null) {
            promise.reject("NO_ADAPTER", "Este dispositivo nao tem adaptador Bluetooth")
            return
        }
        if (!granted()) {
            promise.reject("NO_PERMISSION", "Falta a permissao BLUETOOTH_CONNECT")
            return
        }
        if (!a.isEnabled) {
            promise.reject("OFF", "O Bluetooth esta desligado")
            return
        }
        closeQuietly()
        val s: BluetoothSocket = try {
            @Suppress("DEPRECATION")
            a.getRemoteDevice(address).createRfcommSocketToServiceRecord(serviceUuid)
        } catch (e: IllegalArgumentException) {
            // Endereco mal formado: e o que da quando o JS manda um nome em vez
            // do endereco, e a excecao e a unica pista.
            promise.reject("BAD_ADDRESS", "Endereco invalido: $address", e)
            return
        }
        // A promessa resolve-se aqui e nao no fim do `connect()`: o socket estar
        // aberto e o que interessa, e o `auth` sai no evento `connected`. Se a
        // promessa esperasse pela ligacao Useful, um PC que aceita o socket mas
        // nao responde ao `auth` deixava o telefone sem nenhuma pista.
        Thread {
            try {
                s.connect()
            } catch (e: Exception) {
                try {
                    s.close()
                } catch (_: Exception) {
                }
                promise.reject("CONNECT_FAILED", "Ligacao RFCOMM falhou: ${e.message}", e)
                return@Thread
            }
            socket = s
            closed.set(false)
            resetRx()
            promise.resolve(true)
            emit("connected", null, null)
            val t = Thread { readerLoop(s, s.inputStream) }
            t.isDaemon = true
            t.name = "rfcomm-leitor"
            t.start()
        }.apply {
            isDaemon = true
            name = "rfcomm-liga"
        }.start()
    }

    /**
     * Le o stream e entrega ao JS cada mensagem inteira.
     *
     * Um `read` pode trazer meio cabecalho, duas mensagens, ou o fim de uma e o todo
     * de outra. O acumulador so avanca quando a mensagem inteira chegou, e o que
     * sobra e o inicio da seguinte.
     */
    private fun readerLoop(owner: BluetoothSocket, input: InputStream) {
        val chunk = ByteArray(4096)
        try {
            while (socket === owner && !closed.get()) {
                val n = input.read(chunk)
                if (n < 0) break
                if (n > 0) onTx(chunk.copyOf(n))
            }
            if (socket === owner && !closed.get()) {
                emit("disconnected", null, "O PC fechou a ligacao")
            }
        } catch (_: java.io.IOException) {
            if (socket === owner && !closed.get()) {
                emit("disconnected", null, "Ligacao RFCOMM terminada")
            }
        } finally {
            if (socket === owner) closeQuietly()
        }
    }

    /**
     * Junta o stream em mensagens completas.
     *
     * O mesmo protocolo do `_Frames` do PC: um tamanho que nao faz sentido descarta
     * o acumulado, porque a partir dai ja nao se sabe onde acaba a mensagem anterior
     * e o que chega e lixo — que e o que uma tentativa de inundar o buffer parece.
     */
    private fun onTx(chunk: ByteArray) {
        rx.write(chunk, 0, chunk.size)
        while (true) {
            val buf = rx.toByteArray()
            // Menos de 5 bytes nao da nem para ler um tamanho valido: o PC conta
            // o corpo, e um tamanho tem de valer pelo menos 1.
            if (buf.size < 5) break
            val total = ((buf[0].toInt() and 0xFF) shl 24) or
                ((buf[1].toInt() and 0xFF) shl 16) or
                ((buf[2].toInt() and 0xFF) shl 8) or
                (buf[3].toInt() and 0xFF)
            if (total <= 0 || total > MAX_FRAME) {
                resetRx()
                return
            }
            if (buf.size < TAM_FRAME + total) break
            val msg = String(buf, TAM_FRAME, total, Charsets.UTF_8)
            // Sobra o inicio da mensagem seguinte, que veio no mesmo `read`.
            val resto = buf.size - (TAM_FRAME + total)
            rx.reset()
            if (resto > 0) rx.write(buf, TAM_FRAME + total, resto)
            emit("message", msg, null)
        }
    }

    private fun resetRx() {
        rx.reset()
    }

    // ── Envio ──────────────────────────────────────────────────────────

    /**
     * Envia `[tam:4 big-endian][json]`.
     *
     * O tamanho e o do **corpo**, sem o cabecalho: e assim que o PC le, e um
     * `tam` a contar o prefixo faz o PC ler quatro bytes do corpo como se fossem a
     * cauda da proxima mensagem.
     */
    @SuppressLint("MissingPermission")
    @ReactMethod
    fun sendJson(json: String, promise: Promise) {
        val out: OutputStream? = try {
            socket?.outputStream
        } catch (_: java.io.IOException) {
            null
        }
        if (socket == null || closed.get() || out == null) {
            promise.reject("SEND_FAILED", "Sem ligacao RFCOMM")
            return
        }
        val body = json.toByteArray(Charsets.UTF_8)
        if (body.size > MAX_FRAME) {
            promise.reject("TOO_LONG", "Mensagem acima do tecto de ${MAX_FRAME} bytes")
            return
        }
        val frame = ByteArray(TAM_FRAME + body.size)
        frame[0] = ((body.size shr 24) and 0xFF).toByte()
        frame[1] = ((body.size shr 16) and 0xFF).toByte()
        frame[2] = ((body.size shr 8) and 0xFF).toByte()
        frame[3] = (body.size and 0xFF).toByte()
        System.arraycopy(body, 0, frame, TAM_FRAME, body.size)
        try {
            // `write` num stream pode escrever menos do que pediu. O `OutputStream`
            // de um socket nem sempre cumpre o contrato dos N bytes, e um prefixo
            // pela metade deixa o PC a ler cabecalhos de mensagens que nao existem.
            out.write(frame)
            out.flush()
        } catch (e: java.io.IOException) {
            promise.reject("SEND_FAILED", "Escrita falhou: ${e.message}", e)
            emit("disconnected", null, "Ligacao RFCOMM terminada")
            closeQuietly()
            return
        }
        promise.resolve(true)
    }

    @SuppressLint("MissingPermission")
    @ReactMethod
    fun disconnect() {
        closeQuietly()
    }

    @ReactMethod
    fun isConnected(promise: Promise) {
        promise.resolve(socket != null && !closed.get())
    }

    @ReactMethod
    fun hasPermissions(promise: Promise) {
        promise.resolve(granted())
    }

    @ReactMethod
    fun isBluetoothEnabled(promise: Promise) {
        promise.resolve(adapter?.isEnabled == true)
    }

    /**
     * Os dispositivos já emparelhados com este telemóvel.
     *
     * O RFCOMM não anuncia nada e não se pode varrer: o Android só liga a um
     * dispositivo que já esteja emparelhado. Esta lista é a única forma de o
     * utilizador chegar ao PC — escrever um endereço MAC à mão não é uma
     * interface, é um teste manual.
     */
    @SuppressLint("MissingPermission")
    @ReactMethod
    fun listBonded(promise: Promise) {
        val a = adapter
        if (a == null) {
            promise.reject("NO_ADAPTER", "Este dispositivo não tem adaptador Bluetooth")
            return
        }
        if (!granted()) {
            promise.reject("NO_PERMISSION", "Falta a permissão BLUETOOTH_CONNECT")
            return
        }
        try {
            val out = Arguments.createArray()
            for (d in a.bondedDevices) {
                val m = Arguments.createMap()
                m.putString("address", d.address)
                m.putString("name", d.name ?: "")
                out.pushMap(m)
            }
            promise.resolve(out)
        } catch (e: SecurityException) {
            promise.reject("NO_PERMISSION", "Falta a permissão BLUETOOTH_CONNECT", e)
        }
    }

    /**
     * Fecha o socket e trava a thread leitora.
     *
     * Fechar o socket e o que desbloqueia o `read()` — um `read` num stream de um
     * socket so termina quando o outro lado fecha ou o socket fecha. Sem isto a
     * thread leitora sobrevive a todos os `disconnect` e fica a prender o socket
     * antigo, e o telefone nao consegue ligar ao PC seguinte.
     */
    private fun closeQuietly() {
        closed.set(true)
        val s = socket
        socket = null
        resetRx()
        if (s != null) {
            try {
                s.close()
            } catch (_: java.io.IOException) {
                // Ja fechado: e o caminho normal do `disconnect`.
            }
        }
    }

    // ── Sobrevivência a eventos ───────────────────────────────────────
    //
    // NAO sao `override`: em RN 0.86 `BaseJavaModule`/`NativeModule` nao declaram
    // `addListener`/`removeListeners` (o `NativeEventEmitter` do JS limita-se a
    // chamar `this._nativeModule?.addListener(...)` por nome). Com `override` o
    // compilador Kotlin chumbava com "'addListener' overrides nothing".
    @ReactMethod
    fun addListener(eventName: String) {
        // Os eventos sao enviados por `emit`; este metodo existe porque o
        // `NativeEventEmitter` do JS o exige.
    }

    @ReactMethod
    fun removeListeners(count: Int) {
    }

    private fun emit(event: String, payload: Any?, error: String?) {
        val body: WritableMap = Arguments.createMap()
        if (payload is String) body.putString("message", payload)
        if (error != null) body.putString("error", error)
        try {
            context
                .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
                .emit(event, body)
        } catch (_: RuntimeException) {
            // O contexto JS ja foi destruido (app a fechar).
        }
    }

    /**
     * So `BLUETOOTH_CONNECT` e necessaria, ao contrario do BLE que tambem precisa de
     * `BLUETOOTH_SCAN`: aqui nao ha varrimento nenhum, o telefone e que sabe o
     * endereco. Pedir `SCAN` sem necessidade faria o Android mostrar o dialogo de
     * localizacao, que e uma confusao a ninguem ajuda.
     */
    private fun granted(): Boolean =
        context.checkSelfPermission("android.permission.BLUETOOTH_CONNECT") ==
            PackageManager.PERMISSION_GRANTED

    // ── Constantes do protocolo ───────────────────────────────────────

    private companion object {
        /** Tamanho do prefixo, em bytes. Big-endian, como o `htonl` do TCP. */
        const val TAM_FRAME = 4

        /** Tecto por mensagem. Tem de bater certo com `MAX_FRAME` do lado Python. */
        const val MAX_FRAME = 64 * 1024
    }
}