# O T2M dentro de uma esteira (n8n, Jenkins, GitHub Actions)

## A ideia

O T2M nao ganhou integracao com o n8n. Ganhou um **contrato**, e o n8n é um dos
que sabem falar com ele — junto com Jenkins, GitHub Actions, Azure DevOps, um
`.bat` agendado no Windows ou qualquer coisa que saiba executar um comando e
olhar o codigo de saida.

Escrever integracao para uma ferramenta especifica seria escrever de novo para a
proxima. O contrato e o mesmo para todas:

    entrada declarada  ->  execucao  ->  JSON com o laudo  ->  codigo de saida

## O comando

```
python agente_mcp.py --headless --modo tela ^
  --alvo "https://sistema/login" ^
  --objetivo "fazer login com senha errada e confirmar a mensagem de erro" ^
  --json saida.json
```

Os modos sao `tela`, `banco`, `api` e `arquivos`. O `--alvo` muda de significado
conforme o modo: URL, DSN, JSON da requisicao ou pasta. A chave da IA vem por
`--chave` ou pela variavel `T2M_CHAVE`.

## O codigo de saida, que e a parte que importa

| Codigo | Significado | O que a esteira deve fazer |
|--------|-------------|----------------------------|
| `0` | O teste rodou e **nao encontrou problema** | seguir |
| `1` | O teste rodou e **encontrou problema** | parar, e ler o `motivo` do JSON |
| `2` | **Indeterminado** — nao da para afirmar nem uma coisa nem outra | parar e chamar alguem |

O `2` existe de proposito, e e o mais importante dos tres.

Cota estourada no meio, modelo que divagou, navegador que morreu, pagina que nao
carregou: tudo isso produz uma execucao **sem resposta**. Mapear isso para `0`
faria a esteira seguir adiante porque o teste nao soube responder — e um deploy
que acontece porque ninguem conseguiu testar e pior que um deploy travado.

Um pipeline que para por duvida custa uma investigacao. Um que segue por duvida
entrega o defeito ao cliente.

## O JSON

```json
{
  "modo": "tela",
  "alvo": "https://sistema/login",
  "objetivo": "fazer login com senha errada e confirmar a mensagem de erro",
  "provedor": "Gemini",
  "modelo": "gemini-2.5-flash",
  "passos": 7,
  "limite_de_passos_atingido": false,
  "veredito": "passou",
  "motivo": "A mensagem \"Your password is invalid!\" foi exibida conforme o esperado.",
  "prints": ["C:\\Users\\...\\prints\\259b3bc4c6cb_01.png"],
  "recusas": "",
  "relatorio": "..."
}
```

O campo `prints` traz os caminhos das evidencias — e por isso a esteira consegue
anexar a prova ao build sem saber nada da nossa estrutura de pastas. O `recusas`
diz se alguma chamada de ferramenta foi barrada durante a execucao: laudo com
recusa e laudo com ressalva.

## n8n

Use o no **Execute Command**:

```
Command: python
Arguments:
  C:\Program Files\T2M Security Manager\agente_mcp.py
  --headless
  --modo tela
  --alvo https://sistema/login
  --objetivo fazer login com senha errada e confirmar a mensagem de erro
  --json C:\temp\saida.json
```

Ligue a saida num no **IF** comparando `{{ $json.exitCode }}`:

- `0` → segue o fluxo;
- `1` → ramo de falha: leia `C:\temp\saida.json` com o no **Read Binary File** e
  mande `veredito` e `motivo` para o canal da equipe;
- qualquer outro → ramo de indeterminado, que **nao** deve ser tratado como
  sucesso.

O erro mais comum aqui e usar apenas dois ramos e deixar o `2` cair no ramo de
sucesso por omissao. Se o seu no de decisao so tem dois caminhos, faca o de
sucesso testar `exitCode === 0` explicitamente, e nunca `exitCode !== 1`.

A chave da IA deve entrar como credencial do n8n, exposta ao comando pela
variavel `T2M_CHAVE` — nunca escrita no campo de argumentos, que fica visivel no
historico de execucoes do proprio n8n.

## GitHub Actions

```yaml
- name: Teste de tela (T2M)
  env:
    T2M_CHAVE: ${{ secrets.T2M_CHAVE }}
  run: |
    python agente_mcp.py --headless --modo tela `
      --alvo "https://sistema/login" `
      --objetivo "fazer login com senha errada e confirmar a mensagem de erro" `
      --json saida.json

- name: Guardar a evidencia
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: evidencia-t2m
    path: |
      saida.json
```

O `if: always()` e proposital: a evidencia interessa **principalmente** quando o
passo anterior falhou.

## Jenkins

```groovy
def codigo = bat(returnStatus: true, script: """
  python agente_mcp.py --headless --modo tela ^
    --alvo "https://sistema/login" ^
    --objetivo "fazer login com senha errada" ^
    --json saida.json
""")
if (codigo == 1) { error("T2M encontrou um problema - veja saida.json") }
if (codigo != 0) { unstable("T2M nao conseguiu concluir o teste (indeterminado)") }
```

`unstable` em vez de `error` no caso indeterminado deixa a diferenca visivel no
painel: "achou defeito" e "nao consegui testar" sao coisas diferentes, e tratar
as duas como falha esconde qual delas aconteceu.

## Quanto custa

Cada execucao gasta cota da IA — sao varias requisicoes por teste, uma por
passo. Numa esteira que roda a cada commit, isso soma rapido.

Duas formas de reduzir, em ordem de eficacia:

A primeira e **gerar o script uma vez e repetir o script**, sem IA. O T2M gera
Robot Framework, Python e SQL a partir de uma execucao bem-sucedida: a IA e paga
uma vez, e a repeticao e de graca. Automacao com IA a cada commit e cara e
lenta; use-a para **escrever** o teste e para os casos que mudam.

A segunda e reservar a execucao com IA para os fluxos que mudam de forma
imprevisivel, e deixar os estaveis no script gerado.
