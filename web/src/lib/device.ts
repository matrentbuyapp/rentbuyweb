const STORAGE_KEY = "device_id";

export function getDeviceId(): string {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return stored;
    const id = crypto.randomUUID();
    localStorage.setItem(STORAGE_KEY, id);
    return id;
  } catch {
    // SSR or storage blocked — return ephemeral ID
    return crypto.randomUUID();
  }
}
