package com.maouse.mobile

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.net.wifi.WifiManager
import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.bridge.WritableMap
import com.facebook.react.modules.core.DeviceEventManagerModule
import java.net.InetAddress
import java.util.concurrent.atomic.AtomicBoolean

/**
 * MdnsDiscoveryModule: encontra o PC por mDNS, para o telefone não escrever um IP à mão.
 *
 * O outro lado é `core/discovery.py`, que anuncia `_maouse._tcp` por mDNS. Aqui
 * o `NsdManager` do Android faz o papel do `zeroconf`: descobre o serviço e
 * entrega o endereço e a porta onde o WebSocket está a ouvir.
 *
 * ## As três coisas que o `NsdManager` não diz
 *
 * 1. **O `serviceName` chega a ser só o rótulo.** O Android entrega
 *    `Maouse 1` onde o PC publicou `Maouse 1._maouse._tcp.local.`. Ligar
 *    diretamente dá `UnknownHostException`; é preciso acrescentar o sufixo.
 *
 * 2. **A resolução é assíncrona e tem de ser explicitamente pedida.**
 *    `onServiceFound` dá os metadados anunciados, e o endereço só depois de
 *    `resolveService`. Pedir o IP no `onServiceFound` dá `null` — e um `null`
 *    que se parece com "o PC está noutra sub-rede".
 *
 * 3. **O `NsdManager` precisa do WiFi ligado, mesmo em `WIFI_P2P` / Ethernet.**
 *    Este é o motivo de o `INTERNET` não chegar: sem um interface WiFi, o
 *    Android não faz multicast, e o multicast é o mDNS inteiro. Com o
 *    telemóvel em dados móveis e o PC em Ethernet, a descoberta simplesmente
 *    não encontra nada — e o utilizador conclui que o PC está errado.
 */
class MdnsDiscoveryModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    override fun getName(): String = "MdnsDiscovery"

    private val context: ReactApplicationContext = reactContext

    private val nsd: NsdManager? by lazy {
        context.getSystemService(Context.NSD_SERVICE) as? NsdManager
    }

    /** `NsdManager` só tem uma descoberta activa; o token cancela-a. */
    private var listener: NsdManager.DiscoveryListener? = null
    private var active = AtomicBoolean(false)

    /** Endereços já vistos, para não repetir a mesma entrada a cada 30 s. */
    private val seen = LinkedHashMap<String, String>()

    private companion object {
        /** Tem de bater certo com `SERVICE_TYPE` em `core/discovery.py`. */
        const val SERVICE_TYPE = "_maouse._tcp."
        const val SUFFIX = "._maouse._tcp.local."
    }

    @ReactMethod
    fun isSupported(promise: Promise) {
        promise.resolve(nsd != null)
    }

    @ReactMethod
    fun start(promise: Promise) {
        val mgr = nsd
        if (mgr == null) {
            promise.reject("NO_NSD", "Este dispositivo nao tem NsdManager")
            return
        }
        stop()
        seen.clear()
        active.set(true)
        val l = object : NsdManager.DiscoveryListener {
            override fun onDiscoveryStarted(serviceType: String?) {
                emit("state", null, null, "running")
            }

            override fun onServiceFound(serviceInfo: NsdServiceInfo?) {
                val info = serviceInfo ?: return
                // `onServiceFound` traz o que foi anunciado, que normalmente
                // não inclui o endereço. Pedi-lo aqui daria `null`; é preciso
                // `resolveService`, e o resultado volta em
                // `onServiceResolved`.
                //
                // `resolveService` devolve `void` (nao `boolean`): o Android
                // so recusa lancando `IllegalArgumentException` - a falha de
                // rede chega em `onResolveFailed`. O `if (mgr.resolveService
                // (...))` que aqui estava nao compilava, e para alem disso
                // tratava `Unit` como se fosse a confirmacao do pedido.
                try {
                    mgr.resolveService(info, resolveListener(mgr))
                } catch (e: IllegalArgumentException) {
                    emit("error", null, "Nao foi possivel resolver ${info.serviceName}", null)
                }
            }

            override fun onServiceLost(serviceInfo: NsdServiceInfo?) {
                val name = serviceInfo?.serviceName ?: return
                seen.remove(name)
                val map: WritableMap = Arguments.createMap()
                map.putString("name", name)
                emit("lost", map, null, null)
            }

            override fun onDiscoveryStopped(serviceType: String?) {
                emit("state", null, null, "stopped")
            }

            override fun onStartDiscoveryFailed(serviceType: String?, errorCode: Int) {
                active.set(false)
                // `FAILURE_ALREADY_ACTIVE` (3) é o `stop` anterior a ainda não
                // ter terminado. Não é um erro: o `stop` novo vai resolver.
                if (errorCode != 3) {
                    emit("error", null, "Descoberta nao arrancou (codigo $errorCode)", null)
                }
            }

            override fun onStopDiscoveryFailed(serviceType: String?, errorCode: Int) {
                emit("error", null, "Descoberta nao parou (codigo $errorCode)", null)
            }
        }
        listener = l
        // `discoverServices` tambem devolve `void`: nao ha boolean de
        // "aceite". O `promise.resolve(true)` aqui significa so "o pedido foi
        // entregue"; se o Android recusar vem `onStartDiscoveryFailed`, e se
        // ele outright lanca `IllegalArgumentException` apanha-se a seguir.
        try {
            mgr.discoverServices(SERVICE_TYPE, NsdManager.PROTOCOL_DNS_SD, l)
            promise.resolve(true)
        } catch (e: IllegalArgumentException) {
            active.set(false)
            listener = null
            promise.reject("NO_START", "O Android recusou comecar a descoberta")
        }
    }

    private fun resolveListener(mgr: NsdManager): NsdManager.ResolveListener {
        return object : NsdManager.ResolveListener {
            override fun onResolveFailed(info: NsdServiceInfo?, errorCode: Int) {
                emit("error", null, "Resolucao falhou (codigo $errorCode)", null)
            }

            override fun onServiceResolved(info: NsdServiceInfo?) {
                val svc = info ?: return
                val host: InetAddress? = svc.host
                val address = host?.hostAddress ?: return
                val full = normalise(svc.serviceName)
                val key = "$full|$address|${svc.port}"
                if (seen.containsKey(key)) return
                seen[key] = full

                val map: WritableMap = Arguments.createMap()
                map.putString("name", full)
                map.putString("host", address)
                map.putInt("port", svc.port)
                // Os TXT do PC: `v` (versão do protocolo) e `id`. O token
                // nunca cá vem — ver o docstring de `core/discovery.py`.
                for (entry in svc.attributes.entries) {
                    val key0 = entry.key
                    val v = entry.value
                    map.putString(
                        "txt_" + key0,
                        if (v == null) "" else String(v, Charsets.UTF_8)
                    )
                }
                emit("found", map, null, null)
            }
        }
    }

    /**
     * O `NsdManager` pode devolver o rótulo sem o sufixo.
     *
     * `Maouse 1` e `Maouse 1._maouse._tcp.local.` são o mesmo serviço, e ligar
     * ao primeiro dá `UnknownHostException`. Guardar a chave errada também
     * duplica a entrada na lista, porque o próximo `onServiceFound` traz o
     * nome completo.
     */
    private fun normalise(serviceName: String?): String {
        val raw = serviceName ?: return ""
        return if (raw.endsWith(SUFFIX)) raw else raw + SUFFIX
    }

    @ReactMethod
    fun stop() {
        val l = listener ?: return
        listener = null
        active.set(false)
        try {
            nsd?.stopServiceDiscovery(l)
        } catch (_: Exception) {
            // Já parada: `stop` sem `start` é o caminho normal do
            // unmount do componente React.
        }
    }

    /**
     * Diz se há WiFi ligado.
     *
     * Vale a pena mostrar ao utilizador: sem isto, "não encontra o PC" e "o PC
     * está mal configurado" são indistinguíveis, e o problema é quase sempre o
     * telemóvel em dados móveis com o PC em Ethernet.
     */
    @ReactMethod
    fun hasWifi(promise: Promise) {
        try {
            @Suppress("DEPRECATION")
            val wm = context.getSystemService(Context.WIFI_SERVICE) as? WifiManager
            promise.resolve(wm?.isWifiEnabled == true)
        } catch (_: SecurityException) {
            promise.resolve(false)
        }
    }

    // NAO sao `override`: em RN 0.86 `BaseJavaModule`/`NativeModule` nao
    // declaram `addListener`/`removeListeners`. Sao exportados por
    // `@ReactMethod`; sem eles o `NativeEventEmitter` do JS nao regista o
    // modulo e os eventos nao chegam - sem erro nenhum.
    @ReactMethod
    fun addListener(eventName: String) {
    }

    @ReactMethod
    fun removeListeners(count: Int) {
    }

    private fun emit(event: String, payload: Any?, error: String?, state: String?) {
        val body: WritableMap = Arguments.createMap()
        if (payload is WritableMap) body.putMap("service", payload)
        if (state != null) body.putString("state", state)
        if (error != null) body.putString("error", error)
        try {
            context
                .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
                .emit(event, body)
        } catch (_: RuntimeException) {
            // Contexto JS destruído (app a fechar).
        }
    }
}
