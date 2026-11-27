---
type: Plan
title: Roadmap da integração MIRAGE
description: Tarefas concluídas, pendentes e critérios de aceite.
tags:
- roadmap
- mirage
- planning
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:28:27-03:00"
evidence_basis: [approved, proposal]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d0fb7f2 + alterações não commitadas), inspecionado e testado em 17/11/2026
  title: Código, testes e execuções locais
- id: conversation
  resource: Relatos de desenvolvimento e decisões do usuário, 10–17/11/2026
  title: Evidências da conversa de desenvolvimento
---

# Objetivo final

Imagem + prompt → MIRAGE → resposta textual → JSON de detecções → imagem com bounding boxes.

- A primeira parte é a integração multimodal com resposta em texto.
- A segunda parte é a geração de detecções com coordenadas, que é **hipótese experimental**.

## Concluído e verificado

- [x] Artefatos de texto (7 testes).
- [x] Visualizador implementado e refatorado para `tuple[ImageContent, DetectionContent]`, com testes adaptados (17/11/2026).
- [x] Integração com `FakeDetector`; fluxo real YOLO → JSON → visualizador com 17 detecções (revalidado em 17/11/2026).
- [x] Pesquisa das capacidades reais do MIRAGE nas fontes oficiais (17/11/2026).
- [x] `VisualQuestionAnswerer` + `VisualQuestionAnsweringComponent`, experimental, com 10 testes (17/11/2026).
- [x] `TextDetectionParser` + `TextDetectionParsingComponent`; `Detection.conf` opcional; rótulo do visualizador sem confiança (17/11/2026).
- [x] Documentação sincronizada, `CLAUDE.md` e `handoff.md` (17/11/2026).
- [x] Documentação reorganizada no padrão OKF do `new-visio-research-models`, com validador local (18/11/2026; [plano](2026-11-18-plan-docs-restructure.md)).

## Pendente

- [ ] Reavaliar o formato de colchetes do treino ou a extração de JSON de texto, **somente** com base em respostas reais do MIRAGE.
- [x] Prova de conceito em `experiments/mirage/` presente e revisada (17/11/2026); dry run testado.
- [x] `run_poc.py` compatível com Python 3.10; o `run.json` registra dimensões, EXIF, revisão, parâmetros e associação imagem-resposta (17/11/2026).
- [x] Parser: P1–P3 corrigidos, com testes de regressão (17/11/2026).
- [x] Suíte: 218 passed com ONNX real; 22 passed no experimento (Python 3.10 e 3.12). *Depois do avaliador: 69 passed no experimento.*
- [ ] Commits, aguardando autorização (plano em [plano de commits](2026-11-17-plan-commits.md)).
- [x] Avaliador offline em `experiments/mirage/` (IoU, TP/FP/FN, precisão e revocação, no total e por classe), com 47 testes (17/11/2026).
- [ ] Preparar o conjunto de anotações humanas e o manifesto de predições para a execução real.
- [ ] Conseguir uma máquina com GPU NVIDIA e imagens com anotação humana.
- [ ] Executar o MIRAGE em uma máquina com GPU NVIDIA; guardar as respostas exatas.
- [ ] Medir a localização (IoU, precisão, revocação) contra anotações verdadeiras.
- [ ] Implementar o `MirageAnswerer` fora do processo, com mecanismo a definir conforme o ambiente da GPU.
- [ ] Se o MIRAGE não localizar bem, avaliar OWLv2 ou Grounding DINO como `ObjectDetector`.
- [ ] Atualizar os diagramas do ADR ([diagramas](../diagrams/index.md), antes em `docs/diagrams/`) e o ADR.
- [ ] Revisão e PR, só com autorização.

## Critérios de aceite

1. A arquitetura preserva as abstrações existentes.
2. Os prompts trafegam por `TextReference`/`TextContent`.
3. A saída tem formato validado e é rastreável por artefatos.
4. O visualizador continua independente do modelo de origem.
5. Testes e lint passam; as limitações do modelo estão documentadas.
6. Nenhuma coordenada, classe ou confiança é inventada.
7. A documentação está atualizada a cada etapa (regra de 17/11/2026).
