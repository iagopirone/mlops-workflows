---
type: ADR
title: "ADR 003 — Detection.conf pode ser nulo"
description: Detecções sem confiança calibrada usam conf null; nunca se inventa um valor.
tags:
- adr
- detection
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:34:40-03:00"
evidence_basis: [approved, verified]
---

# ADR 003 — `Detection.conf` pode ser nulo

- **Status:** Aceito (aprovado pelo usuário em 17/11/2026; registrado em ADR em 18/11/2026)

## Contexto

O MIRAGE só produz texto e não tem nota de confiança de detecção. O `Detection` exigia `conf: float`. Preencher um valor fixo violaria a regra do usuário de **nunca inventar** confiança.

## Decisão

- `Detection.conf: float | None`, **obrigatório e sem padrão**; quando numérico, entre 0 e 1.
- `null` significa "a fonte não fornece confiança".
- O visualizador mostra só a classe quando `conf` é `null`.

## Alternativas consideradas

- Valor fixo (por exemplo, `1.0`): descartado pela regra "nunca inventar confiança".
- Aceitar um `conf` escrito pelo próprio modelo no texto: descartado, porque não é nota calibrada; o parser rejeita `conf`/`confidence` (veja [ADR 005](005-strict-json-text-detection-parsing.md)).

## Consequências

- O YOLO continua gravando a confiança real; revalidado com 17 detecções idênticas.
- Métricas que dependem de confiança (AP/mAP) ficam indisponíveis para fontes sem `conf` (veja [ADR 006](006-offline-detection-evaluation.md)).
- Documentos vivos: [artefato de detecção](../references/artifact-detection.md), [contratos](../references/contracts.md), [visualizador](../references/component-detection-visualization.md).
- Origem: [log](../log.md), 17/11/2026, "Implementação: interpretação de respostas textuais em detecções", decisão 1.
