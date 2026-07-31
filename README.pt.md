# T2M Security Manager

> Ferramenta desktop com IA para automação de testes e testes de segurança, construída sobre o Model Context Protocol (MCP).

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078D6.svg)](#)
[![Language: C++/CLI + Python](https://img.shields.io/badge/language-C%2B%2B%2FCLI%20%2B%20Python-orange.svg)](#)

*Leia em outros idiomas: [English](README.md)*

<!-- SCREENSHOT: janela principal / interface de chat aqui -->

---

## O que é

O T2M Security Manager é uma **ferramenta desktop Windows, gratuita e open-source**,
que leva automação de testes e testes de segurança com IA para desenvolvedores
individuais e pequenas equipes de QA — sem o custo de suítes comerciais.

Você descreve o que quer testar em linguagem natural, e um agente de IA executa ao
vivo através do **Model Context Protocol (MCP)**: ele controla um navegador real,
consulta um banco de dados ou chama uma API HTTP — e depois relata o que encontrou,
podendo gerar um script de teste reutilizável.

O projeto roteia entre **Claude, Gemini e OpenAI** — você escolhe a IA pela chave de
API que fornece.

> **Status do projeto:** todas as funcionalidades estão construídas e a interface está
> completa. As execuções de validação de ponta a ponta contra alvos reais ainda estão
> em andamento — veja o [Roadmap](#roadmap).

---

## Recursos

- **Assistente de IA conversacional** para planejar e escrever testes (foco em QA e segurança).
- **Três modos de automação**, selecionáveis no chat:
  - **Teste de Tela** — um navegador real (Playwright via MCP) que a IA controla passo
    a passo: navega, clica, digita e valida o comportamento real em páginas dinâmicas.
  - **Teste de API** — monte uma requisição HTTP (método, URL, headers, body) e deixe a
    IA chamá-la e analisar a resposta.
  - **Teste de Banco de Dados** — a IA explora o schema e executa consultas, somente
    leitura por padrão.
- **Sete bancos de dados suportados:**

  | Banco | Como conecta |
  |---|---|
  | PostgreSQL, MySQL, MariaDB, SQLite, SQL Server | Servidor MCP DBHub |
  | Oracle | Driver oficial `python-oracledb` (thin mode — dispensa o Instant Client) |
  | MongoDB | Servidor MCP oficial da MongoDB |

- **Scan de DOM estático** — leitura rápida e leve da estrutura de uma página, útil para
  análise de segurança e verificações simples.
- **Roteamento multi-IA** — Claude (`sk-ant-...`), OpenAI (`sk-...`), Groq (`gsk_...`)
  ou Gemini, escolhido automaticamente pelo prefixo da chave, com um indicador visual
  claro.
- **Endpoints compatíveis com a OpenAI** — um campo de endereço em Configurações libera
  Groq, Ollama, LM Studio, vLLM e OpenRouter sem código novo: todos falam o mesmo
  protocolo. Serve para testar sem gastar cota paga, e o Ollama roda **local, sem
  internet** — o único jeito de demonstrar em cliente que não pode mandar dado para fora.
- **Controle de custo** — escolha o modelo Claude (Haiku / Sonnet / Opus) e limite os
  passos do agente por tarefa, decidindo o equilíbrio entre capacidade e gasto.
- **Histórico de sessões** — salve uma conversa e reabra depois, com a formatação intacta.
- **Relatórios em HTML** — exporte o relatório do teste ou o log técnico como página
  formatada.
- **Biblioteca de scripts** — os scripts gerados (Python, Robot Framework, SQL) são
  salvos e listados para reutilização.
- **Temas claro e escuro**, aplicados em todas as janelas.
- **Segurança em primeiro lugar** — chaves de API e senhas de banco são cifradas em
  disco com o Windows DPAPI; o acesso a banco é somente-leitura por padrão; e as
  credenciais ficam na pasta de perfil do usuário, nunca dentro do diretório do programa.

---

## Como funciona

```
+-------------------+       +------------------+       +---------------------------+
|  App Desktop T2M  |       |  Agente Python   |       |  Servidores MCP / drivers |
|   (C++/CLI, UI)   | ----> |  (agente_mcp.py) | ----> |  - Playwright (tela)      |
|                   |       |                  |       |  - DBHub (bancos SQL)     |
| chat + formularios| stdin |  loop agentico:  |       |  - MongoDB MCP (oficial)  |
|                   | <---- |  IA <-> tools    | <---- |  - oracledb (Oracle)      |
+-------------------+ stdout+------------------+       |  - HTTP nativo (API)      |
                                                       +---------------------------+
```

O app desktop em C++/CLI coleta a requisição e a passa para um agente Python via stdin.
O agente sobe o servidor MCP certo (ou usa um driver nativo para Oracle e HTTP) e roda
um **loop agêntico**: a IA raciocina, chama uma ferramenta, observa o resultado real e
repete até concluir a tarefa — retornando por fim um relatório e, quando útil, um script
de teste.

---

## Requisitos

- **Windows** (x64)
- **Node.js 18+** — para os servidores MCP (`npx` inicia o Playwright, o DBHub e o
  servidor do MongoDB)
- **Python 3.10+**
- Uma **chave de API** de pelo menos um provedor (Claude, OpenAI, Gemini ou Groq) — ou
  nenhuma, se você usar um modelo local via Ollama

> **Sobre as IAs:** os modos de automação fazem **uma chamada por passo**, então o limite
> que importa é o de requisições por minuto, não o de tokens. Chaves gratuitas do Gemini
> rendem poucas por minuto e uma automação de 15 passos entra em fila de espera. Para
> testar sem esse atrito, veja [Endpoints compatíveis](#endpoints-compatíveis-com-a-openai);
> para trabalho sério, uma chave Claude ou OpenAI com crédito dá a experiência mais confiável.

---

## Endpoints compatíveis com a OpenAI

Groq, Ollama, LM Studio, vLLM e OpenRouter falam **o mesmo protocolo da OpenAI** — muda
só o endereço. Por isso não existe "provedor novo" no código: existe a rota da OpenAI
apontando para outro lugar, reaproveitando o mesmo laço de chamada de ferramentas.

Configure em **Configurações → Endpoint compatível com a OpenAI**. Os botões *Groq* e
*Ollama* preenchem o endereço para você.

| Serviço | Endereço | Chave | Modelo de exemplo |
|---|---|---|---|
| Groq (nuvem, gratuito) | `https://api.groq.com/openai/v1` | a sua `gsk_...` | `llama-3.3-70b-versatile` ou `llama-3.1-8b-instant` |
| Ollama (local) | `http://localhost:11434/v1` | qualquer texto (ex.: `ollama`) | `qwen2.5:7b` |
| LM Studio (local) | `http://localhost:1234/v1` | qualquer texto | o modelo carregado |

**Groq dispensa configuração:** chaves que começam com `gsk_` são reconhecidas sozinhas
e já apontam para o endereço oficial. Basta colar a chave e escolher o modelo.

**Ollama, passo a passo:**

```bash
ollama pull qwen2.5:7b     # baixa o modelo (uma vez)
ollama serve               # sobe o servidor local
```

Depois, em Configurações, clique em *Ollama*, escreva `qwen2.5:7b` no campo de modelo e
cadastre uma chave qualquer. Prefira modelos que suportem **tool calling** — sem isso os
modos de automação não funcionam, só o Chat.

> **Duas garantias.** Com o campo vazio, nada muda: quem já usa o aplicativo continua
> exatamente como está. E mesmo preenchido, chaves reconhecidas como Claude (`sk-ant-`),
> OpenAI (`sk-`) ou Google (`AIza`/`AQ`) **nunca** são desviadas — só chaves que não se
> parecem com nenhuma conhecida vão para o endpoint. Sem isso, um endereço mal digitado
> sequestraria em silêncio as chaves que já funcionavam.

---

## Começando

### Opção A — instalador (recomendado)

Baixe o instalador na página de [Releases](https://github.com/LJCGJ/T2M_Security_Manager/releases)
e execute. Ele instala o app e oferece configurar automaticamente as bibliotecas Python
e o navegador de testes.

### Opção B — a partir do código

1. Clone o repositório:
   ```bash
   git clone https://github.com/LJCGJ/T2M_Security_Manager.git
   ```
2. Instale o Node.js 18+ e depois as dependências Python:
   ```bash
   pip install -r requirements.txt
   npx playwright install chromium
   ```
3. Abra a solução no Visual Studio e compile em **Release / x64**.
4. Rode o app, adicione sua chave de API e escolha um modo de automação.

<!-- SCREENSHOT: menu de automação / formulário de API / formulário de banco aqui -->

---

## Uso

1. Abra a janela do assistente de IA e selecione sua chave de API (o indicador mostra
   qual IA ela usa).
2. Escolha um modo:
   - **Chat** — converse sobre sua estratégia de testes.
   - **Scan DOM** — aponte para uma URL para uma leitura estrutural rápida.
   - **Automação** — escolha Tela, API ou Banco, preencha os detalhes e descreva o que
     validar.
3. Leia o relatório no chat. Exporte como HTML, salve a sessão para continuar depois, ou
   extraia o script gerado para reutilizar.

As configurações (pastas, modelo, limites de passos) ficam em **Configuracoes**, na
janela principal.

---

## Onde ficam seus dados

| O quê | Onde |
|---|---|
| Chaves de API, preferências, tema | `%APPDATA%\T2M Security Manager` (cifrado com DPAPI) |
| Relatórios, sessões, scripts | Pastas que você escolhe em Configurações (padrão: `Documentos`) |

Nada é enviado para lugar nenhum além do provedor de IA cuja chave você fornecer.

---

## Roadmap

- [x] Assistente conversacional + três modos de automação (tela / API / banco)
- [x] Sete bancos de dados, incluindo Oracle e MongoDB
- [x] Roteamento multi-IA com indicador visual e escolha de modelo
- [x] Credenciais cifradas (DPAPI), banco somente-leitura por padrão
- [x] Histórico de sessões, relatórios HTML, biblioteca de scripts, temas claro/escuro
- [x] Instalador para Windows com preparação automática de dependências
- [ ] Execuções de validação de ponta a ponta em todos os modos
- [ ] Binários publicados em Releases

---

## Contribuindo

Contribuições são bem-vindas. Este é um projeto em estágio inicial, então issues, ideias
e pull requests ajudam bastante. Por favor, abra uma issue para discutir mudanças
significativas antes.

---

## Licença

Este projeto é licenciado sob a **GNU General Public License v3.0** — veja o arquivo
[LICENSE](LICENSE) para detalhes. Em resumo: você é livre para usar, estudar e modificar
o software, mas derivados distribuídos também devem permanecer abertos sob a GPL.

---

## Autor

**Leonardo Gonzaga** — engenheiro de automação de testes (QA).
GitHub: [@LJCGJ](https://github.com/LJCGJ)

*Construído como um recurso gratuito para a comunidade de QA e testes de segurança.*
