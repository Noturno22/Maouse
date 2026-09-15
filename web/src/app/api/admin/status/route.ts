import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { ADMIN_COOKIE, verifySession } from "@/lib/admin-auth";

export const dynamic = "force-dynamic";

export async function GET() {
  const store = await cookies();
  const cookie = store.get(ADMIN_COOKIE);
  const ok = Boolean(cookie && verifySession(cookie.value));
  return NextResponse.json({ ok });
}