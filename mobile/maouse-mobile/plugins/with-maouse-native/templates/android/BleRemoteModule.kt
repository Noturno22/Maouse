package com.maouse.mobile

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattDescriptor
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.bluetooth.BluetoothStatusCodes
import android.bluetooth.le.BluetoothLeScanner
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.ParcelUuid
import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.bridge.WritableMap
import com.facebook.react.modules.core.DeviceEventManagerModule
import java.nio.ByteBuffer
import java.util.UUID
import java.util.concurrent.atomic.AtomicBoolean

/**
 * BleRemoteModule: cliente BLE do protocolo que o PC publica (core/remote_ble.py).
 *
 * O PC é o *peripheral* GATT e este módulo é o *central*. Não há serviço de
 * descoberta: o telefone procura o UUID do serviço nos anúncios e conecta.
 *
 * ## Protocolo (tem de bater certo com o PC, byte a byte)
 *
 * O BLE não tem mensagens, tem escritas de tamanho fixo. Cada fragmento começa
 * com o comprimento **total** da mensagem em 2 bytes big-endian, e o receptor
 * acumula até ter esse tamanho. Ver `split_frame`/`FrameBuffer` no lado Python.
 *
 * O valor de uma característica é `MTU - 3` bytes, e com a MTU por omissão (23)
 * isso dá 20 — dos quais 2 são o cabeçalho, logo 18 de corpo. Pedir uma MTU
 * maior é permitido e só aumenta isto, por isso o corpo é calculado a partir da
 * MTU negociada e nunca de uma constante. Mandar mais do que a MTU não dá erro:
 * o link layer recorta e o PC recebe lixo.
 *
 * Duas caracteristicas:
 *  - `rx` (escrita): comandos do telefone para o rato. O `auth` vai aqui.
 *  - `tx` (notificação): respostas do PC (`ok`, `err`, `pong`).
 *
 * ## Duas coisas que só se descobrem a correr
 *
 * 1. **ACCC.** A notificação só chega depois de escrever no descritor
 *    `00002902-0000-1000-8000-00805f9b34fb`. Sem esse passo o `subscribe`
 *    parece funcionar e não chega nada — e o PC, que só responde a quem tem
 *    `Notifying` ligado, fica calado sem dizer porquê.
 *
 * 2. **A MTU chega num callback, não no `connect`.** Pedir MTU na ligação e
 *    escrever logo a seguir manda o valor por omissão, que chega para
 *    comandos pequenos e por isso passa despercebido até um comando maior
 *    desaparecer sem erro.
 */
class BleRemoteModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    override fun getName(): String = "BleRemote"

    private val context: ReactApplicationContext = reactContext

    private val serviceUuid: UUID = UUID.fromString(
        "D9905F51-F497-49A4-88DF-784D82249EFD"
    )
    private val rxUuid: UUID = UUID.fromString("4C7F582E-BD6F-40ED-B181-AE537DD154ED")
    private val txUuid: UUID = UUID.fromString("64DB3D43-0354-4142-8EBE-EDE62429DD8A")
    private val cccUuid: UUID = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")

    private val adapter: BluetoothAdapter? by lazy {
        val mgr = context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
        mgr?.adapter
    }

    private var scanner: BluetoothLeScanner? = null
    private var gatt: BluetoothGatt? = null

    /** Byte de corpo por fragmento. 18 é a MTU por omissão menos 3 e menos o cabeçalho. */
    private var bodyMax: Int = 18

    /** `@Volatile` não serve: o GATT vem de uma thread do Binder e o JS de outra. */
    private val scanning = AtomicBoolean(false)

    // ── Bytes à espera de virar mensagem ────────────────────────────────
    //
    // **Bytes, nunca `String`.** Um fragmento de texto UTF-8 acaba a meio de
    // um caractere multi-byte — o `ã` são 2 bytes (`0xC3 0xA3`). Decodificar
    // cada fragmento antes de juntar põe dois `U+FFFD` no meio do `ã` e a
    // asserção de fidelidade de texto (§3.7) passa a falhar só com acentos, o
    // que é a pior altura para descobrir que a culpa é do buffer e não do
    // teclado. accumulating bytes e descodificar **uma vez**, no fim, é o que o
    // `FrameBuffer` do PC faz e o que está certo.
    private val rx = java.io.ByteArrayOutputStream()

    /** O `ScanCallback` tem de ser a **mesma instância** que/startScan() deu. */
    private var activeScan: ScanCallback? = null

    @SuppressLint("MissingPermission")
    private fun gattCallback(): BluetoothGattCallback {
        return object : BluetoothGattCallback() {

            @SuppressLint("MissingPermission")
            override fun onConnectionStateChange(g: BluetoothGatt, status: Int, newState: Int) {
                if (status != BluetoothGatt.GATT_SUCCESS) {
                    emit("disconnected", null, "ligacao falhou (status $status)")
                    cleanup()
                    return
                }
                when (newState) {
                    BluetoothProfile.STATE_CONNECTED -> {
                        // Nada de escritas antes disto: o GATT ainda não está
                        // pronto e a escrita sai sem erro e sem chegar a lado
                        // nenhum.
                        discover(g)
                    }
                    BluetoothProfile.STATE_DISCONNECTED -> {
                        emit("disconnected", null, null)
                        cleanup()
                    }
                }
            }

            @SuppressLint("MissingPermission")
            override fun onServicesDiscovered(g: BluetoothGatt, status: Int) {
                if (status != BluetoothGatt.GATT_SUCCESS) {
                    emit("disconnected", null, "servicos nao encontrados (status $status)")
                    cleanup()
                    return
                }
                // Pedir MTU aqui e não em `onConnectionStateChange`: este callback
                // e o primeiro em que o GATT aceita a chamada.
                g.requestMtu(185)
                // A MTU so chega em `onMtuChanged`, e e ai que `bodyMax` muda.
                // A `subscribe` vai ja na sequencia porque a escrita no CCC e
                // pequena (2 bytes) e nao sofre do limite: fazer-se a espera
                // deixaria a notificacao dependente de um `requestMtu` que o
                // PC pode recusar, e o telefone nunca mais receberia resposta
                // — falha maior que a que se evita. O que nao pode acontecer e
                // enviar um *comando* antes de a MTU vir, e nao acontece: o
                // `auth` so sai depois do evento `connected`, que vem do
                // `onDescriptorWrite`, ja depois deste ciclo todo.
                subscribe(g)
            }

            @SuppressLint("MissingPermission")
            override fun onMtuChanged(g: BluetoothGatt, mtu: Int, status: Int) {
                if (status == BluetoothGatt.GATT_SUCCESS && mtu > 23) {
                    bodyMax = mtu - 3 - 2
                }
            }

            override fun onDescriptorWrite(
                g: BluetoothGatt,
                descriptor: BluetoothGattDescriptor,
                status: Int
            ) {
                // A inscricao e o ultimo passo. Só agora o PC passa a ver
                // `Notifying` a true e aceita responder.
                if (status == BluetoothGatt.GATT_SUCCESS) {
                    emit("connected", null, null)
                }
            }

            override fun onCharacteristicChanged(
                g: BluetoothGatt,
                characteristic: BluetoothGattCharacteristic,
                value: ByteArray
            ) {
                val data = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    characteristic.value ?: value
                } else {
                    value
                }
                onTx(data)
            }

            @Deprecated("API < 33, mantida porque o callback antigo e o que chega abaixo disso")
            @Suppress("DEPRECATION")
            override fun onCharacteristicChanged(
                g: BluetoothGatt,
                characteristic: BluetoothGattCharacteristic
            ) {
                onTx(characteristic.value ?: return)
            }

            override fun onCharacteristicWrite(
                g: BluetoothGatt,
                characteristic: BluetoothGattCharacteristic,
                status: Int
            ) {
                if (status != BluetoothGatt.GATT_SUCCESS) {
                    emit("error", null, "escrita falhou (status $status)")
                }
                // A fila anda uma escrita de cada vez: o GATT aceita uma
                // operação pendente. Chamar `writeCharacteristic` a seguir sem
                // esperar por este callback devolve `false` e o segundo
                // fragmento nunca sai. O `pump` destrava e escreve o
                // seguinte; se a escrita anterior foi sem resposta, o
                // `postDelayed` do `pump` já tinha destrancado o trinco e
                // este `pump` não faz nada.
                //
                // O timeout de segurança pendente é cancelado aqui: se
                // disparasse depois, destrancava a escrita **seguinte** a meio
                // e o `pump` escrevia por cima dela.
                noRespRunnable?.let { mainHandler.removeCallbacks(it) }
                noRespRunnable = null
                writeInFlight = false
                pump()
            }
        }
    }

    // ── Remoção de framing ─────────────────────────────────────────────

    /**
     * Junta fragmentos até dar uma mensagem, e entrega-a ao JS.
     *
     * O mesmo protocol de `FrameBuffer` do PC: se o total mudar a meio, o que
     * estava acumulado é lixo de uma mensagem que se perdeu e recomeça-se.
     */
    private fun onTx(chunk: ByteArray) {
        if (chunk.size < 2) return
        val total = ((chunk[0].toInt() and 0xFF) shl 8) or (chunk[1].toInt() and 0xFF)
        if (total <= 0) {
            resetRx()
            return
        }
        // A contagem e em **bytes**, que e como o total foi medido no PC. Contar
        // caracteres dava "completa" assim que os acentos perdiam bytes, e a
        // mensagem ia ao JS cortada a meio.
        if (rx.size() == 0) {
            pending = total
        } else if (pending != total) {
            // O total mudou a meio: o que estava acumulado era lixo de uma
            // mensagem perdida. Recomeça-se, como no `FrameBuffer` do PC.
            resetRx()
            pending = total
        }
        rx.write(chunk, 2, chunk.size - 2)
        if (rx.size() < total) return
        val msg = String(rx.toByteArray(), Charsets.UTF_8)
        resetRx()
        emit("message", msg, null)
    }

    private fun resetRx() {
        rx.reset()
        pending = 0
    }

    private var pending: Int = 0

    // ── Envio ─────────────────────────────────────────────────────────

    /**
     * Envia uma mensagem, fragmentando o que não caiba numa escrita.
     *
     * `writeType` decide a fiabilidade: `auth` e os comandos confirmados vão
     * **com** resposta (o telefone tem de saber que chegaram), os gestos vão
     * **sem** (perder um gesto é um gesto perdido, e esperar por resposta a cada
     * um deles faria o rato ir aos soluços).
     */
    @SuppressLint("MissingPermission")
    private fun send(json: String, withResponse: Boolean): Boolean {
        // A característica vem do `gatt` dentro do `pump`, e não aqui: com a
        // fila em curso, quem escreve é o `pump`, e duplicar a escrita aqui
        // seria o mesmo bug outra vez.
        if (gatt == null) return false
        val bytes = json.toByteArray(Charsets.UTF_8)
        val total = bytes.size
        if (total > 0xFFFF) return false
        val type = if (withResponse) {
            BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT
        } else {
            BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE
        }
        val limit = bodyMax.coerceAtLeast(4)
        var off = 0
        while (off < total) {
            val n = minOf(limit, total - off)
            val frame = ByteBuffer.allocate(2 + n)
            frame.put(((total shr 8) and 0xFF).toByte())
            frame.put((total and 0xFF).toByte())
            frame.put(bytes, off, n)
            off += n
            enqueue(frame.array(), type)
        }
        pump()
        return true
    }

    /**
     * Fragmentos à espera de escrita, um de cada vez.
     *
     * O GATT do Android aceita **uma** operação pendente por ligação. O
     * `send` original escrevia o ciclo inteiro num `while`, e o segundo
     * `writeCharacteristic` devolvia `false` — o que, com `move` binário a
     * caber sempre num fragmento, nunca apareceu. Aparece com texto longo (um
     * parágrafo vai a 3–4 fragmentos) e a falha é silenciosa: o rato move-se, o
     * `text` sai truncado ao meio, e nada diz porque.
     */
    private val writeQueue = ArrayDeque<QueuedWrite>()

    /** Um fragmento e o tipo com que foi pedido. */
    private class QueuedWrite(val data: ByteArray, val type: Int)

    /**
     * A fila tem tecto porque é a memória que cresce sem limite se a ligação
     * cair a meio de um texto e ninguém drainar: cada `move` a 60 Hz durante
     * 30 s são ~1800 fragmentos de 7 bytes, e a app fica a comer heap sem
     * nada visível. Ao encher, descarta-se o mais antigo — que é o gesto, e um
     * gesto perdido é um gesto perdido.
     */
    private fun enqueue(data: ByteArray, type: Int) {
        writeQueue.addLast(QueuedWrite(data, type))
        while (writeQueue.size > MAX_QUEUED_WRITES) {
            writeQueue.removeFirst()
        }
    }

    /**
     * Escreve o próximo fragmento, **um de cada vez**, e só o próximo quando
     * o anterior saiu.
     *
     * Isto reescreve a versão anterior, que tinha dois defeitos que só
     * apareciam com um aparelho real:
     *
     * * `writeNext` lia `writeQueue.firstOrNull()` e **não o removia**. O
     *   único código que removia era `drainWriteQueue`, chamado só do
     *   `onCharacteristicWrite`. Os gestos vão com `WRITE_TYPE_NO_RESPONSE`,
     *   para o qual o Android **não garante** esse callback — num ROM que não
     *   o entregue, o fragmento #1 era reenviado a cada gesto, nunca saía da
     *   fila, e o PC repetia o primeiro gesto indefinidamente sem o segundo
     *   chegar. Nos ROMs que entregam, funcionava por acidente.
     *
     * * e mesmo nos ROMs que entregam o callback, cada fragmento era escrito
     *   duas ou três vezes: uma pelo `writeNext` que reenviava a cabeça e
     *   outra pelo `drainWriteQueue` a seguir. Um clique escrito três vezes é
     *   um clique duplo e um `key` escrito três vezes é uma letra repetida —
     *   e o rato vai sempre atrasado, porque a fila só anda quando alguém
     *   avisa que acabou.
     *
     * `writeInFlight` é o trinco que resolve os dois: só há uma escrita
     * pendente, o que sai da fila **sai**, e `pump()` é o único caminho que
     * escreve.
     */
    @SuppressLint("MissingPermission")
    private fun pump() {
        if (writeInFlight) return
        if (writeQueue.isEmpty()) return
        val g = gatt ?: run {
            writeQueue.clear()
            return
        }
        val ch = g.getService(serviceUuid)?.getCharacteristic(rxUuid) ?: run {
            writeQueue.clear()
            return
        }
        val next = writeQueue.removeFirst()
        writeInFlight = true
        if (!writeValue(g, ch, next.data, next.type)) {
            writeInFlight = false
            emit("error", null, "a fila de escrita bloqueou")
            return
        }
        // Com resposta, o `onCharacteristicWrite` avisa. Sem resposta, **não há
        // garantia de que venha** — e esperar por um callback que pode não
        // chegar é o que fazia a fila encravar. O `postDelayed` é a rede de
        // segurança: se o callback vier, `pump` já foi chamado e este é um
        // no-op; se não vier, este é o que destranca.
        if (next.type == BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE) {
            val r = Runnable {
                noRespRunnable = null
                writeInFlight = false
                pump()
            }
            noRespRunnable = r
            mainHandler.postDelayed(r, WRITE_NO_RESPONSE_TIMEOUT_MS)
        }
    }

    /** Há uma escrita pendente de resposta (ou à espera do seu tempo). */
    private var writeInFlight = false

    /** Handler do looper principal, partilhado pelo timeout de segurança. */
    private val mainHandler = android.os.Handler(context.mainLooper)

    /**
     * O `postDelayed` de segurança da escrita sem resposta, guardado para
     * poder ser cancelado.
     *
     * Sem o guardar, o timeout ficava agendado depois de a escrita já ter
     * concluído e disparava mais tarde: destrancava o `writeInFlight` de uma
     * escrita seguinte — que ainda estava em curso — e o `pump` escrevia por
     * cima dela. Guardar a referência é o que permite cancelá-lo quando o
     * callback chega (ou quando a ligação cai, em `cleanup`).
     */
    private var noRespRunnable: Runnable? = null

    /**
     * `writeCharacteristic` com `ByteArray` só existe do API 33 em diante. Abaixo
     * disso a via é a antiga, que escreve em `characteristic.value` e não
     * aceita o tipo como argumento — e a app tem de correr em Android 7, onde
     * esta chamada compila e rebenta em runtime.
     */
    @SuppressLint("MissingPermission")
    private fun writeValue(
        g: BluetoothGatt,
        ch: BluetoothGattCharacteristic,
        data: ByteArray,
        type: Int
    ): Boolean =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            // A sobrecarga de API 33 devolve um `int` de estado, nao um
            // `boolean` como a antiga. Sem esta comparacao os dois ramos do
            // `if` tinham tipos diferentes e o `if/else` inteiro nao
            // inferia `Boolean` - o compilador Kotlin chumbava a funcao.
            g.writeCharacteristic(ch, data, type) == BluetoothStatusCodes.SUCCESS
        } else {
            @Suppress("DEPRECATION")
            run {
                ch.writeType = type
                ch.value = data
                g.writeCharacteristic(ch)
            }
        }

    // ── API para o JS ─────────────────────────────────────────────────

    @ReactMethod
    fun hasPermissions(promise: Promise) {
        promise.resolve(granted())
    }

    @ReactMethod
    fun isBluetoothEnabled(promise: Promise) {
        promise.resolve(adapter?.isEnabled == true)
    }

    @ReactMethod
    fun startScan(seconds: Double, promise: Promise) {
        val a = adapter
        if (a == null) {
            promise.reject("NO_ADAPTER", "Este dispositivo nao tem adaptador Bluetooth")
            return
        }
        if (!granted()) {
            promise.reject("NO_PERMISSION", "Falta a permissao BLUETOOTH_SCAN")
            return
        }
        if (!a.isEnabled) {
            promise.reject("OFF", "O Bluetooth esta desligado")
            return
        }
        stopScanQuietly()
        // `SCAN_MODE_LOW_LATENCY` e o que faz aparecer o resultado em segundos.
        // O filtro pelo UUID do servico e o que evita encher a lista de dezenas
        // de relogios e fones que o Android anuncia continuamente.
        val filters = listOf(ScanFilter.Builder().setServiceUuid(ParcelUuid(serviceUuid)).build())
        val settings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            .build()
        val s = a.bluetoothLeScanner
        if (s == null) {
            promise.reject("NO_SCANNER", "O adaptador nao tem scanner BLE")
            return
        }
        scanner = s
        scanning.set(true)
        val cb = scanCallback()
        activeScan = cb
        s.startScan(filters, settings, cb)
        promise.resolve(true)
        if (seconds > 0) {
            // `postDelayed` sem `Handler` explicito usa a thread do looper
            // principal, que e onde o callback do scanner corre.
            android.os.Handler(context.mainLooper).postDelayed({
                stopScanQuietly()
            }, (seconds * 1000).toLong())
        }
    }

    @SuppressLint("MissingPermission")
    private fun scanCallback(): ScanCallback {
        return object : ScanCallback() {
            override fun onScanResult(callbackType: Int, result: ScanResult) {
                emitDevice(result.device)
            }

            override fun onBatchScanResults(results: MutableList<ScanResult>) {
                results.forEach { emitDevice(it.device) }
            }
        }
    }

    private fun emitDevice(device: BluetoothDevice) {
        val map: WritableMap = Arguments.createMap()
        map.putString("address", device.address)
        map.putString("name", device.name ?: "")
        emit("device", map, null)
    }

    @SuppressLint("MissingPermission")
    private fun stopScanQuietly() {
        if (!scanning.getAndSet(false)) return
        val s = scanner
        val cb = activeScan
        scanner = null
        activeScan = null
        if (s == null || cb == null) return
        try {
            // A **mesma** instância de `ScanCallback` que o `startScan` recebeu.
            // `stopScan` compara por identidade, e passar um callback novo — que
            // é o que `scanCallback()` devolvia — não pára nada: o scan
            // continuava, o telefone ia dormir com o rádio ligado, e a
            // `SecurityException` do API 31 só aparecia mais tarde, no meio de
            // outra coisa.
            s.stopScan(cb)
        } catch (_: SecurityException) {
            // A permissao pode ter sido revogada entre o start e o stop.
        }
    }

    @ReactMethod
    fun stopScan() {
        stopScanQuietly()
    }

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
        cleanup()
        try {
            @Suppress("DEPRECATION")
            val device = a.getRemoteDevice(address)
            gatt = device.connectGatt(context, false, gattCallback(), BluetoothDevice.TRANSPORT_LE)
        } catch (e: IllegalArgumentException) {
            // Endereco mal formado: e o que da quando o JS manda um nome em
            // vez do endereco, e a excecao e a unica pista.
            promise.reject("BAD_ADDRESS", "Endereco invalido: $address", e)
            return
        }
        promise.resolve(true)
    }

    @SuppressLint("MissingPermission")
    @ReactMethod
    fun disconnect() {
        stopScanQuietly()
        cleanup()
    }

    @SuppressLint("MissingPermission")
    private fun cleanup() {
        val g = gatt
        gatt = null
        resetRx()
        writeQueue.clear()
        // Um `postDelayed` de segurança ainda pendente chamaria `pump()` já
        // depois de o GATT fechado; cancelá-lo é o que evita esse pump tardio.
        noRespRunnable?.let { mainHandler.removeCallbacks(it) }
        noRespRunnable = null
        // O trinco também se abre: deixar `writeInFlight` a `true` era a
        // segunda forma do mesmo encravamento, e desta vez de forma
        // permanente — nenhuma escrita nova sairia enquanto a ligação não
        // morresse.
        writeInFlight = false
        if (g != null) {
            try {
                g.close()
            } catch (_: SecurityException) {
                // Sem permissao para fechar: o `close` logo apanha o leak.
            }
        }
    }

    @SuppressLint("MissingPermission")
    private fun discover(g: BluetoothGatt) {
        g.discoverServices()
    }

    /**
     * Liga a notificação de `tx` escrevendo no descritor CCC.
     *
     * `ENABLE_NOTIFICATION_VALUE` no CCC é o que faz o PC passar a responder.
     * Sem isto, `send` continua a funcionar e as respostas nunca aparecem — a
     * falha mais silenciosa do protocolo, e a razão de o `auth` ter de esperar
     * por isto.
     */
    @SuppressLint("MissingPermission")
    private fun subscribe(g: BluetoothGatt) {
        val ch = g.getService(serviceUuid)?.getCharacteristic(txUuid)
        if (ch == null) {
            emit("disconnected", null, "O PC nao tem a caracteristica de resposta")
            cleanup()
            return
        }
        if (!g.setCharacteristicNotification(ch, true)) {
            emit("disconnected", null, "O Android recusou a notificacao")
            cleanup()
            return
        }
        val ccc = ch.getDescriptor(cccUuid)
        if (ccc == null) {
            emit("disconnected", null, "Sem descritor CCC no PC")
            cleanup()
            return
        }
        @Suppress("DEPRECATION")
        ccc.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
        if (!g.writeDescriptor(ccc)) {
            emit("disconnected", null, "A escrita no CCC falhou")
            cleanup()
        }
    }

    @ReactMethod
    fun sendJson(json: String, withResponse: Boolean, promise: Promise) {
        val ok = send(json, withResponse)
        if (ok) promise.resolve(true) else promise.reject("SEND_FAILED", "Sem ligacao GATT")
    }

    /**
     * Envia o comando de `move` no caminho binário, sem JSON.
     *
     * 1 byte de opcode, e depois dois `int16` em décimos de pixel. O JSON
     * equivalente ocupa ~30 bytes e é partido em dois fragmentos; este cabe
     * numa escrita, o que numa rede de 60 Hz de gestos é a diferença entre o
     * rato seguir o dedo e ficar a pedir desculpa.
     */
    @ReactMethod
    fun sendMove(dxTenths: Int, dyTenths: Int, promise: Promise) {
        if (gatt == null) {
            promise.reject("SEND_FAILED", "Sem ligacao GATT")
            return
        }
        val buf = ByteBuffer.allocate(5)
        buf.put(OP_MOVE)
        buf.putShort(clamp16(dxTenths))
        buf.putShort(clamp16(dyTenths))
        val frame = ByteBuffer.allocate(2 + 5)
        frame.put(0)
        frame.put(5)
        frame.put(buf.array())
        // Passa pela mesma fila do `send`: um `move` a 60 Hz e um texto longo a
        // competir pela ligação é a situação normal, e cada um a escrever por si
        // sobrepunha-se — ou perdia-se o gesto. A fila drena uma escrita de
        // cada vez, cada uma no tipo com que foi pedida.
        enqueue(frame.array(), BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE)
        pump()
        // `true` quer dizer "entrou na fila", que é tudo o que o `move` pode
        // prometer: um gesto que ainda está à espera é um gesto que vai sair.
        // Devolver `false` aqui tirava do JS a confiança de que o gesto
        // entrou, e o `bleRemoteClient.ts` tratava isso como falha.
        promise.resolve(true)
    }

    private fun clamp16(v: Int): Short = v.coerceIn(-32768, 32767).toShort()

    @ReactMethod
    fun isConnected(promise: Promise) {
        promise.resolve(gatt != null)
    }

    // ── Sobrevivência a eventos ───────────────────────────────────────

    // NAO sao `override`: em RN 0.86 `BaseJavaModule`/`NativeModule` nao
    // declaram `addListener`/`removeListeners` (o `NativeEventEmitter` do JS
    // limita-se a chamar `this._nativeModule?.addListener(...)` por nome). Sao
    // exportados por `@ReactMethod` como os restantes. Com `override` o
    // compilador Kotlin chumbava com "'addListener' overrides nothing".
    @ReactMethod
    fun addListener(eventName: String) {
        // Os eventos sao enviados por `emit`; este metodo existe porque o
        // `NativeEventEmitter` do JS o exige. Sem ele o JS nao se queixa - a
        // falha aparece como "os eventos nunca chegam".
    }

    @ReactMethod
    fun removeListeners(count: Int) {
    }

    private fun emit(event: String, payload: Any?, error: String?) {
        val body: WritableMap = Arguments.createMap()
        if (payload is String) body.putString("message", payload)
        if (payload is WritableMap) body.putMap("device", payload)
        if (error != null) body.putString("error", error)
        try {
            context
                .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
                .emit(event, body)
        } catch (_: RuntimeException) {
            // O contexto JS já foi destruido (app a fechar). Perder um evento
            // aqui e melhor do que rebentar numa thread do Binder.
        }
    }

    /**
     * `BLUETOOTH_SCAN` e `BLUETOOTH_CONNECT` sao as duas metades do mesmo
     * pedido no Android 12+ (`neverForLocation`). Pedir uma sem a outra dá um
     * `SecurityException` no meio de um `startScan`, que é um sítio horrível
     * para ela aparecer: a stack aponta para o framework, não para o que
     * faltou.
     */
    private fun granted(): Boolean =
        context.checkSelfPermission("android.permission.BLUETOOTH_SCAN") ==
            PackageManager.PERMISSION_GRANTED &&
            context.checkSelfPermission("android.permission.BLUETOOTH_CONNECT") ==
            PackageManager.PERMISSION_GRANTED

    // ── Constantes do protocolo ───────────────────────────────────────

    private companion object {
        /** `0x01` = `move`. Tem de bater certo com `OP_MOVE` no PC. */
        const val OP_MOVE: Byte = 0x01

        /** Tecto da fila de escritas. Ver `enqueue`. */
        const val MAX_QUEUED_WRITES = 64

        /**
         * Quanto tempo se espera por um `onCharacteristicWrite` de uma escrita
         * **sem resposta**, antes de assumir que não vem.
         *
         * A MTU e a ligação de um telemóvel real dão para uma escrita em
         * poucos milissegundos; 60 ms é folga para um aparelho lento sem ser
         * uma pausa que se note a cada gesto. O caminho **com** resposta não
         * usa isto: espera pelo callback, como deve ser.
         */
        const val WRITE_NO_RESPONSE_TIMEOUT_MS = 60L
    }
}
