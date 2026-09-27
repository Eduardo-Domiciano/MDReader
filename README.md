# MDReader

Editor Markdown simples para Ubuntu, com preview ao vivo. Escrito em Python + PySide6; o mesmo código pode ser empacotado depois para Windows e macOS.

## Rodar no Ubuntu

```bash
sudo apt install python3 python3-venv python3-pip
./scripts/setup.sh
./scripts/run.sh
```

Ou, com o ambiente já criado:

```bash
source .venv/bin/activate
python -m app
```

Se a janela Qt não abrir, instale as bibliotecas do sistema:

```bash
sudo apt install libxcb-cursor0 libxkbcommon-x11-0
```

## Empacotar

Executável local (PyInstaller):

```bash
./scripts/package.sh
```

O `.deb` e os instaladores de outros sistemas ficam para um passo seguinte (Briefcase ou o próprio PyInstaller em cada SO). Não é preciso reescrever o app.


`comando`