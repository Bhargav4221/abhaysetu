import * as ed25519 from "@noble/ed25519";

function bytesToB64(bytes: Uint8Array): string {
  return btoa(String.fromCharCode(...bytes));
}

function b64ToBytes(value: string): Uint8Array {
  return Uint8Array.from(atob(value), (c) => c.charCodeAt(0));
}

export async function getOrCreateDeviceKeys(): Promise<{ publicKey: string; secretKey: string; deviceId: string }> {
  const existing = localStorage.getItem("abhaysetu.device");
  if (existing) return JSON.parse(existing);
  const privateKey = ed25519.utils.randomPrivateKey();
  const publicKey = await ed25519.getPublicKeyAsync(privateKey);
  const record = {
    publicKey: bytesToB64(publicKey),
    secretKey: bytesToB64(privateKey),
    deviceId: `DEV-${crypto.randomUUID().replace(/-/g, "").slice(0, 16).toUpperCase()}`,
  };
  localStorage.setItem("abhaysetu.device", JSON.stringify(record));
  return record;
}

export function canonicalJson(data: unknown): Uint8Array {
  const json = JSON.stringify(data, Object.keys(data as object).sort());
  return new TextEncoder().encode(json);
}

export async function signPayload(payload: Record<string, unknown>, secretKeyB64: string): Promise<string> {
  const sorted = JSON.parse(JSON.stringify(payload));
  const body = new TextEncoder().encode(stableStringify(sorted));
  const sig = await ed25519.signAsync(body, b64ToBytes(secretKeyB64));
  return bytesToB64(sig);
}

export function hashPayload(payload: Record<string, unknown>): Promise<string> {
  return crypto.subtle.digest("SHA-256", new TextEncoder().encode(stableStringify(payload))).then((buf) =>
    Array.from(new Uint8Array(buf))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("")
  );
}

export function generateSosId(): string {
  const year = new Date().getUTCFullYear();
  const rand = crypto.randomUUID().replace(/-/g, "").slice(0, 8).toUpperCase();
  return `SOS-${year}-${rand}`;
}

function stableStringify(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
  const obj = value as Record<string, unknown>;
  const keys = Object.keys(obj).sort();
  return `{${keys.map((k) => `${JSON.stringify(k)}:${stableStringify(obj[k])}`).join(",")}}`;
}
