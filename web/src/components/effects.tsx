"use client";

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";

export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function canHover(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(hover: hover) and (pointer: fine)").matches;
}

/** Fundo ambiente global: grid, aurora de luz e spotlight que segue o rato. */
export function BackgroundFX() {
  const spotRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!canHover() || prefersReducedMotion()) return;
    let raf = 0;
    const move = (ev: PointerEvent) => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const el = spotRef.current;
        if (!el) return;
        el.style.opacity = "1";
        el.style.background = `radial-gradient(650px circle at ${ev.clientX}px ${ev.clientY}px, rgba(80,200,255,0.10), rgba(180,120,255,0.05) 35%, transparent 65%)`;
      });
    };
    const leave = () => {
      if (spotRef.current) spotRef.current.style.opacity = "0";
    };
    window.addEventListener("pointermove", move, { passive: true });
    window.addEventListener("pointerleave", leave);
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerleave", leave);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      <div className="bg-grid absolute inset-0" />
      <div className="hero-orb absolute -top-32 -left-24 h-[34rem] w-[34rem] rounded-full bg-neon/14 blur-3xl" />
      <div className="hero-orb absolute top-1/3 -right-28 h-[30rem] w-[30rem] rounded-full bg-violet/14 blur-3xl [animation-delay:-6s]" />
      <div className="hero-orb absolute -bottom-40 left-1/3 h-[26rem] w-[26rem] rounded-full bg-royal/12 blur-3xl [animation-delay:-10s]" />
      <div
        ref={spotRef}
        className="absolute inset-0 opacity-0 transition-opacity duration-700"
      />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_50%,rgba(10,10,18,0.65)_100%)]" />
    </div>
  );
}

/** Aparece suavemente quando entra no ecrã (com IntersectionObserver). */
export function Reveal({
  children,
  delay = 0,
  className = "",
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (prefersReducedMotion()) {
      el.classList.add("is-in");
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-in");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={`reveal ${className}`}
      style={{ "--reveal-delay": `${delay}ms` } as CSSProperties}
    >
      {children}
    </div>
  );
}

/** Card com brilho radial que segue o rato dentro do próprio card. */
export function SpotlightCard({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || !canHover() || prefersReducedMotion()) return;
    const move = (ev: PointerEvent) => {
      const r = el.getBoundingClientRect();
      el.style.setProperty("--mx", `${ev.clientX - r.left}px`);
      el.style.setProperty("--my", `${ev.clientY - r.top}px`);
    };
    el.addEventListener("pointermove", move);
    return () => el.removeEventListener("pointermove", move);
  }, []);

  return (
    <div ref={ref} className={`spotlight-card group relative overflow-hidden ${className}`}>
      {children}
    </div>
  );
}

/** Contador animado (números sobem quando o valor aparece no ecrã). */
export function Counter({ value, className = "" }: { value: string; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const [display, setDisplay] = useState(value);

  useEffect(() => {
    const el = ref.current;
    const m = value.match(/^(\d+(?:[.,]\d+)?)(.*)$/);
    if (!el || !m || prefersReducedMotion()) return;
    const target = parseFloat(m[1].replace(",", "."));
    const suffix = m[2];

    const io = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          io.disconnect();
          const t0 = performance.now();
          const dur = 1200;
          const tick = (t: number) => {
            const p = Math.min(1, (t - t0) / dur);
            const eased = 1 - Math.pow(1 - p, 3);
            const shown = String(
              Number.isInteger(target) ? Math.round(target * eased) : Math.round(target * eased * 10) / 10,
            );
            setDisplay(`${shown}${suffix}`);
            if (p < 1) requestAnimationFrame(tick);
          };
          requestAnimationFrame(tick);
        }
      },
      { threshold: 0.5 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [value]);

  return (
    <span ref={ref} className={className}>
      {display}
    </span>
  );
}