import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { ADMIN_COOKIE, isAdminPassword, makeSession } from "@/lib/admin-auth";

export async function POST(request: Request) {
  const form = await request.formData();
  const password = String(form.get("password") ?? "");
  if (!password || !isAdminPassword(password)) {
    return NextResponse.json({ ok: false }, { status: 401 });
  }

  const store = await cookies();
  store.set(ADMIN_COOKIE, makeSession(), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 7 * 24 * 3600,
  });

  return NextResponse.json({ ok: true });
}