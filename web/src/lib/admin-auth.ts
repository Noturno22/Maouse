import { createHmac, timingSafeEqual } from "crypto";

export const ADMIN_COOKIE = "maouse_admin_progress";
const SESSION_MAX_MS = 7 * 24 * 3600 * 1000;

function secret(): string {
  return process.env.ADMIN_SESSION_SECRET ?? process.env.ADMIN_TOKEN ?? "dev-admin-session";
}

function adminToken(): string {
  return process.env.ADMIN_TOKEN ?? "dev-admin-token";
}

function sign(value: string): string {
  return createHmac("sha256", secret()).update(value).digest("hex");
}

function safeEqual(a: string, b: string): boolean {
  const ab = Buffer.from(a, "utf8");
  const bb = Buffer.from(b, "utf8");
  return ab.length === bb.length && timingSafeEqual(ab, bb);
}

export function makeSession(now = Date.now()): string {
  const payload = String(now);
  return `${payload}.${sign(payload)}`;
}

export function verifySession(value: string | undefined | null): boolean {
  if (!value) return false;
  const idx = value.lastIndexOf(".");
  if (idx <= 0) return false;
  const payload = value.slice(0, idx);
  const mac = value.slice(idx + 1);
  const now = Number(payload);
  if (!Number.isFinite(now) || now <= 0) return false;
  if (!safeEqual(mac, sign(payload))) return false;
  return Date.now() - now <= SESSION_MAX_MS;
}

export function isAdminPassword(password: string): boolean {
  return safeEqual(password, adminToken());
}