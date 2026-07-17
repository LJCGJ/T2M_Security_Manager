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

> **Status do projeto:** inicial e em desenvolvimento ativo. A interface, a camada de
> segurança e a fiação dos três modos de automação estão completas. As execuções reais
> de ponta a ponta dependem de uma IA com capacidade suficiente (veja [Requisitos](#requisitos)).

---

## Recursos

- **Assistente de IA conversacional** para planejar e escrever testes (foco em QA e segurança).
- **Três modos de automação**, selecionáveis no chat:
  - **Teste de Tela** — um navegador real (Playwright via MCP) que a IA controla passo
    a passo: navega, clica, digita e valida o comportamento real em páginas dinâmicas.
  - **Teste de API** — monte uma requisição HTTP (método, URL, headers, body) e deixe a
    IA chamá-la e analisar a resposta.
  - **Teste de Banco de Dados** — conecte a um banco e deixe a IA explorar o schema e
    executar consultas somente-leitura (via um servidor MCP de banco).
- **Scan de DOM estático** — leitura rápida e leve da estrutura de uma página, útil para
  análise de segurança e verificações simples.
- **Roteamento multi-IA** — Claude (`sk-ant-...`), OpenAI (`sk-...`) ou Gemini, escolhido
  automaticamente pelo prefixo da chave, com um indicador visual claro.
- **Geração de scripts** — a IA pode produzir scripts de teste reutilizáveis (Robot
  Framework, Python ou SQL) que você salva e executa de novo.
- **Segurança em primeiro lugar** — chaves de API e senhas de banco são cifradas em
  disco com o Windows DPAPI; o acesso a banco é somente-leitura por padrão.

---

## Como funciona

```
+-------------------+       +------------------+       +-----------------------+
|  App Desktop T2M  |       |  Agente Python   |       |    Servidores MCP /   |
|   (C++/CLI, UI)   | ----> |  (agente_mcp.py) | ----> |    ferramenta HTTP    |
|                   |       |                  |       |  - Playwright (tela)  |
|  chat + formularios| stdin|  loop agentico:  |       |  - DBHub (banco)      |
|                   | <---- |  IA <-> ferramentas| <-- |  - HTTP nativo (API)  |
+-------------------+ stdout+------------------+       +-----------------------+
```

O app desktop em C++/CLI coleta a requisição e a passa para um agente Python via stdin.
O agente sobe o servidor MCP certo (ou usa uma ferramenta HTTP nativa para APIs) e roda
um **loop agêntico**: a IA raciocina, chama uma ferramenta, observa o resultado real e
repete até concluir a tarefa — retornando por fim um relatório e, quando útil, um script
de teste.

---

## Requisitos

- **Windows** (x64)
- **Node.js 18+** — para os servidores MCP (`npx` inicia Playwright / servidores de banco)
- **Python 3.10+** com: `mcp`, `anthropic`, `google-generativeai`, `openai`, `requests`
- Uma **chave de API** de pelo menos um provedor (Claude, OpenAI ou Gemini)

> **Sobre as IAs:** os modos de automação fazem várias chamadas sequenciais à IA. Chaves
> gratuitas do Gemini têm limites baixos por minuto que podem interromper execuções mais
> longas; uma chave Claude ou OpenAI com crédito disponível dá a experiência mais confiável.

---

## Começando

1. Clone o repositório:
   ```bash
   git clone https://github.com/LJCGJ/T2M_Security_Manager.git
   ```
2. Instale o Node.js 18+ e as dependências Python:
   ```bash
   pip install mcp anthropic google-generativeai openai requests
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
3. Leia o relatório no chat. Peça à IA para gerar um script e salve com
   **Extrair e Salvar Script**.

---

## Roadmap

- [x] Assistente conversacional + três modos de automação (tela / API / banco)
- [x] Roteamento multi-IA com indicador visual
- [x] Credenciais cifradas (DPAPI), banco somente-leitura por padrão
- [ ] Execuções de validação de ponta a ponta em todos os modos
- [ ] Suporte a Oracle e MongoDB (servidores MCP dedicados)
- [ ] Instalador empacotado (Python + Node embutidos)

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
