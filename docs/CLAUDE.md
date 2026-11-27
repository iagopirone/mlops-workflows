# docs/CLAUDE.md — regras do bundle de documentação

Este diretório é um bundle **OKF 0.2** no padrão do repositório `new-visio-research-models`, adaptado a este projeto. As diretrizes completas, com justificativas, estão em [`references/okf-guidelines.md`](references/okf-guidelines.md). Aqui fica o resumo que todo agente precisa seguir ao editar `docs/`.

## Retomar o contexto (sessão nova ou depois de compactação)

1. [`handoff.md`](handoff.md): estado atual, última tarefa, próxima ação.
2. [`references/status.md`](references/status.md): o que está verificado, aprovado, em hipótese ou proposto.
3. [`log.md`](log.md): histórico, mais recente primeiro.
4. [`index.md`](index.md) e os `index.md` de cada pasta, para achar a página técnica da tarefa.

## Arquivos da raiz de `docs/`

Só podem existir: `index.md`, `log.md`, `CLAUDE.md` e `handoff.md`. O `handoff.md` é uma **extensão local** (decisão D2): fica na raiz porque é o ponto fixo de recuperação de contexto. Todo o resto vai para uma categoria.

## Categorias

| Pasta | Tipo (`type`) | Natureza | Nome do arquivo |
|---|---|---|---|
| `playbooks/` | `Playbook` | viva: como fazer | `slug.md` |
| `references/` | `Reference` | viva: estado atual, contratos, regras | `slug.md` |
| `diagrams/` | `Diagram` | viva: Mermaid dentro do `.md` | `slug.md` |
| `adr/` | `ADR` | temporal: decisão e porquê | `NNN-slug.md` |
| `plans/` | `Plan` | temporal: o que se pretende fazer | `YYYY-MM-DD-slug.md` |
| `reports/` | `Report` | temporal: o que foi observado | `YYYY-MM-DD-slug.md` |

Documentos temporais não são reescritos depois de concluídos; uma mudança gera um documento novo ou uma seção "Atualização de DD/MM/AAAA" claramente marcada.

## Frontmatter

```yaml
---
type: Reference            # obrigatório
title: Título curto
description: Uma frase.
tags:
- tag
status: draft              # draft | stable | deprecated
generated:
  by: human:iago.pirone
  at: "2026-11-18T09:00:00-03:00"   # ISO 8601 com fuso, entre aspas
evidence_basis: [verified]  # extensão local: verified | approved | hypothesis | proposal
sources:                   # opcional
- id: local-checkout
  resource: ...
  title: ...
---
```

## Regras

- **Uma decisão = um documento temporal (ADR ou plano) + atualização do documento vivo correspondente, na mesma mudança.**
- Todo documento novo entra no `index.md` da sua pasta, no formato `* [Título](arquivo.md) - descrição`.
- Links internos são **relativos ao arquivo** (`../references/contracts.md`), para funcionarem no GitHub; links absolutos `/...` são recusados pelo validador. Isso diverge do repositório de referência ([ADR 008](adr/008-relative-internal-links.md)).
- `log.md`: seções `## YYYY-MM-DD`, a mais recente no topo.
- Mecanismos provisórios entram em [`references/transitional-mechanisms.md`](references/transitional-mechanisms.md) e saem junto com o código.
- Diferencie sempre **verificado**, **aprovado**, **hipótese** e **proposta**, no corpo e em `evidence_basis`.
- Documentação em português; código, nomes e docstrings em inglês.
- Blocos ```` ```python ```` dentro dos `.md` são verificados pelo `ruff format --check`: escreva-os já formatados.

## Validação

```bash
uv run python scripts/okf_lint.py           # estrutura, frontmatter, índices, links, log
uv run ruff format --check .                # também verifica blocos Python nos .md
```

O que o validador verifica (e o que não verifica) está em [`references/okf-guidelines.md`](references/okf-guidelines.md#validador-local).
