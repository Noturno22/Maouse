"use client";

import { useLang } from "@/components/lang";
import {
  AccentIcon,
  DownloadButton,
  Icon,
  SectionHeader,
  Wordmark,
} from "@/components/ui";

function sectionId(lang: "pt" | "en", key: "features" | "pricing" | "privacy" | "matrix" | "faq" | "progress") {
  const ids: Record<string, Record<typeof key, string>> = {
    pt: { features: "beneficios", pricing: "precos", privacy: "privacidade", matrix: "matriz", faq: "faq", progress: "progresso" },
    en: { features: "benefits", pricing: "pricing", privacy: "privacy", matrix: "compatibility", faq: "faq", progress: "roadmap" },
  };
  return ids[lang][key];
}

export function Features() {
  const { lang, t } = useLang();
  return (
    <section id={sectionId(lang, "features")} className="scroll-mt-24 py-20 lg:py-28">
      <div className="mx-auto max-w-6xl px-5">
        <SectionHeader tag={t.features.tag} title={t.features.title} sub={t.features.sub} />
        <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {t.features.items.map((item) => (
            <div
              key={item.title}
              className="group rounded-2xl border border-line bg-panel p-6 transition-all hover:-translate-y-1 hover:border-neon/40 hover:shadow-[0_0_40px_rgba(80,200,255,0.15)]"
            >
              <AccentIcon name={item.icon} accent={item.accent} />
              <h3 className="mt-5 font-display text-lg font-semibold text-ice">
                {item.title}
              </h3>
              <p className="mt-2 text-sm leading-6 text-tech">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

const PADDLE_VENDOR_ID = process.env.NEXT_PUBLIC_PADDLE_VENDOR_ID;
const LIFETIME_URL = process.env.NEXT_PUBLIC_PADDLE_LIFETIME_URL;
const FAMILY_URL = process.env.NEXT_PUBLIC_PADDLE_FAMILY_URL;
const ACCESS_URL = process.env.NEXT_PUBLIC_PADDLE_ACCESS_URL;

export function Pricing() {
  const { lang, t } = useLang();
  const checkoutFor = (id: string) => {
    const overrides: Record<string, string> = {
      lifetime: LIFETIME_URL || "",
      family: FAMILY_URL || "",
      access: ACCESS_URL || "",
    };
    if (overrides[id]) return overrides[id] || null;
    if (!PADDLE_VENDOR_ID) return null;
    const products: Record<string, string> = {
      lifetime: "maouse-pro-lifetime",
      family: "maouse-family",
      access: "maouse-pro-access",
    };
    return `https://checkout.paddle.com/${PADDLE_VENDOR_ID}?product=${products[id] ?? id}`;
  };

  return (
    <section id={sectionId(lang, "pricing")} className="scroll-mt-24 border-t border-line/60 bg-panel/30 py-20 lg:py-28">
      <div className="mx-auto max-w-6xl px-5">
        <SectionHeader tag={t.pricing.tag} title={t.pricing.title} sub={t.pricing.sub} />

        <div className="mt-14 grid gap-5 lg:grid-cols-3 lg:items-stretch">
          {t.pricing.plans.map((plan) => {
            const isFree = plan.id === "free";
            const isHighlight = plan.highlight;
            const cta = isFree ? (
              <DownloadButton label={plan.cta} className="w-full" />
            ) : (() => {
              const href = checkoutFor(plan.id);
              return href ? (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex w-full items-center justify-center rounded-lg bg-neon px-5 py-3 text-sm font-semibold text-night transition-all hover:bg-ice"
                >
                  {plan.cta}
                </a>
              ) : (
                <button
                  type="button"
                  disabled
                  title={t.pricing.comingSoon}
                  className="inline-flex w-full cursor-not-allowed items-center justify-center rounded-lg border border-line bg-panel px-5 py-3 text-sm font-semibold text-tech"
                >
                  {plan.cta}
                </button>
              );
            })();

            return (
              <div
                key={plan.id}
                className={`relative flex flex-col rounded-2xl border p-7 ${
                  isHighlight
                    ? "border-neon/50 bg-panel shadow-[0_0_50px_rgba(80,200,255,0.18)] lg:-my-4 lg:py-11"
                    : "border-line bg-panel"
                }`}
              >
                {isHighlight && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-neon px-3 py-1 font-mono text-[10px] font-semibold tracking-widest text-night uppercase">
                    {t.pricing.popular}
                  </span>
                )}
                <h3 className="font-display text-lg font-semibold text-ice">
                  {plan.name}
                </h3>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className="font-display text-4xl font-bold text-neon">
                    {plan.price}
                  </span>
                  <span className="font-mono text-xs text-tech">{plan.extra}</span>
                </div>
                <ul className="mt-6 flex-1 space-y-3">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2.5 text-sm text-ice">
                      <span className="mt-0.5 shrink-0 text-success">
                        <Icon name="check" className="h-4 w-4" />
                      </span>
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
                <div className="mt-8">{cta}</div>
              </div>
            );
          })}
        </div>

        <div className="mx-auto mt-14 max-w-3xl space-y-4 rounded-2xl border border-line bg-panel/70 p-6 text-center">
          <p className="flex items-center justify-center gap-2 text-sm text-ice">
            <Icon name="gift" className="h-4 w-4 text-warn" />
            {t.pricing.accessNote}
          </p>
          <p className="font-mono text-xs text-tech">
            {t.pricing.guarantee} · {t.pricing.contact}
          </p>
        </div>
      </div>
    </section>
  );
}

export function Privacy() {
  const { lang, t } = useLang();
  return (
    <section id={sectionId(lang, "privacy")} className="scroll-mt-24 py-20 lg:py-28">
      <div className="mx-auto grid max-w-6xl items-center gap-14 px-5 lg:grid-cols-2">
        <div>
          <SectionHeader tag={t.privacy.tag} title={t.privacy.title} sub={t.privacy.sub} />
          <div className="mt-10 space-y-4">
            {t.privacy.bullets.map((item) => (
              <div key={item.title} className="flex items-start gap-4 rounded-2xl border border-line bg-panel p-5">
                <span className="text-neon">
                  <Icon name={item.icon} className="h-5 w-5" />
                </span>
                <div>
                  <h3 className="font-display text-base font-semibold text-ice">{item.title}</h3>
                  <p className="mt-1 text-sm leading-6 text-tech">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <figure className="relative overflow-hidden rounded-2xl border border-line bg-panel p-8">
          <div className="hero-orb absolute -top-10 -right-10 h-48 w-48 rounded-full bg-neon/15 blur-3xl" />
          <blockquote className="relative font-display text-2xl leading-relaxed font-semibold text-ice">
            “{t.privacy.statement}”
          </blockquote>
          <figcaption className="relative mt-6 flex items-center gap-2 font-mono text-xs tracking-widest text-neon uppercase">
            <span className="h-1.5 w-1.5 rounded-full bg-neon" />
            Mãouse — privacy by architecture
          </figcaption>
        </figure>
      </div>
    </section>
  );
}

const verdictStyle = {
  ok: "bg-success/15 text-success border-success/30",
  warn: "bg-warn/15 text-warn border-warn/30",
  no: "bg-error/15 text-error border-error/30",
} as const;

export function Matrix() {
  const { lang, t } = useLang();

  return (
    <section id={sectionId(lang, "matrix")} className="scroll-mt-24 border-t border-line/60 bg-panel/30 py-20 lg:py-28">
      <div className="mx-auto max-w-6xl px-5">
        <SectionHeader tag={t.matrix.tag} title={t.matrix.title} sub={t.matrix.sub} />

        <div className="mt-14 overflow-x-auto rounded-2xl border border-line">
          <table className="w-full min-w-[720px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-line bg-panel2 font-mono text-xs tracking-wider text-tech uppercase">
                {t.matrix.cols.map((col) => (
                  <th key={col} className="px-5 py-3.5 font-medium">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {t.matrix.rows.map((row) => (
                <tr
                  key={row.device}
                  className="border-b border-line/50 bg-panel last:border-0"
                >
                  <td className="px-5 py-4 font-medium text-ice">{row.device}</td>
                  <td className="px-5 py-4 font-mono text-xs text-tech">{row.webcam}</td>
                  <td className="px-5 py-4 font-mono text-xs text-tech">{row.fps}</td>
                  <td className="px-5 py-4 font-mono text-xs text-tech">{row.latency}</td>
                  <td className="px-5 py-4 font-mono text-xs text-success">{row.ghosts}</td>
                  <td className="px-5 py-4">
                    <span
                      className={`inline-flex rounded-md border px-2.5 py-1 font-mono text-xs ${verdictStyle[row.verdict]}`}
                    >
                      {row.verdict === "ok"
                        ? t.matrix.legendOk
                        : row.verdict === "warn"
                          ? t.matrix.legendWarn
                          : t.matrix.legendNo}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap gap-4 text-xs text-tech">
            {(Object.keys(verdictStyle) as (keyof typeof verdictStyle)[]).map((v) => (
              <span key={v} className="inline-flex items-center gap-2">
                <span className={`inline-block h-2.5 w-2.5 rounded-full ${verdictStyle[v]}`} />
                {v === "ok" ? t.matrix.legendOk : v === "warn" ? t.matrix.legendWarn : t.matrix.legendNo}
              </span>
            ))}
          </div>
        </div>

        <p className="mt-6 rounded-2xl border border-warn/30 bg-warn/10 p-5 text-sm leading-6 text-warn">
          {t.matrix.note}
        </p>
      </div>
    </section>
  );
}

export function Faq() {
  const { lang, t } = useLang();
  return (
    <section id={sectionId(lang, "faq")} className="scroll-mt-24 py-20 lg:py-28">
      <div className="mx-auto max-w-3xl px-5">
        <SectionHeader tag={t.faq.tag} title={t.faq.title} sub={t.faq.sub} />
        <div className="mt-12 space-y-3">
          {t.faq.items.map((item) => (
            <details
              key={item.q}
              className="group rounded-2xl border border-line bg-panel open:border-neon/40"
            >
              <summary className="flex cursor-pointer items-center justify-between gap-4 px-6 py-5 font-display text-base font-semibold text-ice transition-colors group-open:text-neon">
                {item.q}
                <span className="shrink-0 font-mono text-neon transition-transform group-open:rotate-45">
                  +
                </span>
              </summary>
              <p className="px-6 pb-6 text-sm leading-7 text-tech">{item.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

export function Footer() {
  const { t } = useLang();
  return (
    <footer className="border-t border-line/60 bg-panel/40">
      <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8">
        <div className="grid gap-12 lg:grid-cols-[1.2fr_2fr]">
          <div>
            <Wordmark />
            <p className="mt-4 font-display text-lg text-neon">{t.footer.tagline}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {t.footer.hashtags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full border border-line bg-panel px-3 py-1 font-mono text-xs text-tech"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-8 sm:grid-cols-3">
            {t.footer.columns.map((column) => (
              <div key={column.title}>
                <h3 className="font-mono text-xs tracking-widest text-tech uppercase">
                  {column.title}
                </h3>
                <ul className="mt-4 space-y-3">
                  {column.links.map((link) => (
                    <li key={link.label}>
                      <a
                        href={link.href}
                        className="text-sm text-ice transition-colors hover:text-neon"
                      >
                        {link.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-16 flex flex-col items-center justify-between gap-3 border-t border-line/60 pt-10 sm:flex-row">
          <p className="text-xs text-tech">{t.footer.rights}</p>
          <p className="font-mono text-xs text-tech">{t.footer.made}</p>
        </div>
      </div>
    </footer>
  );
}