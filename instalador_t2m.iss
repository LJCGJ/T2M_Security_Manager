; ============================================================
;  T2M Security Manager - script do instalador (Inno Setup)
;
;  COMO USAR:
;   1. Instale o Inno Setup: https://jrsoftware.org/isdl.php
;   2. Ajuste PastaRelease abaixo se o caminho for diferente
;   3. Abra este arquivo no Inno Setup e clique em Compile (F9)
;   4. O instalador sai em: <pasta deste script>\Saida\
; ============================================================

#define NomeApp        "T2M Security Manager"
#define VersaoApp      "4.3"
#define AutorApp       "Leonardo Gonzaga"
#define UrlApp         "https://github.com/LJCGJ/T2M_Security_Manager"
#define ExeApp         "T2M_Security_Manager.exe"

; Pasta onde estao os arquivos compilados (Release x64)
#define PastaRelease   "C:\Users\LeonardoJoseCordeiro\source\repos\T2M_Security_Manager\x64\Release"
; Pasta onde estao os arquivos de apoio (requirements.txt, .bat)
#define PastaApoio     "C:\Users\LeonardoJoseCordeiro\source\repos\T2M_Security_Manager"

[Setup]
AppId={{8F3A2C41-7B95-4E62-A1D8-T2MSECMGR2026}
AppName={#NomeApp}
AppVersion={#VersaoApp}
AppPublisher={#AutorApp}
AppPublisherURL={#UrlApp}
AppSupportURL={#UrlApp}/issues
DefaultDirName={autopf}\T2M Security Manager
DefaultGroupName=T2M Security Manager
DisableProgramGroupPage=yes
OutputDir=Saida
OutputBaseFilename=T2M_Security_Manager_Setup_{#VersaoApp}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Licenca GPL-3.0 exibida durante a instalacao
LicenseFile={#PastaApoio}\LICENSE
; Nao exige admin se o usuario escolher instalar na pasta pessoal
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Area de Trabalho"; GroupDescription: "Atalhos:"
Name: "instalardeps"; Description: "Preparar o ambiente agora (instala Python, Node.js e as bibliotecas necessarias)"; GroupDescription: "Dependencias:"

[Files]
; Executavel principal
Source: "{#PastaRelease}\{#ExeApp}"; DestDir: "{app}"; Flags: ignoreversion
; Scripts Python do agente - listados UM A UM de proposito.
; Um curinga (*.py) levaria junto utilitarios de teste e diagnostico que
; ficam na pasta de trabalho e nao fazem parte do produto.
Source: "{#PastaRelease}\agente_mcp.py";     DestDir: "{app}"; Flags: ignoreversion
Source: "{#PastaRelease}\gerador_ia.py";     DestDir: "{app}"; Flags: ignoreversion
Source: "{#PastaRelease}\get_token.py";      DestDir: "{app}"; Flags: ignoreversion
Source: "{#PastaRelease}\listar_modelos.py"; DestDir: "{app}"; Flags: ignoreversion
; Servidor MCP proprio do T2M para o modo "Teste de API HTTP".
; Ficou de fora ate a versao 4.2: o agente_mcp.py procura este arquivo ao lado
; dele (SCRIPT_DIR) e, sem ele, o modo de API respondia "Arquivo ausente:
; servidor_http_mcp.py". Na pasta Release o arquivo sempre esteve la - o build
; copia *.py -, entao a falha NUNCA aparecia em desenvolvimento: so na maquina
; de quem instalou. E o motivo de testar o instalador, e nao so o programa.
Source: "{#PastaRelease}\servidor_http_mcp.py"; DestDir: "{app}"; Flags: ignoreversion
; Imagens e icones usados pelo app. Nomeados um a um pelo mesmo motivo dos .py:
; a pasta Release acumula sobras de teste, e um curinga as levaria embutidas no
; instalador (icon2_antigo.ico, prints de execucoes antigas).
Source: "{#PastaRelease}\T2M_logo-03.png"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#PastaRelease}\icon2.ico"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
; O icone fica na pasta do codigo-fonte (nao e copiado para a Release pelo build)
Source: "{#PastaApoio}\T2M_Security_Manager\icon2.ico"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
; Apoio: dependencias e documentacao
Source: "{#PastaApoio}\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PastaApoio}\instalar_dependencias.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PastaApoio}\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PastaApoio}\README.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#PastaApoio}\README.pt.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#NomeApp}"; Filename: "{app}\{#ExeApp}"; IconFilename: "{app}\icon2.ico"
Name: "{group}\Preparar ambiente (dependencias)"; Filename: "{app}\instalar_dependencias.bat"
Name: "{group}\Desinstalar {#NomeApp}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#NomeApp}"; Filename: "{app}\{#ExeApp}"; IconFilename: "{app}\icon2.ico"; Tasks: desktopicon

[Run]
; Prepara o ambiente (se o usuario marcou a tarefa).
;
; runasoriginaluser: quando o Setup roda elevado (instalacao em Program Files),
;   tudo que ele dispara herda a conta do ADMINISTRADOR. Sem esta flag, o winget
;   instalava o Python em C:\Users\<admin>\AppData, o pip gravava no site-packages
;   do admin e o "npx playwright install" baixava o Chromium no perfil do admin.
;   O usuario real fazia login depois, abria o app, e NADA estava instalado.
;
; postinstall: sem ela o Description era ignorado e o .bat rodava DURANTE a
;   instalacao. Como ele termina em "pause" e faz perguntas com "set /p", o
;   instalador parecia travado, com o console escondido atras da janela.
;
; nowait: nao prender o instalador esperando o .bat terminar (ele e interativo).
Filename: "{app}\instalar_dependencias.bat"; \
  Description: "Preparar ambiente agora (Python, Node.js e bibliotecas)"; \
  Flags: shellexec postinstall skipifsilent nowait runasoriginaluser; \
  Tasks: instalardeps
; Abre o app ao final
Filename: "{app}\{#ExeApp}"; \
  Description: "Abrir o {#NomeApp}"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Arquivos tecnicos gerados ao lado do programa (seguro apagar sempre).
; A memoria do chat NAO fica mais aqui: passou para %APPDATA%\T2M Security
; Manager, junto das configuracoes, porque a pasta do programa e somente
; leitura para o usuario comum. A remocao dela e oferecida no desinstalador.
; A linha antiga fica so para limpar instalacoes anteriores.
Type: files; Name: "{app}\memoria_chat.json"
Type: files; Name: "{app}\__pycache__\*"
Type: dirifempty; Name: "{app}\__pycache__"

[Code]
// Avisa antes de instalar se faltar Python ou Node, mas nao bloqueia.
function TemNoPath(Exe: String): Boolean;
var
  Codigo: Integer;
begin
  Result := Exec('cmd.exe', '/C where ' + Exe, '', SW_HIDE, ewWaitUntilTerminated, Codigo)
            and (Codigo = 0);
end;

function InitializeSetup(): Boolean;
var
  Faltando: String;
begin
  Faltando := '';
  if not TemNoPath('python') then
    Faltando := Faltando + '  - Python 3.10 ou superior (https://www.python.org/downloads/)' + #13#10;
  if not TemNoPath('npx') then
    Faltando := Faltando + '  - Node.js 18 ou superior (https://nodejs.org/)' + #13#10;

  if Faltando <> '' then
    MsgBox('O T2M precisa destes programas para a automacao funcionar:' + #13#10#13#10
           + Faltando + #13#10
           + 'Nao se preocupe: ao final da instalacao, o preparador de ambiente '
           + 'pode instala-los automaticamente para voce (basta aceitar quando '
           + 'ele perguntar).' + #13#10#13#10
           + 'Se preferir, instale por conta propria e depois use o atalho '
           + '"Preparar ambiente" no menu Iniciar.',
           mbInformation, MB_OK);

  Result := True;  // segue com a instalacao de qualquer forma
end;

// ------------------------------------------------------------------
//  DESINSTALACAO
//  Pergunta se o usuario quer remover os dados pessoais do aplicativo.
//  IMPORTANTE: relatorios, scripts e sessoes NAO sao apagados, porque
//  ficam em pastas escolhidas pelo usuario (que podem conter outros
//  arquivos dele). Apenas informamos onde estao.
// ------------------------------------------------------------------
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  PastaDados: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    PastaDados := ExpandConstant('{userappdata}\T2M Security Manager');

    if DirExists(PastaDados) then
    begin
      if MsgBox('Deseja remover tambem suas configuracoes e chaves de API?' + #13#10#13#10
                + 'Pasta: ' + PastaDados + #13#10#13#10
                + 'Escolha NAO se pretende reinstalar o T2M depois — '
                + 'assim suas chaves continuam salvas.',
                mbConfirmation, MB_YESNO) = IDYES then
      begin
        DelTree(PastaDados, True, True, True);
      end;
    end;

    MsgBox('Seus relatorios, scripts e sessoes NAO foram apagados.' + #13#10#13#10
           + 'Eles estao nas pastas que voce escolheu em Configuracoes '
           + '(por padrao, dentro de Documentos):' + #13#10
           + '  - relatorios T2M' + #13#10
           + '  - sessoes T2M' + #13#10
           + '  - modelos de teste em IA' + #13#10#13#10
           + 'Apague manualmente se nao precisar mais deles.',
           mbInformation, MB_OK);
  end;
end;
