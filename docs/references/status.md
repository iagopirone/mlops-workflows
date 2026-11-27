---
type: Reference
title: Inventário de implementação e pendências
description: Distingue o que foi verificado no código, o que foi aprovado, o que é hipótese e o que está planejado.
tags:
- status
- tests
- development
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:28:27-03:00"
evidence_basis: [verified, approved, hypothesis]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d0fb7f2 + alterações não commitadas), inspecionado e testado em 17/11/2026
  title: Código, testes e execuções locais
- id: conversation
  resource: Relatos de desenvolvimento e decisões do usuário, 10–17/11/2026
  title: Evidências da conversa de desenvolvimento
---

# Matriz de estado (atualizada em 26/11/2026)

Legenda: **Verificado** = inspecionado no código e/ou executado em 17/11/2026 · **Aprovado** = decisão do usuário ainda sem código · **Hipótese** = não comprovada · **Planejado** = proposta.

| Item | Estado | Evidência |
|---|---|---|
| `ArtifactReference` / `ArtifactContent` | Verificado | `artifacts/interface.py`, `artifacts/content.py` |
| Artefatos de imagem e vídeo | Verificado | Testes em `tests/unit/artifacts/{image,video}/` e `tests/integration/artifacts/` |
| Artefatos de texto (`TextReference`/`TextContent`) | Verificado (não commitado) | 7 testes passando |
| Artefatos de detecção (`Detection`, `DetectionContent`, `DetectionReference`) | Verificado (commit `b1b3c4f`; `conf` alterado e não commitado) | `Detection` **continua** em `detection.py`; mudá-la para `detection_content.py` foi discutido e **não aplicado** |
| `ObjectDetector`, `YoloDetector`, `ObjectDetectionComponent` | Verificado (commit `c629973`) | `prepare()` ainda retorna `np.ndarray` (fora do escopo da refatoração aprovada) |
| `DetectionVisualizationComponent` com `prepare() -> tuple[ImageContent, DetectionContent]` | Verificado (não commitado) | Refatoração aplicada e aprovada em 17/11/2026; 6 unitários + 1 de integração |
| Fluxo real YOLO → JSON → visualização | Verificado em 17/11/2026 | 17 detecções; imagem anotada conferida visualmente |
| `VisualQuestionAnswerer` + `VisualQuestionAnsweringComponent` | Verificado (não commitado), **experimental** | 9 unitários + 1 de integração com `FakeAnswerer` |
| Suíte completa | Verificado em 18/11/2026, após a reorganização da documentação | **253 passed** (ONNX real); 252 passed + 1 skipped (sem ONNX), depois dos links relativos (ADR 008). Antes disso, em 18/11: 250 / 249 + 1 skipped. Os testes do validador são 35. Em 17/11/2026, depois de P1–P3: 218; antes: 171, confirmado também pelo usuário |
| `ruff check .` | Verificado | All checks passed |
| `ruff format --check .` | Verificado | Passa após a correção do exemplo na página do visualizador, hoje [/references/component-detection-visualization.md](component-detection-visualization.md) (17/11/2026) |
| Documentação contínua + `CLAUDE.md` + `handoff.md` | Verificado | Criados em 17/11/2026 |
| Documentação reorganizada em `docs/` no padrão OKF do `new-visio-research-models` | Verificado em 18/11/2026 (não commitado) | Decisões D1–D6 aprovadas; [ADR 007](../adr/007-okf-documentation-structure.md), [plano](../plans/2026-11-18-plan-docs-restructure.md) |
| Validador `scripts/okf_lint.py` (só biblioteca padrão) | Verificado em 18/11/2026 (não commitado) | `OK: no problems found.` no bundle real; 35 testes em `tests/unit/scripts/test_okf_lint.py`. Não é parser YAML completo; veja [diretrizes](okf-guidelines.md#validador-local) |
| `TextDetectionParser` + `TextDetectionParsingComponent` | Verificado com respostas simuladas (não commitado), **experimental** | 55 + 7 unitários + 2 de integração; veja [interpretação](component-text-detection-parsing.md) |
| `Detection.conf: float \| None` (obrigatório, `null` no JSON) | Verificado, aprovado em 17/11/2026 | +4 testes; YOLO revalidado com 17 detecções idênticas |
| Rótulo do visualizador sem confiança | Verificado, aprovado em 17/11/2026 | +1 teste |
| Prova de conceito do MIRAGE em `experiments/mirage/` | Arquivos presentes (não versionados; criados fora desta sessão), revisados e **corrigidos** em 17/11/2026 | 22 passed no Python 3.10.21 e no 3.12.14; dry run real no 3.10 OK. **Nunca executada contra o MIRAGE real.** Veja [MIRAGE](mirage.md) |
| Avaliador offline (`experiments/mirage/evaluate_detections.py`) | Verificado com dados sintéticos (não commitado), **experimental** | 47 passed no 3.10.21 e no 3.12.14; nunca usado com respostas reais. Veja [avaliador](mirage-evaluation.md) |
| Revisão do parser | Concluída em 17/11/2026 | Conforme as decisões. **P1–P3 corrigidos** (chaves duplicadas, `cls` com espaços, `bool`); P4–P7 só documentados. Veja [interpretação](component-text-detection-parsing.md#correções-p1p3-17112026-aprovadas-pelo-usuário) |
| PR #3 (`feature/implementar-componentes` → `rc`) | **Mesclado** (verificado com `gh` em 27/11/2026) | `origin/rc` em `f50f2f8`, mesma árvore de `d0fb7f2` |
| Divisão do PR #4 em 7 PRs menores | **Publicada em 27/11/2026**: PRs empilhados #5–#11 abertos (nenhum mesclado); PR #4 fechado sem merge, branch preservada; VISRES-337 comentada com o link do #8 | Pedido do líder; bases, commits e árvore conferidos antes do fechamento ([log](../log.md#2026-11-27)) |
| Adaptador real `MirageAnswerer` | Não iniciado | Mecanismo fora do processo, a definir. **O VQA não está integrado ao MIRAGE**; o pipeline 2 lê a resposta salva pelo `run_poc.py` como `TextReference` |
| MIRAGE real executado | **Não** | Nunca rodou neste projeto |
| Pipelines E2E, terceira rodada (E4, relatório, correções) | **Implementado e testado com dados sintéticos** (18/11/2026); nenhum modelo executado | Adaptador do formato do treino, ferramenta do relatório com verificações de inferência real, VRAM amostrada pelo `run_poc.py`, exclusões e substituições do BCCD, proteção `E2E_ALLOW_REAL_MODELS`. Plano de execução real e decisões R1–R6 na seção 12 do [plano](../plans/2026-11-18-plan-real-models-e2e.md); **pausado** pela prioridade Florence-2 |
| Origem do YOLO `best.onnx` | Investigada em 18/11/2026 (duas rodadas, só leitura) | É o `models/v0` do **commit inicial `b37eca2`** do kit (upstream `aqilputi/mlops-pipeline-challenge`, um commit só). O autor declara treino só no seed (91 imagens, 70/15/15). Nenhuma das 20 imagens avaliadas está no seed. **Risco de vazamento considerado baixo; ausência não comprovada.** Detalhes no [piloto](../reports/2026-11-18-qwen3vl-bccd-pilot.md) |
| Avaliação quantitativa do Qwen3-VL no BCCD | **Concluída em 20 imagens** (18/11/2026; exploratória). Qwen A: P 0,31 / R 0,29 (WBC R 0,95; plaquetas 0); YOLO: P 0,76 / R 0,73. Leitura E8: inconclusivo. 0 falhas de infraestrutura, 1/80 saída inválida; ~111 s/imagem (4 prompts), ≤ 2,90 GiB | [Plano](../plans/2026-11-18-plan-qwen3vl-bccd-evaluation.md), [ADR 010](../adr/010-optimal-bipartite-matching.md), [piloto](../reports/2026-11-18-qwen3vl-bccd-pilot.md), [avaliação das 20 imagens](../reports/2026-11-18-qwen3vl-bccd-evaluation.md) |
| Relatório resumido para a liderança | Concluído em 19/11/2026 (só documentação; nenhuma execução) | [Resumo](../reports/2026-11-19-local-multimodal-detection-summary.md) |
| Versionamento da branch `feature/integracao-mirage` | Concluído em 19/11/2026 (autorizado): 12 commits, push e PR empilhado sobre `feature/implementar-componentes` | [Plano de commits](../plans/2026-11-17-plan-commits.md) |
| Qwen3-VL-2B-Instruct Q4_K_M em CPU (llama.cpp) | **Executado de verdade** em 18/11/2026 (experimento isolado, com teto de memória) | 2,95 GiB de pico (cgroup), sem swap no processo; ~12 s por resposta curta. Coordenadas relativas 0–1000 verificadas; localiza o glóbulo branco, mas troca rótulos; respostas longas degeneram (JSON cortado). **Com 1024 tokens (testado em 18/11/2026):** aviso some, pico do cgroup 3,21 GiB, sem localização melhor observável numa imagem. **Com `official_sampling` (18/11/2026):** os prompts "red blood cell" e combinado passaram a dar JSON válido, completo e sem duplicatas exatas, sem custo extra de memória; plaquetas ainda não localizadas; uma semente só. `combined` não executada. **Os 4 prompts com `official_sampling`:** "white" correto; "platelet" respondeu *"There are none."* (inválido e falso). [Plano de avaliação no BCCD](../plans/2026-11-18-plan-qwen3vl-bccd-evaluation.md) aguarda aprovação. [Relatório](../reports/2026-11-18-qwen3vl-cpu-poc.md), [referência](qwen3vl.md) |
| Florence-2-base-ft em CPU | **Executado de verdade** em 18/11/2026 (experimento isolado) | 1,7 GiB de pico, 8 a 12 s por tarefa (`use_cache=False`); localiza o glóbulo branco, mas não discrimina as classes. [Relatório](../reports/2026-11-18-florence2-cpu-poc.md), [referência](florence2.md) |
| Cópia persistente da documentação anterior | Verificado em 18/11/2026 | `/home/visioer/Projetos/backups/mlops-workflows-docs-before-okf-2026-11-18.tar.gz` + SHA-256; veja [proveniência](provenance.md) |
| Revisão do `evidence_basis` e navegação dos links no GitHub | Concluído em 18/11/2026 | `evidence_basis` conferido e corrigido ([proveniência](provenance.md)); links relativos aprovados e aplicados ([ADR 008](../adr/008-relative-internal-links.md)) |
| Pipelines de ponta a ponta com modelos reais (YOLO e MIRAGE) + relatório como artefato | **Preparação local implementada e testada com dados sintéticos** (18/11/2026); nenhum modelo executado para resultados; E4 e E8 em proposta | E1–E7 aprovadas; [plano](../plans/2026-11-18-plan-real-models-e2e.md), [ADR 009](../adr/009-execution-report-artifact.md), [relatório e drivers](artifact-execution-report.md). Validação do nome do checkpoint no `run_poc.py` (E3) implementada |
| MIRAGE produzir bounding boxes confiáveis | **Hipótese experimental** | Sem capacidade documentada; veja [MIRAGE](mirage.md) |
| `ClassCountingComponent` + artefato `ClassCount` (VISRES-337) | **Verificado e aprovado** em 23/11/2026; commit autorizado (VISRES-337) | Regras da tarefa e decisões do [ADR 011](../adr/011-class-counting-component.md) aprovadas pelo usuário depois da revisão do código. Limitações conhecidas registradas, sem correção: chave repetida no JSON aceita na leitura; `ClassCount` mutável. 48 testes novos (24 + 22 + 2); suíte principal 357 passed + 1 skipped; experimentos 332 + 1 skipped. Exemplo `examples/demo_class_counting.py` executado só com `--detections` sobre JSONs já salvos (YOLO e Qwen3-VL); o caminho `--model` não foi executado. Veja [contagem](component-class-counting.md) |
| `Step` e `Pipeline` em `mlops_workflows/pipeline/` (VISRES-305) | **Verificado** em 26/11/2026; aprovado e versionado em 27/11/2026 no PR [#12](https://github.com/iagopirone/mlops-workflows/pull/12) (base #8; 394 passed + 1 skipped na nova base) | Imutáveis na estrutura (rasa), tipos de `component` e dos artefatos verificados, `depends_on` por identificador, finalização em campo próprio, validação na criação (IDs duplicados ou vazios, dependência externa, ciclo, autodependência, dependência repetida, nenhuma etapa de processamento, dependência da finalização, etapa sem caminho até a finalização). Decisões 1–11 aprovadas em 26/11/2026 ([ADR 012](../adr/012-pipeline-structure-validation.md), aceito); arquitetura aprovada pelo usuário em 27/11/2026. 37 testes novos; suíte 394 passed + 1 skipped (ONNX não repetido após o ajuste final); experimentos 332 + 1 skipped. Pipeline de exemplo só estrutural, num teste. Veja [pipeline](pipeline.md) |
| Orquestrador (`WorkflowRunner`, `StepSelector` etc.) | Só esqueletos | `domain.py` com `NotImplementedError`; `Step` e `Pipeline` agora vêm de `mlops_workflows/pipeline/` |

## Resultados de testes por arquivo (17/11/2026; validador acrescentado em 18/11/2026)

| Arquivo | Testes |
|---|---:|
| `tests/unit/artifacts/image/test_image_content.py` / `test_image_reference.py` | 9 / 7 |
| `tests/unit/artifacts/video/test_video_content.py` / `test_video_reference.py` | 2 / 1 |
| `tests/unit/artifacts/text/test_text_content.py` / `test_text_reference.py` | 2 / 5 |
| `tests/unit/artifacts/detection/test_detection.py` / `test_detection_content.py` / `test_detection_reference.py` | 3 / 17 / 7 |
| `tests/unit/artifacts/report/test_execution_report.py` / `_content.py` / `_reference.py` | 34 / 1 / 5 |
| `tests/unit/components/object_detection/detectors/test_yolo_detector.py` | 32 |
| `tests/unit/components/object_detection/test_object_detection_component.py` | 6 |
| `tests/unit/components/object_detection/test_object_detector.py` | 1 |
| `tests/unit/components/detection_visualization/test_detection_visualization_component.py` | 7 |
| `tests/unit/components/visual_question_answering/test_visual_question_answerer.py` | 1 |
| `tests/unit/components/visual_question_answering/test_visual_question_answering_component.py` | 8 |
| `tests/unit/components/text_detection_parsing/test_text_detection_parser.py` | 99 |
| `tests/unit/artifacts/class_count/test_class_count.py` / `_content.py` / `_reference.py` (23/11/2026) | 15 / 3 / 6 |
| `tests/unit/components/class_counting/test_class_counting_component.py` (23/11/2026) | 22 |
| `tests/integration/components/class_counting/test_class_counting_pipeline.py` (23/11/2026) | 2 |
| `tests/unit/components/text_detection_parsing/test_text_detection_parsing_component.py` | 10 |
| `tests/integration/artifacts/image/test_image_content.py` / `test_image_reference.py` | 3 / 6 |
| `tests/integration/artifacts/video/test_video_content.py` / `test_video_reference.py` | 1 / 3 |
| `tests/integration/components/object_detection/test_object_detection_component.py` | 1 (pulado sem ONNX) |
| `tests/integration/components/detection_visualization/test_detection_pipeline.py` | 1 |
| `tests/integration/components/visual_question_answering/test_visual_question_answering_pipeline.py` | 1 |
| `tests/integration/components/text_detection_parsing/test_text_detection_pipeline.py` | 2 |
| `tests/unit/scripts/test_okf_lint.py` (18/11/2026) | 35 |
| **Total da suíte principal** | **278** |
| `experiments/mirage/tests/test_run_poc.py` (fora da suíte principal) | 34 |
| `experiments/mirage/tests/test_evaluate_detections.py` (fora da suíte principal) | 47 |
| `tests/unit/artifacts/report/test_execution_report.py` (18/11/2026) | 25 |
| `experiments/e2e/tests/` (fora da suíte principal; 7 + 15 + 14) | 36 |

## Histórico

- O registro anterior (16/11/2026) apontava "92 passed" e marcava como "não confirmadas" a refatoração do visualizador e a mudança de lugar de `Detection`.
- Em 17/11/2026:
  - a refatoração do visualizador foi aplicada e verificada;
  - a mudança de lugar de `Detection` continua não aplicada;
  - a suíte cresceu para 102 testes com o componente VQA, depois para 171 com o parser de texto, e para 218 com as correções P1–P3.
- Em 18/11/2026, a documentação foi reorganizada e o validador trouxe +32 testes: 250.

Detalhes no [log](../log.md).
