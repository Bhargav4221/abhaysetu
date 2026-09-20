import { get, set, del, keys } from "idb-keyval";

export type QueuedSos = {
  sos_id: string;
  payload: Record<string, unknown>;
  digital_signature: string;
  created_at: string;
  attempts: number;
  last_error: string;
  status: "WAITING_FOR_COMMUNICATION" | "TRANSMITTING" | "DELIVERED" | "FAILED";
  honest_status_message: string;
  priority: string;
};

const PREFIX = "sos-queue:";

export async function enqueueSos(item: QueuedSos): Promise<void> {
  await set(PREFIX + item.sos_id, item);
}

export async function listQueue(): Promise<QueuedSos[]> {
  const all = await keys();
  const items: QueuedSos[] = [];
  for (const key of all) {
    if (String(key).startsWith(PREFIX)) {
      const item = await get<QueuedSos>(key);
      if (item) items.push(item);
    }
  }
  const rank = (p: string) => (p === "CRITICAL" ? 0 : p === "HIGH" ? 1 : 2);
  return items.sort((a, b) => rank(a.priority) - rank(b.priority) || a.created_at.localeCompare(b.created_at));
}

export async function updateQueued(sosId: string, patch: Partial<QueuedSos>): Promise<void> {
  const current = await get<QueuedSos>(PREFIX + sosId);
  if (!current) return;
  await set(PREFIX + sosId, { ...current, ...patch });
}

export async function removeQueued(sosId: string): Promise<void> {
  await del(PREFIX + sosId);
}
