---
type: ADR
title: "ADR 006 — Avaliação offline de detecções"
description: Respostas inválidas ou ausentes contam como falso negativo; métricas sem AP/mAP porque não há confiança.
tags:
- adr
- evaluation
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:34:40-03:00"
evidence_basis: [approved, verified]
---

# ADR 006 — Avaliação offline de detecções

- **Status:** Aceito (aprovado e implementado em 17/11/2026; registrado em ADR em 18/11/2026)

## Contexto

Para transformar a hipótese "o MIRAGE localiza objetos" em números, as caixas extraídas das respostas precisam ser comparadas com anotações humanas.

## Decisão

- `experiments/mirage/evaluate_detections.py` reutiliza o `TextDetectionParser` (respostas e anotações), sem duplicar validação.
- Correspondência um-para-um, por classe, gulosa por IoU decrescente, com limiar inclusivo (padrão 0,5).
- Métricas: TP, FP, FN, precisão e revocação, no total e por classe; `null` quando indefinidas; `mean_matched_iou`.
- **Respostas inválidas ou ausentes nunca são excluídas:** entram com zero predições, e todas as anotações da imagem viram FN.
- **Sem AP/mAP**, porque não há confiança.
- Roda **fora** do ambiente conda do MIRAGE, porque precisa de Pydantic 2.

## Alternativas consideradas

- Excluir respostas inválidas do cálculo: descartado, porque esconderia falhas do modelo.
- Calcular AP/mAP: impossível sem confiança.

## Consequências

- A correspondência gulosa não é ótima; a classe é comparada por igualdade exata; não há métrica que ignore a classe.
- **Nunca usado com dados reais** até 18/11/2026.
- Documento vivo: [avaliador](../references/mirage-evaluation.md).
- Origem: [log](../log.md), 17/11/2026, "Implementação: avaliador offline de detecções".
