---
type: Playbook
title: "Documentar uma mudança"
description: O ciclo planejar, executar, validar e documentar, e o que atualizar em docs/ a cada etapa.
tags:
- playbook
- documentation
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:34:40-03:00"
evidence_basis: [verified]
---

# Documentar uma mudança

Ciclo obrigatório ([ADR 007](../adr/007-okf-documentation-structure.md)): **planejar → aprovação → executar → validar → documentar → apresentar → aguardar**.

## 1. Planejar

- Leia `docs/handoff.md`, [status](../references/status.md), o [log](../log.md) e as páginas técnicas envolvidas; confira `git status`.
- Apresente o plano ao usuário, com as decisões em aberto. **Não execute antes da aprovação.**
- Mudança grande (várias etapas ou arquivos): registre o plano aprovado em `plans/YYYY-MM-DD-plan-<slug>.md`.

## 2. Executar

Implemente só o que foi aprovado. Commits, pushes e mudanças de branch só com autorização.

## 3. Validar

Siga [testar localmente](test-locally.md) e o validador da documentação. Registre os resultados **reais**.

## 4. Documentar

| O que aconteceu | O que atualizar |
|---|---|
| Qualquer etapa concluída | página técnica (`references/...`), entrada no topo do [log](../log.md), [status](../references/status.md), `handoff.md` |
| Decisão de arquitetura ou de processo | ADR novo em `adr/` **e** o documento vivo afetado, na mesma mudança |
| Execução, pesquisa ou revisão com resultados | relatório em `reports/` |
| Algo provisório | [mecanismos transitórios](../references/transitional-mechanisms.md) |
| Regra que não pode ser quebrada | [invariantes](../references/invariants.md) |
| Documento novo | linha no `index.md` da pasta |

Em cada entrada, registre quando for relevante: objetivo, arquivos criados, alterados ou removidos, responsabilidades, decisões e porquês, dependências, entradas e saídas, testes com comandos e resultados reais, problemas e soluções, limitações e próximos passos. Diferencie **verificado**, **aprovado**, **hipótese** e **proposta**.

## 5. Antes de uma compactação

Atualize `handoff.md` primeiro: é o que garante a retomada.

## Checagem final

```bash
uv run python scripts/okf_lint.py
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest -q -rs
```
