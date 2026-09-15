"use client";

import Image from "next/image";
import { useLang } from "@/components/lang";
import { AccentIcon, Icon, SectionHeader } from "@/components/ui";
import { Reveal, SpotlightCard } from "@/components/effects";
import { sectionId } from "@/lib/sections";

const DEMO_YOUTUBE = process.env.NEXT_PUBLIC_DEMO_YOUTUBE ?? "";
const DEMO_MP4 = process.env.NEXT_PUBLIC_DEMO_MP4 ?? "";
const DEMO_POSTER = process.env.NEXT_PUBLIC_DEMO_POSTER ?? "";

function DemoVideo() {
  const { t } = useLang();

  const frame = "relative aspect-video w-full overflow-hidden rounded-2xl";

  if (DEMO_YOUTUBE) {
    return (
      <div className={frame}>
        <iframe
          className="absolute inset-0 h-full w-full"
          src={`https://www.youtube-nocookie.com/embed/${DEMO_YOUTUBE}`}
          title={t.media.title}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>
    );
  }

  if (DEMO_MP4) {
    return (
      <div className={frame}>
        <video
          className="absolute inset-0 h-full w-full"
          controls
          preload="metadata"
          poster={DEMO_POSTER || undefined}
        >
          <source src={DEMO_MP4} />
        </video>
      </div>
    );
  }

  return (
    <div className={frame}>
      <div className="absolute inset-0 bg-gradient-to-br from-panel via-night to-panel2" />
      <div className="demo-scan absolute right-0 left-0 h-24 bg-gradient-to-b from-transparent via-neon/20 to-transparent" />
      {[
        "top-3 left-3 border-t-2 border-l-2",
        "top-3 right-3 border-t-2 border-r-2",
        "bottom-3 left-3 border-b-2 border-l-2",
        "bottom-3 right-3 border-b-2 border-r-2",
      ].map((pos) => (
        <span key={pos} className={`absolute h-5 w-5 border-neon/60 ${pos}`} />
      ))}
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 text-center">
        <span className="relative inline-flex h-16 w-16 items-center justify-center rounded-full border border-neon/50 bg-neon/10 text-neon shadow-[0_0_50px_rgba(80,200,255,0.5)]">
          <span className="pulse-ring absolute inset-0 rounded-full" />
          <svg viewBox="0 0 24 24" fill="currentColor" className="ml-1 h-7 w-7" aria-hidden="true">
            <path d="M8 5v14l11-7z" />
          </svg>
        </span>
        <span className="font-mono text-xs tracking-widest text-tech uppercase">
          {t.media.demoNote}
        </span>
      </div>
    </div>
  );
}

export function Media() {
  const { lang, t } = useLang();
  return (
    <section
      id={sectionId(lang, "media")}
      className="scroll-mt-24 border-t border-line/60 bg-white/[0.02] py-20 lg:py-28"
    >
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal>
          <SectionHeader tag={t.media.tag} title={t.media.title} sub={t.media.sub} />
        </Reveal>

        <Reveal delay={100}>
          <div className="relative mt-14">
            <div className="hero-orb absolute -top-10 -left-10 h-56 w-56 rounded-full bg-neon/15 blur-3xl" />
            <div className="hero-orb absolute -right-10 -bottom-12 h-48 w-48 rounded-full bg-violet/15 blur-3xl [animation-delay:-6s]" />

            <div className="relative overflow-hidden rounded-3xl border border-line bg-panel/60 p-2 shadow-[0_0_80px_rgba(80,200,255,0.12)] backdrop-blur-xl">
              <div className="flex items-center justify-between px-4 py-2.5">
                <span className="font-mono text-xs tracking-widest text-neon uppercase">
                  Mãouse · {t.hero.demoLabel}
                </span>
                <span className="flex items-center gap-2 font-mono text-xs text-success">
                  <span className="pulse-dot relative inline-flex h-1.5 w-1.5 rounded-full bg-success text-success" />
                  {t.media.liveLabel}
                </span>
              </div>
              <DemoVideo />
            </div>
          </div>
        </Reveal>

        <Reveal delay={150}>
          <h3 className="mt-16 text-center font-display text-xl font-semibold text-ice">
            {t.media.stepsTitle}
          </h3>
        </Reveal>

        <div className="mt-10 grid gap-5 sm:grid-cols-3">
          {t.media.steps.map((step, i) => (
            <Reveal key={step.title} delay={i * 90}>
              <SpotlightCard className="group h-full rounded-2xl border border-line bg-panel/50 p-6 transition-all duration-300 hover:-translate-y-1.5 hover:border-neon/40 hover:shadow-[0_0_50px_rgba(80,200,255,0.18)]">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-2xl font-bold text-neon/40 transition-colors group-hover:text-neon">
                    0{i + 1}
                  </span>
                  <span className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-line bg-panel text-neon">
                    <Icon name={step.icon} className="h-5 w-5" />
                  </span>
                </div>
                <h4 className="mt-5 font-display text-base font-semibold text-ice">
                  {step.title}
                </h4>
                <p className="mt-2 text-sm leading-6 text-tech">{step.desc}</p>
              </SpotlightCard>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

function GalleryMock({ title }: { title: string }) {
  return (
    <div className="absolute inset-0 overflow-hidden bg-gradient-to-br from-panel via-night to-panel2">
      <div className="bg-grid absolute inset-0 opacity-40" />
      <div className="demo-scan absolute right-0 left-0 h-20 bg-gradient-to-b from-transparent via-neon/10 to-transparent" />
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="font-display text-sm font-semibold text-tech/70">{title}</span>
      </div>
      <div className="absolute top-3 left-3 flex gap-1.5">
        <span className="h-2 w-2 rounded-full bg-error/60" />
        <span className="h-2 w-2 rounded-full bg-warn/60" />
        <span className="h-2 w-2 rounded-full bg-success/60" />
      </div>
    </div>
  );
}

export function Gallery() {
  const { lang, t } = useLang();
  return (
    <section id={sectionId(lang, "gallery")} className="scroll-mt-24 py-20 lg:py-28">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal>
          <SectionHeader tag={t.gallery.tag} title={t.gallery.title} sub={t.gallery.sub} />
        </Reveal>

        <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {t.gallery.items.map((item, i) => (
            <Reveal key={item.title} delay={i * 70}>
              <SpotlightCard className="group h-full overflow-hidden rounded-2xl border border-line bg-panel/50 p-2 transition-all duration-300 hover:-translate-y-1.5 hover:border-neon/40 hover:shadow-[0_0_50px_rgba(80,200,255,0.18)]">
                <div className="relative aspect-video w-full overflow-hidden rounded-xl border border-line/60">
                  {item.image ? (
                    <Image
                      src={item.image}
                      alt={item.title}
                      fill
                      sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
                      className="object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                  ) : (
                    <GalleryMock title={item.title} />
                  )}
                </div>
                <div className="flex items-start gap-3 p-4">
                  <AccentIcon name="eye" accent={item.accent} />
                  <div>
                    <h3 className="font-display text-base font-semibold text-ice">{item.title}</h3>
                    <p className="mt-1 text-sm leading-6 text-tech">{item.desc}</p>
                  </div>
                </div>
              </SpotlightCard>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
