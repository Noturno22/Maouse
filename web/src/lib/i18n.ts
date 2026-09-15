import type { ProgressStatus } from "@/lib/progress";

export type Lang = "pt" | "ptbr" | "en" | "es" | "fr" | "de" | "it";

export const LANGS: Lang[] = ["pt", "ptbr", "en", "es", "fr", "de", "it"];

export const LANG_NATIVE: Record<Lang, string> = {
  pt: "Português",
  ptbr: "Português (BR)",
  en: "English",
  es: "Español",
  fr: "Français",
  de: "Deutsch",
  it: "Italiano",
};

export const LANG_LOCALE: Record<Lang, string> = {
  pt: "pt-PT",
  ptbr: "pt-BR",
  en: "en-GB",
  es: "es-ES",
  fr: "fr-FR",
  de: "de-DE",
  it: "it-IT",
};

export interface SiteLink {
  label: string;
  href: string;
}

export interface Plan {
  id: string;
  name: string;
  price: string;
  extra: string;
  highlight: boolean;
  features: string[];
  cta: string;
}

export interface Copy {
  meta: { title: string; description: string };
  nav: { product: string; links: SiteLink[]; cta: string; langLabel: string };
  progress: {
    tag: string;
    title: string;
    sub: string;
    phases: string;
    milestones: string;
    goals: string;
    updated: string;
    loading: string;
    error: string;
    byStatus: Record<ProgressStatus, string>;
  };
  hero: {
    badge: string;
    titleA: string;
    titleB: string;
    sub: string;
    bullets: string[];
    download: string;
    secondary: string;
    demoLabel: string;
    demoNote: string;
    stats: { value: string; label: string }[];
  };
  features: {
    tag: string;
    title: string;
    sub: string;
    items: { icon: IconKey; title: string; desc: string; accent: AccentKey }[];
  };
  pricing: {
    tag: string;
    title: string;
    sub: string;
    comingSoon: string;
    freeName: string;
    freeExtra: string;
    popular: string;
    guarantee: string;
    accessNote: string;
    contact: string;
    plans: Plan[];
  };
  privacy: {
    tag: string;
    title: string;
    sub: string;
    bullets: { icon: IconKey; title: string; desc: string }[];
    statement: string;
  };
  matrix: {
    tag: string;
    title: string;
    sub: string;
    cols: string[];
    rows: MatrixRow[];
    legendOk: string;
    legendWarn: string;
    legendNo: string;
    note: string;
  };
  faq: {
    tag: string;
    title: string;
    sub: string;
    items: { q: string; a: string }[];
  };
  media: {
    tag: string;
    title: string;
    sub: string;
    watchLabel: string;
    liveLabel: string;
    demoNote: string;
    stepsTitle: string;
    steps: { icon: IconKey; title: string; desc: string }[];
  };
  gallery: {
    tag: string;
    title: string;
    sub: string;
    items: { title: string; desc: string; accent: AccentKey; image?: string }[];
  };
  footer: {
    tagline: string;
    columns: { title: string; links: SiteLink[] }[];
    rights: string;
    made: string;
    hashtags: string[];
  };
}

export type IconKey =
  | "hand"
  | "mic"
  | "cpu"
  | "shield"
  | "phone"
  | "zap"
  | "check"
  | "pointer"
  | "eye"
  | "file"
  | "globe"
  | "gift";

export type AccentKey =
  | "neon"
  | "success"
  | "warn"
  | "pink"
  | "violet"
  | "royal"
  | "teal"
  | "gold";

export interface MatrixRow {
  device: string;
  webcam: string;
  fps: string;
  latency: string;
  ghosts: string;
  verdict: "ok" | "warn" | "no";
  note: string;
}

const pt: Copy = {
  meta: {
    title: "Mãouse — Sem cauda. Sem fios. Sem limites.",
    description:
      "Controle o computador com a mão e a voz, direto pela webcam. Sem hardware extra, sem fios, 100% privado. Windows 10/11.",
  },
  nav: {
    product: "Mãouse",
    links: [
      { label: "Benefícios", href: "#beneficios" },
      { label: "Preços", href: "#precos" },
      { label: "Privacidade", href: "#privacidade" },
      { label: "Compatibilidade", href: "#matriz" },
      { label: "FAQ", href: "#faq" },
      { label: "Progresso", href: "#progresso" },
    ],
    cta: "Testar grátis",
    langLabel: "Idioma",
  },
  progress: {
    tag: "Progresso",
    title: "Estamos a construir Mãouse à vista de todos.",
    sub: "Fases, marcos e metas acompanhados em tempo real — assim sabes exatamente onde estamos no caminho para a 1.ª venda e para a expansão na Europa.",
    phases: "Fases",
    milestones: "Marcos",
    goals: "Metas",
    updated: "Atualizado a",
    loading: "A carregar…",
    error: "Não foi possível carregar a progressão.",
    byStatus: {
      pendente: "Pendente",
      em_curso: "Em curso",
      concluido: "Concluído",
    },
  },
  hero: {
    badge: "Windows 10/11 · beta fechado #Maouse",
    titleA: "Sem cauda. Sem fios.",
    titleB: "Sem limites.",
    sub: "Mãouse transforma a tua webcam num rato completo: ponteiro, cliques, scroll, arrastar e comandos de voz — só com a mão. Sem hardware extra, sem fios, sem rato. 100% local e privado.",
    bullets: [
      "Sem hardware — só precisas da tua webcam",
      "Processamento 100% local, a IA corre no teu PC",
      "5 minutos de teste grátis, sem cartão",
    ],
    download: "Testar de graça",
    secondary: "Ver como funciona",
    demoLabel: "DEMO",
    demoNote: "Demo vídeo em produção — descarrega e testa já",
    stats: [
      { value: "5 min", label: "teste grátis por sessão" },
      { value: "0", label: "hardware extra" },
      { value: "100%", label: "privado, sem nuvem" },
    ],
  },
  features: {
    tag: "Benefícios",
    title: "Deixa o rato no caixote. Nada mais muda.",
    sub: "Mãouse foi desenhado para profissionais, apresentadores e pessoas com mobilidade reduzida — com precisão de produtividade, não de brinquedo.",
    items: [
      {
        icon: "hand",
        title: "Ponteiro com as tuas mãos",
        desc: "Abre a palma e o cursor segue-te. Pinch para clicar, punho para arrastar, dois dedos para scroll. Sem superfícies, sem pilhas.",
        accent: "neon",
      },
      {
        icon: "mic",
        title: "Voz como atalho",
        desc: "Stop, play, volume, abrir apps e navegar por voz — com IA local que respeita o que dizes e nunca grava para a nuvem.",
        accent: "violet",
      },
      {
        icon: "zap",
        title: "Snap magnético",
        desc: "O cursor cola-se a botões e ícones. Clicar no alvo certo deixa de ser um jogo de pontaria.",
        accent: "success",
      },
      {
        icon: "cpu",
        title: "IA embarcada",
        desc: "Rastreio neural em tempo real com filtros de precisão. Funciona no teu hardware, não num datacenter distante.",
        accent: "warn",
      },
      {
        icon: "phone",
        title: "Telemóvel como companheiro",
        desc: "Usa o telemóvel como controlo remoto ou câmara extra para gestos nas duas mãos. Do PC para o telemóvel, sem cauda.",
        accent: "pink",
      },
      {
        icon: "shield",
        title: "Feito para a tua saúde",
        desc: "Menos repetição de movimentos do rato — uma alternativa real para prevenir desconfortos e LER no dia a dia.",
        accent: "teal",
      },
    ],
  },
  pricing: {
    tag: "Preços",
    title: "Simples. Justo. Sem assinatura.",
    sub: "Compra uma vez, fica teu para sempre. O Pro inclui tudo o que o software faz.",
    comingSoon: "Loja a abrir em breve",
    freeName: "Grátis",
    freeExtra: "para sempre",
    popular: "Mais escolhido",
    guarantee: "Garantia de 14 dias e reembolso — sem perguntas.",
    accessNote:
      "Tens o plano Acessibilidade com 50% de desconto (€19,95 em vez de €39,90) mediante comprovativo — fala connosco.",
    contact: "suporte@maouse.app",
    plans: [
      {
        id: "free",
        name: "Grátis",
        price: "€0",
        extra: "teste de 5 min por sessão · marca d'agua",
        highlight: false,
        features: [
          "Teste de 5 minutos por sessão",
          "Mover, clique, scroll e arrastar",
          "Voz básica e teclas de atalho",
          "Sem cartão, instala e usa",
        ],
        cta: "Descarrega grátis",
      },
      {
        id: "lifetime",
        name: "Pro Lifetime",
        price: "€39,90",
        extra: "uma vez · para sempre",
        highlight: true,
        features: [
          "Sem limite de tempo, sem marca d'agua",
          "Todos os gestos: 12+ e duas mãos",
          "Voz completa com comandos e IA",
          "Snap magnético e multi-monitor",
          "Telemóvel como companheiro",
          "Ativação por chave · atualizações incluídas",
        ],
        cta: "Comprar Pro",
      },
      {
        id: "family",
        name: "Família",
        price: "€59,90",
        extra: "3 dispositivos",
        highlight: false,
        features: [
          "Tudo do Pro Lifetime",
          "Até 3 dispositivos na mesma chave",
          "Ideal para casa e escritório",
        ],
        cta: "Comprar Família",
      },
    ],
  },
  privacy: {
    tag: "Privacidade",
    title: "O teu olhar e a tua voz nunca saem do teu PC.",
    sub: "Mãouse é privacidade por arquitetura: a câmara, a voz e os gestos são processados no próprio dispositivo.",
    bullets: [
      {
        icon: "eye",
        title: "Câmara 100% local",
        desc: "O vídeo é processado em tempo real no teu PC e nunca é gravado nem enviado.",
      },
      {
        icon: "mic",
        title: "Voz local (STT on-device)",
        desc: "O reconhecimento de voz corre localmente. Sem microfones na nuvem, sem gravações.",
      },
      {
        icon: "file",
        title: "Zero conta obrigatória",
        desc: "Instala, usa e desinstala. Não há perfil, não há telemetria forçada.",
      },
    ],
    statement:
      "Fica sem Wi-Fi e continua a funcionar. A tua privacidade não depende da nossa boa-vontade — depende de onde corre o código: no teu dispositivo.",
  },
  matrix: {
    tag: "Compatibilidade",
    title: "Matriz de dispositivos em validação",
    sub: "Testamos cada modelo antes de prometer. Registo em curso — atualização semanal durante o beta.",
    cols: ["Dispositivo", "Webcam", "FPS", "Latência", "Cliques fantasma", "Veredito"],
    rows: [
      {
        device: "HP Notebook · Intel i3-5005U · 8GB · Win 10",
        webcam: "640×480 / 30fps",
        fps: "14.6",
        latency: "48 ms",
        ghosts: "0",
        verdict: "warn",
        note: "CPU sem GPU. Funciona, abaixo do alvo 25 fps.",
      },
      {
        device: "HP Notebook · i3-5005U + HD 5500 (noite)",
        webcam: "640×480 / 30fps",
        fps: "11.9",
        latency: "78 ms",
        ghosts: "0",
        verdict: "warn",
        note: "GPU antiga sem OpenCL. 0 glitches.",
      },
    ],
    legendOk: "Validado",
    legendWarn: "Aceite",
    legendNo: "Não validado",
    note: "Qualidade profissional garantida acima do alvo (≥25 fps). Para parques 100% sem GPU, aconselhamos teste prévio — podemos validar no teu parque antes que prometas.",
  },
  faq: {
    tag: "FAQ",
    title: "Perguntas frequentes",
    sub: "Respostas diretas. Se ficar algo por responder, escreve para suporte@maouse.app.",
    items: [
      {
        q: "O teste é mesmo grátis?",
        a: "Sim. Instalas, testes 5 minutos por sessão à vontade e não precisas de cartão. O vídeo sai com uma marca d'agua pequena até ativares o Pro.",
      },
      {
        q: "Preciso de comprar hardware?",
        a: "Não. Mãouse funciona com a webcam que já tens. Recomendamos 720p, mas modelos de 480p funcionam (com menor qualidade).",
      },
      {
        q: "O que desbloqueia o Pro Lifetime?",
        a: "Tudo: sem limite de tempo, sem marca d'agua, os 12+ gestos, duas mãos, voz completa, snap magnético e o telemóvel como companheiro. Compra-se uma vez, é teu para sempre.",
      },
      {
        q: "Os meus dados saem do computador?",
        a: "Não. A câmara, a voz e o rastreio são processados no teu PC. Mãouse funciona offline. A chave de ativação valida apenas a licença.",
      },
      {
        q: "Como instalo no Windows?",
        a: "Instalas o ficheiro .exe e em 1 clique está pronto. Se o SmartScreen mostrar um aviso durante o beta, clica em \"Mais informações → Executar assim mesmo\", como em qualquer software novo.",
      },
      {
        q: "Como funciona a garantia e o reembolso?",
        a: "Tens 14 dias para pedir reembolso sem perguntas. Se funcionar no teu hardware, ótimo; se não, devolvemos.",
      },
      {
        q: "Por que preço de 50% na Acessibilidade?",
        a: "O plano Acessibilidade custa €19,95 (metade do Pro) mediante comprovativo — pagamos a diferença. É uma decisão de produto, não de marketing.",
      },
      {
        q: "Em que línguas está o Mãouse?",
        a: "Interfaces e voz em 7 idiomas: português (PT-PT e PT-BR), inglês, espanhol, francês, alemão e italiano.",
      },
    ],
  },
  media: {
    tag: "Como funciona",
    title: "Vê a Mãouse em ação, sem sair daqui.",
    sub: "Um vídeo rápido de como a tua webcam se transforma num rato completo — mão, voz e cliques, tudo em tempo real e 100% local.",
    watchLabel: "Ver vídeo demo",
    liveLabel: "Live demo",
    demoNote: "Demo vídeo em produção — descarrega e testa já",
    stepsTitle: "Três passos e estás a usar.",
    steps: [
      {
        icon: "hand",
        title: "Abre o Mãouse",
        desc: "Lança o programa e deixa a webcam ver as tuas mãos.",
      },
      {
        icon: "pointer",
        title: "Faz um gesto",
        desc: "Mão aberta move o cursor, pinch clica e o punho arrasta.",
      },
      {
        icon: "mic",
        title: "Diz o que queres",
        desc: "Dá ordens por voz: abrir apps, play/stop, volume, navegar.",
      },
    ],
  },
  gallery: {
    tag: "Galeria",
    title: "O interior, à vista.",
    sub: "Capturas do Mãouse em funcionamento — painel, gestos, voz e o modo duas mãos.",
    items: [
      {
        title: "Painel principal",
        desc: "Estado da webcam, gestos ativos e atalhos de voz.",
        accent: "neon",
      },
      {
        title: "Duas mãos",
        desc: "Rastreio real das duas mãos para equipas e apresentações.",
        accent: "royal",
      },
      {
        title: "Voz local",
        desc: "Comandos de voz reconhecidos offline, sem nuvem.",
        accent: "violet",
      },
      {
        title: "Snap magnético",
        desc: "O cursor cola-se aos alvos com precisão cirúrgica.",
        accent: "gold",
      },
      {
        title: "Modo apresentador",
        desc: "Ponteiro gigante e spotlight para projetar com confiança.",
        accent: "pink",
      },
      {
        title: "Telemóvel companheiro",
        desc: "Controlo remoto completo a partir do telemóvel.",
        accent: "teal",
      },
    ],
  },
  footer: {
    tagline: "Sem cauda. Sem fios. Sem limites.",
    columns: [
      {
        title: "Produto",
        links: [
          { label: "Benefícios", href: "#beneficios" },
          { label: "Preços", href: "#precos" },
          { label: "Compatibilidade", href: "#matriz" },
          { label: "FAQ", href: "#faq" },
        ],
      },
      {
        title: "Suporte",
        links: [
          { label: "suporte@maouse.app", href: "mailto:suporte@maouse.app" },
        ],
      },
      {
        title: "Sobre",
        links: [
          { label: "Luar Studio Angola", href: "#" },
          { label: "Imprensa", href: "#" },
        ],
      },
    ],
    rights: "© 2026 Luar Studio Angola. Mãouse® é uma marca registada.",
    made: "Feito em português, com a mão.",
    hashtags: ["#Maouse", "#SemCauda"],
  },
};

const ptbr: Copy = {
  meta: {
    title: "Mãouse — Sem cauda. Sem fios. Sem limites.",
    description:
      "Controle o computador com a mão e a voz, direto pela webcam. Sem hardware extra, sem fios, 100% privado. Windows 10/11.",
  },
  nav: {
    product: "Mãouse",
    links: [
      { label: "Benefícios", href: "#beneficios" },
      { label: "Preços", href: "#precos" },
      { label: "Privacidade", href: "#privacidade" },
      { label: "Compatibilidade", href: "#matriz" },
      { label: "FAQ", href: "#faq" },
      { label: "Progresso", href: "#progresso" },
    ],
    cta: "Testar grátis",
    langLabel: "Idioma",
  },
  progress: {
    tag: "Progresso",
    title: "Estamos construindo a Mãouse às claras.",
    sub: "Fases, marcos e metas acompanhados em tempo real — assim você sabe exatamente onde estamos no caminho para a 1ª venda e para a expansão na Europa.",
    phases: "Fases",
    milestones: "Marcos",
    goals: "Metas",
    updated: "Atualizado em",
    loading: "Carregando…",
    error: "Não foi possível carregar o progresso.",
    byStatus: {
      pendente: "Pendente",
      em_curso: "Em andamento",
      concluido: "Concluído",
    },
  },
  hero: {
    badge: "Windows 10/11 · beta fechado #Maouse",
    titleA: "Sem cauda. Sem fios.",
    titleB: "Sem limites.",
    sub: "A Mãouse transforma sua webcam em um mouse completo: ponteiro, cliques, scroll, arrastar e comandos de voz — só com a mão. Sem hardware extra, sem fios, sem mouse. 100% local e privado.",
    bullets: [
      "Sem hardware — só precisa da sua webcam",
      "Processamento 100% local, a IA roda no seu PC",
      "5 minutos de teste grátis, sem cartão",
    ],
    download: "Testar de graça",
    secondary: "Ver como funciona",
    demoLabel: "DEMO",
    demoNote: "Demo em vídeo em produção — baixe e teste agora",
    stats: [
      { value: "5 min", label: "teste grátis por sessão" },
      { value: "0", label: "hardware extra" },
      { value: "100%", label: "privado, sem nuvem" },
    ],
  },
  features: {
    tag: "Benefícios",
    title: "Deixe o mouse na gaveta. Nada mais muda.",
    sub: "A Mãouse foi feita para profissionais, apresentadores e pessoas com mobilidade reduzida — precisão de produtividade, não de brinquedo.",
    items: [
      {
        icon: "hand",
        title: "Ponteiro com suas mãos",
        desc: "Abra a palma e o cursor segue. Pinch para clicar, punho para arrastar, dois dedos para o scroll. Sem superfícies, sem pilhas.",
        accent: "neon",
      },
      {
        icon: "mic",
        title: "Voz como atalho",
        desc: "Stop, play, volume, abrir apps e navegar por voz — com IA local que respeita o que você fala e nunca grava para a nuvem.",
        accent: "violet",
      },
      {
        icon: "zap",
        title: "Snap magnético",
        desc: "O cursor gruda em botões e ícones. Acertar o alvo deixa de ser um jogo de pontaria.",
        accent: "success",
      },
      {
        icon: "cpu",
        title: "IA embarcada",
        desc: "Rastreamento neural em tempo real com filtros de precisão. Roda no seu hardware, não em um datacenter distante.",
        accent: "warn",
      },
      {
        icon: "phone",
        title: "Celular como parceiro",
        desc: "Use o celular como controle remoto ou como câmera extra para gestos com as duas mãos. Do PC para o celular, sem cauda.",
        accent: "pink",
      },
      {
        icon: "shield",
        title: "Feito para sua saúde",
        desc: "Menos repetição de movimento do mouse — uma alternativa real para prevenir desconfortos e LER no dia a dia.",
        accent: "teal",
      },
    ],
  },
  pricing: {
    tag: "Preços",
    title: "Simples. Justo. Sem assinatura.",
    sub: "Compre uma vez, fique com ele para sempre. O Pro inclui tudo o que o software faz.",
    comingSoon: "Loja abrindo em breve",
    freeName: "Grátis",
    freeExtra: "para sempre",
    popular: "Mais escolhido",
    guarantee: "Garantia de 14 dias e reembolso — sem perguntas.",
    accessNote:
      "Tem o plano Acessibilidade com 50% de desconto (R$ — e €19,95 em vez de €39,90) mediante comprovante — fale com a gente.",
    contact: "suporte@maouse.app",
    plans: [
      {
        id: "free",
        name: "Grátis",
        price: "€0",
        extra: "teste de 5 min por sessão · marca d'água",
        highlight: false,
        features: [
          "Teste de 5 minutos por sessão",
          "Mover, clique, scroll e arrastar",
          "Voz básica e teclas de atalho",
          "Sem cartão, instala e usa",
        ],
        cta: "Baixar grátis",
      },
      {
        id: "lifetime",
        name: "Pro Lifetime",
        price: "€39,90",
        extra: "uma vez · para sempre",
        highlight: true,
        features: [
          "Sem limite de tempo, sem marca d'água",
          "Todos os gestos: 12+ e duas mãos",
          "Voz completa com comandos e IA",
          "Snap magnético e multi-monitor",
          "Celular como parceiro",
          "Ativação por chave · atualizações incluídas",
        ],
        cta: "Comprar Pro",
      },
      {
        id: "family",
        name: "Família",
        price: "€59,90",
        extra: "3 dispositivos",
        highlight: false,
        features: [
          "Tudo do Pro Lifetime",
          "Até 3 dispositivos na mesma chave",
          "Ideal para casa e escritório",
        ],
        cta: "Comprar Família",
      },
    ],
  },
  privacy: {
    tag: "Privacidade",
    title: "Seu olhar e sua voz nunca saem do seu PC.",
    sub: "A Mãouse é privacidade por arquitetura: a câmera, a voz e os gestos são processados no próprio dispositivo.",
    bullets: [
      {
        icon: "eye",
        title: "Câmera 100% local",
        desc: "O vídeo é processado em tempo real no seu PC e nunca é gravado nem enviado.",
      },
      {
        icon: "mic",
        title: "Voz local (STT on-device)",
        desc: "O reconhecimento de voz roda localmente. Sem microfones na nuvem, sem gravações.",
      },
      {
        icon: "file",
        title: "Zero conta obrigatória",
        desc: "Instala, usa e desinstala. Sem perfil, sem telemetria forçada.",
      },
    ],
    statement:
      "Fique sem Wi-Fi e continue funcionando. Sua privacidade não depende da nossa boa-vontade — depende de onde o código roda: no seu dispositivo.",
  },
  matrix: {
    tag: "Compatibilidade",
    title: "Matriz de dispositivos em validação",
    sub: "Testamos cada modelo antes de prometer. Registro em andamento — atualização semanal durante o beta.",
    cols: ["Dispositivo", "Webcam", "FPS", "Latência", "Cliques fantasma", "Veredito"],
    rows: [
      {
        device: "HP Notebook · Intel i3-5005U · 8GB · Win 10",
        webcam: "640×480 / 30fps",
        fps: "14.6",
        latency: "48 ms",
        ghosts: "0",
        verdict: "warn",
        note: "CPU sem GPU. Funciona, abaixo da meta de 25 fps.",
      },
      {
        device: "HP Notebook · i3-5005U + HD 5500 (noite)",
        webcam: "640×480 / 30fps",
        fps: "11.9",
        latency: "78 ms",
        ghosts: "0",
        verdict: "warn",
        note: "GPU antiga sem OpenCL. 0 glitches.",
      },
    ],
    legendOk: "Validado",
    legendWarn: "Aceito",
    legendNo: "Não validado",
    note: "Qualidade profissional garantida acima da meta (≥25 fps). Para parques 100% sem GPU, aconselhamos teste prévio — podemos validar no seu parque antes que você prometa.",
  },
  faq: {
    tag: "FAQ",
    title: "Perguntas frequentes",
    sub: "Respostas diretas. Se ficar algo sem resposta, escreva para suporte@maouse.app.",
    items: [
      {
        q: "O teste é mesmo grátis?",
        a: "Sim. Instala, testa 5 minutos por sessão à vontade e não precisa de cartão. O vídeo sai com uma marca d'água pequena até ativar o Pro.",
      },
      {
        q: "Preciso comprar hardware?",
        a: "Não. A Mãouse funciona com a webcam que você já tem. Recomendamos 720p, mas modelos de 480p funcionam (com menor qualidade).",
      },
      {
        q: "O que o Pro Lifetime desbloqueia?",
        a: "Tudo: sem limite de tempo, sem marca d'água, os 12+ gestos, duas mãos, voz completa, snap magnético e o celular como parceiro. Compra uma vez, é seu para sempre.",
      },
      {
        q: "Meus dados saem do computador?",
        a: "Não. A câmera, a voz e o rastreamento são processados no seu PC. A Mãouse funciona offline. A chave de ativação valida apenas a licença.",
      },
      {
        q: "Como instalo no Windows?",
        a: "Instala o arquivo .exe e em 1 clique está pronto. Se o SmartScreen mostrar um aviso durante o beta, clique em \"Mais informações → Executar mesmo assim\", como em qualquer software novo.",
      },
      {
        q: "Como funciona a garantia e o reembolso?",
        a: "Você tem 14 dias para pedir reembolso sem perguntas. Se funcionar no seu hardware, ótimo; se não, devolvemos.",
      },
      {
        q: "Por que 50% de desconto na Acessibilidade?",
        a: "O plano Acessibilidade custa €19,95 (metade do Pro) mediante comprovante — pagamos a diferença. É decisão de produto, não de marketing.",
      },
      {
        q: "Em que idiomas a Mãouse está?",
        a: "Interfaces e voz em 7 idiomas: português (PT-PT e PT-BR), inglês, espanhol, francês, alemão e italiano.",
      },
    ],
  },
  media: {
    tag: "Como funciona",
    title: "Veja a Mãouse em ação, sem sair daqui.",
    sub: "Um vídeo rápido de como sua webcam vira um mouse completo — mão, voz e cliques, tudo em tempo real e 100% local.",
    watchLabel: "Ver vídeo demo",
    liveLabel: "Live demo",
    demoNote: "Demo em vídeo em produção — baixe e teste agora",
    stepsTitle: "Três passos e você está usando.",
    steps: [
      {
        icon: "hand",
        title: "Abra a Mãouse",
        desc: "Inicie o programa e deixe a webcam ver suas mãos.",
      },
      {
        icon: "pointer",
        title: "Faça um gesto",
        desc: "Mão aberta move o cursor, pinch clica e o punho arrasta.",
      },
      {
        icon: "mic",
        title: "Diga o que quer",
        desc: "Dê ordens por voz: abrir apps, play/stop, volume, navegar.",
      },
    ],
  },
  gallery: {
    tag: "Galeria",
    title: "O interior, à vista.",
    sub: "Capturas da Mãouse em funcionamento — painel, gestos, voz e o modo duas mãos.",
    items: [
      {
        title: "Painel principal",
        desc: "Estado da webcam, gestos ativos e atalhos de voz.",
        accent: "neon",
      },
      {
        title: "Duas mãos",
        desc: "Rastreamento real das duas mãos para equipes e apresentações.",
        accent: "royal",
      },
      {
        title: "Voz local",
        desc: "Comandos de voz reconhecidos offline, sem nuvem.",
        accent: "violet",
      },
      {
        title: "Snap magnético",
        desc: "O cursor gruda nos alvos com precisão cirúrgica.",
        accent: "gold",
      },
      {
        title: "Modo apresentador",
        desc: "Ponteiro gigante e spotlight para projetar com confiança.",
        accent: "pink",
      },
      {
        title: "Celular parceiro",
        desc: "Controle remoto completo a partir do celular.",
        accent: "teal",
      },
    ],
  },
  footer: {
    tagline: "Sem cauda. Sem fios. Sem limites.",
    columns: [
      {
        title: "Produto",
        links: [
          { label: "Benefícios", href: "#beneficios" },
          { label: "Preços", href: "#precos" },
          { label: "Compatibilidade", href: "#matriz" },
          { label: "FAQ", href: "#faq" },
        ],
      },
      {
        title: "Suporte",
        links: [
          { label: "suporte@maouse.app", href: "mailto:suporte@maouse.app" },
        ],
      },
      {
        title: "Sobre",
        links: [
          { label: "Luar Studio Angola", href: "#" },
          { label: "Imprensa", href: "#" },
        ],
      },
    ],
    rights: "© 2026 Luar Studio Angola. Mãouse® é uma marca registrada.",
    made: "Feito em português, com as mãos.",
    hashtags: ["#Maouse", "#SemCauda"],
  },
};

const en: Copy = {
  meta: {
    title: "Mãouse — No tail. No wires. No limits.",
    description:
      "Control your computer with your hand and voice, straight from your webcam. No extra hardware, no wires, 100% private. Windows 10/11.",
  },
  nav: {
    product: "Mãouse",
    links: [
      { label: "Features", href: "#benefits" },
      { label: "Pricing", href: "#pricing" },
      { label: "Privacy", href: "#privacy" },
      { label: "Compatibility", href: "#compatibility" },
      { label: "FAQ", href: "#faq" },
      { label: "Roadmap", href: "#roadmap" },
    ],
    cta: "Try for free",
    langLabel: "Language",
  },
  progress: {
    tag: "Progress",
    title: "We’re building Mãouse out in the open.",
    sub: "Phases, milestones and goals tracked in real time — so you always know exactly where we are on the road to the first sale and the European expansion.",
    phases: "Phases",
    milestones: "Milestones",
    goals: "Goals",
    updated: "Updated",
    loading: "Loading…",
    error: "Could not load the progress.",
    byStatus: {
      pendente: "Pending",
      em_curso: "In progress",
      concluido: "Done",
    },
  },
  hero: {
    badge: "Windows 10/11 · closed beta #Maouse",
    titleA: "No tail. No wires.",
    titleB: "No limits.",
    sub: "Mãouse turns your webcam into a full mouse: pointer, clicks, scroll, drag and voice commands — using only your hand. No extra hardware, no wires, no mouse. 100% local and private.",
    bullets: [
      "No hardware — just your webcam",
      "100% on-device processing, AI runs on your PC",
      "5 minutes free per session, no card required",
    ],
    download: "Try for free",
    secondary: "See how it works",
    demoLabel: "DEMO",
    demoNote: "Demo video in production — download and try now",
    stats: [
      { value: "5 min", label: "free test per session" },
      { value: "0", label: "extra hardware" },
      { value: "100%", label: "private, no cloud" },
    ],
  },
  features: {
    tag: "Benefits",
    title: "Leave the mouse in the drawer. Nothing else changes.",
    sub: "Mãouse is built for professionals, presenters and people with reduced mobility — productivity-grade precision, not a toy.",
    items: [
      {
        icon: "hand",
        title: "Pointer with your hands",
        desc: "Open your palm and the cursor follows. Pinch to click, fist to drag, two fingers to scroll. No surfaces, no batteries.",
        accent: "neon",
      },
      {
        icon: "mic",
        title: "Voice as a shortcut",
        desc: "Stop, play, volume, open apps and browse by voice — with local AI that respects what you say and never records to the cloud.",
        accent: "violet",
      },
      {
        icon: "zap",
        title: "Magnetic snap",
        desc: "The cursor sticks to buttons and icons. Hitting the right target stops being a game of aim.",
        accent: "success",
      },
      {
        icon: "cpu",
        title: "Embedded AI",
        desc: "Real-time neural tracking with precision filters. It runs on your hardware, not on a distant datacenter.",
        accent: "warn",
      },
      {
        icon: "phone",
        title: "Phone as companion",
        desc: "Use your phone as a remote or as an extra camera for two-handed gestures. From PC to phone, no tail.",
        accent: "pink",
      },
      {
        icon: "shield",
        title: "Made for your health",
        desc: "Less repetitive mouse motion — a real alternative to prevent strain and RSI in daily work.",
        accent: "teal",
      },
    ],
  },
  pricing: {
    tag: "Pricing",
    title: "Simple. Fair. No subscription.",
    sub: "Buy once, it’s yours forever. Pro includes everything the software does.",
    comingSoon: "Store opening soon",
    freeName: "Free",
    freeExtra: "forever",
    popular: "Most popular",
    guarantee: "14-day guarantee and refund — no questions asked.",
    accessNote:
      "Accessibility plan available at 50% off (€19.95 instead of €39.90) with proof — talk to us.",
    contact: "suporte@maouse.app",
    plans: [
      {
        id: "free",
        name: "Free",
        price: "€0",
        extra: "5-min test per session · watermark",
        highlight: false,
        features: [
          "5-minute test per session",
          "Move, click, scroll and drag",
          "Basic voice and hotkeys",
          "No card, install and go",
        ],
        cta: "Download free",
      },
      {
        id: "lifetime",
        name: "Pro Lifetime",
        price: "€39,90",
        extra: "once · forever",
        highlight: true,
        features: [
          "No time limit, no watermark",
          "All 12+ gestures and two hands",
          "Full voice with commands and AI",
          "Magnetic snap and multi-monitor",
          "Phone as companion",
          "Key activation · updates included",
        ],
        cta: "Buy Pro",
      },
      {
        id: "family",
        name: "Family",
        price: "€59,90",
        extra: "3 devices",
        highlight: false,
        features: [
          "Everything in Pro Lifetime",
          "Up to 3 devices on one key",
          "Great for home and office",
        ],
        cta: "Buy Family",
      },
    ],
  },
  privacy: {
    tag: "Privacy",
    title: "Your eyes and your voice never leave your PC.",
    sub: "Mãouse is privacy by architecture: the camera, voice and gestures are processed on your own device.",
    bullets: [
      {
        icon: "eye",
        title: "100% local camera",
        desc: "Video is processed in real time on your PC and never recorded or sent.",
      },
      {
        icon: "mic",
        title: "Local voice (on-device STT)",
        desc: "Speech recognition runs locally. No microphones in the cloud, no recordings.",
      },
      {
        icon: "file",
        title: "Zero required account",
        desc: "Install, use and uninstall. No profile, no forced telemetry.",
      },
    ],
    statement:
      "Go offline and it keeps working. Your privacy doesn’t depend on our goodwill — it depends on where the code runs: your device.",
  },
  matrix: {
    tag: "Compatibility",
    title: "Device matrix under validation",
    sub: "We test each model before promising. Register in progress — weekly updates during beta.",
    cols: ["Device", "Webcam", "FPS", "Latency", "Ghost clicks", "Verdict"],
    rows: [
      {
        device: "HP Notebook · Intel i3-5005U · 8GB · Win 10",
        webcam: "640×480 / 30fps",
        fps: "14.6",
        latency: "48 ms",
        ghosts: "0",
        verdict: "warn",
        note: "CPU without GPU. Works, below the 25 fps target.",
      },
      {
        device: "HP Notebook · i3-5005U + HD 5500 (night)",
        webcam: "640×480 / 30fps",
        fps: "11.9",
        latency: "78 ms",
        ghosts: "0",
        verdict: "warn",
        note: "Old GPU without OpenCL. 0 glitches.",
      },
    ],
    legendOk: "Validated",
    legendWarn: "Accepted",
    legendNo: "Not validated",
    note: "Professional quality guaranteed above target (≥25 fps). For 100% GPU-less fleets we recommend a prior test — we can validate on your fleet before we promise.",
  },
  faq: {
    tag: "FAQ",
    title: "Frequently asked questions",
    sub: "Straight answers. Anything left unanswered — write to suporte@maouse.app.",
    items: [
      {
        q: "Is it really free to try?",
        a: "Yes. Install, test 5 minutes per session freely and you don’t need a card. The video shows a small watermark until you activate Pro.",
      },
      {
        q: "Do I need to buy hardware?",
        a: "No. Mãouse works with the webcam you already have. We recommend 720p, but 480p models work too (with lower quality).",
      },
      {
        q: "What does Pro Lifetime unlock?",
        a: "Everything: no time limit, no watermark, all 12+ gestures, two hands, full voice, magnetic snap and your phone as companion. Buy once, it’s yours forever.",
      },
      {
        q: "Does my data leave my computer?",
        a: "No. The camera, voice and tracking are processed on your PC. Mãouse works offline. The activation key only validates your license.",
      },
      {
        q: "How do I install on Windows?",
        a: "Install the .exe and it’s ready in 1 click. If SmartScreen shows a warning during beta, click “More info → Run anyway”, like with any new software.",
      },
      {
        q: "How does the guarantee and refund work?",
        a: "You have 14 days to ask for a refund, no questions asked. If it works on your hardware, great; if not, we refund.",
      },
      {
        q: "Why 50% off on Accessibility?",
        a: "The Accessibility plan costs €19.95 (half of Pro) with proof — we pay the difference. It’s a product decision, not marketing.",
      },
      {
        q: "Which languages is Mãouse in?",
        a: "Interfaces and voice in 7 languages: Portuguese (PT-PT and PT-BR), English, Spanish, French, German and Italian.",
      },
    ],
  },
  media: {
    tag: "How it works",
    title: "See Mãouse in action, without leaving the page.",
    sub: "A quick video of how your webcam becomes a full mouse — hand, voice and clicks, all in real time and 100% local.",
    watchLabel: "Watch demo video",
    liveLabel: "Live demo",
    demoNote: "Demo video in production — download and try now",
    stepsTitle: "Three steps and you're using it.",
    steps: [
      {
        icon: "hand",
        title: "Open Mãouse",
        desc: "Launch the app and let the webcam see your hands.",
      },
      {
        icon: "pointer",
        title: "Make a gesture",
        desc: "Open palm moves the cursor, pinch clicks and fist drags.",
      },
      {
        icon: "mic",
        title: "Say what you want",
        desc: "Give voice commands: open apps, play/stop, volume, browse.",
      },
    ],
  },
  gallery: {
    tag: "Gallery",
    title: "The inside, in plain sight.",
    sub: "Shots of Mãouse in action — panel, gestures, voice and the two-hand mode.",
    items: [
      {
        title: "Main panel",
        desc: "Webcam status, active gestures and voice shortcuts.",
        accent: "neon",
      },
      {
        title: "Two hands",
        desc: "Real tracking of both hands for teams and presentations.",
        accent: "royal",
      },
      {
        title: "Local voice",
        desc: "Voice commands recognised offline, no cloud.",
        accent: "violet",
      },
      {
        title: "Magnetic snap",
        desc: "The cursor sticks to targets with surgical precision.",
        accent: "gold",
      },
      {
        title: "Presenter mode",
        desc: "Giant pointer and spotlight to project with confidence.",
        accent: "pink",
      },
      {
        title: "Phone companion",
        desc: "Full remote control from your phone.",
        accent: "teal",
      },
    ],
  },
  footer: {
    tagline: "No tail. No wires. No limits.",
    columns: [
      {
        title: "Product",
        links: [
          { label: "Features", href: "#benefits" },
          { label: "Pricing", href: "#pricing" },
          { label: "Compatibility", href: "#compatibility" },
          { label: "FAQ", href: "#faq" },
        ],
      },
      {
        title: "Support",
        links: [{ label: "suporte@maouse.app", href: "mailto:suporte@maouse.app" }],
      },
      {
        title: "About",
        links: [
          { label: "Luar Studio Angola", href: "#" },
          { label: "Press", href: "#" },
        ],
      },
    ],
    rights: "© 2026 Luar Studio Angola. Mãouse® is a registered trademark.",
    made: "Made in Portuguese, by hand.",
    hashtags: ["#Maouse", "#SemCauda"],
  },
};

const es: Copy = {
  meta: {
    title: "Mãouse — Sin cola. Sin cables. Sin límites.",
    description:
      "Controla tu ordenador con la mano y la voz, directo desde la webcam. Sin hardware extra, sin cables, 100% privado. Windows 10/11.",
  },
  nav: {
    product: "Mãouse",
    links: [
      { label: "Beneficios", href: "#beneficios" },
      { label: "Precios", href: "#precios" },
      { label: "Privacidad", href: "#privacidad" },
      { label: "Compatibilidad", href: "#compatibilidad" },
      { label: "FAQ", href: "#faq" },
      { label: "Progreso", href: "#progreso" },
    ],
    cta: "Probar gratis",
    langLabel: "Idioma",
  },
  progress: {
    tag: "Progreso",
    title: "Estamos construyendo Mãouse a la vista de todos.",
    sub: "Fases, hitos y metas seguidos en tiempo real — así sabes exactamente dónde estamos en el camino hacia la primera venta y la expansión en Europa.",
    phases: "Fases",
    milestones: "Hitos",
    goals: "Metas",
    updated: "Actualizado el",
    loading: "Cargando…",
    error: "No se pudo cargar el progreso.",
    byStatus: {
      pendente: "Pendiente",
      em_curso: "En curso",
      concluido: "Completado",
    },
  },
  hero: {
    badge: "Windows 10/11 · beta cerrada #Maouse",
    titleA: "Sin cola. Sin cables.",
    titleB: "Sin límites.",
    sub: "Mãouse convierte tu webcam en un ratón completo: puntero, clics, scroll, arrastrar y comandos de voz — solo con la mano. Sin hardware extra, sin cables, sin ratón. 100% local y privado.",
    bullets: [
      "Sin hardware — solo necesitas tu webcam",
      "Procesamiento 100% local, la IA se ejecuta en tu PC",
      "5 minutos de prueba gratis, sin tarjeta",
    ],
    download: "Probar gratis",
    secondary: "Ver cómo funciona",
    demoLabel: "DEMO",
    demoNote: "Vídeo demo en producción — descarga y prueba ya",
    stats: [
      { value: "5 min", label: "prueba gratis por sesión" },
      { value: "0", label: "hardware extra" },
      { value: "100%", label: "privado, sin nube" },
    ],
  },
  features: {
    tag: "Beneficios",
    title: "Deja el ratón en el cajón. Nada más cambia.",
    sub: "Mãouse está diseñado para profesionales, ponentes y personas con movilidad reducida — precisión de productividad, no de juguete.",
    items: [
      {
        icon: "hand",
        title: "Puntero con tus manos",
        desc: "Abre la palma y el cursor te sigue. Pinch para clicar, puño para arrastrar, dos dedos para el scroll. Sin superficies, sin pilas.",
        accent: "neon",
      },
      {
        icon: "mic",
        title: "Voz como atajo",
        desc: "Stop, play, volumen, abrir apps y navegar por voz — con IA local que respeta lo que dices y nunca graba en la nube.",
        accent: "violet",
      },
      {
        icon: "zap",
        title: "Snap magnético",
        desc: "El cursor se pega a botones e iconos. Acertar el objetivo deja de ser un juego de puntería.",
        accent: "success",
      },
      {
        icon: "cpu",
        title: "IA integrada",
        desc: "Seguimiento neuronal en tiempo real con filtros de precisión. Funciona en tu hardware, no en un centro de datos lejano.",
        accent: "warn",
      },
      {
        icon: "phone",
        title: "Móvil como compañero",
        desc: "Usa el móvil como control remoto o cámara extra para gestos con las dos manos. Del PC al móvil, sin cola.",
        accent: "pink",
      },
      {
        icon: "shield",
        title: "Hecho para tu salud",
        desc: "Menos repetición de movimientos del ratón — una alternativa real para prevenir molestias y LER en el día a día.",
        accent: "teal",
      },
    ],
  },
  pricing: {
    tag: "Precios",
    title: "Simple. Justo. Sin suscripción.",
    sub: "Compra una vez, es tuyo para siempre. El Pro incluye todo lo que hace el software.",
    comingSoon: "Tienda abriendo pronto",
    freeName: "Gratis",
    freeExtra: "para siempre",
    popular: "Más elegido",
    guarantee: "Garantía de 14 días y reembolso — sin preguntas.",
    accessNote:
      "Tienes el plan Accesibilidad con un 50% de descuento (19,95 € en vez de 39,90 €) con comprobante — habla con nosotros.",
    contact: "suporte@maouse.app",
    plans: [
      {
        id: "free",
        name: "Gratis",
        price: "0 €",
        extra: "prueba de 5 min por sesión · marca de agua",
        highlight: false,
        features: [
          "Prueba de 5 minutos por sesión",
          "Mover, clic, scroll y arrastrar",
          "Voz básica y teclas de atajo",
          "Sin tarjeta, instala y usa",
        ],
        cta: "Descargar gratis",
      },
      {
        id: "lifetime",
        name: "Pro Lifetime",
        price: "39,90 €",
        extra: "una vez · para siempre",
        highlight: true,
        features: [
          "Sin límite de tiempo, sin marca de agua",
          "Todos los gestos: 12+ y dos manos",
          "Voz completa con comandos e IA",
          "Snap magnético y multipantalla",
          "Móvil como compañero",
          "Activación por clave · actualizaciones incluidas",
        ],
        cta: "Comprar Pro",
      },
      {
        id: "family",
        name: "Familia",
        price: "59,90 €",
        extra: "3 dispositivos",
        highlight: false,
        features: [
          "Todo lo del Pro Lifetime",
          "Hasta 3 dispositivos en la misma clave",
          "Ideal para casa y oficina",
        ],
        cta: "Comprar Familia",
      },
    ],
  },
  privacy: {
    tag: "Privacidad",
    title: "Tu mirada y tu voz nunca salen de tu PC.",
    sub: "Mãouse es privacidad por arquitectura: la cámara, la voz y los gestos se procesan en tu propio dispositivo.",
    bullets: [
      {
        icon: "eye",
        title: "Cámara 100% local",
        desc: "El vídeo se procesa en tiempo real en tu PC y nunca se graba ni se envía.",
      },
      {
        icon: "mic",
        title: "Voz local (STT on-device)",
        desc: "El reconocimiento de voz se ejecuta localmente. Sin micrófonos en la nube, sin grabaciones.",
      },
      {
        icon: "file",
        title: "Cero cuentas obligatorias",
        desc: "Instala, usa y desinstala. Sin perfil, sin telemetría forzada.",
      },
    ],
    statement:
      "Quédate sin Wi-Fi y sigue funcionando. Tu privacidad no depende de nuestra buena voluntad — depende de dónde corre el código: en tu dispositivo.",
  },
  matrix: {
    tag: "Compatibilidad",
    title: "Matriz de dispositivos en validación",
    sub: "Probamos cada modelo antes de prometer. Registro en curso — actualización semanal durante la beta.",
    cols: ["Dispositivo", "Webcam", "FPS", "Latencia", "Clics fantasma", "Veredicto"],
    rows: [
      {
        device: "HP Notebook · Intel i3-5005U · 8GB · Win 10",
        webcam: "640×480 / 30fps",
        fps: "14.6",
        latency: "48 ms",
        ghosts: "0",
        verdict: "warn",
        note: "CPU sin GPU. Funciona, por debajo del objetivo de 25 fps.",
      },
      {
        device: "HP Notebook · i3-5005U + HD 5500 (noche)",
        webcam: "640×480 / 30fps",
        fps: "11.9",
        latency: "78 ms",
        ghosts: "0",
        verdict: "warn",
        note: "GPU antigua sin OpenCL. 0 fallos.",
      },
    ],
    legendOk: "Validado",
    legendWarn: "Aceptado",
    legendNo: "No validado",
    note: "Calidad profesional garantizada por encima del objetivo (≥25 fps). Para parques 100% sin GPU, aconsejamos una prueba previa — podemos validar en tu parque antes de que prometas.",
  },
  faq: {
    tag: "FAQ",
    title: "Preguntas frecuentes",
    sub: "Respuestas directas. Si queda algo sin responder, escribe a suporte@maouse.app.",
    items: [
      {
        q: "¿La prueba es realmente gratis?",
        a: "Sí. Instalas, pruebas 5 minutos por sesión sin límite y no necesitas tarjeta. El vídeo sale con una pequeña marca de agua hasta que actives el Pro.",
      },
      {
        q: "¿Necesito comprar hardware?",
        a: "No. Mãouse funciona con la webcam que ya tienes. Recomendamos 720p, pero los modelos de 480p también funcionan (con menor calidad).",
      },
      {
        q: "¿Qué desbloquea el Pro Lifetime?",
        a: "Todo: sin límite de tiempo, sin marca de agua, los 12+ gestos, dos manos, voz completa, snap magnético y el móvil como compañero. Se compra una vez, es tuyo para siempre.",
      },
      {
        q: "¿Mis datos salen del ordenador?",
        a: "No. La cámara, la voz y el seguimiento se procesan en tu PC. Mãouse funciona sin conexión. La clave de activación solo valida la licencia.",
      },
      {
        q: "¿Cómo lo instalo en Windows?",
        a: "Instalas el archivo .exe y en 1 clic está listo. Si SmartScreen muestra un aviso durante la beta, haz clic en \"Más información → Ejecutar de todos modos\", como con cualquier software nuevo.",
      },
      {
        q: "¿Cómo funcionan la garantía y el reembolso?",
        a: "Tienes 14 días para pedir el reembolso sin preguntas. Si funciona en tu hardware, perfecto; si no, te lo devolvemos.",
      },
      {
        q: "¿Por qué el 50% en Accesibilidad?",
        a: "El plan Accesibilidad cuesta 19,95 € (la mitad del Pro) con comprobante — pagamos la diferencia. Es una decisión de producto, no de marketing.",
      },
      {
        q: "¿En qué idiomas está Mãouse?",
        a: "Interfaces y voz en 7 idiomas: portugués (PT-PT y PT-BR), inglés, español, francés, alemán e italiano.",
      },
    ],
  },
  media: {
    tag: "Cómo funciona",
    title: "Mira Mãouse en acción, sin salir de aquí.",
    sub: "Un vídeo rápido de cómo tu webcam se convierte en un ratón completo — mano, voz y clics, todo en tiempo real y 100% local.",
    watchLabel: "Ver vídeo demo",
    liveLabel: "Demo en vivo",
    demoNote: "Vídeo demo en producción — descarga y prueba ya",
    stepsTitle: "Tres pasos y ya lo estás usando.",
    steps: [
      {
        icon: "hand",
        title: "Abre Mãouse",
        desc: "Inicia el programa y deja que la webcam vea tus manos.",
      },
      {
        icon: "pointer",
        title: "Haz un gesto",
        desc: "Mano abierta mueve el cursor, pinch clica y el puño arrastra.",
      },
      {
        icon: "mic",
        title: "Di lo que quieres",
        desc: "Da órdenes por voz: abrir apps, play/stop, volumen, navegar.",
      },
    ],
  },
  gallery: {
    tag: "Galería",
    title: "El interior, a la vista.",
    sub: "Capturas de Mãouse en funcionamiento — panel, gestos, voz y el modo dos manos.",
    items: [
      {
        title: "Panel principal",
        desc: "Estado de la webcam, gestos activos y atajos de voz.",
        accent: "neon",
      },
      {
        title: "Dos manos",
        desc: "Seguimiento real de las dos manos para equipos y presentaciones.",
        accent: "royal",
      },
      {
        title: "Voz local",
        desc: "Comandos de voz reconocidos sin conexión, sin nube.",
        accent: "violet",
      },
      {
        title: "Snap magnético",
        desc: "El cursor se pega a los objetivos con precisión quirúrgica.",
        accent: "gold",
      },
      {
        title: "Modo ponente",
        desc: "Puntero gigante y spotlight para proyectar con confianza.",
        accent: "pink",
      },
      {
        title: "Móvil compañero",
        desc: "Control remoto completo desde el móvil.",
        accent: "teal",
      },
    ],
  },
  footer: {
    tagline: "Sin cola. Sin cables. Sin límites.",
    columns: [
      {
        title: "Producto",
        links: [
          { label: "Beneficios", href: "#beneficios" },
          { label: "Precios", href: "#precios" },
          { label: "Compatibilidad", href: "#compatibilidad" },
          { label: "FAQ", href: "#faq" },
        ],
      },
      {
        title: "Soporte",
        links: [{ label: "suporte@maouse.app", href: "mailto:suporte@maouse.app" }],
      },
      {
        title: "Sobre",
        links: [
          { label: "Luar Studio Angola", href: "#" },
          { label: "Prensa", href: "#" },
        ],
      },
    ],
    rights: "© 2026 Luar Studio Angola. Mãouse® es una marca registrada.",
    made: "Hecho en portugués, con la mano.",
    hashtags: ["#Maouse", "#SemCauda"],
  },
};

const fr: Copy = {
  meta: {
    title: "Mãouse — Sans queue. Sans fil. Sans limites.",
    description:
      "Contrôlez votre ordinateur avec la main et la voix, directement depuis la webcam. Sans matériel supplémentaire, sans fil, 100 % privé. Windows 10/11.",
  },
  nav: {
    product: "Mãouse",
    links: [
      { label: "Avantages", href: "#avantages" },
      { label: "Tarifs", href: "#tarifs" },
      { label: "Confidentialité", href: "#confidentialite" },
      { label: "Compatibilité", href: "#compatibilite" },
      { label: "FAQ", href: "#faq" },
      { label: "Progression", href: "#progression" },
    ],
    cta: "Essayer gratuitement",
    langLabel: "Langue",
  },
  progress: {
    tag: "Progression",
    title: "Nous construisons Mãouse à la vue de tous.",
    sub: "Phases, jalons et objectifs suivis en temps réel — vous savez ainsi exactement où nous en sommes vers la première vente et l'expansion en Europe.",
    phases: "Phases",
    milestones: "Jalons",
    goals: "Objectifs",
    updated: "Mis à jour le",
    loading: "Chargement…",
    error: "Impossible de charger la progression.",
    byStatus: {
      pendente: "En attente",
      em_curso: "En cours",
      concluido: "Terminé",
    },
  },
  hero: {
    badge: "Windows 10/11 · bêta fermée #Maouse",
    titleA: "Sans queue. Sans fil.",
    titleB: "Sans limites.",
    sub: "Mãouse transforme votre webcam en souris complète : pointeur, clics, défilement, glisser-déposer et commandes vocales — avec la seule main. Sans matériel supplémentaire, sans fil, sans souris. 100 % local et privé.",
    bullets: [
      "Sans matériel — il vous faut juste votre webcam",
      "Traitement 100 % local, l'IA tourne sur votre PC",
      "5 minutes d'essai gratuit, sans carte",
    ],
    download: "Essayer gratuitement",
    secondary: "Voir comment ça marche",
    demoLabel: "DÉMO",
    demoNote: "Vidéo démo en production — téléchargez et essayez maintenant",
    stats: [
      { value: "5 min", label: "essai gratuit par session" },
      { value: "0", label: "matériel supplémentaire" },
      { value: "100 %", label: "privé, sans cloud" },
    ],
  },
  features: {
    tag: "Avantages",
    title: "Laissez la souris au tiroir. Rien d'autre ne change.",
    sub: "Mãouse est conçu pour les professionnels, les présentateurs et les personnes à mobilité réduite — une précision de productivité, pas un jouet.",
    items: [
      {
        icon: "hand",
        title: "Pointeur avec vos mains",
        desc: "Ouvrez la paume et le curseur vous suit. Pinch pour cliquer, poing pour glisser, deux doigts pour défiler. Sans surface, sans pile.",
        accent: "neon",
      },
      {
        icon: "mic",
        title: "La voix comme raccourci",
        desc: "Stop, play, volume, ouvrir des apps et naviguer à la voix — avec une IA locale qui respecte ce que vous dites et n'enregistre jamais dans le cloud.",
        accent: "violet",
      },
      {
        icon: "zap",
        title: "Snap magnétique",
        desc: "Le curseur colle aux boutons et aux icônes. Atteindre la bonne cible n'est plus un jeu d'adresse.",
        accent: "success",
      },
      {
        icon: "cpu",
        title: "IA embarquée",
        desc: "Suivi neuronal en temps réel avec filtres de précision. Il tourne sur votre matériel, pas dans un datacenter lointain.",
        accent: "warn",
      },
      {
        icon: "phone",
        title: "Téléphone comme compagnon",
        desc: "Utilisez votre téléphone comme télécommande ou caméra supplémentaire pour des gestes à deux mains. Du PC au téléphone, sans queue.",
        accent: "pink",
      },
      {
        icon: "shield",
        title: "Conçu pour votre santé",
        desc: "Moins de mouvements répétitifs de la souris — une vraie alternative pour prévenir les tensions et les TMS au quotidien.",
        accent: "teal",
      },
    ],
  },
  pricing: {
    tag: "Tarifs",
    title: "Simple. Juste. Sans abonnement.",
    sub: "Achetez une fois, c'est à vous pour toujours. Le Pro inclut tout ce que fait le logiciel.",
    comingSoon: "Boutique bientôt ouverte",
    freeName: "Gratuit",
    freeExtra: "pour toujours",
    popular: "Le plus choisi",
    guarantee: "Garantie et remboursement de 14 jours — sans questions.",
    accessNote:
      "Le plan Accessibilité est à -50 % (19,95 € au lieu de 39,90 €) sur justificatif — parlez-nous.",
    contact: "suporte@maouse.app",
    plans: [
      {
        id: "free",
        name: "Gratuit",
        price: "0 €",
        extra: "essai de 5 min par session · filigrane",
        highlight: false,
        features: [
          "Essai de 5 minutes par session",
          "Déplacer, clic, défilement et glisser",
          "Voix de base et raccourcis clavier",
          "Sans carte, installez et utilisez",
        ],
        cta: "Télécharger gratuitement",
      },
      {
        id: "lifetime",
        name: "Pro Lifetime",
        price: "39,90 €",
        extra: "une fois · pour toujours",
        highlight: true,
        features: [
          "Sans limite de temps, sans filigrane",
          "Tous les gestes : 12+ et deux mains",
          "Voix complète avec commandes et IA",
          "Snap magnétique et multi-écrans",
          "Téléphone comme compagnon",
          "Activation par clé · mises à jour incluses",
        ],
        cta: "Acheter Pro",
      },
      {
        id: "family",
        name: "Famille",
        price: "59,90 €",
        extra: "3 appareils",
        highlight: false,
        features: [
          "Tout le Pro Lifetime",
          "Jusqu'à 3 appareils sur la même clé",
          "Idéal pour la maison et le bureau",
        ],
        cta: "Acheter Famille",
      },
    ],
  },
  privacy: {
    tag: "Confidentialité",
    title: "Votre regard et votre voix ne quittent jamais votre PC.",
    sub: "Mãouse, c'est la confidentialité par architecture : la caméra, la voix et les gestes sont traités sur votre propre appareil.",
    bullets: [
      {
        icon: "eye",
        title: "Caméra 100 % locale",
        desc: "La vidéo est traitée en temps réel sur votre PC et n'est jamais enregistrée ni envoyée.",
      },
      {
        icon: "mic",
        title: "Voix locale (STT on-device)",
        desc: "La reconnaissance vocale s'exécute localement. Pas de micro dans le cloud, pas d'enregistrement.",
      },
      {
        icon: "file",
        title: "Aucun compte obligatoire",
        desc: "Installez, utilisez et désinstallez. Pas de profil, pas de télémétrie forcée.",
      },
    ],
    statement:
      "Coupez le Wi-Fi et ça continue de fonctionner. Votre confidentialité ne dépend pas de notre bonne volonté — elle dépend de l'endroit où tourne le code : votre appareil.",
  },
  matrix: {
    tag: "Compatibilité",
    title: "Matrice d'appareils en validation",
    sub: "Nous testons chaque modèle avant de promettre. Enregistrement en cours — mise à jour hebdomadaire pendant la bêta.",
    cols: ["Appareil", "Webcam", "FPS", "Latence", "Clics fantômes", "Verdict"],
    rows: [
      {
        device: "HP Notebook · Intel i3-5005U · 8GB · Win 10",
        webcam: "640×480 / 30fps",
        fps: "14.6",
        latency: "48 ms",
        ghosts: "0",
        verdict: "warn",
        note: "CPU sans GPU. Fonctionne, sous l'objectif de 25 fps.",
      },
      {
        device: "HP Notebook · i3-5005U + HD 5500 (nuit)",
        webcam: "640×480 / 30fps",
        fps: "11.9",
        latency: "78 ms",
        ghosts: "0",
        verdict: "warn",
        note: "GPU ancien sans OpenCL. 0 accroc.",
      },
    ],
    legendOk: "Validé",
    legendWarn: "Accepté",
    legendNo: "Non validé",
    note: "Qualité professionnelle garantie au-dessus de l'objectif (≥25 fps). Pour les parcs 100 % sans GPU, nous conseillons un test préalable — nous pouvons valider sur votre parc avant que vous ne promettiez.",
  },
  faq: {
    tag: "FAQ",
    title: "Questions fréquentes",
    sub: "Des réponses directes. S'il reste une question, écrivez à suporte@maouse.app.",
    items: [
      {
        q: "L'essai est-il vraiment gratuit ?",
        a: "Oui. Installez, testez 5 minutes par session librement et sans carte. La vidéo affiche un petit filigrane jusqu'à l'activation du Pro.",
      },
      {
        q: "Dois-je acheter du matériel ?",
        a: "Non. Mãouse fonctionne avec la webcam que vous avez déjà. Nous recommandons 720p, mais les modèles 480p fonctionnent aussi (qualité moindre).",
      },
      {
        q: "Que débloque le Pro Lifetime ?",
        a: "Tout : sans limite de temps, sans filigrane, les 12+ gestes, deux mains, voix complète, snap magnétique et le téléphone comme compagnon. Achetez une fois, c'est à vous pour toujours.",
      },
      {
        q: "Mes données quittent-elles mon ordinateur ?",
        a: "Non. La caméra, la voix et le suivi sont traités sur votre PC. Mãouse fonctionne hors ligne. La clé d'activation ne valide que la licence.",
      },
      {
        q: "Comment installer sur Windows ?",
        a: "Installez le fichier .exe et c'est prêt en 1 clic. Si SmartScreen affiche un avertissement pendant la bêta, cliquez sur « Plus d'infos → Exécuter quand même », comme pour tout nouveau logiciel.",
      },
      {
        q: "Comment marchent la garantie et le remboursement ?",
        a: "Vous avez 14 jours pour demander un remboursement, sans questions. Si ça fonctionne sur votre matériel, parfait ; sinon, nous remboursons.",
      },
      {
        q: "Pourquoi -50 % sur l'Accessibilité ?",
        a: "Le plan Accessibilité coûte 19,95 € (la moitié du Pro) sur justificatif — nous payons la différence. C'est une décision produit, pas du marketing.",
      },
      {
        q: "En quelles langues est Mãouse ?",
        a: "Interfaces et voix en 7 langues : portugais (PT-PT et PT-BR), anglais, espagnol, français, allemand et italien.",
      },
    ],
  },
  media: {
    tag: "Comment ça marche",
    title: "Voyez Mãouse en action, sans quitter la page.",
    sub: "Une courte vidéo montrant comment votre webcam devient une souris complète — main, voix et clics, en temps réel et 100 % local.",
    watchLabel: "Voir la vidéo démo",
    liveLabel: "Démo en direct",
    demoNote: "Vidéo démo en production — téléchargez et essayez maintenant",
    stepsTitle: "Trois étapes et c'est parti.",
    steps: [
      {
        icon: "hand",
        title: "Ouvrez Mãouse",
        desc: "Lancez le programme et laissez la webcam voir vos mains.",
      },
      {
        icon: "pointer",
        title: "Faites un geste",
        desc: "Main ouverte déplace le curseur, pinch clique et le poing glisse.",
      },
      {
        icon: "mic",
        title: "Dites ce que vous voulez",
        desc: "Donnez des ordres à la voix : ouvrir des apps, play/stop, volume, naviguer.",
      },
    ],
  },
  gallery: {
    tag: "Galerie",
    title: "L'intérieur, à la vue.",
    sub: "Captures de Mãouse en fonctionnement — panneau, gestes, voix et mode deux mains.",
    items: [
      {
        title: "Panneau principal",
        desc: "État de la webcam, gestes actifs et raccourcis vocaux.",
        accent: "neon",
      },
      {
        title: "Deux mains",
        desc: "Suivi réel des deux mains pour les équipes et présentations.",
        accent: "royal",
      },
      {
        title: "Voix locale",
        desc: "Commandes vocales reconnues hors ligne, sans cloud.",
        accent: "violet",
      },
      {
        title: "Snap magnétique",
        desc: "Le curseur colle aux cibles avec une précision chirurgicale.",
        accent: "gold",
      },
      {
        title: "Mode présentateur",
        desc: "Pointeur géant et spotlight pour projeter en confiance.",
        accent: "pink",
      },
      {
        title: "Téléphone compagnon",
        desc: "Contrôle à distance complet depuis le téléphone.",
        accent: "teal",
      },
    ],
  },
  footer: {
    tagline: "Sans queue. Sans fil. Sans limites.",
    columns: [
      {
        title: "Produit",
        links: [
          { label: "Avantages", href: "#avantages" },
          { label: "Tarifs", href: "#tarifs" },
          { label: "Compatibilité", href: "#compatibilite" },
          { label: "FAQ", href: "#faq" },
        ],
      },
      {
        title: "Support",
        links: [{ label: "suporte@maouse.app", href: "mailto:suporte@maouse.app" }],
      },
      {
        title: "À propos",
        links: [
          { label: "Luar Studio Angola", href: "#" },
          { label: "Presse", href: "#" },
        ],
      },
    ],
    rights: "© 2026 Luar Studio Angola. Mãouse® est une marque déposée.",
    made: "Fait en portugais, à la main.",
    hashtags: ["#Maouse", "#SemCauda"],
  },
};

const de: Copy = {
  meta: {
    title: "Mãouse — Kein Kabel. Keine Maus. Keine Grenzen.",
    description:
      "Steuere deinen Computer mit Hand und Stimme, direkt über die Webcam. Keine zusätzliche Hardware, kein Kabel, 100 % privat. Windows 10/11.",
  },
  nav: {
    product: "Mãouse",
    links: [
      { label: "Vorteile", href: "#vorteile" },
      { label: "Preise", href: "#preise" },
      { label: "Datenschutz", href: "#datenschutz" },
      { label: "Kompatibilität", href: "#kompatibilitaet" },
      { label: "FAQ", href: "#faq" },
      { label: "Fortschritt", href: "#fortschritt" },
    ],
    cta: "Gratis testen",
    langLabel: "Sprache",
  },
  progress: {
    tag: "Fortschritt",
    title: "Wir bauen Mãouse offen vor aller Augen.",
    sub: "Phasen, Meilensteine und Ziele in Echtzeit verfolgt — so weißt du genau, wo wir auf dem Weg zum ersten Verkauf und zur Expansion in Europa stehen.",
    phases: "Phasen",
    milestones: "Meilensteine",
    goals: "Ziele",
    updated: "Aktualisiert am",
    loading: "Lädt…",
    error: "Fortschritt konnte nicht geladen werden.",
    byStatus: {
      pendente: "Ausstehend",
      em_curso: "Läuft",
      concluido: "Abgeschlossen",
    },
  },
  hero: {
    badge: "Windows 10/11 · geschlossene Beta #Maouse",
    titleA: "Kein Kabel. Keine Maus.",
    titleB: "Keine Grenzen.",
    sub: "Mãouse macht deine Webcam zur vollständigen Maus: Zeiger, Klicks, Scrollen, Ziehen und Sprachbefehle — nur mit der Hand. Keine zusätzliche Hardware, kein Kabel, keine Maus. 100 % lokal und privat.",
    bullets: [
      "Keine Hardware — nur deine Webcam nötig",
      "100 % lokale Verarbeitung, die KI läuft auf deinem PC",
      "5 Minuten gratis testen, ohne Karte",
    ],
    download: "Gratis testen",
    secondary: "So funktioniert's",
    demoLabel: "DEMO",
    demoNote: "Demo-Video in Produktion — jetzt herunterladen und testen",
    stats: [
      { value: "5 Min", label: "gratis Test pro Sitzung" },
      { value: "0", label: "zusätzliche Hardware" },
      { value: "100 %", label: "privat, ohne Cloud" },
    ],
  },
  features: {
    tag: "Vorteile",
    title: "Lass die Maus in der Schublade. Sonst ändert sich nichts.",
    sub: "Mãouse ist für Profis, Präsentatoren und Menschen mit eingeschränkter Mobilität gemacht — Produktivitäts-Präzision, kein Spielzeug.",
    items: [
      {
        icon: "hand",
        title: "Zeiger mit deinen Händen",
        desc: "Öffne die Handfläche und der Cursor folgt. Pinch zum Klicken, Faust zum Ziehen, zwei Finger zum Scrollen. Ohne Oberfläche, ohne Batterien.",
        accent: "neon",
      },
      {
        icon: "mic",
        title: "Stimme als Shortcut",
        desc: "Stop, Play, Lautstärke, Apps öffnen und navigieren per Stimme — mit lokaler KI, die respektiert, was du sagst, und nie in die Cloud aufnimmt.",
        accent: "violet",
      },
      {
        icon: "zap",
        title: "Magnetischer Snap",
        desc: "Der Cursor haftet an Buttons und Symbolen. Das richtige Ziel treffen ist kein Zielspiel mehr.",
        accent: "success",
      },
      {
        icon: "cpu",
        title: "Integrierte KI",
        desc: "Neuronales Echtzeit-Tracking mit Präzisionsfiltern. Es läuft auf deiner Hardware, nicht in einem fernen Rechenzentrum.",
        accent: "warn",
      },
      {
        icon: "phone",
        title: "Handy als Begleiter",
        desc: "Nutze dein Handy als Fernbedienung oder zweite Kamera für Gesten mit beiden Händen. Vom PC zum Handy, ohne Kabel.",
        accent: "pink",
      },
      {
        icon: "shield",
        title: "Für deine Gesundheit gemacht",
        desc: "Weniger wiederholte Mausbewegungen — eine echte Alternative zur Vorbeugung von Beschwerden und RSI im Alltag.",
        accent: "teal",
      },
    ],
  },
  pricing: {
    tag: "Preise",
    title: "Einfach. Fair. Kein Abo.",
    sub: "Einmal kaufen, für immer deins. Pro enthält alles, was die Software kann.",
    comingSoon: "Shop öffnet bald",
    freeName: "Gratis",
    freeExtra: "für immer",
    popular: "Am beliebtesten",
    guarantee: "14 Tage Garantie und Rückerstattung — ohne Fragen.",
    accessNote:
      "Der Barrierefreiheit-Tarif mit 50 % Rabatt (19,95 € statt 39,90 €) gegen Nachweis — sprich uns an.",
    contact: "suporte@maouse.app",
    plans: [
      {
        id: "free",
        name: "Gratis",
        price: "0 €",
        extra: "5-Min-Test pro Sitzung · Wasserzeichen",
        highlight: false,
        features: [
          "5-Minuten-Test pro Sitzung",
          "Bewegen, Klick, Scroll und Ziehen",
          "Basis-Stimme und Hotkeys",
          "Ohne Karte, installieren und loslegen",
        ],
        cta: "Gratis herunterladen",
      },
      {
        id: "lifetime",
        name: "Pro Lifetime",
        price: "39,90 €",
        extra: "einmal · für immer",
        highlight: true,
        features: [
          "Keine Zeitbegrenzung, kein Wasserzeichen",
          "Alle 12+ Gesten und zwei Hände",
          "Volle Stimme mit Befehlen und KI",
          "Magnetischer Snap und Multi-Monitor",
          "Handy als Begleiter",
          "Aktivierung per Schlüssel · Updates inklusive",
        ],
        cta: "Pro kaufen",
      },
      {
        id: "family",
        name: "Familie",
        price: "59,90 €",
        extra: "3 Geräte",
        highlight: false,
        features: [
          "Alles aus Pro Lifetime",
          "Bis zu 3 Geräte mit einem Schlüssel",
          "Ideal für Zuhause und Büro",
        ],
        cta: "Familie kaufen",
      },
    ],
  },
  privacy: {
    tag: "Datenschutz",
    title: "Dein Blick und deine Stimme verlassen niemals deinen PC.",
    sub: "Mãouse ist Datenschutz durch Architektur: Kamera, Stimme und Gesten werden auf deinem eigenen Gerät verarbeitet.",
    bullets: [
      {
        icon: "eye",
        title: "100 % lokale Kamera",
        desc: "Das Video wird in Echtzeit auf deinem PC verarbeitet und niemals aufgezeichnet oder gesendet.",
      },
      {
        icon: "mic",
        title: "Lokale Stimme (STT on-device)",
        desc: "Die Spracherkennung läuft lokal. Keine Mikrofone in der Cloud, keine Aufnahmen.",
      },
      {
        icon: "file",
        title: "Kein Pflichtkonto",
        desc: "Installieren, nutzen, deinstallieren. Kein Profil, keine erzwungene Telemetrie.",
      },
    ],
    statement:
      "Geh offline und es funktioniert weiter. Dein Datenschutz hängt nicht von unserem guten Willen ab — sondern davon, wo der Code läuft: auf deinem Gerät.",
  },
  matrix: {
    tag: "Kompatibilität",
    title: "Gerätematrix in Validierung",
    sub: "Wir testen jedes Modell, bevor wir etwas versprechen. Registrierung läuft — wöchentliche Updates während der Beta.",
    cols: ["Gerät", "Webcam", "FPS", "Latenz", "Geisterklicks", "Urteil"],
    rows: [
      {
        device: "HP Notebook · Intel i3-5005U · 8GB · Win 10",
        webcam: "640×480 / 30fps",
        fps: "14.6",
        latency: "48 ms",
        ghosts: "0",
        verdict: "warn",
        note: "CPU ohne GPU. Funktioniert, unter dem Ziel von 25 fps.",
      },
      {
        device: "HP Notebook · i3-5005U + HD 5500 (Nacht)",
        webcam: "640×480 / 30fps",
        fps: "11.9",
        latency: "78 ms",
        ghosts: "0",
        verdict: "warn",
        note: "Alte GPU ohne OpenCL. 0 Aussetzer.",
      },
    ],
    legendOk: "Validiert",
    legendWarn: "Akzeptiert",
    legendNo: "Nicht validiert",
    note: "Professionelle Qualität über dem Ziel garantiert (≥25 fps). Für Flotten ganz ohne GPU empfehlen wir einen vorherigen Test — wir können vorab auf deiner Flotte validieren, bevor du etwas versprichst.",
  },
  faq: {
    tag: "FAQ",
    title: "Häufige Fragen",
    sub: "Klare Antworten. Bleibt etwas offen, schreib an suporte@maouse.app.",
    items: [
      {
        q: "Ist der Test wirklich gratis?",
        a: "Ja. Installiere, teste 5 Minuten pro Sitzung frei und ohne Karte. Das Video zeigt ein kleines Wasserzeichen, bis du Pro aktivierst.",
      },
      {
        q: "Muss ich Hardware kaufen?",
        a: "Nein. Mãouse funktioniert mit der Webcam, die du schon hast. Wir empfehlen 720p, aber auch 480p-Modelle funktionieren (mit geringerer Qualität).",
      },
      {
        q: "Was schaltet Pro Lifetime frei?",
        a: "Alles: keine Zeitbegrenzung, kein Wasserzeichen, die 12+ Gesten, zwei Hände, volle Stimme, magnetischer Snap und das Handy als Begleiter. Einmal kaufen, für immer deins.",
      },
      {
        q: "Verlassen meine Daten den Computer?",
        a: "Nein. Kamera, Stimme und Tracking werden auf deinem PC verarbeitet. Mãouse funktioniert offline. Der Aktivierungsschlüssel prüft nur die Lizenz.",
      },
      {
        q: "Wie installiere ich unter Windows?",
        a: "Installiere die .exe und in 1 Klick ist es bereit. Zeigt SmartScreen während der Beta eine Warnung, klicke auf „Weitere Informationen → Trotzdem ausführen“, wie bei jeder neuen Software.",
      },
      {
        q: "Wie funktionieren Garantie und Rückerstattung?",
        a: "Du hast 14 Tage für eine Rückerstattung, ohne Fragen. Wenn es auf deiner Hardware läuft, super; wenn nicht, erstatten wir.",
      },
      {
        q: "Warum 50 % bei Barrierefreiheit?",
        a: "Der Barrierefreiheit-Tarif kostet 19,95 € (die Hälfte von Pro) gegen Nachweis — wir zahlen die Differenz. Eine Produktentscheidung, kein Marketing.",
      },
      {
        q: "In welchen Sprachen gibt es Mãouse?",
        a: "Oberflächen und Stimme in 7 Sprachen: Portugiesisch (PT-PT und PT-BR), Englisch, Spanisch, Französisch, Deutsch und Italienisch.",
      },
    ],
  },
  media: {
    tag: "So funktioniert's",
    title: "Sieh Mãouse in Aktion, ohne die Seite zu verlassen.",
    sub: "Ein kurzes Video, wie deine Webcam zur vollständigen Maus wird — Hand, Stimme und Klicks, alles in Echtzeit und 100 % lokal.",
    watchLabel: "Demo-Video ansehen",
    liveLabel: "Live-Demo",
    demoNote: "Demo-Video in Produktion — jetzt herunterladen und testen",
    stepsTitle: "Drei Schritte und du nutzt es.",
    steps: [
      {
        icon: "hand",
        title: "Mãouse öffnen",
        desc: "Starte das Programm und lass die Webcam deine Hände sehen.",
      },
      {
        icon: "pointer",
        title: "Geste machen",
        desc: "Offene Hand bewegt den Cursor, Pinch klickt und die Faust zieht.",
      },
      {
        icon: "mic",
        title: "Sag, was du willst",
        desc: "Gib Befehle per Stimme: Apps öffnen, Play/Stop, Lautstärke, navigieren.",
      },
    ],
  },
  gallery: {
    tag: "Galerie",
    title: "Das Innere, offen gezeigt.",
    sub: "Aufnahmen von Mãouse im Betrieb — Panel, Gesten, Stimme und der Zwei-Hand-Modus.",
    items: [
      {
        title: "Hauptpanel",
        desc: "Webcam-Status, aktive Gesten und Sprach-Shortcuts.",
        accent: "neon",
      },
      {
        title: "Zwei Hände",
        desc: "Echtes Tracking beider Hände für Teams und Präsentationen.",
        accent: "royal",
      },
      {
        title: "Lokale Stimme",
        desc: "Sprachbefehle offline erkannt, ohne Cloud.",
        accent: "violet",
      },
      {
        title: "Magnetischer Snap",
        desc: "Der Cursor haftet mit chirurgischer Präzision an Zielen.",
        accent: "gold",
      },
      {
        title: "Präsentationsmodus",
        desc: "Riesiger Zeiger und Spotlight für sicheres Projizieren.",
        accent: "pink",
      },
      {
        title: "Handy-Begleiter",
        desc: "Vollständige Fernsteuerung vom Handy aus.",
        accent: "teal",
      },
    ],
  },
  footer: {
    tagline: "Kein Kabel. Keine Maus. Keine Grenzen.",
    columns: [
      {
        title: "Produkt",
        links: [
          { label: "Vorteile", href: "#vorteile" },
          { label: "Preise", href: "#preise" },
          { label: "Kompatibilität", href: "#kompatibilitaet" },
          { label: "FAQ", href: "#faq" },
        ],
      },
      {
        title: "Support",
        links: [{ label: "suporte@maouse.app", href: "mailto:suporte@maouse.app" }],
      },
      {
        title: "Über",
        links: [
          { label: "Luar Studio Angola", href: "#" },
          { label: "Presse", href: "#" },
        ],
      },
    ],
    rights: "© 2026 Luar Studio Angola. Mãouse® ist eine eingetragene Marke.",
    made: "Auf Portugiesisch gemacht, mit der Hand.",
    hashtags: ["#Maouse", "#SemCauda"],
  },
};

const it: Copy = {
  meta: {
    title: "Mãouse — Senza coda. Senza fili. Senza limiti.",
    description:
      "Controlla il computer con la mano e la voce, direttamente dalla webcam. Senza hardware aggiuntivo, senza fili, 100% privato. Windows 10/11.",
  },
  nav: {
    product: "Mãouse",
    links: [
      { label: "Vantaggi", href: "#vantaggi" },
      { label: "Prezzi", href: "#prezzi" },
      { label: "Privacy", href: "#privacy" },
      { label: "Compatibilità", href: "#compatibilita" },
      { label: "FAQ", href: "#faq" },
      { label: "Progresso", href: "#progresso" },
    ],
    cta: "Prova gratis",
    langLabel: "Lingua",
  },
  progress: {
    tag: "Progresso",
    title: "Stiamo costruendo Mãouse a vista di tutti.",
    sub: "Fasi, traguardi e obiettivi seguiti in tempo reale — così sai esattamente dove siamo nel cammino verso la prima vendita e l'espansione in Europa.",
    phases: "Fasi",
    milestones: "Traguardi",
    goals: "Obiettivi",
    updated: "Aggiornato il",
    loading: "Caricamento…",
    error: "Impossibile caricare il progresso.",
    byStatus: {
      pendente: "In attesa",
      em_curso: "In corso",
      concluido: "Completato",
    },
  },
  hero: {
    badge: "Windows 10/11 · beta chiusa #Maouse",
    titleA: "Senza coda. Senza fili.",
    titleB: "Senza limiti.",
    sub: "Mãouse trasforma la tua webcam in un mouse completo: puntatore, clic, scroll, trascinamento e comandi vocali — solo con la mano. Senza hardware aggiuntivo, senza fili, senza mouse. 100% locale e privato.",
    bullets: [
      "Senza hardware — ti serve solo la webcam",
      "Elaborazione 100% locale, l'IA gira sul tuo PC",
      "5 minuti di prova gratis, senza carta",
    ],
    download: "Prova gratis",
    secondary: "Vedi come funziona",
    demoLabel: "DEMO",
    demoNote: "Video demo in produzione — scarica e prova ora",
    stats: [
      { value: "5 min", label: "prova gratis per sessione" },
      { value: "0", label: "hardware aggiuntivo" },
      { value: "100%", label: "privato, senza cloud" },
    ],
  },
  features: {
    tag: "Vantaggi",
    title: "Lascia il mouse nel cassetto. Niente altro cambia.",
    sub: "Mãouse è pensato per professionisti, relatori e persone con mobilità ridotta — precisione da produttività, non da giocattolo.",
    items: [
      {
        icon: "hand",
        title: "Puntatore con le tue mani",
        desc: "Apri il palmo e il cursore ti segue. Pinch per cliccare, pugno per trascinare, due dita per lo scroll. Senza superfici, senza batterie.",
        accent: "neon",
      },
      {
        icon: "mic",
        title: "Voce come scorciatoia",
        desc: "Stop, play, volume, aprire app e navigare a voce — con IA locale che rispetta ciò che dici e non registra mai sul cloud.",
        accent: "violet",
      },
      {
        icon: "zap",
        title: "Snap magnetico",
        desc: "Il cursore si attacca a pulsanti e icone. Colpire il bersaglio giusto non è più un gioco di mira.",
        accent: "success",
      },
      {
        icon: "cpu",
        title: "IA integrata",
        desc: "Tracciamento neurale in tempo reale con filtri di precisione. Gira sul tuo hardware, non in un datacenter lontano.",
        accent: "warn",
      },
      {
        icon: "phone",
        title: "Telefono come compagno",
        desc: "Usa il telefono come telecomando o come camera extra per gesti con due mani. Dal PC al telefono, senza coda.",
        accent: "pink",
      },
      {
        icon: "shield",
        title: "Fatto per la tua salute",
        desc: "Meno movimenti ripetitivi del mouse — un'alternativa reale per prevenire fastidi e disturbi da sforzo ripetitivo.",
        accent: "teal",
      },
    ],
  },
  pricing: {
    tag: "Prezzi",
    title: "Semplice. Giusto. Senza abbonamento.",
    sub: "Compra una volta, è tuo per sempre. Il Pro include tutto ciò che fa il software.",
    comingSoon: "Negozio in apertura",
    freeName: "Gratis",
    freeExtra: "per sempre",
    popular: "Il più scelto",
    guarantee: "Garanzia di 14 giorni e rimborso — senza domande.",
    accessNote:
      "Il piano Accessibilità è al 50% (19,95 € invece di 39,90 €) con prova — parlaci.",
    contact: "suporte@maouse.app",
    plans: [
      {
        id: "free",
        name: "Gratis",
        price: "0 €",
        extra: "prova di 5 min per sessione · filigrana",
        highlight: false,
        features: [
          "Prova di 5 minuti per sessione",
          "Muovere, clic, scroll e trascinare",
          "Voce base e scorciatoie da tastiera",
          "Senza carta, installa e usa",
        ],
        cta: "Scarica gratis",
      },
      {
        id: "lifetime",
        name: "Pro Lifetime",
        price: "39,90 €",
        extra: "una volta · per sempre",
        highlight: true,
        features: [
          "Nessun limite di tempo, nessuna filigrana",
          "Tutti i gesti: 12+ e due mani",
          "Voce completa con comandi e IA",
          "Snap magnetico e multi-monitor",
          "Telefono come compagno",
          "Attivazione con chiave · aggiornamenti inclusi",
        ],
        cta: "Compra Pro",
      },
      {
        id: "family",
        name: "Famiglia",
        price: "59,90 €",
        extra: "3 dispositivi",
        highlight: false,
        features: [
          "Tutto del Pro Lifetime",
          "Fino a 3 dispositivi sulla stessa chiave",
          "Ideale per casa e ufficio",
        ],
        cta: "Compra Famiglia",
      },
    ],
  },
  privacy: {
    tag: "Privacy",
    title: "Il tuo sguardo e la tua voce non lasciano mai il tuo PC.",
    sub: "Mãouse è privacy per architettura: telecamera, voce e gesti sono elaborati sul tuo dispositivo.",
    bullets: [
      {
        icon: "eye",
        title: "Telecamera 100% locale",
        desc: "Il video è elaborato in tempo reale sul tuo PC e non viene mai registrato né inviato.",
      },
      {
        icon: "mic",
        title: "Voce locale (STT on-device)",
        desc: "Il riconoscimento vocale gira localmente. Nessun microfono nel cloud, nessuna registrazione.",
      },
      {
        icon: "file",
        title: "Zero account obbligatorio",
        desc: "Installa, usa e disinstalla. Nessun profilo, nessuna telemetria forzata.",
      },
    ],
    statement:
      "Resta senza Wi-Fi e continua a funzionare. La tua privacy non dipende dalla nostra buona volontà — dipende da dove gira il codice: sul tuo dispositivo.",
  },
  matrix: {
    tag: "Compatibilità",
    title: "Matrice dispositivi in validazione",
    sub: "Testiamo ogni modello prima di promettere. Registrazione in corso — aggiornamento settimanale durante la beta.",
    cols: ["Dispositivo", "Webcam", "FPS", "Latenza", "Clic fantasma", "Verdetto"],
    rows: [
      {
        device: "HP Notebook · Intel i3-5005U · 8GB · Win 10",
        webcam: "640×480 / 30fps",
        fps: "14.6",
        latency: "48 ms",
        ghosts: "0",
        verdict: "warn",
        note: "CPU senza GPU. Funziona, sotto l'obiettivo di 25 fps.",
      },
      {
        device: "HP Notebook · i3-5005U + HD 5500 (notte)",
        webcam: "640×480 / 30fps",
        fps: "11.9",
        latency: "78 ms",
        ghosts: "0",
        verdict: "warn",
        note: "GPU vecchia senza OpenCL. 0 intoppi.",
      },
    ],
    legendOk: "Validato",
    legendWarn: "Accettato",
    legendNo: "Non validato",
    note: "Qualità professionale garantita sopra l'obiettivo (≥25 fps). Per parchi 100% senza GPU consigliamo una prova preliminare — possiamo validare sul tuo parco prima che tu prometta.",
  },
  faq: {
    tag: "FAQ",
    title: "Domande frequenti",
    sub: "Risposte dirette. Se resta qualcosa, scrivi a suporte@maouse.app.",
    items: [
      {
        q: "La prova è davvero gratis?",
        a: "Sì. Installa, prova 5 minuti per sessione liberamente e senza carta. Il video mostra una piccola filigrana finché non attivi il Pro.",
      },
      {
        q: "Devo comprare hardware?",
        a: "No. Mãouse funziona con la webcam che hai già. Consigliamo 720p, ma anche i modelli 480p funzionano (con qualità inferiore).",
      },
      {
        q: "Cosa sblocca il Pro Lifetime?",
        a: "Tutto: nessun limite di tempo, nessuna filigrana, i 12+ gesti, due mani, voce completa, snap magnetico e il telefono come compagno. Compra una volta, è tuo per sempre.",
      },
      {
        q: "I miei dati lasciano il computer?",
        a: "No. Telecamera, voce e tracciamento sono elaborati sul tuo PC. Mãouse funziona offline. La chiave di attivazione valida solo la licenza.",
      },
      {
        q: "Come installo su Windows?",
        a: "Installa il file .exe ed è pronto in 1 clic. Se SmartScreen mostra un avviso durante la beta, clicca «Ulteriori informazioni → Esegui comunque», come con qualsiasi software nuovo.",
      },
      {
        q: "Come funzionano garanzia e rimborso?",
        a: "Hai 14 giorni per chiedere il rimborso, senza domande. Se funziona sul tuo hardware, ottimo; se no, rimborsiamo.",
      },
      {
        q: "Perché il 50% su Accessibilità?",
        a: "Il piano Accessibilità costa 19,95 € (metà del Pro) con prova — paghiamo la differenza. È una decisione di prodotto, non di marketing.",
      },
      {
        q: "In quali lingue è Mãouse?",
        a: "Interfacce e voce in 7 lingue: portoghese (PT-PT e PT-BR), inglese, spagnolo, francese, tedesco e italiano.",
      },
    ],
  },
  media: {
    tag: "Come funziona",
    title: "Guarda Mãouse in azione, senza uscire da qui.",
    sub: "Un breve video di come la tua webcam diventa un mouse completo — mano, voce e clic, tutto in tempo reale e 100% locale.",
    watchLabel: "Guarda il video demo",
    liveLabel: "Demo dal vivo",
    demoNote: "Video demo in produzione — scarica e prova ora",
    stepsTitle: "Tre passi e stai già usando.",
    steps: [
      {
        icon: "hand",
        title: "Apri Mãouse",
        desc: "Avvia il programma e lascia che la webcam veda le tue mani.",
      },
      {
        icon: "pointer",
        title: "Fai un gesto",
        desc: "Mano aperta muove il cursore, pinch clicca e il pugno trascina.",
      },
      {
        icon: "mic",
        title: "Di' cosa vuoi",
        desc: "Dai ordini a voce: aprire app, play/stop, volume, navigare.",
      },
    ],
  },
  gallery: {
    tag: "Galleria",
    title: "L'interno, a vista.",
    sub: "Istantanee di Mãouse in funzione — pannello, gesti, voce e modalità due mani.",
    items: [
      {
        title: "Pannello principale",
        desc: "Stato della webcam, gesti attivi e scorciatoie vocali.",
        accent: "neon",
      },
      {
        title: "Due mani",
        desc: "Tracciamento reale di entrambe le mani per team e presentazioni.",
        accent: "royal",
      },
      {
        title: "Voce locale",
        desc: "Comandi vocali riconosciuti offline, senza cloud.",
        accent: "violet",
      },
      {
        title: "Snap magnetico",
        desc: "Il cursore si attacca ai bersagli con precisione chirurgica.",
        accent: "gold",
      },
      {
        title: "Modalità relatore",
        desc: "Puntatore gigante e spotlight per proiettare con sicurezza.",
        accent: "pink",
      },
      {
        title: "Telefono compagno",
        desc: "Controllo remoto completo dallo smartphone.",
        accent: "teal",
      },
    ],
  },
  footer: {
    tagline: "Senza coda. Senza fili. Senza limiti.",
    columns: [
      {
        title: "Prodotto",
        links: [
          { label: "Vantaggi", href: "#vantaggi" },
          { label: "Prezzi", href: "#prezzi" },
          { label: "Compatibilità", href: "#compatibilita" },
          { label: "FAQ", href: "#faq" },
        ],
      },
      {
        title: "Supporto",
        links: [{ label: "suporte@maouse.app", href: "mailto:suporte@maouse.app" }],
      },
      {
        title: "Informazioni",
        links: [
          { label: "Luar Studio Angola", href: "#" },
          { label: "Stampa", href: "#" },
        ],
      },
    ],
    rights: "© 2026 Luar Studio Angola. Mãouse® è un marchio registrato.",
    made: "Fatto in portoghese, con la mano.",
    hashtags: ["#Maouse", "#SemCauda"],
  },
};

export const copy: Record<Lang, Copy> = { pt, ptbr, en, es, fr, de, it };