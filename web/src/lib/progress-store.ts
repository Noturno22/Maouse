import { list, put } from "@vercel/blob";
import { SEED_PROGRESS, sanitizeProgress, type ProgressData } from "@/lib/progress";

const BLOB_FILE = "progress.json";

export async function readProgress(): Promise<ProgressData> {
  try {
    if (!process.env.BLOB_READ_WRITE_TOKEN) return SEED_PROGRESS;
    const { blobs } = await list({ prefix: BLOB_FILE });
    if (blobs.length === 0) return SEED_PROGRESS;
    const res = await fetch(blobs[0].url, { cache: "no-store" });
    if (!res.ok) return SEED_PROGRESS;
    const raw: unknown = await res.json();
    return sanitizeProgress(raw);
  } catch {
    return SEED_PROGRESS;
  }
}

export async function writeProgress(data: ProgressData): Promise<void> {
  if (!process.env.BLOB_READ_WRITE_TOKEN) {
    throw new Error("BLOB_READ_WRITE_TOKEN nao definido no servidor");
  }
  await put(BLOB_FILE, JSON.stringify(data, null, 2), {
    access: "public",
    addRandomSuffix: false,
    contentType: "application/json",
  });
}