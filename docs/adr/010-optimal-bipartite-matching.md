---
type: ADR
title: "ADR 010 — Correspondência bipartida ótima no avaliador offline"
description: O avaliador troca o pareamento greedy por correspondência bipartida ótima (mais TP primeiro, depois maior soma de IoU) e ganha um modo independente de classe com matriz de confusão.
tags:
- adr
- evaluation
- matching
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T16:10:33-03:00"
evidence_basis: [approved, verified]
---

# ADR 010 — Correspondência bipartida ótima

- **Status:** Aceito (decisão Q1 do usuário em 18/11/2026); implementado e testado.
- **Altera:** o método de correspondência do [ADR 006](006-offline-detection-evaluation.md). O resto do ADR 006 continua valendo: respostas inválidas e ausentes contam como FN, sem AP/mAP.

## Contexto

O avaliador escolhia os pares em ordem decrescente de IoU (*greedy*). Isso foi **verificado** como subestimando os verdadeiros positivos.

**Contraexemplo:**
- A0 = `[5, 0, 15, 10]` e A1 = `[7, 0, 17, 10]`;
- P0 = `[5.5, 0, 15.5, 10]`, com IoU 0,905 com A0 e 0,739 com A1;
- P1 = `[2, 0, 12, 10]`, com IoU 0,538 com A0 e 0,333 com A1.

O *greedy* casa P0–A0 e fica com **1 TP**; P0–A1 + P1–A0 dão **2 TP**. Células sobrepostas, como hemácias aglomeradas, tornam esse caso realista.

## Decisão

1. **Correspondência um-para-um ótima**, pelo algoritmo húngaro (Kuhn-Munkres, O(n²m)), implementado só com a biblioteca padrão e compatível com o Python 3.10. Fica em `experiments/mirage/evaluate_detections.py`.
2. **Pares elegíveis:** IoU ≥ limiar (0,5) e, no modo sensível à classe, a mesma classe.
3. **Objetivo lexicográfico:** primeiro **o maior número de pares** (TP), depois **a maior soma de IoU**. Cada par pesa `M + IoU`, com `M` maior que o número máximo de pares, de modo que um par a mais sempre vale mais do que qualquer ganho de IoU.
4. **Modo independente de classe** (`evaluate(..., class_aware=False)`): mede a localização sozinha.
   - TP e FN contam na classe anotada; FP, na classe prevista.
   - `confusion[classe anotada][classe prevista]` conta os pares casados, o que mede a classificação.
   - No modo sensível à classe, a matriz é diagonal.

## Consequências

- **Testes:**
  - o contraexemplo, com o *greedy* antigo mantido **só no teste** como referência;
  - a preferência pela soma de IoU;
  - 80 casos aleatórios (semente fixa, 2 modos) conferidos por força bruta;
  - o modo independente de classe e a matriz de confusão.

  168 testes do experimento passam no Python 3.12 e no 3.10.
- **Empates de mesma quantidade e mesma soma:** a solução é determinística para a mesma entrada, mas a regra de desempate não é especificada.
- Os números de qualquer avaliação anterior, que só existiam com dados sintéticos, podem mudar. Nenhuma métrica real tinha sido produzida.
- Documentação: [avaliador](../references/mirage-evaluation.md).
