# T2M Security Manager 4.3

Automação de testes de QA e segurança para Windows, com agente de IA que executa
de verdade — tela (Playwright), banco de dados e APIs HTTP — via MCP.

---

## Antes de instalar, três coisas que você precisa saber

**O instalador não é assinado digitalmente.** O Windows vai exibir a tela azul
"O Windows protegeu o seu computador" (SmartScreen). Para continuar, clique em
*Mais informações* e depois em *Executar assim mesmo*.

Em máquina corporativa isso pode ir além do aviso: durante os testes desta
versão, um antivírus gerenciado **impediu a execução** do instalador, com erro
de acesso negado. Se acontecer com você, fale com o TI da sua empresa e peça a
liberação — não desative a proteção por conta própria. Um certificado de
assinatura de código está no planejamento e deve resolver o caso do SmartScreen;
políticas corporativas que bloqueiam qualquer programa não aprovado continuarão
exigindo liberação pelo TI.

**Pré-requisitos: Python 3.10+ e Node.js 18+.** Você não precisa instalá-los por
conta própria: marque a opção *Preparar o ambiente agora* durante a instalação e
o próprio T2M cuida disso, sempre pedindo sua permissão antes de cada passo. Ele
também baixa o navegador de testes (Chromium) e os servidores MCP que a automação
usa.

**Suas chaves de API ficam só na sua máquina**, em
`%APPDATA%\T2M Security Manager`, e nunca são enviadas para lugar nenhum além do
provedor de IA que você mesmo escolher. Ao desinstalar, o T2M pergunta se você
quer removê-las — responda *Não* se pretende reinstalar depois.

---

## O que mudou nesta versão

### Correções que só apareciam em quem instalava

O modo **Teste de API HTTP** não funcionava em máquinas com o T2M instalado: o
`servidor_http_mcp.py`, que o agente carrega em tempo de execução, não estava
sendo empacotado. Em desenvolvimento o arquivo sempre esteve presente, então a
falha nunca aparecia para quem compilava — só para quem instalava. O instalador
agora leva esse arquivo, e uma verificação automática cruza a lista de arquivos
empacotados com o que o programa procura, para que a próxima ausência apareça
antes de publicar.

### O relatório não afirma mais o que não foi observado

Três defeitos diferentes levavam a mesma consequência — um laudo com aparência de
prova e nada por trás:

Quando a automação era interrompida por cota antes do primeiro passo, um print da
página em branco era guardado como "evidência". Agora, execução sem nenhum passo
executado não gera print, e o log diz por quê.

Quando o modelo fechava o navegador com `browser_close` ao terminar, a captura de
evidência — que acontece depois do laço — falhava em silêncio e o relatório saía
sem prova. Agora o print é garantido antes de o fechamento seguir adiante.

Quando o modelo escrevia um espaço reservado (`[ref]`) no lugar da referência de
elemento, o servidor não encontrava nada, a ação não acontecia, e a execução
continuava como se tivesse acontecido. Agora essa chamada é recusada antes de sair
do aplicativo, com a instrução de tirar um snapshot e usar a referência real.

### Aviso quando o modelo não é bom o suficiente para automação

O novo `avaliar_modelo.py` mede, em sete cenários, se um modelo escolhe a
ferramenta certa, usa os argumentos certos, sabe parar quando o objetivo foi
cumprido e resiste a texto plantado na página tentando dar ordens. Se o modelo
reprovar, o Copilot avisa ao entrar em modo Automação — e fica calado quando o
modelo passa. Modelos reprovados continuam úteis em Chat e Scan DOM.

### A conversa com a IA passou a ter tempo limite

Com a cota diária do Gemini esgotada, a requisição seguinte não era recusada: ficava
pendurada por vários minutos e a automação travava sem escrever nada na tela. Todas
as chamadas agora respeitam o tempo limite definido em Configurações, e a mensagem
explica a causa provável em vez de culpar "instabilidade".

### Desinstalação mais completa

O desinstalador passou a oferecer a remoção do navegador de testes e do cache dos
servidores MCP, mostrando quantos megabytes serão liberados. Python, Node.js e as
bibliotecas instaladas **não** são removidos: outros projetos da sua máquina podem
depender deles.

---

## Limitações conhecidas

O T2M roda em **Windows x64**. Versões para Linux, macOS e ARM estão no
planejamento e exigem substituir a interface, que hoje é WinForms.

Chaves gratuitas de IA têm cotas apertadas. No plano gratuito do Google, uma
automação de tela pode esgotar o limite por minuto no meio do teste — o aplicativo
espera e refaz, mas há um teto. Para testes longos, uma chave paga ou um provedor
com limite mais folgado faz diferença.

O modelo `llama-3.3-70b-versatile` reprovou na medição de escolha de ferramenta
(57% de acerto, mínimo 80%) e não é recomendado para o modo Automação. O
`gemini-2.5-flash` foi aprovado (85,7%).

---

## Verificação

Esta versão passa em **980 verificações automáticas** (`testar_regressao.py`), que
cobrem desde o comportamento da interface até as regras que impedem o agente de
obedecer a instruções plantadas em páginas, bancos ou arquivos anexados.

O instalador é conferido por `verificar_instalador.py`, que lê a lista de arquivos
do próprio script do Inno Setup e a cruza com o que o programa carrega em tempo de
execução — antes e depois de instalar.

---

## Licença

GPL-3.0. O código-fonte completo está neste repositório.
