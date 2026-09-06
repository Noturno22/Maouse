import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space",
  subsets: ["latin"],
});

const jetBrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Mãouse — Sem cauda. Sem fios. Sem limites.",
  description:
    "Controle o computador com a mão e a voz, direto pela webcam. Sem hardware extra, sem fios, 100% privado. Windows 10/11.",
  keywords: [
    "Mãouse",
    "mouse por gestos",
    "controle por webcam",
    "mouse de mão",
    "acessibilidade",
    "controle por voz",
    "hand tracking",
  ],
  openGraph: {
title: "Mãouse — Sem cauda. Sem fios. Sem limites.",
    description:
      "Controle o computador com a mão e a voz, direto pela webcam. Sem hardware extra, 100% privado.",
    type: "website",
    siteName: "Mãouse",
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="pt"
      className={`${inter.variable} ${spaceGrotesk.variable} ${jetBrainsMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-night font-sans text-ice">
        {children}
      </body>
    </html>
  );
}