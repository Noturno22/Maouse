"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import Link from "next/link";
import {
  STATUS_ORDER,
  type Fase,
  type Marco,
  type Meta,
  type ProgressData,
  type ProgressStatus,
} from "@/lib/progress";
import { Wordmark } from "@/components/ui";
import { Reveal, SpotlightCard } from "@/components/effects";

const STATUS_LABEL: Record<ProgressStatus, string> = {
  pendente: "Pendente",
  em_curso: "Em curso",
  concluido: "Concluído",
};

const STATUS_TEXT: Record<ProgressStatus, string> = {
  pendente: "text-tech",
  em_curso: "text-warn",
  concluido: "text-success",
};

const STATUS_GLOW: Record<ProgressStatus, string> = {
  pendente: "",
  em_curso: "border-warn/40 shadow-[0_0_18px_rgba(255,170,60,0.18)]",
  concluido: "border-success/30 shadow-[0_0_18px_rgba(90,220,90,0.15)]",
};

const STATUS_PULSE: Record<ProgressStatus, string> = {
  pendente: "",
  em_curso: "pulse-dot relative",
  concluido: "",
};

function nextStatus(s: ProgressStatus): ProgressStatus {
  const i = STATUS_ORDER.indexOf(s);
  return STATUS_ORDER[(i + 1) % STATUS_ORDER.length];
}

function uid(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="font-mono text-[11px] tracking-widest text-tech uppercase">{label}</span>
      {children}
    </label>
  );
}

const inputCls =
  "w-full rounded-lg border border-line bg-night/60 px-3 py-2 text-sm text-ice outline-none transition-all placeholder:text-tech/70 focus:border-neon/50 focus:shadow-[0_0_0_3px_rgba(80,200,255,0.15)]";

const btnPrimary =
  "btn-shine inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-neon to-royal px-4 py-2.5 text-sm font-semibold text-night shadow-[0_0_20px_rgba(80,200,255,0.35)] transition-all hover:shadow-[0_0_32px_rgba(80,200,255,0.55)] disabled:cursor-not-allowed disabled:from-panel disabled:to-panel disabled:text-tech disabled:shadow-none";

const btnGhost =
  "inline-flex items-center justify-center rounded-lg border border-line bg-panel/60 px-3 py-2 text-sm text-tech transition-all hover:border-error/40 hover:text-error";

function StatusBadge({
  status,
  onClick,
}: {
  status: ProgressStatus;
  onClick?: () => void;
}) {
  const Tag = onClick ? "button" : "span";
  return (
    <Tag
      type={onClick ? "button" : undefined}
      onClick={onClick}
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border border-line bg-panel px-3 py-1 font-mono text-xs ${STATUS_TEXT[status]} ${STATUS_GLOW[status]} ${
        onClick ? "cursor-pointer transition-all hover:scale-105 hover:border-warn" : ""
      }`}
      title={onClick ? "Clicar para mudar o estado" : undefined}
    >
      <span className={`inline-flex h-1.5 w-1.5 rounded-full bg-current ${STATUS_PULSE[status]}`} />
      {STATUS_LABEL[status]}
    </Tag>
  );
}

function SectionTitle({ title, dot }: { title: string; dot: string }) {
  return (
    <h2 className="flex items-center gap-2 font-display text-lg font-semibold text-ice">
      <span
        className={`inline-flex h-2 w-2 rounded-full ${dot} shadow-[0_0_12px_currentColor]`}
      />
      <span className="text-gradient">{title}</span>
    </h2>
  );
}

function DeleteButton({ label, onClick }: { label: string; onClick?: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="shrink-0 rounded-lg border border-line px-2 py-1 text-sm text-tech transition-all hover:scale-105 hover:border-error/50 hover:text-error"
      aria-label={label}
    >
      ✕
    </button>
  );
}

export function AdminArea() {
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState(false);
  const [data, setData] = useState<ProgressData | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!authed) return;
    let cancelled = false;
    void fetch("/api/progress", { cache: "no-store" })
      .then((r) => (r.ok ? (r.json() as Promise<ProgressData>) : null))
      .then((j) => {
        if (cancelled) return;
        if (j) {
          setData(j);
        } else {
          setMessage({ ok: false, text: "Não foi possível carregar os dados." });
        }
      })
      .catch(() => {
        if (!cancelled) setMessage({ ok: false, text: "Não foi possível carregar os dados." });
      });
    return () => {
      cancelled = true;
    };
  }, [authed]);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/admin/status", { cache: "no-store" })
      .then((r) => r.json())
      .then((j: { ok: boolean }) => {
        if (cancelled) return;
        setAuthed(j.ok);
      })
      .catch(() => {
        if (!cancelled) setAuthed(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function onLogin(e: FormEvent) {
    e.preventDefault();
    setLoginError(false);
    const body = new FormData();
    body.set("password", password);
    void fetch("/api/admin/login", { method: "POST", body })
      .then(async (r) => {
        if (!r.ok) {
          setLoginError(true);
          return;
        }
        setAuthed(true);
        setPassword("");
      })
      .catch(() => setLoginError(true));
  }

  function markDirty() {
    setDirty(true);
    setMessage(null);
  }

  function patchFase(id: string, patch: Partial<Fase>) {
    if (!data) return;
    setData({ ...data, fases: data.fases.map((f) => (f.id === id ? { ...f, ...patch } : f)) });
    markDirty();
  }
  function addFase(nome: string, resumo: string) {
    if (!data || !nome.trim()) return;
    setData({
      ...data,
      fases: [...data.fases, { id: uid(), nome: nome.trim(), resumo: resumo.trim(), estado: "pendente" }],
    });
    markDirty();
  }
  function delFase(id: string) {
    if (!data) return;
    setData({
      ...data,
      fases: data.fases.filter((f) => f.id !== id),
      marcos: data.marcos.filter((m) => m.fase_id !== id),
    });
    markDirty();
  }

  function patchMarco(id: string, patch: Partial<Marco>) {
    if (!data) return;
    setData({ ...data, marcos: data.marcos.map((m) => (m.id === id ? { ...m, ...patch } : m)) });
    markDirty();
  }
  function addMarco(faseId: string, titulo: string) {
    if (!data || !titulo.trim()) return;
    setData({
      ...data,
      marcos: [...data.marcos, { id: uid(), fase_id: faseId, titulo: titulo.trim(), estado: "pendente" }],
    });
    markDirty();
  }
  function delMarco(id: string) {
    if (!data) return;
    setData({ ...data, marcos: data.marcos.filter((m) => m.id !== id) });
    markDirty();
  }

  function patchMeta(id: string, patch: Partial<Meta>) {
    if (!data) return;
    setData({ ...data, metas: data.metas.map((g) => (g.id === id ? { ...g, ...patch } : g)) });
    markDirty();
  }
  function addMeta(titulo: string, prazo: string) {
    if (!data || !titulo.trim()) return;
    setData({
      ...data,
      metas: [
        ...data.metas,
        { id: uid(), titulo: titulo.trim(), estado: "pendente", prazo: prazo.trim() || undefined },
      ],
    });
    markDirty();
  }
  function delMeta(id: string) {
    if (!data) return;
    setData({ ...data, metas: data.metas.filter((g) => g.id !== id) });
    markDirty();
  }

  async function save() {
    if (!data) return;
    setSaving(true);
    setMessage(null);
    try {
      const res = await fetch("/api/progress", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const json = (await res.json()) as { ok?: boolean; error?: string; detail?: string; data?: ProgressData };
      if (res.ok && json.data) {
        setData(json.data);
        setDirty(false);
        setMessage({ ok: true, text: "Guardado. A secção pública já mostra a nova progressão." });
      } else {
        setMessage({ ok: false, text: json.error === "nao_autenticado" ? "Sessão expirada. Volta a iniciar sessão." : `Erro ao guardar${json.detail ? ` (${json.detail})` : ""}.` });
      }
    } catch {
      setMessage({ ok: false, text: "Erro de rede ao guardar." });
    } finally {
      setSaving(false);
    }
  }

  async function logout() {
    try {
      await fetch("/api/admin/logout", { method: "POST" });
    } finally {
      setAuthed(false);
      setData(null);
      setDirty(false);
      setMessage(null);
    }
  }

  if (authed === null) {
    return (
      <main className="mx-auto flex min-h-screen max-w-4xl items-center justify-center px-5 py-12">
        <p className="font-mono text-sm text-tech">A verificar sessão…</p>
      </main>
    );
  }

  if (!authed) {
    return (
      <main className="relative mx-auto flex min-h-screen max-w-md flex-col items-center justify-center px-5 py-12">
        <Reveal className="w-full">
          <div className="border-animated glass-strong relative flex w-full flex-col items-center gap-6 rounded-3xl p-8">
            <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-3xl">
              <div className="hero-orb absolute -top-16 -right-10 h-44 w-44 rounded-full bg-neon/20 blur-3xl" />
              <div className="hero-orb absolute -bottom-16 -left-10 h-40 w-40 rounded-full bg-violet/20 blur-3xl [animation-delay:-7s]" />
            </div>

            <Link href="/" aria-label="Voltar ao site Mãouse" className="relative transition-transform hover:scale-105">
              <Wordmark compact />
            </Link>

            <div className="relative text-center">
              <h1 className="font-display text-2xl font-bold text-ice">
                Painel de <span className="text-gradient">progresso</span>
              </h1>
              <p className="mt-1 text-xs text-tech">Área reservada — Luar Studio Angola</p>
            </div>

            <form onSubmit={onLogin} className="relative flex w-full flex-col gap-3">
              <input
                type="password"
                autoFocus
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Palavra-passe"
                className={`${inputCls} py-3`}
              />
              {loginError && (
                <p className="flex items-center gap-2 text-sm text-error">
                  <span className="pulse-dot relative inline-flex h-1.5 w-1.5 rounded-full bg-error text-error" />
                  Palavra-passe incorreta.
                </p>
              )}
              <button type="submit" className={btnPrimary}>
                Entrar
              </button>
            </form>

            <Link
              href="/"
              className="relative text-sm text-tech transition-colors hover:text-neon"
            >
              ← Voltar ao site
            </Link>
          </div>
        </Reveal>
      </main>
    );
  }

  return (
    <main className="relative mx-auto flex min-h-screen max-w-4xl flex-col px-5 py-10">
      <header className="glass-strong sticky top-0 z-40 flex flex-wrap items-center justify-between gap-4 rounded-2xl px-5 py-4">
        <div className="flex items-center gap-3">
          <Link href="/" aria-label="Voltar ao site Mãouse" className="transition-transform hover:scale-105">
            <Wordmark compact />
          </Link>
          <div>
            <h1 className="font-display text-xl font-bold text-ice">
              Painel — <span className="text-gradient">Progresso &amp; Fases</span>
            </h1>
            <p className="text-xs text-tech">
              Editas aqui; a secção pública do site mostra a progressão.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={logout} className={btnGhost}>
            Sair
          </button>
          <button
            type="button"
            onClick={save}
            disabled={saving || !dirty}
            className={`${btnPrimary} ${dirty && !saving ? "" : "opacity-90"}`}
          >
            {dirty && !saving && (
              <span className="pulse-dot relative inline-flex h-1.5 w-1.5 rounded-full bg-night text-night" />
            )}
            {saving ? "A guardar…" : "Guardar alterações"}
          </button>
        </div>
      </header>

      {message && (
        <p
          className={`mt-4 rounded-xl border bg-panel/50 px-4 py-2.5 text-sm backdrop-blur ${
            message.ok ? "border-success/30 text-success" : "border-error/30 text-error"
          }`}
        >
          {message.ok && <span className="mr-2 text-success">✓</span>}
          {message.text}
        </p>
      )}

      {!data ? (
        <p className="mt-8 font-mono text-sm text-tech">A carregar dados…</p>
      ) : (
        <div className="mt-6 flex flex-col gap-8">
          <section className="flex flex-col gap-3">
            <SectionTitle title="Fases" dot="bg-neon text-neon" />
            {data.fases.map((f) => (
              <SpotlightCard
                key={f.id}
                className="flex flex-col gap-2 rounded-xl border border-line bg-panel/50 p-3 backdrop-blur transition-colors hover:border-neon/30"
              >
                <div className="relative flex items-center gap-2">
                  <input
                    className={inputCls}
                    value={f.nome}
                    onChange={(e) => patchFase(f.id, { nome: e.target.value })}
                    aria-label="Nome da fase"
                  />
                  <StatusBadge status={f.estado} onClick={() => patchFase(f.id, { estado: nextStatus(f.estado) })} />
                  <DeleteButton label="Eliminar fase" onClick={() => delFase(f.id)} />
                </div>
                <div className="relative">
                  <textarea
                    className={`${inputCls} min-h-16 resize-y`}
                    value={f.resumo}
                    onChange={(e) => patchFase(f.id, { resumo: e.target.value })}
                    placeholder="Resumo da fase"
                    aria-label="Resumo da fase"
                  />
                </div>
              </SpotlightCard>
            ))}
            <AddPhaseForm onAdd={addFase} />
          </section>

          <section className="flex flex-col gap-3">
            <SectionTitle title="Marcos" dot="bg-royal text-royal" />
            {data.marcos.map((m) => (
              <SpotlightCard
                key={m.id}
                className="flex flex-col gap-2 rounded-xl border border-line bg-panel/50 p-3 backdrop-blur transition-colors hover:border-neon/30"
              >
                <div className="relative flex items-center gap-2">
                  <input
                    className={inputCls}
                    value={m.titulo}
                    onChange={(e) => patchMarco(m.id, { titulo: e.target.value })}
                    aria-label="Título do marco"
                  />
                  <StatusBadge status={m.estado} onClick={() => patchMarco(m.id, { estado: nextStatus(m.estado) })} />
                  <DeleteButton label="Eliminar marco" onClick={() => delMarco(m.id)} />
                </div>
                <div className="relative flex items-center gap-2">
                  <select
                    className={`${inputCls} w-auto bg-night/60`}
                    value={m.fase_id}
                    onChange={(e) => patchMarco(m.id, { fase_id: e.target.value })}
                    aria-label="Fase do marco"
                  >
                    {data.fases.length ? (
                      data.fases.map((f) => (
                        <option key={f.id} value={f.id}>
                          {f.nome}
                        </option>
                      ))
                    ) : (
                      <option value="">Sem fases</option>
                    )}
                  </select>
                  {m.nota !== undefined && (
                    <input
                      className={inputCls}
                      value={m.nota}
                      onChange={(e) => patchMarco(m.id, { nota: e.target.value })}
                      placeholder="Nota"
                      aria-label="Nota do marco"
                    />
                  )}
                </div>
              </SpotlightCard>
            ))}
            <AddMarcoForm fases={data.fases} onAdd={addMarco} />
          </section>

          <section className="flex flex-col gap-3">
            <SectionTitle title="Metas" dot="bg-gold text-gold" />
            {data.metas.map((g) => (
              <SpotlightCard
                key={g.id}
                className="flex items-center gap-2 rounded-xl border border-line bg-panel/50 p-3 backdrop-blur transition-colors hover:border-neon/30"
              >
                <div className="relative flex flex-1 items-center gap-2">
                  <input
                    className={inputCls}
                    value={g.titulo}
                    onChange={(e) => patchMeta(g.id, { titulo: e.target.value })}
                    aria-label="Título da meta"
                  />
                  <input
                    className={`${inputCls} w-36`}
                    value={g.prazo ?? ""}
                    onChange={(e) => patchMeta(g.id, { prazo: e.target.value })}
                    placeholder="Prazo"
                    aria-label="Prazo da meta"
                  />
                </div>
                <div className="relative">
                  <StatusBadge status={g.estado} onClick={() => patchMeta(g.id, { estado: nextStatus(g.estado) })} />
                </div>
                <div className="relative">
                  <DeleteButton label="Eliminar meta" onClick={() => delMeta(g.id)} />
                </div>
              </SpotlightCard>
            ))}
            <AddMetaForm onAdd={addMeta} />
          </section>
        </div>
      )}

      <footer className="mt-10 border-t border-line/60 pt-5 text-center">
        <Link href="/" className="nav-link text-sm text-tech transition-colors hover:text-neon">
          ← Voltar ao site
        </Link>
      </footer>
    </main>
  );
}

function addBtn() {
  return "btn-shine inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-neon/50 bg-neon/10 px-3 py-2 text-sm text-neon transition-all hover:bg-neon hover:text-night hover:shadow-[0_0_24px_rgba(80,200,255,0.45)]";
}

function AddPhaseForm({ onAdd }: { onAdd: (nome: string, resumo: string) => void }) {
  const [nome, setNome] = useState("");
  const [resumo, setResumo] = useState("");
  return (
    <form
      className="flex flex-col gap-2 rounded-xl border border-dashed border-neon/25 bg-panel/30 p-3 backdrop-blur transition-colors focus-within:border-neon/50"
      onSubmit={(e) => {
        e.preventDefault();
        onAdd(nome, resumo);
        setNome("");
        setResumo("");
      }}
    >
      <div className="flex items-center gap-2">
        <Field label="Nova fase">
          <input className={inputCls} value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Nome da fase" />
        </Field>
        <button type="submit" className={`${addBtn()} mt-5`}>
          + Adicionar
        </button>
      </div>
      <Field label="Resumo">
        <textarea className={`${inputCls} min-h-14 resize-y`} value={resumo} onChange={(e) => setResumo(e.target.value)} placeholder="Resumo (opcional)" />
      </Field>
    </form>
  );
}

function AddMarcoForm({ fases, onAdd }: { fases: Fase[]; onAdd: (faseId: string, titulo: string) => void }) {
  const [titulo, setTitulo] = useState("");
  const [faseId, setFaseId] = useState(fases[0]?.id ?? "");
  return (
    <form
      className="flex items-end gap-2 rounded-xl border border-dashed border-neon/25 bg-panel/30 p-3 backdrop-blur transition-colors focus-within:border-neon/50"
      onSubmit={(e) => {
        e.preventDefault();
        onAdd(faseId, titulo);
        setTitulo("");
      }}
    >
      <Field label="Novo marco">
        <input className={inputCls} value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder="Título do marco" />
      </Field>
      {fases.length > 0 && (
        <Field label="Fase">
          <select className={`${inputCls} w-auto bg-night/60`} value={faseId} onChange={(e) => setFaseId(e.target.value)}>
            {fases.map((f) => (
              <option key={f.id} value={f.id}>
                {f.nome}
              </option>
            ))}
          </select>
        </Field>
      )}
      <button type="submit" className={`${addBtn()} mb-0.5`}>
        + Adicionar
      </button>
    </form>
  );
}

function AddMetaForm({ onAdd }: { onAdd: (titulo: string, prazo: string) => void }) {
  const [titulo, setTitulo] = useState("");
  const [prazo, setPrazo] = useState("");
  return (
    <form
      className="flex items-end gap-2 rounded-xl border border-dashed border-neon/25 bg-panel/30 p-3 backdrop-blur transition-colors focus-within:border-neon/50"
      onSubmit={(e) => {
        e.preventDefault();
        onAdd(titulo, prazo);
        setTitulo("");
        setPrazo("");
      }}
    >
      <Field label="Nova meta">
        <input className={inputCls} value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder="Título da meta" />
      </Field>
      <Field label="Prazo">
        <input className={`${inputCls} w-36`} value={prazo} onChange={(e) => setPrazo(e.target.value)} placeholder="Prazo (opcional)" />
      </Field>
      <button type="submit" className={`${addBtn()} mb-0.5`}>
        + Adicionar
      </button>
    </form>
  );
}