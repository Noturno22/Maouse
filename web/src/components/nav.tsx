"use client";

import { useEffect, useState } from "react";
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
      className="flex items-center rounded-full border border-line bg-panel/70 p-0.5"
    >
      {opts.map((o) => (
        <button
          key={o}
          type="button"
          onClick={() => set(o)}
          aria-pressed={lang === o}
          className={`rounded-full px-2.5 py-1 font-mono text-xs uppercase transition-colors ${
            lang === o
              ? "bg-neon font-semibold text-night shadow-[0_0_14px_rgba(80,200,255,0.5)]"
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
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const onScroll = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      setProgress(max > 0 ? Math.min(1, window.scrollY / max) : 0);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, []);

  return (
    <header className="sticky top-0 z-50 border-b border-line/60 bg-night/70 backdrop-blur-xl">
      <div
        className="scroll-progress h-0.5 bg-gradient-to-r from-neon via-royal to-violet"
        style={{ transform: `scaleX(${progress})` }}
      />
      <nav className="relative mx-auto flex max-w-6xl items-center justify-between gap-5 px-5 py-2.5 sm:px-8">
        <a href="#top" aria-label="Mãouse" className="transition-transform hover:scale-105">
          <Wordmark compact />
        </a>

        <div className="hidden items-center gap-7 lg:flex">
          {t.nav.links.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="nav-link text-sm text-tech transition-colors hover:text-neon"
            >
              {link.label}
            </a>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <LangToggle />
          <a
            href="#download"
            className="btn-shine inline-flex items-center rounded-lg bg-neon px-4 py-2 text-sm font-semibold text-night transition-all hover:bg-ice hover:shadow-[0_0_24px_rgba(80,200,255,0.5)]"
          >
            {t.nav.cta}
          </a>
        </div>
      </nav>
    </header>
  );
}