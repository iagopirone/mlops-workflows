---
type: Reference
title: DetectionVisualizationComponent
description: Anotação independente do detector a partir de imagem e detecções.
tags:
- visualization
- opencv
- component
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:28:27-03:00"
evidence_basis: [verified, approved]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d0fb7f2 + alterações não commitadas), inspecionado e testado em 17/11/2026
  title: Código, testes e execuções locais
- id: conversation
  resource: Relatos de desenvolvimento e decisões do usuário, 10–17/11/2026
  title: Evidências da conversa de desenvolvimento
---

# Objetivo

Receber a imagem original e as detecções, desenhar retângulos e rótulos sobre uma **cópia** dos pixels e salvar uma nova imagem.

- Não faz inferência e não interpreta prompts.
- Não conhece YOLO nem MIRAGE.

Arquivo: `mlops_workflows/components/detection_visualization/detection_visualization_component.py` (ainda não commitado).

## Entradas e saída

- **Entradas, em ordem:**
  1. `ImageReference`: a imagem original;
  2. `DetectionReference`: o JSON com `cls`, `conf` e `box`.
- **Saída:** `[output_reference]`, um `ImageReference` recebido no construtor que aponta para a nova imagem anotada.

## `prepare()`: contrato aplicado em 17/11/2026

```python
def prepare(
    self, input_artifacts: list[ArtifactReference]
) -> tuple[ImageContent, DetectionContent]:
    # Validate count, order and types; raise ValueError otherwise.
    image_content = input_artifacts[0].materialize()
    detection_content = input_artifacts[1].materialize()
    return image_content, detection_content
```

Retorna os **conteúdos dos artefatos**, não os campos `.data`. A decisão foi do usuário, e a implementação foi aprovada em 17/11/2026.

## `execute()`

- Exige uma tupla `(ImageContent, DetectionContent)`; senão gera `TypeError`. Tupla incompleta, ordem invertida, `np.ndarray` puro e `list` pura também são rejeitados.
- Copia os pixels com `image_content.data.copy()`, então a imagem original não é alterada.
- Para cada `Detection`, desenha `cv2.rectangle` (verde, espessura 2) e `cv2.putText`.
  - O rótulo é `"{cls} {conf:.2f}"`.
  - Quando `conf is None`, o rótulo é só `cls` (ajuste aprovado e aplicado em 17/11/2026).
- Salva com `ImageContent(data=annotated).dematerialize(output_reference)` e retorna `[output_reference]`.

## Testes (verificados em 17/11/2026)

- **Unitários** (`tests/unit/components/detection_visualization/`, 7):
  - `prepare()` retorna conteúdos;
  - o pixel `(10, 10)` fica verde;
  - a imagem original é preservada;
  - zero detecções;
  - `prepare()` rejeita entradas inválidas;
  - `execute()` rejeita dados inválidos;
  - desenho de detecção sem confiança (17/11/2026).
- **Integração** (`tests/integration/components/detection_visualization/test_detection_pipeline.py`): `ObjectDetectionComponent(FakeDetector)` → JSON → visualizador. Não precisou mudar com a refatoração.
- **Fluxo real** YOLO11n ONNX → JSON → visualizador: 17 detecções, imagem conferida visualmente.

## Histórico

- A versão inicial retornava `tuple[np.ndarray, list[Detection]]` e passou nos 6 testes originais.
- Em 17/11/2026 foi refatorada para o contrato acima, e os testes foram adaptados para o novo contrato.

## Limitações e mudança proposta

- O rótulo pode ficar fora da imagem perto das bordas, e caixas sobrepostas não recebem tratamento especial.
- Detecções sem confiança (`conf: null`, vindas do [parser de texto](component-text-detection-parsing.md)) são desenhadas com a mesma cor. Visualmente, só o rótulo as diferencia.
