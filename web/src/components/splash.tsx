"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function Splash() {
  const [fading, setFading] = useState(false);
  const [gone, setGone] = useState(false);

  useEffect(() => {
    const reduce = prefersReducedMotion();
    const fadeAt = reduce ? 80 : 1000;
    const removeAt = reduce ? 380 : 1650;
    const t1 = setTimeout(() => setFading(true), fadeAt);
    const t2 = setTimeout(() => setGone(true), removeAt);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, []);

  if (gone) return null;

  return (
    <div
      aria-hidden="true"
      className={`fixed inset-0 z-[100] flex items-center justify-center bg-night transition-opacity duration-700 ease-out ${
        fading ? "pointer-events-none opacity-0" : "opacity-100"
      }`}
    >
      <Image
        src="/icon.png"
        alt=""
        width={148}
        height={148}
        unoptimized
        preload
        className="splash-logo rounded-2xl"
      />
    </div>
  );
}