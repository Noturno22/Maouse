; Inno Setup script for Maouse (Mãouse)
; Build input: dist\Maouse\  (PyInstaller onedir)
; Compile:
;   "C:\Users\Luar Studio Angola\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer.iss
;
; Assinatura digital (opcional): compile com
;   ISCC.exe installer.iss /DPfxPath=C:\path\cert.pfx /DPfxPass=SECRET
; Sem PfxPath o build NÃO assina (seguro para testes).

#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

#define MyAppName "Mãouse"
#define MyAppExeName "Maouse.exe"
#define MyAppPublisher "Luar Studio Angola"
#define MyAppURL "https://example.com"

[Setup]
AppId={{1C7E5048-FF54-4EA9-A454-BF3512E443A7}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=Maouse-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=assets\brand\maouse.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Controla o rato do PC com a mão, via webcam
VersionInfoProductName={#MyAppName}
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; ── Assinatura condicional (só quando /DPfxPath é passado) ──────────────
#ifdef PfxPath
SignTool=signtool="C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x86\signtool.exe" sign /f "{#PfxPath}" /p "{#PfxPass}" /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /d "{#MyAppName}" $f
#endif

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\Maouse\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
{ Regra de firewall para a descoberta automatica (mDNS, UDP 5353).

  Sem isto, o Windows Firewall — que bloqueia entrada por omissao — deixa o
  telefone fazer as consultas mDNS e o PC nunca responder. O sintoma e o pior
  possivel para esta funcionalidade: nao ha erro nenhum, o telefone e que
  "nao encontra o PC", e a unica pista esta no log.

  Vai no bloco [Code] e nao no [Run] porque um `netsh` que falhe (politica de
  empresa, `netsh` ausente) nao pode fazer o instalador falhar. `Exec` ignora
  o codigo de saida, que e o comportamento pretendido aqui. }

procedure MaouseAbrePortaMdns;
var
  Resultado: Integer;
begin
  Exec(
    ExpandConstant('{sys}\netsh.exe'),
    'advfirewall firewall add rule name="Maouse Discovery mDNS" dir=in action=allow protocol=UDP localport=5353 profile=any enable=yes',
    '',
    SW_HIDE,
    ewWaitUntilTerminated,
    Resultado);
  { A porta de resposta sai, a de consulta nao: o `zeroconf` responde do
    5353 e o Windows trata a resposta como entrada. E por isso que a regra
    e `dir=in` para a porta que responde, e nao uma regra de saida. }
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    MaouseAbrePortaMdns;
end;
