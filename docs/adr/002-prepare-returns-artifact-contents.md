---
type: ADR
title: "ADR 002 — prepare() devolve conteúdos de artefatos"
description: Component.prepare() retorna ImageContent, DetectionContent, TextContent etc., e não o .data cru.
tags:
- adr
- components
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:34:40-03:00"
evidence_basis: [approved, verified]
---

# ADR 002 — `prepare()` devolve conteúdos de artefatos

- **Status:** Aceito (aprovado pelo usuário em 17/11/2026; registrado em ADR em 18/11/2026)
- **Decisão anterior relacionada:** [ADR 001](001-workflow-architecture.md)

## Contexto

O contrato `Component.prepare(list[ArtifactReference]) -> object` não define o que é devolvido. O `ObjectDetectionComponent` devolvia o `np.ndarray` cru. Para o `DetectionVisualizationComponent`, que recebe imagem e detecções, devolver dados crus perdia o tipo e a validação Pydantic entre `prepare()` e `execute()`.

## Decisão

`prepare()` materializa as referências e devolve os **conteúdos** (`ImageContent`, `DetectionContent`, `TextContent`). `execute()` valida os tipos recebidos e só então acessa `.data`.

## Alternativas consideradas

- Devolver `.data` (como o `ObjectDetectionComponent`): mais curto, mas sem tipo nem validação no meio do caminho.

## Consequências

- Aplicada no visualizador (refatoração aprovada e verificada em 17/11/2026: 17 detecções no fluxo real) e nos componentes novos (VQA e parser).
- O `ObjectDetectionComponent` **continua divergente**; mudá-lo exige aprovação. Registrado em [mecanismos transitórios](../references/transitional-mechanisms.md).
- Documento vivo: [contratos](../references/contracts.md#convenção-aprovada-prepare-devolve-conteúdos), invariante I2 em [invariantes](../references/invariants.md).
- Origem no histórico: [log](../log.md), 17/11/2026, "Implementação: refatoração do `DetectionVisualizationComponent`".
