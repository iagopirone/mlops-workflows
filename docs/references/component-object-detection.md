---
type: Reference
title: ObjectDetectionComponent
description: Adaptação entre artefato de imagem, algoritmo de inferência e artefato JSON.
tags:
- detection
- component
- di
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:28:27-03:00"
evidence_basis: [verified]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d0fb7f2 + alterações não commitadas), inspecionado e testado em 17/11/2026
  title: Código, testes e execuções locais
- id: conversation
  resource: Relatos de desenvolvimento e decisões do usuário, 10–17/11/2026
  title: Evidências da conversa de desenvolvimento
---

# Contrato

Arquivo: `mlops_workflows/components/object_detection/object_detection_component.py` (commit `c629973`).

O construtor recebe:
- `detector: ObjectDetector`: a dependência injetada que implementa `detect(image)`;
- `output_reference: DetectionReference`: o destino do JSON.

## `prepare(input_artifacts)`

- Exige exatamente um `ImageReference`; senão gera `ValueError("Expected exactly one ImageReference.")`.
- Retorna **`np.ndarray`** (`content.data`).
- **Divergência consciente com a convenção de devolver conteúdos:** o usuário decidiu não refatorar este componente por enquanto.
- **Risco se for refatorado:**
  - o teste unitário `test_prepare_loads_image_from_reference` troca `materialize()` por um `SimpleNamespace`;
  - `examples/demo_detection.py` e o teste com ONNX real usam o `np.ndarray` retornado.

## `execute(prepared_data)`

- Exige `np.ndarray`; senão gera `TypeError`.
- Chama `self.detector.detect(...)`, cria `DetectionContent(data=detections)`, salva o JSON em `output_reference` e retorna `[output_reference]`.

## Testes

- 6 unitários com `FakeDetector`.
- 1 de integração com ONNX real, pulado se as variáveis `DETECTION_MODEL_PATH` e `DETECTION_IMAGE_PATH` não estiverem definidas.
- Esse teste passou em 17/11/2026 com `best.onnx` (YOLO11n: RBC, WBC, Platelets).

## Pendências

- Uniformizar o `prepare()` com a convenção de conteúdos: só com aprovação.
