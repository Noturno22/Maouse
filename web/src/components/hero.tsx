"use client";

import { useLang } from "@/components/lang";
import { DownloadButton, Icon } from "@/components/ui";
import { Counter, Reveal } from "@/components/effects";

function DemoStage() {
  const { t } = useLang();
  return (
    <Reveal className="relative">
      <div className="hero-orb absolute -top-16 -right-10 h-72 w-72 rounded-full bg-neon/25 blur-3xl" />
      <div className="hero-orb absolute -bottom-16 -left-10 h-56 w-56 rounded-full bg-violet/25 blur-3xl [animation-delay:-6s]" />

      <div className="relative overflow-hidden rounded-2xl border border-line bg-panel/60 shadow-[0_0_80px_rgba(80,200,255,0.14)] backdrop-blur-xl">
        <div className="flex items-center justify-between border-b border-line/60 px-5 py-3">
          <span className="font-mono text-xs tracking-widest text-neon uppercase">
            Mãouse · live tracking
          </span>
          <span className="flex items-center gap-3 font-mono text-xs text-tech">
            <span>FPS 60</span>
            <span className="flex items-center gap-1.5 text-success">
              <span className="pulse-dot relative inline-flex h-1.5 w-1.5 rounded-full bg-success text-success" />
              IA local
            </span>
          </span>
        </div>

        <div className="relative flex aspect-[4/3] flex-col items-center justify-center overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-panel via-night to-panel2" />
          <div className="demo-scan absolute right-0 left-0 h-24 bg-gradient-to-b from-transparent via-neon/15 to-transparent" />

          {/* HUD: cantos sci-fi */}
          {[
            "top-3 left-3 border-t-2 border-l-2",
            "top-3 right-3 border-t-2 border-r-2",
            "bottom-3 left-3 border-b-2 border-l-2",
            "bottom-3 right-3 border-b-2 border-r-2",
          ].map((pos) => (
            <span
              key={pos}
              className={`absolute h-5 w-5 border-neon/60 ${pos}`}
            />
          ))}

          {/* Retícula central */}
          <div className="orbit-ring" />
          <span className="absolute inset-0 m-auto h-px w-40 bg-gradient-to-r from-transparent via-neon/40 to-transparent" />
          <span className="absolute inset-0 m-auto h-40 w-px bg-gradient-to-b from-transparent via-neon/40 to-transparent" />

          <div className="relative flex flex-col items-center gap-3 px-8 text-center">
            <span className="animate-float-y inline-flex h-16 w-16 items-center justify-center rounded-2xl border border-neon/40 bg-neon/10 text-neon shadow-[0_0_40px_rgba(80,200,255,0.45)]">
              <Icon name="pointer" className="h-8 w-8" />
            </span>
            <span className="font-mono text-xs tracking-widest text-tech uppercase">
              hand recognized — pinch to click
            </span>
          </div>

          <span className="absolute top-4 left-4 rounded-md bg-panel/80 px-2 py-1 font-mono text-[10px] text-success backdrop-blur">
            ✓ 21 joints
          </span>
          <span className="absolute top-4 right-4 rounded-md bg-panel/80 px-2 py-1 font-mono text-[10px] text-tech backdrop-blur">
            0 ghost clicks
          </span>
          <span className="absolute right-4 bottom-4 animate-pulse rounded-md bg-panel/80 px-2 py-1 font-mono text-[10px] text-neon backdrop-blur">
            ● REC
          </span>
        </div>
      </div>

      <span className="absolute -top-3 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-full border border-line bg-night px-3 py-1 font-mono text-[10px] tracking-widest text-neon uppercase shadow-[0_0_20px_rgba(80,200,255,0.35)]">
        {t.hero.demoLabel}
      </span>
    </Reveal>
  );
}

export function Hero() {
  const { lang, t } = useLang();
  const benefitsId = lang === "pt" ? "#beneficios" : "#benefits";

  return (
    <section id="download" className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute top-0 left-1/2 h-px w-full max-w-6xl -translate-x-1/2 bg-gradient-to-r from-transparent via-neon/50 to-transparent" />
        <div className="absolute -top-40 left-1/2 h-96 w-[52rem] -translate-x-1/2 rounded-full bg-neon/10 blur-3xl" />
      </div>

      <div className="relative mx-auto grid max-w-6xl items-center gap-14 px-5 pt-20 pb-16 lg:grid-cols-[1.05fr_0.95fr] lg:pt-28 lg:pb-24">
        <div className="[animation:fade-up_0.9s_cubic-bezier(0.16,1,0.3,1)_both]">
          <span className="inline-flex items-center gap-2 rounded-full border border-line bg-panel/70 px-3 py-1 font-mono text-xs text-tech backdrop-blur">
            <span className="pulse-dot relative inline-flex h-1.5 w-1.5 rounded-full bg-success text-success" />
            {t.hero.badge}
          </span>

          <h1 className="mt-6 font-display text-4xl leading-[1.05] font-bold tracking-tight sm:text-6xl">
            {t.hero.titleA}{" "}
            <span className="text-gradient drop-shadow-[0_0_24px_rgba(80,200,255,0.35)]">
              {t.hero.titleB}
            </span>
          </h1>

          <p className="mt-6 max-w-xl text-lg leading-8 text-tech">{t.hero.sub}</p>

          <ul className="mt-8 space-y-3">
            {t.hero.bullets.map((item) => (
              <li key={item} className="flex items-start gap-3 text-ice">
                <span className="mt-0.5 text-success">
                  <Icon name="check" className="h-5 w-5" />
                </span>
                <span>{item}</span>
              </li>
            ))}
          </ul>

          <div className="mt-10 flex flex-wrap items-center gap-4">
            <DownloadButton label={t.hero.download} big />
            <a
              href={benefitsId}
              className="btn-shine inline-flex items-center gap-2 rounded-lg border border-line bg-panel/70 px-6 py-4 font-display text-base font-semibold text-ice backdrop-blur transition-all hover:border-neon/50 hover:text-neon hover:shadow-[0_0_24px_rgba(80,200,255,0.2)]"
            >
              {t.hero.secondary}
            </a>
          </div>
        </div>

        <div className="relative hidden lg:block">
          <DemoStage />
          <div className="absolute top-1/2 right-0 z-20 -translate-y-1/2 translate-x-1/2">
            <DownloadButton label={t.hero.download} big />
          </div>
        </div>

        <DownloadButton
          label={t.hero.download}
          big
          className="lg:hidden"
        />
      </div>

      <div className="relative border-t border-line/60 bg-white/[0.02] backdrop-blur">
        <dl className="mx-auto grid max-w-6xl grid-cols-1 gap-6 px-5 py-8 sm:grid-cols-3">
          {t.hero.stats.map((stat) => (
            <Reveal
              key={stat.label}
              delay={100}
              className="flex items-baseline gap-3"
            >
              <dt className="sr-only">{stat.label}</dt>
              <dd>
                <Counter
                  value={stat.value}
                  className="font-mono text-2xl font-bold text-neon drop-shadow-[0_0_16px_rgba(80,200,255,0.5)]"
                />
              </dd>
              <dd className="text-sm text-tech">{stat.label}</dd>
            </Reveal>
          ))}
        </dl>
      </div>
    </section>
  );
}