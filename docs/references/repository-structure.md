---
type: Reference
title: Estrutura do repositório
description: Mapa real dos diretórios e módulos no checkout local.
tags:
- repository
- files
- structure
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

# Árvore real (17/11/2026; `docs/`, `scripts/`, `experiments/e2e/` e `artifacts/report/` atualizados em 18/11/2026)

`(nc)` = ainda não commitado.

```text
mlops-workflows/
├── CLAUDE.md                          # instruções para agentes (nc)
├── mlops_workflows/
│   ├── domain.py                      # Event, Step, Pipeline + esqueletos do orquestrador
│   ├── artifacts/
│   │   ├── interface.py               # ArtifactReference
│   │   ├── content.py                 # ArtifactContent
│   │   ├── image/                     # ImageReference / ImageContent
│   │   ├── video/                     # VideoReference / VideoContent
│   │   ├── detection/                 # detection.py, detection_content.py, detection_reference.py
│   │   ├── text/                      # TextReference / TextContent (nc)
│   │   └── report/                    # ExecutionReport + Reference/Content (nc, 18/11/2026)
│   └── components/
│       ├── interface.py               # Component
│       ├── object_detection/
│       │   ├── object_detector.py     # ObjectDetector
│       │   ├── object_detection_component.py
│       │   └── detectors/yolo_detector.py
│       ├── detection_visualization/   # DetectionVisualizationComponent (nc)
│       ├── visual_question_answering/ # VisualQuestionAnswerer + component (nc)
│       └── text_detection_parsing/    # TextDetectionParser + component (nc)
├── examples/demo_detection.py
├── experiments/mirage/              # prova de conceito isolada: run_poc.py, evaluate_detections.py, prompts/, tests/, ruff.toml, README (nc)
├── experiments/e2e/                 # drivers, anotações BCCD, formato do treino, avaliação, build_report, tests/ (nc, 18/11/2026)
├── experiments/qwen3vl/             # Qwen3-VL-2B GGUF com llama.cpp: run_qwen.py (stdlib, teto de memória), render.py, adaptador, tests/ (nc, 18/11/2026)
├── experiments/florence2/           # Florence-2 isolado: venv próprio, run_florence.py, render.py, adaptador, tests/ (nc, 18/11/2026)
├── tests/
│   ├── unit/artifacts/{image,video,text,detection}/
│   ├── unit/components/{object_detection,detection_visualization,visual_question_answering,text_detection_parsing}/
│   ├── unit/scripts/test_okf_lint.py  # testes do validador da documentação (nc)
│   ├── integration/artifacts/
│   └── integration/components/{object_detection,detection_visualization,visual_question_answering,text_detection_parsing}/
├── scripts/okf_lint.py                # validador do bundle docs/, só biblioteca padrão (nc)
├── docs/                              # bundle OKF (reorganizado em 18/11/2026; nc)
│   ├── index.md, log.md, CLAUDE.md, handoff.md
│   ├── playbooks/, references/, diagrams/   # documentos vivos
│   └── adr/, plans/, reports/               # documentos temporais
├── outputs/                           # saídas locais (ignorado pelo Git)
├── .pre-commit-config.yaml, pyproject.toml, uv.lock, .python-version (3.12)
```

## Planejado, ainda não existe


## Observações

- Os testes não têm `__init__.py`. O pytest usa `--import-mode=importlib`, o que permite arquivos com o mesmo nome em `unit/` e `integration/`.
- Os arquivos antigos `tests/unit/artifacts/test_{image,video}.py` foram movidos para subpastas. A remoção aparece como não commitada.
- Os modelos `.onnx` e as imagens de teste ficam fora do repositório, em caminhos locais.
