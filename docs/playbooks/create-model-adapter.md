---
type: Playbook
title: "Criar um adaptador de modelo"
description: Como colocar um modelo real atrás de uma interface injetável (ObjectDetector ou VisualQuestionAnswerer).
tags:
- playbook
- models
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:34:40-03:00"
evidence_basis: [verified]
---

# Criar um adaptador de modelo

Modelos reais ficam atrás de interfaces injetadas no construtor dos componentes ([injeção de dependências](../references/dependency-injection.md)). Exemplo real: `YoloDetector` implementa `ObjectDetector` ([YOLO](../references/component-yolo-detector.md)).

## Escolher a interface

| Saída do modelo | Interface | Componente que a consome |
|---|---|---|
| Caixas com classe e confiança | `ObjectDetector` (`components/object_detection/object_detector.py`) | `ObjectDetectionComponent` |
| Texto livre sobre uma imagem | `VisualQuestionAnswerer.answer(image, question) -> str` | `VisualQuestionAnsweringComponent` |

Se nenhuma servir, proponha uma interface nova antes de implementar (com aprovação).

## Passos

1. Crie o adaptador numa subpasta do componente (por exemplo, `components/object_detection/detectors/`).
2. Receba caminhos e parâmetros pelo construtor; carregue o modelo uma vez.
3. Converta a entrada e a saída para o contrato da interface (imagem BGR `np.ndarray`, caixas em pixels da imagem original).
4. **Nunca invente** confiança ou caixas; se o modelo não der confiança, use `conf=None` ([ADR 003](../adr/003-nullable-detection-confidence.md)).
5. Dependências novas exigem aprovação. Se forem incompatíveis com o ambiente principal, o modelo roda **fora do processo** ([ADR 004](../adr/004-mirage-out-of-process.md)).
6. Testes:
   - a lógica de pré e pós-processamento com dados sintéticos;
   - um teste com o modelo real só se for **pulado** quando não configurado (como `DETECTION_MODEL_PATH`);
   - o MIRAGE nunca é carregado em testes.

## Documentar

- Página `references/component-<adaptador>.md`, linha no índice, e os arquivos de sempre.
- Registre a decisão de usar o modelo num ADR, se for nova.
