---
type: Reference
title: SOLID e injeção de dependências
description: Como os componentes ficam desacoplados das implementações de modelos.
tags:
- solid
- dip
- di
- design
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

# Objetivo

Os componentes recebem o mecanismo de inferência pelo construtor e dependem de uma **abstração**, não de uma implementação concreta.

```python
detection = ObjectDetectionComponent(
    detector=YoloDetector(config),
    output_reference=detection_reference,
)
vqa = VisualQuestionAnsweringComponent(
    answerer=FakeAnswerer(),
    output_reference=answer_reference,
)
```

## Princípios aplicados

- **DI (injeção de dependência):** `detector` e `answerer` vêm de fora; o componente não os constrói.
- **DIP (inversão de dependência):** os componentes dependem de `ObjectDetector` e `VisualQuestionAnswerer`, não de YOLO ou MIRAGE.
- **SRP (responsabilidade única), cada parte faz uma coisa:**
  - o modelo infere;
  - o componente coordena os artefatos;
  - os `Content` salvam os dados;
  - o visualizador desenha.
  - O parser só interpreta texto.
- **OCP (aberto para extensão):** um detector novo implementa `detect()`, e um modelo de VQA novo implementa `answer()`, sem mudar os componentes.
- **LSP (substituição):** as implementações precisam respeitar o formato e o significado das saídas. Exemplo: `Detection.box` em pixels `[x1, y1, x2, y2]`.
- **ISP (interfaces pequenas):** as interfaces têm um método só.
- **KISS/YAGNI:**
  - não há sistema de plugins;
  - o `TextDetectionParser` é uma classe concreta injetada, sem ABC, porque só existe uma implementação.

## Testes com simuladores

| Simulador | Onde | Uso |
|---|---|---|
| `FakeDetector` | Testes de `ObjectDetectionComponent` e do fluxo com o visualizador | Detecções fixas, sem ONNX |
| `FakeAnswerer` | Testes do VQA | Resposta fixa ou derivada da entrada, sem MIRAGE |
| `MutatingAnswerer` | Teste do VQA | Comprova que o componente protege a imagem original |
| `FailingAnswerer` | Teste do VQA | Comprova que nada é salvo quando a inferência falha |

## MIRAGE

- O MIRAGE entra como implementação de `VisualQuestionAnswerer` (`MirageAnswerer`, ainda não criado), porque recebe imagem + prompt e devolve texto.
- Ele **não** implementa `ObjectDetector`: não há caixas documentadas nem confiança.
- Como as dependências dele são incompatíveis com o ambiente principal, o adaptador vai chamá-lo **fora do processo**.

Veja [MIRAGE](mirage.md).
