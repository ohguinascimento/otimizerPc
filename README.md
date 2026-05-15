# Otimizer PC

Aplicativo desktop para diagnostico e otimizacao segura do Windows.

## Funcionalidades

- Mostra informacoes do sistema
- Exibe uma analise detalhada com memoria RAM e tipo de disco
- Mostra o modelo da placa-mae e uma analise de slots e upgrade de RAM
- Faz auditoria de rede com processos, portas e conexoes ativas
- Lista processos mais pesados
- Limpa arquivos temporarios do usuario

## Requisitos

- Python 3.10+
- `psutil`
- Node.js 18+ para a interface React/Electron
- `pytsk3` para a trilha forense de arquivos

## Instalacao

```bash
pip install -r requirements.txt
```

Para a interface desktop:

```bash
cd web
npm install
```

Para habilitar a analise forense com `pytsk3`:

```bash
pip install -r requirements-forensic.txt
```

No Windows, a instalacao do `pytsk3` pode exigir Microsoft C++ Build Tools.

## Desenvolvimento e testes

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

## GUI Desktop

Para desenvolvimento:

```bash
cd web
npm run dev
```

Para producao local:

```bash
cd web
npm run build
npm run desktop
```

## VS Code

O projeto ja inclui configuracoes prontas em `.vscode/`:

- `Python: Run App` para depurar a aplicacao
- `Python: Run Tests` para depurar a suite de testes
- `GUI: Desktop React` para abrir a interface desktop em desenvolvimento
- `Testes: pytest` e `App: executar` em Tasks
- recomendacao das extensoes `ms-python.python` e `ms-python.debugpy`

Antes de usar, selecione o interpretador da `.venv` no VS Code.

## Execucao

Para abrir a interface desktop:

```bash
cd web
npm run desktop
```

O modo terminal continua disponivel para consulta rapida:

```bash
python main.py
```

ou

```bash
python -m optimizer_pc
```

## Observacao

A limpeza e focada em pastas temporarias e evita acoes agressivas como encerrar processos automaticamente.

