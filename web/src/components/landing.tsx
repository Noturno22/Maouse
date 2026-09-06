"use client";

import { LangProvider } from "@/components/lang";
import { Nav } from "@/components/nav";
import { Hero } from "@/components/hero";
import { Faq, Features, Footer, Matrix, Pricing, Privacy } from "@/components/sections";

export function Landing() {
  return (
    <LangProvider>
      <Nav />
      <main>
        <Hero />
        <Features />
        <Pricing />
        <Privacy />
        <Matrix />
        <Faq />
      </main>
      <Footer />
    </LangProvider>
  );
}