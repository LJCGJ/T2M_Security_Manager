# T2M como extensao do Claude Desktop

Este diretorio monta o `.mcpb` — o pacote de instalacao com dois cliques.

## Por que existe

Editar `claude_desktop_config.json` a mao funciona, mas nao e entregavel: exige
achar o arquivo, respeitar JSON, nao apagar os outros servidores ja
configurados e reiniciar o aplicativo. Uma funcionalidade que depende disso e
uma funcionalidade que a maioria dos usuarios nunca vai usar.

Com o `.mcpb`, o usuario abre o arquivo, o Claude Desktop mostra uma tela de
configuracao gerada a partir do `manifest.json` — pasta permitida, conexao do
banco, tempo limite — e instala. Nenhum arquivo editado a mao.

## Como gerar o pacote

```
npm install -g @anthropic-ai/mcpb
cd plugin_claude
mcpb pack
```

Sai um `t2m-security-manager.mcpb` nesta pasta. Ele vai anexado a release do
GitHub, ao lado do instalador do Windows.

## O que vai dentro

    manifest.json                  metadados, ferramentas e configuracao do usuario
    server/servidor_mcp_t2m.py     o servidor MCP
    server/agente_mcp.py           de onde vem o validador de SQL somente-leitura

O `agente_mcp.py` viaja junto por um motivo especifico: o validador de SQL e
IMPORTADO dele, nunca reescrito. Duas copias de uma regra de seguranca divergem
no primeiro conserto, e a copia esquecida e sempre a que esta rodando na
maquina de alguem.

## Pre-requisito honesto

O Claude Desktop ja traz Node.js, mas nao traz Python — e o nosso servidor e
Python. Quem instalar a extensao precisa ter **Python 3.10+** no PATH. Quem
instalou o T2M pelo instalador do Windows ja tem, porque o preparador de
ambiente cuida disso. Quem so quer a extensao precisa instalar por conta.

Reescrever o servidor em Node resolveria isso e esta na fila — mas significaria
reimplementar as travas (SQL somente-leitura, pasta permitida, recusa de
referencia inventada) numa segunda linguagem, e duas implementacoes da mesma
regra de seguranca e exatamente o que este projeto evita.
