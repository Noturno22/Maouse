/**
 * Expo Config Plugin — Maouse Native Modules
 *
 * Injeta durante `expo prebuild` (Android e iOS):
 * 1. MaouseAccessibilityService (injeção de gestos/teclado sem root)
 * 2. TouchControllerModule / KeyboardControllerModule / SystemControllerModule
 * 3. MaousePackage + registo no MainApplication.kt
 * 4. Serviço de acessibilidade no AndroidManifest.xml + strings
 * 5. KeyboardController.swift (iOS, paridade com os módulos Android)
 *
 * Registo em app.json:
 *   ["../../plugins/with-maouse-native", {}]
 *
 * @platform Android, iOS
 */

const {
  withMainApplication,
  withAndroidManifest,
  withStringsXml,
  withDangerousMod,
} = require("expo/config-plugins");
const fs = require("fs");
const path = require("path");

const TEMPLATES_DIR = path.join(__dirname, "templates");
const PACKAGE_NAME = "com.maouse.mobile";
const PACKAGE_DIR = PACKAGE_NAME.replace(/\./g, "/");

const SERVICE_NAME = "MaouseAccessibilityService";

// -------------------------------
// Ficheiros Kotlin a copiar (Android)
// -------------------------------
const ANDROID_KOTLIN_FILES = [
  "MaouseAccessibilityService.kt",
  "TouchControllerModule.kt",
  "KeyboardControllerModule.kt",
  "SystemControllerModule.kt",
  "BleRemoteModule.kt",
  "MdnsDiscoveryModule.kt",
  "MaousePackage.kt",
];

// Permissões que o Bluetooth e o mDNS precisam no AndroidManifest.
//
// As três `BLUETOOTH_*` (SCAN, CONNECT, ADVERTISE) chegaram no Android 12
// (API 31) e não são um pedido de "localização": `neverForLocation` diz ao
// Android que o Bluetooth não é usado para geolocalizar, e sem isso ele exige
// a permissão de localização para *qualquer* scan BLE. É a primeira coisa que
// falha num telefone novo, e a mensagem do sistema fala de localização numa
// app que não pede localização nenhuma — o que não ajuda ninguém.
//
// `neverForLocation` e a opcao correcta aqui: o scanner filtra pelo UUID do
// servico, e isso e filtragem por servico e nao por localizacao. Quem depois
// quiser varrer BLE sem filtrar por servico tem de tirar este uso e pedir a
// permissao de localizacao, o que muda o que a app pode fazer com os
// resultados.
const BLUETOOTH_PERMISSIONS = [
  { name: "android.permission.BLUETOOTH_SCAN", flags: ["neverForLocation"] },
  { name: "android.permission.BLUETOOTH_CONNECT" },
  { name: "android.permission.BLUETOOTH_ADVERTISE" },
];

// -------------------------------
// Helpers
// -------------------------------
function readTemplate(name) {
  return fs.readFileSync(path.join(TEMPLATES_DIR, name), "utf-8");
}

function writeFileIfChanged(filePath, content) {
  if (fs.existsSync(filePath) && fs.readFileSync(filePath, "utf-8") === content) {
    return false;
  }
  fs.writeFileSync(filePath, content);
  return true;
}

function ensureClassDecl(contents, marker, replacement) {
  if (contents.includes(marker)) {
    return contents;
  }
  return contents.replace(/(package .+\n)/m, `$1${replacement}\n`);
}

// -------------------------------
// 1. MainApplication.kt — registar MaousePackage
// -------------------------------
function withMaouseMainApplication(config) {
  return withMainApplication(config, (mod) => {
    let contents = mod.modResults.contents;

    if (!contents.includes("MaousePackage")) {
      // Injeta add(MaousePackage()) dentro do PackageList(...).packages.apply { ... }
      if (contents.includes("PackageList(this).packages.apply {")) {
        contents = contents.replace(
          /PackageList\(this\)\.packages\.apply\s*\{/,
          `PackageList(this).packages.apply {
          add(MaousePackage())`
        );
        console.log("[MaouseNative] ✅ Registered MaousePackage in MainApplication.kt");
      } else {
        console.log("[MaouseNative] ⚠️  Não encontrei PackageList(...).packages — salta registo");
      }
    } else {
      console.log("[MaouseNative] ⏭️  MaousePackage já registado");
    }

    mod.modResults.contents = contents;
    return mod;
  });
}

// -------------------------------
// 2. AndroidManifest.xml — serviço de acessibilidade
// -------------------------------
function withMaouseManifest(config) {
  return withAndroidManifest(config, (mod) => {
    const manifest = mod.modResults.manifest;
    const app = manifest["application"] && manifest["application"][0];
    if (!app) {
      console.log("[MaouseNative] ⚠️  Sem <application> no manifest — salta serviço");
      return mod;
    }

    // Permissões de Bluetooth e mDNS.
    //
    // `CHANGE_WIFI_MULTICAST_STATE` não é óbvia: sem ela, o `NsdManager`
    // funciona no emulador e falha num telefone, porque o Android não entra
    // em multicast com a app ligada, e o mDNS é todo multicast. É a diferença
    // entre "descobri o PC no meu teste" e "não encontro o PC em lado
    // nenhum", e a permissão não aparece em nenhum tutorial de BLE.
    const REQUIRED = [
      ...BLUETOOTH_PERMISSIONS,
      { name: "android.permission.INTERNET" },
      { name: "android.permission.ACCESS_WIFI_STATE" },
      { name: "android.permission.CHANGE_WIFI_MULTICAST_STATE" },
    ];
    let perms = manifest["uses-permission"];
    if (!perms) perms = [];
    for (const req of REQUIRED) {
      const existing = perms.find((p) => p["$"] && p["$"]["android:name"] === req.name);
      if (existing) {
        // A permissão já vem de outro plugin ou do `app.json`. Não se duplica.
        // Se o `neverForLocation` é pedido por este módulo e a linha de
        // origem não o tem, acrescenta-se: é esta flag que separa "pede
        // localização" de "não pede", e o Android não dá para inferir uma do
        // outro — a diferença está no atributo e não no conteúdo.
        if (req.flags && !existing.$["android:usesPermissionFlags"]) {
          existing.$["android:usesPermissionFlags"] = req.flags.join("|");
        }
        continue;
      }
      const node = { $: { "android:name": req.name } };
      if (req.flags) node.$["android:usesPermissionFlags"] = req.flags.join("|");
      perms.push(node);
    }
    manifest["uses-permission"] = perms;
    let services = app["service"];
    if (services && services.length) {
      const already = services.some(
        (s) => s["$"] && s["$"]["android:name"] === ".MaouseAccessibilityService"
      );
      if (already) {
        console.log("[MaouseNative] ⏭️  MaouseAccessibilityService já existe");
        return mod;
      }
    }
    if (!services) services = [];
    services.push({
      $: {
        "android:name": ".MaouseAccessibilityService",
        "android:exported": "false",
        "android:permission": "android.permission.BIND_ACCESSIBILITY_SERVICE",
        "android:label": "@string/accessibility_service_label",
      },
      "intent-filter": [
        {
          action: [{ $: { "android:name": "android.accessibilityservice.AccessibilityService" } }],
        },
      ],
      "meta-data": [
        {
          $: {
            "android:name": "android.accessibilityservice",
            "android:resource": "@xml/accessibility_service_config",
          },
        },
      ],
    });
    app["service"] = services;
    console.log("[MaouseNative] ✅ Added MaouseAccessibilityService to AndroidManifest.xml");
    return mod;
  });
}

// -------------------------------
// 3. strings.xml — descrição do serviço de acessibilidade
// -------------------------------
function withMaouseStrings(config) {
  return withStringsXml(config, (mod) => {
    const strings = mod.modResults.resources.string;
    const add = (name, value) => {
      if (strings.some((s) => s["$"] && s["$"].name === name)) return;
      strings.push({ $: { name }, _: value });
    };
    add("accessibility_service_label", "Mãouse");
    add(
      "accessibility_service_description",
      "Usa gestos de mão detetados pela câmara para controlar o telemóvel: toques, arrastar, voltar, início e notificações. Ativa para que o Mãouse consiga interagir com outras apps."
    );
    mod.modResults.resources.string = strings;
    return mod;
  });
}

// -------------------------------
// 4. Copiar ficheiros Kotlin + xml do serviço (Android)
// -------------------------------
function withMaouseAndroidFiles(config) {
  return withDangerousMod(config, [
    "android",
    async (mod) => {
      const projectRoot = mod.modRequest.projectRoot;
      const javaDir = path.join(projectRoot, "android", "app", "src", "main", "java", PACKAGE_DIR);
      const xmlDir = path.join(projectRoot, "android", "app", "src", "main", "res", "xml");

      fs.mkdirSync(javaDir, { recursive: true });
      fs.mkdirSync(xmlDir, { recursive: true });

      for (const file of ANDROID_KOTLIN_FILES) {
        const content = readTemplate(path.join("android", file));
        const dest = path.join(javaDir, file);
        if (writeFileIfChanged(dest, content)) {
          console.log(`[MaouseNative] ✅ ${file}`);
        } else {
          console.log(`[MaouseNative] ⏭️  ${file} inalterado`);
        }
      }

      const xmlContent = readTemplate(path.join("android", "accessibility_service_config.xml"));
      const xmlDest = path.join(xmlDir, "accessibility_service_config.xml");
      if (writeFileIfChanged(xmlDest, xmlContent)) {
        console.log("[MaouseNative] ✅ accessibility_service_config.xml");
      } else {
        console.log("[MaouseNative] ⏭️  accessibility_service_config.xml inalterado");
      }

      return mod;
    },
  ]);
}

// -------------------------------
// 5. KeyboardController.swift (iOS)
// -------------------------------
function withMaouseIosFiles(config) {
  return withDangerousMod(config, [
    "ios",
    async (mod) => {
      const projectRoot = mod.modRequest.projectRoot;
      const iosDir = path.join(projectRoot, "ios");
      if (!fs.existsSync(iosDir)) {
        console.log("[MaouseNative] ⏭️  Sem pasta ios/ (só Android?)");
        return mod;
      }
      const content = readTemplate(path.join("ios", "KeyboardController.swift"));
      const dest = path.join(iosDir, "KeyboardController.swift");
      if (writeFileIfChanged(dest, content)) {
        console.log("[MaouseNative] ✅ KeyboardController.swift");
      } else {
        console.log("[MaouseNative] ⏭️  KeyboardController.swift inalterado");
      }
      return mod;
    },
  ]);
}

// -------------------------------
// Plugin principal
// -------------------------------
function withMaouseNative(config) {
  config = withMaouseMainApplication(config);
  config = withMaouseManifest(config);
  config = withMaouseStrings(config);
  config = withMaouseAndroidFiles(config);
  config = withMaouseIosFiles(config);
  return config;
}

module.exports = withMaouseNative;