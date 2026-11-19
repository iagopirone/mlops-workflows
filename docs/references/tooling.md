---
type: Reference
title: Ferramentas de desenvolvimento
description: Python, uv, Ruff, pytest, pre-commit e práticas de versionamento.
tags:
- tooling
- git
- ruff
- uv
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:28:27-03:00"
evidence_basis: [verified]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d0fb7f2 + alterações não commitadas), inspecionado e testado em 17/11/2026
  title: Código, testes e execuções locais
- id: repo-snapshot
  resource: https://github.com/iagopirone/mlops-workflows/tree/666fbb5a210a3cc4143e745bce888eebfe8dc2b2
  title: Snapshot da branch feature/implementar-componentes em 09/11/2026 (commit
    666fbb5)
- id: conversation
  resource: Relatos de desenvolvimento e saídas de terminal fornecidos pelo usuário
    nesta conversa, 10–16/11/2026
  title: Evidências da conversa de desenvolvimento
---

# Ferramentas

- `uv`: gerencia instalação, ambiente e execução das ferramentas Python.
- `pytest`: testes unitários e de integração.
- `ruff check`: lint.
- `ruff format`: padronização de formato.
- `pre-commit`: hooks de higiene de código e validação antes dos commits.
- `git`: versionamento em branches e revisão por PR.

`.pre-commit-config.yaml` e `hooks/pre-push` estão no repositório (conferido em 18/11/2026). `hooks/pre-push` impede *push* direto quando o branch atual é `main` ou `rc` — cuidado: a execução desse hook depende de ele estar instalado/configurado no repositório local.

## Comandos

```bash
uv run ruff check .
uv run ruff format --check .
uv run ruff format caminho/do/modulo/
uv run python -m pytest -q
```

Use `ruff format --check` na validação final para evitar alterações inesperadas de código. Após formatar, reexecute lint e testes.

## Observações verificadas (17/11/2026)

- **`ruff format --check .` verifica blocos de código Python dentro dos `.md`.** Um exemplo mal formatado na página do visualizador (hoje [/references/component-detection-visualization.md](component-detection-visualization.md)) fazia o comando falhar; foi corrigido em 17/11/2026.
- `uv run --offline ...` funciona sem rede quando as dependências já estão instaladas.
- **Ruff 0.17 sem configuração no projeto:** usa o conjunto padrão de regras (inclui UP, TRY e ISC) e toma Python 3.12 como alvo, a partir do `requires-python`. `experiments/mirage/ruff.toml` muda o alvo para 3.10 só naquela pasta.
  - Ele também define `src = ["../.."]`. Sem isso, a configuração aninhada fazia o Ruff tratar `mlops_workflows` e `experiments` como pacotes de terceiros na ordenação de imports.
- **Validar código com Python 3.10 sem tocar no `.venv`:** `uv run --no-project --python 3.10 --with pytest ...`. O interpretador fica em `~/.local/share/uv/python/` (remover com `uv python uninstall 3.10`).
- `-p no:cacheprovider` evita escrever `.pytest_cache` quando necessário.

## Histórico

Branch de feature anterior: `feature/implementar-componentes`. PR #3 para `rc` (estado verificado com `gh` em 17/11/2026, abaixo). Commits, conferidos no `git log` em 18/11/2026:

- `b1b3c4f` — artefatos de detecção.
- `c629973` — generalização do detector YOLO.
- `d0fb7f2` — organização do repositório e remoção de código inicial.

- **Verificado em 17/11/2026:** a branch `feature/integracao-mirage` existe localmente com HEAD `d0fb7f2`. Nada da integração foi commitado. ~~O estado do PR #3 **não foi verificado**.~~ **Atualização:** verificado com `gh` mais tarde em 17/11/2026: o PR #3 está **aberto**.
- **Regra:** commits e pushes só com autorização do usuário (veja `CLAUDE.md`).

## Plano de commits

Movido em 18/11/2026 para [plano de commits](../plans/2026-11-17-plan-commits.md), um documento temporal (`Plan`).
