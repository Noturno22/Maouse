"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useLang } from "@/components/lang";
import { Icon, SectionHeader } from "@/components/ui";
import { Counter, Reveal } from "@/components/effects";
import { sectionId } from "@/lib/sections";
import { LANG_LOCALE, type Lang } from "@/lib/i18n";
import type { Fase, Marco, Meta, ProgressData, ProgressStatus } from "@/lib/progress";

const STATUS_TEXT: Record<ProgressStatus, string> = {
  pendente: "text-tech",
  em_curso: "text-warn",
  concluido: "text-success",
};

const STATUS_DOT: Record<ProgressStatus, string> = {
  pendente: "",
  em_curso: "pulse-dot relative",
  concluido: "",
};

const LEGEND_ORDER: ProgressStatus[] = ["concluido", "em_curso", "pendente"];
const GROUP_ORDER: ProgressStatus[] = ["em_curso", "pendente", "concluido"];

function StatusBadge({ status, label }: { status: ProgressStatus; label: string }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border border-line bg-panel px-2.5 py-0.5 font-mono text-[11px] tracking-wide ${STATUS_TEXT[status]} ${
        status === "em_curso" ? "border-warn/40 shadow-[0_0_18px_rgba(255,170,60,0.15)]" : ""
      } ${status === "concluido" ? "border-success/30 shadow-[0_0_18px_rgba(90,220,90,0.12)]" : ""}`}
    >
      <span className={`inline-flex h-1.5 w-1.5 rounded-full bg-current ${STATUS_DOT[status]}`} />
      {label}
    </span>
  );
}

function formatDate(iso: string | null, lang: Lang): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(LANG_LOCALE[lang], {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "—";
  }
}

function ProgressBar({ pct, className = "" }: { pct: number; className?: string }) {
  const width = Math.min(100, Math.max(0, pct));
  return (
    <div className={`h-1.5 w-full overflow-hidden rounded-full bg-night ${className}`}>
      <div
        className="h-full rounded-full bg-gradient-to-r from-success to-neon transition-all duration-700"
        style={{ width: `${width}%` }}
      />
    </div>
  );
}

function StateDot({ estado }: { estado: ProgressStatus }) {
  if (estado === "concluido") {
    return (
      <span className="mt-1 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-success/30 bg-success/10 text-success">
        <Icon name="check" className="h-3 w-3" />
      </span>
    );
  }
  if (estado === "em_curso") {
    return <span className="pulse-dot relative mt-2.5 inline-flex h-2 w-2 shrink-0 rounded-full bg-warn" />;
  }
  return <span className="mt-2.5 inline-flex h-2 w-2 shrink-0 rounded-full bg-tech/50" />;
}

function StatCard({ value, label, children }: { value: string; label: string; children?: ReactNode }) {
  return (
    <div className="rounded-2xl border border-line bg-panel/50 p-5 backdrop-blur">
      <p className="font-display text-3xl font-bold text-ice">
        <Counter value={value} />
      </p>
      <p className="mt-1 font-mono text-[11px] tracking-widest text-tech uppercase">{label}</p>
      {children}
    </div>
  );
}

function MarcoRow({ marco, label }: { marco: Marco; label: string }) {
  return (
    <li className="flex items-start justify-between gap-3 py-2 transition-colors hover:bg-white/[0.03]">
      <span className="flex min-w-0 flex-1 items-start gap-2.5 text-sm leading-6 text-ice">
        <StateDot estado={marco.estado} />
        <span>
          {marco.titulo}
          {marco.nota ? <span className="block text-xs text-tech">{marco.nota}</span> : null}
        </span>
      </span>
      <StatusBadge status={marco.estado} label={label} />
    </li>
  );
}

function MarcoGroup({
  label,
  marcos,
  statusLabel,
}: {
  label: string;
  marcos: Marco[];
  statusLabel: (s: ProgressStatus) => string;
}) {
  if (marcos.length === 0) return null;
  return (
    <li>
      <p className="flex items-center gap-2 px-1 pt-4 font-mono text-[11px] tracking-widest text-tech uppercase">
        {label}
        <span className="rounded-md border border-line bg-night px-1.5 py-0.5 font-mono text-[10px] text-neon">
          {marcos.length}
        </span>
      </p>
      <ul className="divide-y divide-line/40">
        {marcos.map((m) => (
          <MarcoRow key={m.id} marco={m} label={statusLabel(m.estado)} />
        ))}
      </ul>
    </li>
  );
}

function MetaRow({ meta, label }: { meta: Meta; label: string }) {
  return (
    <li className="flex items-start justify-between gap-3 py-2.5 transition-colors hover:bg-white/[0.03]">
      <span className="flex min-w-0 flex-1 items-start gap-2.5 text-sm leading-6 text-ice">
        <StateDot estado={meta.estado} />
        <span>
          {meta.titulo}
          {meta.prazo ? (
            <span className="ml-2 inline-block rounded-md border border-line bg-night px-1.5 py-0.5 font-mono text-[11px] text-neon">
              {meta.prazo}
            </span>
          ) : null}
        </span>
      </span>
      <StatusBadge status={meta.estado} label={label} />
    </li>
  );
}

export function ProgressSection() {
  const { lang, t } = useLang();
  const [data, setData] = useState<ProgressData | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void fetch("/api/progress", { cache: "no-store" })
      .then((r) => (r.ok ? (r.json() as Promise<ProgressData>) : null))
      .then((j) => {
        if (!cancelled) setData(j);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const statusLabel = (s: ProgressStatus) => t.progress.byStatus[s];

  const groupLabel = (s: ProgressStatus) =>
    s === "em_curso" ? t.progress.inProgressLabel : s === "pendente" ? t.progress.todoLabel : t.progress.doneLabel;

  return (
    <section id={sectionId(lang, "progress")} className="scroll-mt-24 border-t border-line/60 py-20 lg:py-28">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal>
          <SectionHeader tag={t.progress.tag} title={t.progress.title} sub={t.progress.sub} />
        </Reveal>

        {error ? (
          <p className="mt-8 text-center text-sm text-error">{t.progress.error}</p>
        ) : data ? (
          <>
            <Reveal delay={80}>
              <p className="mt-8 text-center font-mono text-xs tracking-widest text-tech uppercase">
                <span className="pulse-dot relative mr-2 inline-flex h-1.5 w-1.5 rounded-full bg-neon text-neon align-middle" />
                {t.progress.updated} {formatDate(data.updatedAt, lang)}
              </p>
            </Reveal>

            <Reveal delay={120}>
              <div className="mt-8 flex flex-wrap items-center justify-center gap-x-5 gap-y-2">
                <span className="font-mono text-[11px] tracking-widest text-tech uppercase">
                  {t.progress.statusHint}
                </span>
                {LEGEND_ORDER.map((s) => (
                  <StatusBadge key={s} status={s} label={statusLabel(s)} />
                ))}
              </div>
            </Reveal>

            {(() => {
              const totalMarcos = data.marcos.length;
              const doneMarcos = data.marcos.filter((m) => m.estado === "concluido").length;
              const activeMarcos = data.marcos.filter((m) => m.estado === "em_curso").length;
              const totalMetas = data.metas.length;
              const doneMetas = data.metas.filter((g) => g.estado === "concluido").length;
              const pctGlobal = totalMarcos ? Math.round((doneMarcos / totalMarcos) * 100) : 0;
              return (
                <div className="mt-10 grid gap-4 sm:grid-cols-3">
                  <Reveal delay={160}>
                    <StatCard value={`${doneMarcos}/${totalMarcos}`} label={t.progress.milestones}>
                      <div className="mt-4">
                        <div className="flex items-center justify-between font-mono text-[11px] text-tech">
                          <span>{t.progress.doneLabel}</span>
                          <span>{pctGlobal}%</span>
                        </div>
                        <ProgressBar pct={pctGlobal} className="mt-1.5" />
                      </div>
                    </StatCard>
                  </Reveal>
                  <Reveal delay={200}>
                    <StatCard value={`${activeMarcos}`} label={t.progress.inProgressLabel} />
                  </Reveal>
                  <Reveal delay={240}>
                    <StatCard value={`${doneMetas}/${totalMetas}`} label={t.progress.goals} />
                  </Reveal>
                </div>
              );
            })()}

            <div className="mt-10 grid gap-6 md:grid-cols-2">
              {data.fases.map((fase: Fase, i: number) => {
                const marcos = data.marcos.filter((m) => m.fase_id === fase.id);
                const done = marcos.filter((m) => m.estado === "concluido").length;
                const pct = marcos.length ? Math.round((done / marcos.length) * 100) : 0;
                const groups = GROUP_ORDER.map((s) => ({
                  status: s,
                  items: marcos.filter((m) => m.estado === s),
                })).filter((g) => g.items.length > 0);
                return (
                  <Reveal key={fase.id} delay={i * 110}>
                    <div className="relative flex h-full flex-col overflow-hidden rounded-2xl border border-line bg-panel/50 p-6 backdrop-blur transition-all duration-300 hover:border-neon/30 hover:shadow-[0_0_50px_rgba(80,200,255,0.15)]">
                      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-neon/50 to-transparent" />
                      <div className="flex items-start justify-between gap-3">
                        <h3 className="font-display text-lg font-semibold text-ice">{fase.nome}</h3>
                        <StatusBadge status={fase.estado} label={statusLabel(fase.estado)} />
                      </div>
                      <p className="mt-2 text-sm leading-6 text-tech">{fase.resumo}</p>
                      {marcos.length > 0 && (
                        <>
                          <div className="mt-4">
                            <div className="flex items-center justify-between font-mono text-[11px] text-tech">
                              <span>
                                {t.progress.doneLabel} · {done}/{marcos.length}
                              </span>
                              <span>{pct}%</span>
                            </div>
                            <ProgressBar pct={pct} className="mt-1.5" />
                          </div>
                          <ul className="mt-4 flex-1 border-t border-line/60">
                            {groups.map((g) => (
                              <MarcoGroup
                                key={g.status}
                                label={groupLabel(g.status)}
                                marcos={g.items}
                                statusLabel={statusLabel}
                              />
                            ))}
                          </ul>
                        </>
                      )}
                    </div>
                  </Reveal>
                );
              })}
            </div>

            {data.metas.length > 0 && (
              <Reveal delay={120}>
                <div className="mt-10 rounded-2xl border border-line bg-panel/50 p-6 backdrop-blur">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="font-display text-lg font-semibold text-ice">
                      <span className="mr-2 inline-flex h-2 w-2 rounded-full bg-gold align-middle shadow-[0_0_14px_rgba(255,200,50,0.7)]" />
                      {t.progress.goals}
                    </h3>
                    <span className="rounded-md border border-line bg-night px-2 py-0.5 font-mono text-[11px] text-neon">
                      {data.metas.filter((g) => g.estado === "concluido").length}/{data.metas.length}{" "}
                      {t.progress.doneLabel.toLowerCase()}
                    </span>
                  </div>
                  <ul className="mt-3 divide-y divide-line/60">
                    {data.metas.map((meta) => (
                      <MetaRow key={meta.id} meta={meta} label={statusLabel(meta.estado)} />
                    ))}
                  </ul>
                </div>
              </Reveal>
            )}
          </>
        ) : (
          <p className="mt-8 text-center font-mono text-sm text-tech">{t.progress.loading}</p>
        )}
      </div>
    </section>
  );
}