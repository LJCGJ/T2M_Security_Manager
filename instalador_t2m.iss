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
#define VersaoApp      "5.0"
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
; Servidor MCP que expoe o T2M ao Claude Desktop. Nao e usado pelo aplicativo:
; quem o inicia e o host, pela configuracao de servidores MCP. Precisa ser
; instalado mesmo assim - sem ele, o plugin nao tem o que apontar, e o usuario
; teria de clonar o repositorio para usar uma funcionalidade que o instalador
; diz entregar.
Source: "{#PastaRelease}\servidor_mcp_t2m.py"; DestDir: "{app}"; Flags: ignoreversion
; Imagens e icones usados pelo app. Nomeados um a um pelo mesmo motivo dos .py:
; a pasta Release acumula sobras de teste, e um curinga as levaria embutidas no
; instalador (icon2_antigo.ico, prints de execucoes antigas).
Source: "{#PastaRelease}\T2M_logo-03.png"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#PastaRelease}\icon2.ico"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
; O icone fica na pasta do codigo-fonte (nao e copiado para a Release pelo build)
Source: "{#PastaApoio}\T2M_Security_Manager\icon2.ico"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
; Ligacao com o Claude Desktop. Vao juntos de proposito: o .mcpb instala com
; dois cliques QUANDO o Claude Desktop existe, e o script diz o que fazer
; quando ele nao existe - inclusive meses depois, pelo atalho do menu Iniciar.
; Instalar os dois mesmo sem o Claude na maquina e barato (88 KB) e evita que a
; funcionalidade dependa de o usuario voltar ao site do projeto para baixar.
Source: "{#PastaApoio}\plugin_claude\t2m-security-manager-5.0.0.mcpb"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#PastaApoio}\conectar_claude.py"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#PastaApoio}\conectar_claude.bat"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
; Apoio: dependencias e documentacao
Source: "{#PastaApoio}\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PastaApoio}\instalar_dependencias.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PastaApoio}\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PastaApoio}\README.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#PastaApoio}\README.pt.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#NomeApp}"; Filename: "{app}\{#ExeApp}"; IconFilename: "{app}\icon2.ico"
Name: "{group}\Preparar ambiente (dependencias)"; Filename: "{app}\instalar_dependencias.bat"
Name: "{group}\Conectar ao Claude Desktop"; Filename: "{app}\conectar_claude.bat"; \
  Comment: "Liga o T2M ao Claude Desktop - ou diz o que falta, se ele ainda nao estiver instalado"
; Atalho na area de trabalho SOMENTE quando o Claude Desktop nao esta instalado.
; Quem ja tem o Claude nao precisa dele na area de trabalho - o do menu Iniciar
; basta. Quem NAO tem e justamente quem vai esquecer que esta parte existe, e
; para essa pessoa o atalho e o lembrete de que falta um passo.
Name: "{autodesktop}\Conectar T2M ao Claude Desktop"; Filename: "{app}\conectar_claude.bat"; \
  Comment: "Rode isto depois de instalar o Claude Desktop, para ligar o T2M a ele"; \
  Check: not TemClaudeDesktop
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

// ------------------------------------------------------------------
//  O CLAUDE DESKTOP ESTA NESTA MAQUINA?
//
//  Varias pastas, porque uma so nao responde - e isso foi MEDIDO, nao
//  suposto. A primeira versao olhava so %APPDATA%\Claude, que e o caminho
//  documentado, e respondeu "nao instalado" numa maquina com o Claude
//  Desktop ABERTO na hora: ali a pasta real era %LOCALAPPDATA%\Claude.
//
//  Some-se a isso que a pasta de configuracao so nasce quando o programa e
//  aberto pela primeira vez - quem instalou e ainda nao abriu apareceria
//  como "nao tem". Por isso a lista cobre dados E instalacao.
//
//  Errar aqui e barato nos dois sentidos: um falso negativo mostra um
//  aviso a mais e deixa um atalho a mais na area de trabalho; um falso
//  positivo apenas deixa de avisar quem ja sabia. Nenhum dos dois
//  impede nada.
// ------------------------------------------------------------------
// A versao da Microsoft Store (MSIX) roda em conteiner: o %APPDATA% dela
// e virtualizado para dentro de Packages, e a configuracao real fica em
//   %LOCALAPPDATA%\Packages\Claude_<sufixo>\LocalCache\Roaming\Claude
// O sufixo muda por instalacao, entao a busca e por padrao. Descoberto
// medindo a maquina de um usuario: as pastas "obvias" existiam e nenhuma
// delas era a certa.
function TemClaudeNaStore(): Boolean;
var
  FR: TFindRec;
  Base: String;
begin
  Result := False;
  Base := ExpandConstant('{localappdata}\Packages\');
  if FindFirst(Base + 'Claude*', FR) then
  begin
    try
      repeat
        if (FR.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
        begin
          if DirExists(Base + FR.Name + '\LocalCache\Roaming\Claude') then
            Result := True;
        end;
      until Result or (not FindNext(FR));
    finally
      FindClose(FR);
    end;
  end;
end;

function TemClaudeDesktop(): Boolean;
begin
  Result := TemClaudeNaStore
         or DirExists(ExpandConstant('{localappdata}\Claude'))
         or DirExists(ExpandConstant('{userappdata}\Claude'))
         or DirExists(ExpandConstant('{localappdata}\AnthropicClaude'))
         or DirExists(ExpandConstant('{localappdata}\Programs\Claude'));
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
//  AVISO DE FIM DE INSTALACAO SOBRE O CLAUDE DESKTOP
//
//  A extensao do Claude Desktop e instalada PELO Claude Desktop. Sem ele
//  na maquina nao existe quem a instale, e escrever nas pastas internas
//  dele seria adivinhar formato nao documentado.
//
//  Entao o instalador faz a unica coisa honesta: conta o que deixou
//  pronto, diz onde esta, e explica o que fazer depois. Sem isso, a
//  funcionalidade existiria no disco e nao na cabeca de ninguem.
// ------------------------------------------------------------------
procedure CurStepChanged(CurStep: TSetupStep);
begin
  // Quem JA TEM o Claude Desktop tambem precisa saber que a opcao existe -
  // antes so quem NAO tinha recebia aviso, e o resultado era o pior dos dois
  // mundos: a funcionalidade pronta no disco e invisivel para quem podia usar
  // no mesmo minuto.
  if (CurStep = ssPostInstall) and TemClaudeDesktop then
  begin
    MsgBox('O Claude Desktop foi encontrado nesta maquina.' + #13#10#13#10
           + 'O T2M pode ser operado por ele: a automacao passa a rodar pela '
           + 'assinatura que voce ja tem, em vez de consumir creditos de API. '
           + 'As travas continuam sendo do T2M - pasta unica, banco somente '
           + 'leitura, sem escrita em disco.' + #13#10#13#10
           + 'Para ligar os dois, use qualquer um destes caminhos:' + #13#10#13#10
           + '  - menu Iniciar > T2M Security Manager > "Conectar ao Claude Desktop";'
           + #13#10
           + '  - ou, dentro do aplicativo, Configuracoes > "Conectar ao Claude Desktop".'
           + #13#10#13#10
           + 'E opcional: com chave de API o T2M funciona como sempre.',
           mbInformation, MB_OK);
  end;

  if (CurStep = ssPostInstall) and (not TemClaudeDesktop) then
  begin
    MsgBox('O Claude Desktop nao foi encontrado nesta maquina.' + #13#10#13#10
           + 'O T2M pode ser usado por ele: em vez de gastar creditos de API, '
           + 'a automacao passa a rodar pela assinatura do Claude que voce ja '
           + 'tiver. Isso e opcional - o T2M funciona normalmente sem ele, com '
           + 'chave de API.' + #13#10#13#10
           + 'Deixamos tudo pronto para quando voce quiser:' + #13#10#13#10
           + '  - a extensao do T2M foi instalada em:' + #13#10
           + '    ' + ExpandConstant('{app}') + #13#10#13#10
           + '  - um atalho "Conectar T2M ao Claude Desktop" foi criado na sua '
           + 'AREA DE TRABALHO.' + #13#10#13#10
           + 'Depois de instalar o Claude Desktop, use esse atalho: ele liga os '
           + 'dois e diz se deu certo. O mesmo atalho fica no menu Iniciar.',
           mbInformation, MB_OK);
  end;
end;

// ------------------------------------------------------------------
//  TAMANHO DE UMA PASTA, EM BYTES
//
//  Serve so para escrever um numero honesto no dialogo. "Remover
//  arquivos temporarios?" nao ajuda ninguem a decidir; "remover 412 MB"
//  ajuda. Pasta inexistente devolve zero, e ai a pergunta nem aparece.
// ------------------------------------------------------------------
function TamanhoEmBytes(Pasta: String): Int64;
var
  FR: TFindRec;
  Total: Int64;
begin
  Total := 0;
  if FindFirst(AddBackslash(Pasta) + '*', FR) then
  begin
    try
      repeat
        if (FR.Name <> '.') and (FR.Name <> '..') then
        begin
          if (FR.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
            Total := Total + TamanhoEmBytes(AddBackslash(Pasta) + FR.Name)
          else
            // Só a parte baixa do tamanho. O numero serve para o usuario
            // decidir, nao para auditoria, e aqui nao existe arquivo de
            // mais de 4 GB: sao binarios de navegador e cache de pacote.
            Total := Total + FR.SizeLow;
        end;
      until not FindNext(FR);
    finally
      FindClose(FR);
    end;
  end;
  Result := Total;
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
  Navegadores: String;
  CacheNpx: String;
  Megas: Int64;
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

    // --------------------------------------------------------------
    //  DOWNLOADS FEITOS POR CAUSA DO T2M
    //
    //  O preparador de ambiente baixa o Chromium de testes e o cache dos
    //  servidores MCP. Sao centenas de megabytes que existem por causa
    //  deste programa e que, ate a versao 4.2, ficavam para tras em
    //  silencio depois da desinstalacao.
    //
    //  Python, Node.js e as bibliotecas do pip NAO entram aqui, de
    //  proposito: outros projetos da maquina dependem deles, e um
    //  desinstalador que arranca o Python causa um estrago muito maior
    //  do que o espaco que devolve.
    // --------------------------------------------------------------
    Navegadores := ExpandConstant('{localappdata}\ms-playwright');
    CacheNpx    := ExpandConstant('{localappdata}\npm-cache\_npx');
    Megas := (TamanhoEmBytes(Navegadores) + TamanhoEmBytes(CacheNpx)) div 1048576;

    if Megas > 0 then
    begin
      if MsgBox('Remover tambem o navegador de testes e os servidores MCP que o T2M baixou?'
                + #13#10#13#10
                + 'Ocupam cerca de ' + IntToStr(Megas) + ' MB:' + #13#10
                + '  - Chromium de testes (' + Navegadores + ')' + #13#10
                + '  - cache dos servidores MCP (' + CacheNpx + ')' + #13#10#13#10
                + 'O Python, o Node.js e as bibliotecas instaladas NAO serao removidos: '
                + 'outros programas seus podem depender deles.' + #13#10#13#10
                + 'Obs.: o cache do npx e compartilhado com outros projetos que usam npx. '
                + 'Apagar nao quebra nada — ele se refaz sozinho no proximo uso —, '
                + 'mas esses projetos vao baixar de novo na primeira vez.',
                mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      begin
        DelTree(Navegadores, True, True, True);
        DelTree(CacheNpx, True, True, True);
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
