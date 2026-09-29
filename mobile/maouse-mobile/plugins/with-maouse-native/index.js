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
  "MaousePackage.kt",
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