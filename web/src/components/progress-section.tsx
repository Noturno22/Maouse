"use client";

import { useEffect, useState } from "react";
import { useLang } from "@/components/lang";
import { SectionHeader } from "@/components/ui";
import type { Fase, Marco, ProgressData, ProgressStatus } from "@/lib/progress";

const STATUS_TEXT: Record<ProgressStatus, string> = {
  pendente: "text-tech",
  em_curso: "text-warn",
  concluido: "text-success",
};

function StatusBadge({ status, label }: { status: ProgressStatus; label: string }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border border-line bg-panel px-2.5 py-0.5 font-mono text-[11px] tracking-wide ${STATUS_TEXT[status]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {label}
    </span>
  );
}

function formatDate(iso: string | null, lang: "pt" | "en"): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(lang === "pt" ? "pt-PT" : "en-GB", {
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
    <li className="flex items-start justify-between gap-3 py-1.5">
      <span className="text-sm leading-6 text-ice">
        {marco.titulo}
        {marco.nota ? <span className="block text-xs text-tech">{marco.nota}</span> : null}
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
    <section id={lang === "pt" ? "progresso" : "roadmap"} className="scroll-mt-24 border-t border-line/60 py-20 lg:py-28">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <SectionHeader tag={t.progress.tag} title={t.progress.title} sub={t.progress.sub} />

        {error ? (
          <p className="mt-8 text-center text-sm text-error">Não foi possível carregar a progressão.</p>
        ) : data ? (
          <>
            <p className="mt-8 text-center font-mono text-xs tracking-widest text-tech uppercase">
              {t.progress.updated} {formatDate(data.updatedAt, lang)}
            </p>

            <div className="mt-10 grid gap-6 md:grid-cols-2">
              {data.fases.map((fase: Fase) => {
                const marcos = data.marcos.filter((m) => m.fase_id === fase.id);
                return (
                  <div
                    key={fase.id}
                    className="flex flex-col rounded-2xl border border-line bg-panel/50 p-6"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <h3 className="font-display text-lg font-semibold text-ice">{fase.nome}</h3>
                      <StatusBadge status={fase.estado} label={statusLabel(fase.estado)} />
                    </div>
                    <p className="mt-2 text-sm leading-6 text-tech">{fase.resumo}</p>
                    {marcos.length > 0 && (
                      <ul className="mt-4 divide-y divide-line/60 border-t border-line/60">
                        {marcos.map((m) => (
                          <MarcoRow key={m.id} marco={m} label={statusLabel(m.estado)} />
                        ))}
                      </ul>
                    )}
                  </div>
                );
              })}
            </div>

            {data.metas.length > 0 && (
              <div className="mt-10 rounded-2xl border border-line bg-panel/50 p-6">
                <h3 className="font-display text-lg font-semibold text-ice">{t.progress.goals}</h3>
                <ul className="mt-3 divide-y divide-line/60">
                  {data.metas.map((meta) => (
                    <li key={meta.id} className="flex items-start justify-between gap-3 py-2.5">
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
            )}
          </>
        ) : (
          <p className="mt-8 text-center font-mono text-sm text-tech">A carregar…</p>
        )}
      </div>
    </section>
  );
}