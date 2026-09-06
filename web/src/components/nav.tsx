"use client";

import { useLang } from "@/components/lang";
import { Wordmark } from "@/components/ui";
import type { Lang } from "@/lib/i18n";

function LangToggle() {
  const { lang, set, t } = useLang();
  const opts: Lang[] = ["pt", "en"];
  return (
    <div
      role="group"
      aria-label={t.nav.langLabel}
      className="flex items-center rounded-full border border-line bg-panel p-0.5"
    >
      {opts.map((o) => (
        <button
          key={o}
          type="button"
          onClick={() => set(o)}
          aria-pressed={lang === o}
          className={`rounded-full px-2.5 py-1 font-mono text-xs uppercase transition-colors ${
            lang === o
              ? "bg-neon font-semibold text-night"
              : "text-tech hover:text-ice"
          }`}
        >
          {o}
        </button>
      ))}
    </div>
  );
}

export function Nav() {
  const { t } = useLang();

  return (
    <header className="sticky top-0 z-50 border-b border-line/60 bg-night/85 backdrop-blur-md">
      <nav className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-3.5">
        <a href="#top" aria-label="Mãouse">
          <Wordmark compact />
        </a>

        <div className="hidden items-center gap-7 lg:flex">
          {t.nav.links.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm text-tech transition-colors hover:text-neon"
            >
              {link.label}
            </a>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <LangToggle />
          <a
            href="#download"
            className="inline-flex items-center rounded-lg bg-neon px-4 py-2 text-sm font-semibold text-night transition-all hover:bg-ice"
          >
            {t.nav.cta}
          </a>
        </div>
      </nav>
    </header>
  );
}