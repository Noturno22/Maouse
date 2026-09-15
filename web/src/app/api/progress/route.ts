import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { verifySession, ADMIN_COOKIE } from "@/lib/admin-auth";
import { sanitizeProgress } from "@/lib/progress";
import { readProgress, writeProgress } from "@/lib/progress-store";

export const dynamic = "force-dynamic";

export async function GET() {
  const data = await readProgress();
  return NextResponse.json(data);
}

export async function PUT(request: Request) {
  const store = await cookies();
  const cookie = store.get(ADMIN_COOKIE);
  if (!cookie || !verifySession(cookie.value)) {
    return NextResponse.json({ error: "nao_autenticado" }, { status: 401 });
  }

  let raw: unknown;
  try {
    raw = await request.json();
  } catch {
    return NextResponse.json({ error: "json_invalido" }, { status: 400 });
  }

  const data = sanitizeProgress(raw);
  data.updatedAt = new Date().toISOString();

  try {
    await writeProgress(data);
  } catch (err) {
    return NextResponse.json(
      { error: "erro_ao_guardar", detail: err instanceof Error ? err.message : String(err) },
      { status: 503 },
    );
  }

  return NextResponse.json({ ok: true, data });
}