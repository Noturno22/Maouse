import type { Lang } from "@/lib/i18n";

export type SectionKey =
  | "features"
  | "pricing"
  | "privacy"
  | "matrix"
  | "faq"
  | "progress"
  | "media"
  | "gallery";

const IDS: Record<Lang, Record<SectionKey, string>> = {
  pt: {
    features: "beneficios",
    pricing: "precos",
    privacy: "privacidade",
    matrix: "matriz",
    faq: "faq",
    progress: "progresso",
    media: "como-funciona",
    gallery: "galeria",
  },
  ptbr: {
    features: "beneficios",
    pricing: "precos",
    privacy: "privacidade",
    matrix: "matriz",
    faq: "faq",
    progress: "progresso",
    media: "como-funciona",
    gallery: "galeria",
  },
  en: {
    features: "benefits",
    pricing: "pricing",
    privacy: "privacy",
    matrix: "compatibility",
    faq: "faq",
    progress: "roadmap",
    media: "how-it-works",
    gallery: "gallery",
  },
  es: {
    features: "beneficios",
    pricing: "precios",
    privacy: "privacidad",
    matrix: "compatibilidad",
    faq: "faq",
    progress: "progreso",
    media: "como-funciona",
    gallery: "galeria",
  },
  fr: {
    features: "avantages",
    pricing: "tarifs",
    privacy: "confidentialite",
    matrix: "compatibilite",
    faq: "faq",
    progress: "progression",
    media: "comment-ca-marche",
    gallery: "galerie",
  },
  de: {
    features: "vorteile",
    pricing: "preise",
    privacy: "datenschutz",
    matrix: "kompatibilitaet",
    faq: "faq",
    progress: "fortschritt",
    media: "so-funktioniert-es",
    gallery: "galerie",
  },
  it: {
    features: "vantaggi",
    pricing: "prezzi",
    privacy: "privacy",
    matrix: "compatibilita",
    faq: "faq",
    progress: "progresso",
    media: "come-funziona",
    gallery: "galleria",
  },
};

export function sectionId(lang: Lang, key: SectionKey): string {
  return IDS[lang][key];
}

export function anchor(lang: Lang, key: SectionKey): string {
  return `#${IDS[lang][key]}`;
}
