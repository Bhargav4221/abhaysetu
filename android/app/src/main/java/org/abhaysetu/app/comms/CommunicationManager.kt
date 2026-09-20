package org.abhaysetu.app.comms

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

enum class Channel { INTERNET, LOCAL_NETWORK, PEER_RELAY, RADIO, SATELLITE, STORE_AND_FORWARD }

data class Capability(
    val channel: Channel,
    val available: Boolean,
    val reason: String
)

data class SendResult(
    val ok: Boolean,
    val ack: Boolean,
    val channel: Channel,
    val message: String
)

interface CommunicationAdapter {
    val channel: Channel
    suspend fun capabilities(): Capability
    suspend fun send(payload: JSONObject, signature: String): SendResult
}

class InternetAdapter(private val context: Context, private val baseUrl: String) : CommunicationAdapter {
    override val channel = Channel.INTERNET
    private val http = OkHttpClient.Builder().callTimeout(12, TimeUnit.SECONDS).build()

    override suspend fun capabilities(): Capability = withContext(Dispatchers.IO) {
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val net = cm.activeNetwork
        val caps = net?.let { cm.getNetworkCapabilities(it) }
        val hasInternet = caps?.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) == true
        if (!hasInternet) return@withContext Capability(channel, false, "Internet unavailable.")
        runCatching {
            val req = Request.Builder().url("$baseUrl/api/v1/healthz").build()
            http.newCall(req).execute().use { res ->
                Capability(channel, res.isSuccessful, if (res.isSuccessful) "AbhaySetu emergency server reachable" else "Server HTTP ${res.code}")
            }
        }.getOrElse { Capability(channel, false, "Internet unavailable.") }
    }

    override suspend fun send(payload: JSONObject, signature: String): SendResult = withContext(Dispatchers.IO) {
        val body = JSONObject()
            .put("payload", payload)
            .put("digital_signature", signature)
            .put("received_via", "internet")
            .toString()
            .toRequestBody("application/json".toMediaType())
        val req = Request.Builder().url("$baseUrl/api/v1/sos").post(body).build()
        runCatching {
            http.newCall(req).execute().use { res ->
                val json = JSONObject(res.body?.string().orEmpty())
                val ack = res.isSuccessful && json.optBoolean("acknowledged")
                SendResult(
                    ok = ack,
                    ack = ack,
                    channel = channel,
                    message = if (ack) json.optString("honest_status_message", "SOS transmitted to AbhaySetu emergency server.")
                    else json.optString("detail", "Server did not acknowledge SOS.")
                )
            }
        }.getOrElse { SendResult(false, false, channel, "Internet unavailable.") }
    }
}

class LocalNetworkAdapter(private val hubUrl: String) : CommunicationAdapter {
    override val channel = Channel.LOCAL_NETWORK
    private val http = OkHttpClient.Builder().callTimeout(8, TimeUnit.SECONDS).build()

    override suspend fun capabilities(): Capability = withContext(Dispatchers.IO) {
        runCatching {
            val req = Request.Builder().url("$hubUrl/healthz").build()
            http.newCall(req).execute().use { res ->
                Capability(channel, res.isSuccessful, if (res.isSuccessful) "Local emergency hub reachable" else "Local hub not responding")
            }
        }.getOrElse { Capability(channel, false, "No local emergency hub detected.") }
    }

    override suspend fun send(payload: JSONObject, signature: String): SendResult = withContext(Dispatchers.IO) {
        val body = JSONObject().put("payload", payload).put("digital_signature", signature).put("received_via", "local_network")
            .toString().toRequestBody("application/json".toMediaType())
        val req = Request.Builder().url("$hubUrl/api/sos").post(body).build()
        runCatching {
            http.newCall(req).execute().use { res ->
                val json = JSONObject(res.body?.string().orEmpty())
                val ack = res.isSuccessful && json.optBoolean("acknowledged")
                SendResult(ack, ack, channel, if (ack) json.optString("honest_status_message", "SOS delivered to local emergency hub.") else "Local hub did not acknowledge SOS.")
            }
        }.getOrElse { SendResult(false, false, channel, "Local hub unreachable.") }
    }
}

class BluetoothAdapter(private val scanner: NearbyScanner) : CommunicationAdapter {
    override val channel = Channel.PEER_RELAY
    override suspend fun capabilities(): Capability {
        val peers = scanner.discover(budgetMs = 4000)
        return if (peers.isNotEmpty()) Capability(channel, true, "Nearby AbhaySetu device detected")
        else Capability(channel, false, "No nearby AbhaySetu peer found. Peer relay is not assumed.")
    }

    override suspend fun send(payload: JSONObject, signature: String): SendResult {
        val ok = scanner.sendToPeer(payload, signature)
        return if (ok.ack) SendResult(true, true, channel, "SOS relayed through a nearby AbhaySetu device.")
        else SendResult(false, false, channel, ok.detail)
    }
}

class RadioHardwareAdapter : CommunicationAdapter {
    override val channel = Channel.RADIO
    override suspend fun capabilities() = Capability(channel, false, "No radio gateway connected. External hardware required.")
    override suspend fun send(payload: JSONObject, signature: String) =
        SendResult(false, false, channel, "Radio gateway not available.")
}

class SatelliteHardwareAdapter : CommunicationAdapter {
    override val channel = Channel.SATELLITE
    override suspend fun capabilities() =
        Capability(channel, false, "Satellite communication requires supported hardware or a provider. This phone software cannot create a satellite link by itself.")
    override suspend fun send(payload: JSONObject, signature: String) =
        SendResult(false, false, channel, "Satellite communication is not available on this device.")
}

class StoreAndForwardAdapter : CommunicationAdapter {
    override val channel = Channel.STORE_AND_FORWARD
    override suspend fun capabilities() = Capability(channel, true, "Encrypted local SOS queue")
    override suspend fun send(payload: JSONObject, signature: String) = SendResult(
        true,
        false,
        channel,
        "SOS saved locally. No communication path is currently available. AbhaySetu will retry automatically when a communication path becomes available."
    )
}

class CommunicationManager(private val adapters: List<CommunicationAdapter>) {
    suspend fun snapshot(): List<Capability> = adapters.map { it.capabilities() }

    suspend fun transmit(payload: JSONObject, signature: String): SendResult {
        for (adapter in adapters) {
            if (adapter.channel == Channel.STORE_AND_FORWARD) continue
            val cap = adapter.capabilities()
            if (!cap.available) continue
            val result = adapter.send(payload, signature)
            if (result.ack) return result
        }
        return adapters.first { it.channel == Channel.STORE_AND_FORWARD }.send(payload, signature)
    }
}

data class PeerSend(val ack: Boolean, val detail: String)

interface NearbyScanner {
    suspend fun discover(budgetMs: Long): List<String>
    suspend fun sendToPeer(payload: JSONObject, signature: String): PeerSend
}
