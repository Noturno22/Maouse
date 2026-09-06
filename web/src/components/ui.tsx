"use client";

import Image from "next/image";
import { useState, type ReactNode } from "react";
import type { AccentKey, IconKey } from "@/lib/i18n";

const accentClass: Record<AccentKey, string> = {
  neon: "text-neon",
  success: "text-success",
  warn: "text-warn",
  pink: "text-pink",
  violet: "text-violet",
  royal: "text-royal",
  teal: "text-teal",
  gold: "text-gold",
};

const iconPaths: Record<IconKey, string> = {
  hand: "M3 3l7.07 16.97 2.51-7.39 7.39-2.51L3 3z",
  mic: "M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3zM19 10v2a7 7 0 0 1-14 0v-2M12 19v3",
  cpu: "M7 7h10v10H7zM9 1v3M15 1v3M9 20v3M15 20v3M1 9h3M1 15h3M20 9h3M20 15h3",
  shield: "M12 3l7 3v5c0 4.5-3.1 7.4-7 8.5C8.1 18.4 5 15.5 5 11V6l7-3z",
  phone: "M4 3h3l1.5 5L6 9.5a12 12 0 0 0 8.5 8.5l1.5-2.5L21 17v3a2 2 0 0 1-2 2A17 17 0 0 1 2 5a2 2 0 0 1 2-2z",
  zap: "M13 2L4 14h6l-1 8 9-12h-6l1-8z",
  check: "M5 13l4 4L19 7",
  pointer: "M3 3l7.07 16.97 2.51-7.39 7.39-2.51L3 3z",
  eye: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7zM12 9a3 3 0 1 1 0 6a3 3 0 1 1 0-6",
  file: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-5-6zM14 2v6h6",
  globe: "M12 5a7 7 0 1 1 0 14a7 7 0 1 1 0-14M2 12h20M12 2c2.5 2.5 3.9 6 3.9 10S14.5 19.5 12 22c-2.5-2.5-3.9-6-3.9-10S9.5 4.5 12 2z",
  gift: "M20 12v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8M2 7h20v5H2zM4 7V4a1 1 0 0 1 1-1h3a4 4 0 0 1 4 4M16 6a4 4 0 0 0-8 0M12 7v15",
};

export function Icon({
  name,
  className = "h-5 w-5",
}: {
  name: IconKey;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d={iconPaths[name]} />
    </svg>
  );
}

export function AccentIcon({ name, accent }: { name: IconKey; accent: AccentKey }) {
  return (
    <span
      className={`inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-line bg-panel ${accentClass[accent]}`}
    >
      <Icon name={name} className="h-5 w-5" />
    </span>
  );
}

export function Tag({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-line bg-panel px-3 py-1 font-mono text-xs tracking-widest text-neon uppercase">
      <span className="h-1.5 w-1.5 rounded-full bg-neon" />
      {children}
    </span>
  );
}

export function SectionHeader({
  tag,
  title,
  sub,
  id,
}: {
  tag: string;
  title: string;
  sub: string;
  id?: string;
}) {
  return (
    <div id={id} className="mx-auto max-w-2xl scroll-mt-24 text-center">
      <Tag>{tag}</Tag>
      <h2 className="mt-5 font-display text-3xl font-bold tracking-tight text-ice sm:text-4xl">
        {title}
      </h2>
      <p className="mt-4 text-base leading-7 text-tech">{sub}</p>
    </div>
  );
}

export function Wordmark({ compact = false }: { compact?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2">
      <Image
        src="/icon.png"
        alt="Mãouse"
        width={compact ? 28 : 36}
        height={compact ? 28 : 36}
        className="rounded-md"
        unoptimized
      />
      <span className="font-display text-xl font-bold tracking-tight">
        <span className="text-neon">Mã</span>
        <span className="text-ice">ouse</span>
      </span>
    </span>
  );
}

const DOWNLOAD_URL = process.env.NEXT_PUBLIC_DOWNLOAD_URL;

export function DownloadButton({
  label,
  className = "",
  big = false,
}: {
  label: string;
  className?: string;
  big?: boolean;
}) {
  const [nagged, setNagged] = useState(false);

  const base = `group relative inline-flex items-center justify-center gap-2 rounded-lg bg-neon font-display font-semibold text-night shadow-[0_0_24px_rgba(80,200,255,0.35)] transition-all hover:bg-ice hover:shadow-[0_0_36px_rgba(80,200,255,0.55)] ${big ? "px-7 py-4 text-base" : "px-5 py-3 text-sm"} ${className}`;

  if (DOWNLOAD_URL) {
    return (
      <a href={DOWNLOAD_URL} download className={base}>
        {label}
        <span className="transition-transform group-hover:translate-y-0.5">
          ↓
        </span>
      </a>
    );
  }

  return (
    <span className="inline-flex flex-col items-stretch gap-2">
      <button
        type="button"
        onClick={() => setNagged(true)}
        className={`${base} cursor-pointer`}
      >
        {label}
        <span>↓</span>
      </button>
      {nagged && (
        <p className="max-w-xs text-xs leading-5 text-tech">
          O instalador Windows estará disponível em breve. Reserva o teu email:
          <a
            href="mailto:suporte@maouse.app?subject=Pr%C3%A9-registo%20M%C3%A3ouse"
            className="ml-1 text-neon underline decoration-line underline-offset-4"
          >
            suporte@maouse.app
          </a>
        </p>
      )}
    </span>
  );
}