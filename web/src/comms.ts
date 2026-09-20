export type ChannelId = "internet" | "local_network" | "peer_relay" | "radio" | "satellite" | "store_and_forward";

export type ChannelStatus = {
  id: ChannelId;
  available: boolean;
  reason: string;
  requiresNative?: boolean;
};

export type SendOutcome = {
  ok: boolean;
  acknowledgement: boolean;
  channel: ChannelId;
  statusMessage: string;
  sos?: unknown;
};

const API = import.meta.env.VITE_API_BASE || "";
const HUB = import.meta.env.VITE_HUB_BASE || "http://localhost:8080";

export async function probeInternet(): Promise<ChannelStatus> {
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 2500);
    const res = await fetch(`${API}/api/v1/healthz`, { signal: ctrl.signal });
    clearTimeout(timer);
    return {
      id: "internet",
      available: res.ok,
      reason: res.ok ? "AbhaySetu emergency server reachable" : `Server responded HTTP ${res.status}`,
    };
  } catch {
    return { id: "internet", available: false, reason: "Internet unavailable." };
  }
}

export async function probeHub(): Promise<ChannelStatus> {
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 2500);
    const res = await fetch(`${HUB}/healthz`, { signal: ctrl.signal });
    clearTimeout(timer);
    return {
      id: "local_network",
      available: res.ok,
      reason: res.ok ? "Local emergency hub reachable" : "Local hub not responding",
    };
  } catch {
    return { id: "local_network", available: false, reason: "No local emergency hub detected." };
  }
}

export function webUnsupportedChannels(): ChannelStatus[] {
  return [
    {
      id: "peer_relay",
      available: false,
      requiresNative: true,
      reason: "Peer relay requires the AbhaySetu Android app (Bluetooth / Wi-Fi Direct).",
    },
    {
      id: "radio",
      available: false,
      requiresNative: true,
      reason: "Radio delivery requires a connected emergency radio gateway.",
    },
    {
      id: "satellite",
      available: false,
      requiresNative: true,
      reason: "Satellite delivery requires supported hardware or a satellite service. A browser cannot create a satellite link.",
    },
  ];
}

export async function snapshot(): Promise<ChannelStatus[]> {
  const [net, hub] = await Promise.all([probeInternet(), probeHub()]);
  return [net, hub, ...webUnsupportedChannels(), { id: "store_and_forward", available: true, reason: "Encrypted local queue on this device" }];
}

export function modeFromSnapshot(channels: ChannelStatus[]): string {
  if (channels.find((c) => c.id === "internet")?.available) return "ONLINE";
  if (channels.find((c) => c.id === "local_network")?.available) return "LOCAL_EMERGENCY_NETWORK";
  return "COMPLETELY_OFFLINE";
}

export async function sendSos(body: unknown): Promise<SendOutcome> {
  const channels = await snapshot();
  const internet = channels.find((c) => c.id === "internet");
  const hub = channels.find((c) => c.id === "local_network");
  const token = localStorage.getItem("abhaysetu.access") || "";
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  if (internet?.available) {
    try {
      const res = await fetch(`${API}/api/v1/sos`, { method: "POST", headers, body: JSON.stringify(body) });
      const data = await res.json();
      if (res.ok && data.acknowledged) {
        return {
          ok: true,
          acknowledgement: true,
          channel: "internet",
          statusMessage: data.honest_status_message || "SOS transmitted to AbhaySetu emergency server.",
          sos: data.sos,
        };
      }
      return { ok: false, acknowledgement: false, channel: "internet", statusMessage: data.detail || "Server did not acknowledge SOS." };
    } catch {
      /* fall through */
    }
  }

  if (hub?.available) {
    try {
      const res = await fetch(`${HUB}/api/sos`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const data = await res.json();
      if (res.ok && data.acknowledged) {
        return {
          ok: true,
          acknowledgement: true,
          channel: "local_network",
          statusMessage: data.honest_status_message || "SOS delivered to local emergency hub.",
          sos: data,
        };
      }
    } catch {
      /* fall through */
    }
  }

  return {
    ok: true,
    acknowledgement: false,
    channel: "store_and_forward",
    statusMessage:
      "SOS saved locally. No communication path is currently available. AbhaySetu will retry automatically when a communication path becomes available.",
  };
}
