---
type: Report
title: Demo YOLO → visualizador (16/11/2026, revalidada em 17/11/2026)
description: Execução relatada do demo YOLO e do visualizador desacoplado.
tags:
- demo
- end-to-end
- yolo
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:28:27-03:00"
evidence_basis: [verified]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d0fb7f2 + alterações não commitadas), inspecionado e testado em 17/11/2026
  title: Código, testes e execuções locais
- id: repo-snapshot
  resource: https://github.com/iagopirone/mlops-workflows/tree/666fbb5a210a3cc4143e745bce888eebfe8dc2b2
  title: Snapshot da branch feature/implementar-componentes em 09/11/2026 (commit
    666fbb5)
- id: conversation
  resource: Relatos de desenvolvimento e saídas de terminal fornecidos pelo usuário
    nesta conversa, 10–16/11/2026
  title: Evidências da conversa de desenvolvimento
---

# Execução feita pelo usuário em 16/11/2026

> **Origem desta seção: relato do usuário** (comandos e console compartilhados na conversa). Não foi reexecutada nesta forma. O que foi **verificado** é a revalidação de 17/11/2026, na seção seguinte, que reproduziu as 17 detecções.

```bash
uv run python -m examples.demo_detection \
  --model /home/visioer/Downloads/best.onnx \
  --image /home/visioer/Downloads/BloodImage_00236.jpg \
  --output-dir outputs
```

Console relatado:

```text
Detections: 17
JSON: outputs/detections.json
Annotated image: outputs/annotated.png
```

Em seguida, o usuário instanciou manualmente `ImageReference`, `DetectionReference` e `DetectionVisualizationComponent`, e executou:

```python
prepared_data = component.prepare([image_ref, detection_ref])
result = component.execute(prepared_data)
```

Resultado:

```text
Detections: 17
Annotated image: outputs/annotated_component.png
```

O usuário abriu a imagem e compartilhou a visualização anotada.

## Revalidação em 17/11/2026 (após a refatoração do visualizador)

- Mesmo modelo e mesma imagem, executados em script com `ObjectDetectionComponent` e o `DetectionVisualizationComponent` refatorado, que agora recebe `ImageContent` e `DetectionContent`.
- Resultado: **17 detecções**, o mesmo número de antes.
- A imagem anotada foi inspecionada visualmente: caixas e rótulos RBC, WBC e Platelets corretos.
- A saída foi gravada fora do repositório, em um diretório temporário.

## O que foi demonstrado

- O detector exporta dados estruturados consumíveis por outro componente.
- A visualização não exige executar novamente o detector: pode consumir o JSON já persistido.
- Foi produzido novo arquivo de imagem sem sobrescrever a imagem original.

## O que **não** demonstra

- O MIRAGE foi executado (não foi).
- A qualidade estatística do detector foi medida (não foi; a demonstração mostra apenas inferência e anotação).
- ~~A versão refatorada do `prepare()` foi testada~~: **resolvido em 17/11/2026**, testada e revalidada.
- Que o componente VQA funcione com um modelo real (até agora, só com simulador).

## Caminhos

Os caminhos `/home/visioer/...` são de uma estação de desenvolvimento específica e não são portáveis. Substituí-los pelos caminhos locais do usuário.
