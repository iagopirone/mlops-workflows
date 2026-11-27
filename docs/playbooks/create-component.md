---
type: Playbook
title: "Criar um componente"
description: Passo a passo para adicionar um Component com prepare() que devolve conteúdos e dependências injetadas.
tags:
- playbook
- components
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:34:40-03:00"
evidence_basis: [verified]
---

# Criar um componente

Modelo real a copiar: `mlops_workflows/components/visual_question_answering/visual_question_answering_component.py`. Regras em [contratos](../references/contracts.md), [injeção de dependências](../references/dependency-injection.md) e [invariantes](../references/invariants.md).

## Passos

1. Crie `mlops_workflows/components/<nome>/` com `__init__.py` e `<nome>_component.py`.
2. A classe herda de `Component`. Dependências (modelo, parser, referência de saída) entram **pelo construtor**; nada é instanciado dentro do componente.
3. `prepare(input_artifacts)`:
   - confere a quantidade e o tipo de cada referência e lança `ValueError` se não baterem;
   - chama `materialize()` e devolve os **conteúdos** ([ADR 002](../adr/002-prepare-returns-artifact-contents.md)).
4. `execute(prepared_data)`:
   - confere a forma e os tipos recebidos e lança `TypeError` se não baterem;
   - só então lê `.data`; passe cópias a dependências que possam alterar os dados;
   - valide tudo **antes** de gravar, para não deixar arquivo parcial;
   - grava com `dematerialize(output_reference)` e devolve `[output_reference]`.
5. Testes:
   - unitários em `tests/unit/components/<nome>/` com simuladores (`Fake*`), cobrindo entradas inválidas, falhas da dependência e ausência de saída em caso de erro;
   - integração em `tests/integration/components/<nome>/` com arquivos reais em `tmp_path`.
6. Não altere componentes que já funcionam sem aprovação.

## Documentar

- Nova página `references/component-<nome>.md` e uma linha em `references/index.md`.
- Atualize [componentes](../references/components.md), [pipeline atual](../diagrams/current-pipeline.md) se o fluxo mudar, e os arquivos de sempre (`log.md`, [status](../references/status.md), `handoff.md`).
- Se for provisório, registre em [mecanismos transitórios](../references/transitional-mechanisms.md).
