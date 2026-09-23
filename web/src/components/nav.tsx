"use client";

import { useEffect, useState } from "react";
import { useLang } from "@/components/lang";
import { Wordmark } from "@/components/ui";
import { LANGS, LANG_NATIVE, type Lang } from "@/lib/i18n";

function LangToggle() {
  const { lang, set, t } = useLang();
  return (
    <div className="relative inline-flex items-center">
      <select
        value={lang}
        onChange={(e) => set(e.target.value as Lang)}
        aria-label={t.nav.langLabel}
        title={t.nav.langLabel}
        className="cursor-pointer appearance-none rounded-full border border-line bg-panel/70 py-1.5 pr-7 pl-3 font-mono text-xs text-ice outline-none transition-colors hover:border-neon/40 focus:border-neon/60 focus:shadow-[0_0_0_3px_rgba(80,200,255,0.15)]"
      >
        {LANGS.map((code) => (
          <option key={code} value={code}>
            {LANG_NATIVE[code]}
          </option>
        ))}
      </select>
      <span className="pointer-events-none absolute right-2.5 text-tech" aria-hidden="true">
        ▾
      </span>
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
      <nav className="relative mx-auto flex flex-wrap items-center justify-between gap-x-5 gap-y-2 px-4 py-1 sm:px-10">
        <a href="#top" aria-label="Mãouse" className="-ml-1 shrink-0 transition-transform hover:scale-105 sm:-ml-2">
          <Wordmark compact className="h-14 w-auto sm:h-24" />
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