---
type: Reference
title: Padrão de componentes
description: Contratos, fronteiras de responsabilidade e componentes atuais.
tags:
- components
- interfaces
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

# Abstração

`Component` impõe duas fases:

1. `prepare(list[ArtifactReference]) -> object`: valida e materializa as entradas e devolve os **conteúdos** dos artefatos (convenção aprovada).
2. `execute(prepared_data: object) -> list[ArtifactReference]`: processa, salva os resultados e retorna as referências.

## Componentes e interfaces

| Item | Papel | Estado (17/11/2026) |
|---|---|---|
| `ObjectDetector` | Interface de detecção em imagem | Verificado |
| `YoloDetector` | Detecção YOLO via ONNX (saída crua `[1, 4+C, N]`) | Verificado, inclusive com modelo real |
| `ObjectDetectionComponent` | Imagem → detector → JSON | Verificado; `prepare()` ainda retorna `np.ndarray` |
| `DetectionVisualizationComponent` | Imagem + JSON → imagem anotada | Verificado; `prepare()` retorna conteúdos |
| `VisualQuestionAnswerer` | Interface imagem + pergunta → texto | Verificado |
| `VisualQuestionAnsweringComponent` | Imagem + prompt → resposta textual | Verificado com simulador; **experimental** |
| `TextDetectionParser` | JSON textual → `list[Detection]` em pixels, com `conf=None` | Verificado com respostas simuladas |
| `TextDetectionParsingComponent` | Imagem + resposta textual → JSON de detecções | Verificado com respostas simuladas; **experimental**. Veja [interpretação](component-text-detection-parsing.md) |
| `ClassCountingComponent` | JSON de detecções → contagem por classe (modo genérico ou restrito a um domínio) | Verificado com detecções simuladas e com JSONs reais já salvos (23/11/2026). Veja [contagem](component-class-counting.md) |
| `MirageAnswerer` | Adaptador real do MIRAGE | Não iniciado |

## Separação de responsabilidades

- Os componentes não conhecem detalhes do modelo. O visualizador não conhece YOLO nem MIRAGE.
- O VQA não interpreta a resposta.
- Transformar texto em detecções é tarefa do `TextDetectionParsingComponent`. Ele não conhece o MIRAGE nem o visualizador.
- O visualizador consome qualquer `DetectionReference` que siga o esquema de `Detection`.
- O `ClassCountingComponent` também consome qualquer `DetectionReference`: conta as predições como recebidas, sem filtrar confiança nem normalizar nomes, e grava um `ClassCountReference`.
