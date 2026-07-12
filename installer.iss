; Instalador do ProntoPsi (Inno Setup) — experiência de software de mercado:
; escolha da pasta de instalação, atalho opcional na área de trabalho,
; item no Menu Iniciar e desinstalador.
;
; Pré-requisitos para gerar o instalador:
;   1) Gerar o executável:   .venv\Scripts\pyinstaller anamnese.spec
;   2) Instalar o Inno Setup: https://jrsoftware.org/isdl.php
;   3) Compilar (passe a versão):
;        ISCC /DAppVersion=1.1.4 installer.iss
; Resultado: Output\ProntoPsi-Setup-1.1.4.exe

#define AppName "ProntoPsi"
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppPublisher "ProntoPsi"
#define AppExe "ProntoPsi.exe"

[Setup]
AppId={{7C2B9F4A-4E1D-4F2A-9B3C-A1B2C3D4E5F6}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=no
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename={#AppName}-Setup-{#AppVersion}
SetupIconFile=frontend\assets\prontopsi.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar um atalho na área de trabalho"; GroupDescription: "Atalhos adicionais:"

[Files]
Source: "dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Abrir o {#AppName} agora"; Flags: nowait postinstall skipifsilent
