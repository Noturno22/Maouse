export type Lang = "pt" | "en";

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
    ],
    cta: "Testar grátis",
    langLabel: "Idioma",
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
        a: "Interfaces e voz em português (PT-PT e PT-BR) e inglês. Mais línguas em agenda.",
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
    ],
    cta: "Try for free",
    langLabel: "Language",
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
        a: "Interfaces and voice in Portuguese (PT-PT and PT-BR) and English. More languages on the roadmap.",
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

export const copy: Record<Lang, Copy> = { pt, en };