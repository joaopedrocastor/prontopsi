; Instalador do ProntoPsi (Inno Setup) — experiência de software de mercado:
; escolha da pasta de instalação, atalho opcional na área de trabalho,
; item no Menu Iniciar e desinstalador.
;
; Pré-requisitos para gerar o instalador:
;   1) Gerar o executável:   .venv\Scripts\pyinstaller anamnese.spec
;   2) Instalar o Inno Setup: https://jrsoftware.org/isdl.php
;   3) Compilar (passe a versão):
;        ISCC /DAppVersion=1.4.4 installer.iss
; Resultado: Output\ProntoPsi-Setup-1.4.4.exe

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
; Instalacao por usuario: nao pede permissao de admin (UAC) -> permite o
; auto-update silencioso do app sem nenhum popup.
PrivilegesRequired=lowest
; Mutex do app em execucao: no update silencioso o instalador aguarda/fecha
; o ProntoPsi antes de substituir o .exe (ver APP_MUTEX em run.py).
AppMutex=ProntoPsi_SingleInstance_Mutex
CloseApplications=yes
RestartApplications=no

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

[Code]
// Versões até a 1.3.x permitiam instalar "para todos os usuários" (modo admin,
// em Program Files, registrada em HKLM). Como este instalador é por usuário
// (HKCU), o Windows passava a listar DUAS instalações do ProntoPsi. Aqui
// procuramos essa instalação antiga e a desinstalamos antes de instalar a nova.
// Os dados (%LOCALAPPDATA%\AnamneseInfantil) não são tocados pelo desinstalador.

const
  UninstKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{7C2B9F4A-4E1D-4F2A-9B3C-A1B2C3D4E5F6}_is1';

// Procura a instalação "para todos os usuários" nas duas visões do registro.
function AcharInstalacaoAntiga(var Uninst: String): Boolean;
begin
  Result := RegQueryStringValue(HKLM32, UninstKey, 'UninstallString', Uninst);
  if not Result and IsWin64 then
    Result := RegQueryStringValue(HKLM64, UninstKey, 'UninstallString', Uninst);
  if Result then
    Uninst := RemoveQuotes(Uninst);
  Result := Result and (Uninst <> '') and FileExists(Uninst);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Uninst: String;
  Code: Integer;
begin
  Result := '';
  if not AcharInstalacaoAntiga(Uninst) then
    exit;
  Log('Instalacao antiga (todos os usuarios) encontrada: ' + Uninst);
  if not WizardSilent then
    MsgBox('Foi encontrada uma versão antiga do ProntoPsi instalada para todos os usuários.' + #13#10#13#10 +
           'Ela será removida para que fique apenas um ProntoPsi no computador. ' +
           'O Windows vai pedir permissão uma única vez. Seus dados NÃO são apagados.',
           mbInformation, MB_OK);
  // Precisa de administrador para remover a instalação em Program Files: pede
  // elevação (UAC) só para o desinstalador antigo.
  if ShellExec('runas', Uninst, '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART', '',
               SW_HIDE, ewWaitUntilTerminated, Code) then
    Log('Desinstalador antigo terminou com codigo ' + IntToStr(Code))
  else
    Log('Nao foi possivel remover a versao antiga (codigo ' + IntToStr(Code) + '). Seguindo com a instalacao.');
end;
