# MDReader

Editor Markdown para o desktop. Você escreve à esquerda e vê o resultado renderizado à direita, ao vivo. Feito em Python e PySide6, pensado primeiro para Ubuntu e depois portátil para outros sistemas.

![MDReader](img/screenshot.png)

O preview acompanha o cursor do editor, o índice à direita leva aos títulos de textos longos, e a paleta segue um tema escuro (padrão) ou claro, com laranja como cor de acento.

## Rodar no Ubuntu

```bash
sudo apt install python3 python3-venv python3-pip
./scripts/setup.sh
./scripts/run.sh
```

Com o ambiente já criado:

```bash
source .venv/bin/activate
python -m app
```

Se a janela Qt não abrir:

```bash
sudo apt install libxcb-cursor0 libxkbcommon-x11-0
```

## Empacotar

Executável local (PyInstaller):

```bash
./scripts/package.sh
```

O binário fica em `dist/MDReader/MDReader`. O `.deb` e os instaladores de outros sistemas ficam para um passo seguinte. Não é preciso reescrever o app.

## Como as imagens são salvas

Ao escolher uma imagem na barra esquerda ou arrastá-la para o editor, o MDReader **copia o arquivo** — não usa só o caminho original.

- A cópia vai para a pasta **`img/`** ao lado do executável. No desenvolvimento (`python -m app`), isso é a raiz do projeto.
- No Markdown entra um caminho relativo, por exemplo `img/foto.png`.
- Se o nome já existir, grava `foto-2.png`, `foto-3.png`, e assim por diante.
- A pasta é criada na primeira inserção. Com o app empacotado, `img/` fica ao lado de `dist/MDReader/MDReader`.

Sintaxe no texto (tamanhos no estilo Wiki.js):

```markdown
![legenda](img/foto.png)
![legenda](img/foto.png =240x)
![legenda](img/foto.png =100%x)
```

## Como funciona

A janela tem quatro áreas:

1. **Barra esquerda** — inserção de ligação, imagem, comando inline, bloco de código e recarregar o arquivo **(R)**.
2. **Editor** — texto Markdown em fonte monoespaçada.
3. **Preview** — renderização ao vivo. Comandos `` `assim` `` viram chips clicáveis (copiam o texto). Blocos ` ``` ` ganham uma caixa com botão **Copiar**; também dá para selecionar trechos e copiar com Ctrl+C.
4. **Índice** — lista os títulos do documento. Clique para ir até o título no preview e no editor.

No topo, a barra de formatação (negrito, itálico, rasurado, títulos e avisos). No fim dela há um botão para **ocultar o preview**; o editor passa a ocupar a janela. Embaixo, a barra de status mostra tipo do arquivo e a posição do cursor (Ln, Col).

O preview atualiza enquanto você digita e rola até o bloco correspondente à linha do cursor.

## Opções de edição

### Barra superior

| Botão | Função | Markdown |
| --- | --- | --- |
| **B** | Negrito | `**texto**` |
| **I** | Itálico | `*texto*` |
| **S** | Rasurado | `~~texto~~` |
| **H** | Título H1–H5 | `#` … `#####` |
| **i** | Aviso (Info, Warning, Danger, Record) | citação + `{.is-info}` etc. |
| Ícone de painéis | Mostrar ou ocultar o preview | — |

### Barra esquerda

| Botão | Função | Markdown |
| --- | --- | --- |
| `[]` | Ligação | `[texto](https://)` |
| Imagem | Escolher arquivo e inserir | `![legenda](img/foto.png)` |
| `` `x` `` | Comando inline | `` `comando` `` |
| `{ }` | Bloco de código | cerca de três crases |
| **(R)** | Recarregar o arquivo do disco | — |

No fim da barra, o **(R)** (parênteses brancos, R laranja) relê o `.md` que está aberto. Serve quando outra pessoa ou outro editor altera o mesmo arquivo.

O app **detecta mudanças no disco** e avisa na barra de status. Se você tiver alterações locais e clicar em **(R)**, aparece um aviso: recarregar **descarta** o que ainda não foi salvo. Sem arquivo aberto no disco, o botão não tem o que recarregar.

### Avisos (callouts)

Use uma citação, uma linha em branco e o marcador. A linha `{.is-*}` some no preview e o bloco ganha cor.

```markdown
> Informação útil para o leitor.

{.is-info}
```

Os tipos são `{.is-info}`, `{.is-warning}`, `{.is-danger}` e `{.is-record}`.

## Atalhos

| Atalho | Ação |
| --- | --- |
| **Ctrl+N** | Novo arquivo |
| **Ctrl+O** | Abrir |
| **Ctrl+S** | Salvar |
| **Ctrl+Shift+S** | Salvar como |
| **Ctrl+B** | Negrito |
| **Ctrl+I** | Itálico |
| **Ctrl+Q** | Sair |

Menus **Arquivo** e **Visualizar** (tema escuro / tema claro) cobrem o restante. O app abre no tema escuro.
