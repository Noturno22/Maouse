export type ProgressStatus = "pendente" | "em_curso" | "concluido";

export const STATUS_ORDER: ProgressStatus[] = ["pendente", "em_curso", "concluido"];

export interface Fase {
  id: string;
  nome: string;
  estado: ProgressStatus;
  resumo: string;
}

export interface Marco {
  id: string;
  fase_id: string;
  titulo: string;
  estado: ProgressStatus;
  nota?: string;
}

export interface Meta {
  id: string;
  titulo: string;
  estado: ProgressStatus;
  prazo?: string;
}

export interface ProgressData {
  fases: Fase[];
  marcos: Marco[];
  metas: Meta[];
  updatedAt: string | null;
}

function isStatus(v: unknown): v is ProgressStatus {
  return v === "pendente" || v === "em_curso" || v === "concluido";
}

function cleanString(v: unknown, max = 200, fallback = ""): string {
  if (typeof v !== "string") return fallback;
  return v.trim().slice(0, max);
}

export function sanitizeProgress(raw: unknown): ProgressData {
  const src = (raw ?? {}) as Partial<ProgressData>;
  const fases: Fase[] = Array.isArray(src.fases)
    ? src.fases
        .filter((f): f is Fase => Boolean(f && typeof f === "object"))
        .map((f) => ({
          id: cleanString((f as Fase).id, 40) || `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          nome: cleanString((f as Fase).nome, 120) || "Fase",
          estado: isStatus((f as Fase).estado) ? (f as Fase).estado : "pendente",
          resumo: cleanString((f as Fase).resumo, 400),
        }))
    : [];
  const marcos: Marco[] = Array.isArray(src.marcos)
    ? src.marcos
        .filter((m): m is Marco => Boolean(m && typeof m === "object"))
        .map((m) => ({
          id: cleanString((m as Marco).id, 40) || `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          fase_id: cleanString((m as Marco).fase_id, 40),
          titulo: cleanString((m as Marco).titulo, 200) || "Marco",
          estado: isStatus((m as Marco).estado) ? (m as Marco).estado : "pendente",
          nota: (m as Marco).nota ? cleanString((m as Marco).nota, 300) : undefined,
        }))
    : [];
  const metas: Meta[] = Array.isArray(src.metas)
    ? src.metas
        .filter((g): g is Meta => Boolean(g && typeof g === "object"))
        .map((g) => ({
          id: cleanString((g as Meta).id, 40) || `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          titulo: cleanString((g as Meta).titulo, 200) || "Meta",
          estado: isStatus((g as Meta).estado) ? (g as Meta).estado : "pendente",
          prazo: (g as Meta).prazo ? cleanString((g as Meta).prazo, 80) : undefined,
        }))
    : [];
  return { fases, marcos, metas, updatedAt: null };
}

export const SEED_PROGRESS: ProgressData = {
  fases: [
    {
      id: "fase-a",
      nome: "Fase A — Lançamento e 1.ª venda (Angola)",
      estado: "em_curso",
      resumo:
        "Produto tecnicamente pronto a vender. O 1.º investimento (≈ US$222) cobre os bloqueadores da Pista A (Paddle real, domínio, servidor, assinatura de código, Play) para o produto ficar “vendável”.",
    },
    {
      id: "fase-b",
      nome: "Fase B — Expansão UE (Pista B)",
      estado: "em_curso",
      resumo:
        "Com Roberto (Rotterdam): marca EUIPO/USPTO, entidade UE (Portugal), landing maouse.app, vídeos demo e criadores (~€1.900–3.700). Equity proposto 8–15% com vesting ligado à entrega.",
    },
  ],
  marcos: [
    {
      id: "ma-paddle",
      fase_id: "fase-a",
      titulo: "Paddle checkout automático (webhook → chave MAO- + email)",
      estado: "concluido",
      nota: "2026-09-03",
    },
    {
      id: "ma-admin",
      fase_id: "fase-a",
      titulo: "Painel admin no license server",
      estado: "concluido",
      nota: "2026-09-13",
    },
    {
      id: "ma-assinatura",
      fase_id: "fase-a",
      titulo: "Assinatura digital do .exe (certificado)",
      estado: "pendente",
      nota: "Bloqueador #1 — falta o certificado PKI",
    },
    {
      id: "ma-deploy",
      fase_id: "fase-a",
      titulo: "Deploy do license server em produção",
      estado: "pendente",
      nota: "Deployment pós-1.ª venda",
    },
    {
      id: "ma-bake",
      fase_id: "fase-a",
      titulo: "Bake do URL real de produção no build desktop",
      estado: "pendente",
    },
    {
      id: "ma-play",
      fase_id: "fase-a",
      titulo: "Store listing mobile (Play Console)",
      estado: "pendente",
    },
    {
      id: "ma-lab",
      fase_id: "fase-a",
      titulo: "LAB de compatibilidade (≥5 dispositivos por categoria)",
      estado: "em_curso",
      nota: "i3 4.ª geração como mínimo suportado",
    },
    {
      id: "mb-roberto",
      fase_id: "fase-b",
      titulo: "Confirmar se a Fase B fica com Roberto (estrutura §3.1)",
      estado: "em_curso",
    },
    {
      id: "mb-ue",
      fase_id: "fase-b",
      titulo: "Entidade UE (Portugal)",
      estado: "pendente",
    },
    {
      id: "mb-marca",
      fase_id: "fase-b",
      titulo: "Marca EUIPO/USPTO",
      estado: "pendente",
    },
    {
      id: "mb-landing",
      fase_id: "fase-b",
      titulo: "Landing maouse.app premium",
      estado: "pendente",
    },
    {
      id: "mb-criadores",
      fase_id: "fase-b",
      titulo: "Vídeos demo e criadores",
      estado: "pendente",
    },
  ],
  metas: [
    {
      id: "g-invest",
      titulo: "1.º investimento externo recebido (Roberto Almeida — 260.000 Kz ≈ US$222)",
      estado: "concluido",
      prazo: "2026-09",
    },
    {
      id: "g-equity",
      titulo: "Fechar % de equity do Roberto (8–15% com vesting ligado à entrega)",
      estado: "em_curso",
    },
    {
      id: "g-venda",
      titulo: "1.ª venda paga (Pista A executada)",
      estado: "em_curso",
      prazo: "2026",
    },
    {
      id: "g-capital",
      titulo: "Capital adicional leve (€3–7k) por receita/piloto/subsídio — não equity",
      estado: "pendente",
      prazo: "meses 3–5",
    },
    {
      id: "g-break",
      titulo: "Break-even no cenário base (mês 14–18)",
      estado: "pendente",
    },
  ],
  updatedAt: null,
};