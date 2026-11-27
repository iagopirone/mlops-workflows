---
type: Reference
title: YoloDetector ONNX
description: Inferência e pós-processamento genérico de modelos YOLO em imagem.
tags:
- yolo
- onnx
- inference
- detector
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:28:27-03:00"
evidence_basis: [verified]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d0fb7f2 + alterações não commitadas), conferido em 18/11/2026
  title: Código local
- id: repo-snapshot
  resource: https://github.com/iagopirone/mlops-workflows/tree/666fbb5a210a3cc4143e745bce888eebfe8dc2b2
  title: Snapshot da branch feature/implementar-componentes em 09/11/2026 (commit
    666fbb5)
- id: conversation
  resource: Relatos de desenvolvimento e saídas de terminal fornecidos pelo usuário
    nesta conversa, 10–16/11/2026
  title: Evidências da conversa de desenvolvimento
---

# Objetivo

O usuário relatou a refatoração de um detector inicialmente restrito a RBC/WBC/Platelets para um `YoloDetector` genérico, com a interface abstrata `ObjectDetector`.

> **Conferido no código em 18/11/2026** (`components/object_detection/detectors/yolo_detector.py`): configuração, os passos 1–9 abaixo (validação da imagem, *letterbox*, BGR→RGB, `/255`, HWC→CHW, `CPUExecutionProvider`, saída `[1, 4+C, N]`, limiar, remoção do padding e recorte, NMS por classe, ordem por confiança) e a leitura dos nomes de classe dos metadados ONNX. Os metadados do `best.onnx` local também foram lidos: *Ultralytics YOLO11n*, `imgsz` 640×640, classes `RBC`, `WBC`, `Platelets`, entrada `[1, 3, 640, 640]` e saída `[1, 7, 8400]`. A página nasceu de um relato (`evidence_basis` antigo: "relato da conversa").

## Configuração

`YoloDetectorConfig` (Pydantic):

- `model_path`: caminho do modelo `.onnx`.
- `class_names`: nomes opcionais; alternativa aos metadados ONNX.
- `confidence_threshold`: valor padrão 0,25.
- `iou_threshold`: valor padrão 0,5.

## Pipeline de inferência

1. Validar imagem de entrada (NumPy, BGR, 3 canais e formato correto).
2. Aplicar resize com preservação de proporção e padding (*letterbox*), conforme input ONNX.
3. Converter BGR→RGB, normalizar, reorganizar HWC→CHW e criar batch.
4. Executar `onnxruntime.InferenceSession` com `CPUExecutionProvider`.
5. Interpretar a saída crua conhecida como `[1, 4+C, N]` (família YOLOv8/YOLO11 exportada sem pós-processamento embutido).
6. Selecionar classes e limiar de confiança; rejeitar predições inválidas.
7. Converter caixas do modelo às coordenadas da imagem original, remover padding e limitar aos limites da imagem.
8. Aplicar NMS por classe para reduzir duplicações.
9. Retornar `list[Detection]` com classe, confiança e caixa.

## Suporte / limites

- A generalidade **não** implica compatibilidade com qualquer arquivo ONNX ou toda versão de YOLO; verificar entradas/saídas reais.
- O caso de referência é o modelo `best.onnx` de células sanguíneas (RBC, WBC, Platelets), YOLO11n, entrada 640 e ONNX Runtime CPU.
- Pesos ONNX não foram incorporados neste bundle. Não confundir os resultados da demo com benchmark de qualidade do detector.

Veja [detecção com componente](component-object-detection.md) e [testes](test-suite.md).
