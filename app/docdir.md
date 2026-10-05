# app

Código do editor Markdown: janela, preview, temas e arquivos.

## Arquivos

| Arquivo | O que faz |
| --- | --- |
| `__init__.py` | Marca a pasta como pacote Python. |
| `__main__.py` | Permite iniciar com `python -m app`. |
| `main.py` | Janela principal, menus, abrir pasta e salvar. |
| `editor.py` | Área de texto Markdown e botões de formatação no texto. |
| `preview.py` | Preview ao vivo, chips de comando e caixas de código. |
| `diagrams.py` | Reconhece a linguagem do bloco e desenha diagramas Mermaid. |
| `chrome.py` | Barras da janela: título, formatação, inserção e status. |
| `theme.py` | Cores dos temas escuro e claro. |
| `files.py` | Barra lateral com a árvore de arquivos `.md`. |
| `outline.py` | Índice de títulos do documento aberto. |
| `images.py` | Copia imagens para `img/` e aplica tamanhos no preview. |
| `callouts.py` | Blocos de aviso (info, warning, danger, record). |
| `icon.py` | Desenha o ícone MD_ da janela. |
| `icon.png` | Imagem do ícone usada na barra de título. |

## Observacoes

- Diagramas Mermaid são gravados em PNG temporário (`mdreader-diagrams` na pasta temporária do sistema).
