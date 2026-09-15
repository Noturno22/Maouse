"use client";

import { useEffect, useState } from "react";
import { useLang } from "@/components/lang";
import { SectionHeader } from "@/components/ui";
import { Reveal } from "@/components/effects";
import { sectionId } from "@/lib/sections";
import { LANG_LOCALE, type Lang } from "@/lib/i18n";
import type { Fase, Marco, ProgressData, ProgressStatus } from "@/lib/progress";

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

function MarcoRow({ marco, label }: { marco: Marco; label: string }) {
  return (
    <li className="flex items-start justify-between gap-3 py-2 transition-colors hover:bg-white/[0.03]">
      <span className="text-sm leading-6 text-ice">
        <span className="mr-2 inline-block h-1.5 w-1.5 translate-y-[-1px] rounded-full bg-current text-neon/60 align-middle" />
        {marco.titulo}
        {marco.nota ? <span className="block pl-3.5 text-xs text-tech">{marco.nota}</span> : null}
      </span>
      <StatusBadge status={marco.estado} label={label} />
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

            <div className="mt-10 grid gap-6 md:grid-cols-2">
              {data.fases.map((fase: Fase, i: number) => {
                const marcos = data.marcos.filter((m) => m.fase_id === fase.id);
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
                        <ul className="mt-4 flex-1 divide-y divide-line/60 border-t border-line/60">
                          {marcos.map((m) => (
                            <MarcoRow key={m.id} marco={m} label={statusLabel(m.estado)} />
                          ))}
                        </ul>
                      )}
                    </div>
                  </Reveal>
                );
              })}
            </div>

            {data.metas.length > 0 && (
              <Reveal delay={120}>
                <div className="mt-10 rounded-2xl border border-line bg-panel/50 p-6 backdrop-blur">
                  <h3 className="font-display text-lg font-semibold text-ice">
                    <span className="mr-2 inline-flex h-2 w-2 rounded-full bg-gold align-middle shadow-[0_0_14px_rgba(255,200,50,0.7)]" />
                    {t.progress.goals}
                  </h3>
                  <ul className="mt-3 divide-y divide-line/60">
                    {data.metas.map((meta) => (
                      <li key={meta.id} className="flex items-start justify-between gap-3 py-2.5 transition-colors hover:bg-white/[0.03]">
                        <span className="text-sm leading-6 text-ice">
                          {meta.titulo}
                          {meta.prazo ? (
                            <span className="ml-2 rounded-md border border-line bg-night px-1.5 py-0.5 font-mono text-[11px] text-neon">
                              {meta.prazo}
                            </span>
                          ) : null}
                        </span>
                        <StatusBadge status={meta.estado} label={statusLabel(meta.estado)} />
                      </li>
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