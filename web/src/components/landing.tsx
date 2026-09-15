"use client";

import { LangProvider } from "@/components/lang";
import { Nav } from "@/components/nav";
import { Hero } from "@/components/hero";
import { Splash } from "@/components/splash";
import { ProgressSection } from "@/components/progress-section";
import { Faq, Features, Footer, Matrix, Pricing, Privacy } from "@/components/sections";
import { Gallery, Media } from "@/components/media";

export function Landing() {
  return (
    <LangProvider>
      <Splash />
      <Nav />
      <main>
        <Hero />
        <Media />
        <Features />
        <Gallery />
        <Pricing />
        <Privacy />
        <Matrix />
        <ProgressSection />
        <Faq />
      </main>
      <Footer />
    </LangProvider>
  );
}