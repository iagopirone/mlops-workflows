---
type: Reference
title: Relatório de execução e drivers de ponta a ponta
description: ExecutionReport (artefato tipado com hashes e verificações de inferência real), drivers dos pipelines YOLO e MIRAGE, adaptador do formato do treino, conversor BCCD, avaliação e ferramenta que monta o relatório.
tags:
- artifacts
- report
- e2e
- evaluation
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T14:09:16-03:00"
evidence_basis: [verified, approved]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage, código e testes de 18/11/2026
  title: Código local
---

# Situação

**Implementado e testado em 18/11/2026, só com dados sintéticos. Não commitado.** Nenhum modelo foi executado para produzir resultados: o MIRAGE nunca rodou, e o relatório real ainda não existe. Decisões: [ADR 009](../adr/009-execution-report-artifact.md) e [plano](../plans/2026-11-18-plan-real-models-e2e.md).

## Artefato `ExecutionReport` (`mlops_workflows/artifacts/report/`)

| Classe | Papel |
|---|---|
| `ExecutionReportReference` | `materialize()` lê o JSON e revalida tudo; arquivo ausente → `FileNotFoundError`; conteúdo inválido → `ValidationError` |
| `ExecutionReportContent` | `data: ExecutionReport`; `dematerialize(reference)` grava JSON UTF-8 indentado e devolve o local |
| `ExecutionReport` | `run_id`, `created_at` (com fuso), `environment`, `inputs` (manifesto, anotações, seleção, prompts), `criteria` (E8, pré-registrados), `models` (≥ 1), `pipelines`, `evaluations`, `deviations` |
| `ModelIdentity` | `key`, `kind` (`onnx_object_detector` ou `mirage_official`; não há tipo simulado), `name`, `source`, `revision`, `details` |
| `PipelineRun` | `pipeline`, `experiment`, `model_key`, `image_id`, `status`, **`class_source`** (`model` ou `prompt`), `error`, `detection_count`, `duration_seconds`, `inputs`, `outputs`, `evidence`, **`inference_checks`** |
| `ArtifactRecord` | `kind` (`image`, `text`, `detection`, `file`), `name`, `location`, **`sha256`** (64 hex, obrigatório) |
| `InferenceCheck` | `name`, `passed`, `detail`: uma evidência de inferência real |
| `Evaluation` | `pipeline`, `experiment`, `ground_truth`, `iou_threshold`, `coordinate_format`, `class_source`, `report` (o JSON completo do avaliador, com hash), `summary`, `per_class` |

**Três categorias de problema, nunca misturadas:**

| Status | Significa | Exemplos |
|---|---|---|
| `infrastructure_failure` | O modelo não rodou, a saída não pôde ser lida **ou faltou evidência de inferência real** | `returncode ≠ 0`, sem `Text Output:`, `run.json` ausente, revisão do código diferente, VRAM de pico abaixo do mínimo, exceção do ONNX |
| `invalid_response` | O modelo respondeu (inferência comprovada), mas a resposta não é uma lista de detecções válida | texto livre, `format_mismatch` no formato do treino, `conf` escrito pelo modelo |
| `succeeded` | Detecções produzidas (inclusive `[]`) | A **correção** (TP/FP/FN, IoU) é medida na avaliação |

**Um identificador de modelo não prova inferência:** `succeeded` e `invalid_response` só são aceitos pelo esquema com `inference_checks` presentes e **todas** aprovadas.

**Recuperar:** `ExecutionReportReference(name=..., location=".../report.json").materialize().data`. As imagens anotadas são os `outputs` de `kind="image"`, carregadas com `ImageReference(name, location).materialize()`. `verify_report()` recarrega o relatório e confere o SHA-256 de **todos** os arquivos registrados.

## Verificações de inferência real

**MIRAGE** (`mirage_inference_checks`, a partir do `run.json` e do `stdout.txt` de cada execução):

| Verificação | Passa quando |
|---|---|
| `process_completed` | `returncode == 0` |
| `official_output_markers` | O `stdout` tem `---Output---` e `Text Output:` (formato do `demo.py` oficial) |
| `official_code_revision` | Revisão do código oficial igual à esperada (hash completo) e `dirty == false` |
| `checkpoint` | Último segmento do caminho resolvido igual ao nome esperado e `allow_remote_model == false` |
| `prompt` | Prompt do `run.json` igual ao arquivo do experimento |
| `offline` | `HF_HUB_OFFLINE=1` registrado |
| `gpu_present` | `nvidia-smi` descreveu uma GPU |
| `gpu_memory_loaded` | Pico de VRAM **amostrado durante a execução** ≥ mínimo do manifesto (proposta: 16 000 MiB; os pesos têm cerca de 17 570 MiB) |

Desde 18/11/2026, o `run_poc.py` amostra a VRAM a cada 500 ms com `nvidia-smi` durante o `demo.py`, grava `gpu-memory.csv` e registra `gpu_memory_peak_mib` e `hf_hub_offline` no `run.json`.

**YOLO** (`yolo_inference_checks`, na ferramenta do relatório):

| Verificação | Passa quando |
|---|---|
| `detector_class` | O detector é `YoloDetector` |
| `model_file` | O caminho do detector é o do manifesto; o SHA-256 vai no detalhe e na identidade |
| `onnxruntime_session` | Há provedores na sessão |
| `class_names` | As classes do modelo são exatamente `RBC`, `WBC`, `Platelets` (`check_class_names`, agora usado) |

## Drivers (`experiments/e2e/pipelines.py`)

- **`run_yolo_pipeline(..., inference_checks)`:** `ObjectDetectionComponent` → `detections.json` → `DetectionVisualizationComponent` → `annotated.png`. Qualquer exceção vira `infrastructure_failure`.
- **`run_mirage_pipeline(run_dir, image, ..., prompt, expected, convert=None)`:**
  1. Verifica se a execução pertence à imagem (uma imagem, mesmo nome, mesmas dimensões). Se não pertencer, levanta `ValueError`: é erro de preparação.
  2. Calcula as verificações de inferência real.
  3. Processo com erro, sem `answer.txt` ou com verificação reprovada vira `infrastructure_failure`.
  4. O `answer.txt` original é usado como **`TextReference`**, sem ser alterado.
  5. Com `convert` (formato do treino), o texto convertido é gravado **à parte** (`answer-converted.json`, outra `TextReference`) e `class_source = "prompt"`.
  6. `TextDetectionParsingComponent` → `DetectionReference`. Se o parser rejeitar, `invalid_response`.
  7. Visualizador.
- O `VisualQuestionAnsweringComponent` **não** participa: não existe `MirageAnswerer`. **Não afirmar** que o VQA está integrado ao MIRAGE.

## Adaptador experimental do formato do treino (`experiments/e2e/training_format.py`, E4)

- **Prompts:** `experiments/mirage/prompts/grounding_{wbc,rbc,platelets}.txt`, com a frase do treino: `Please provide the bounding box coordinate of the region this sentence describes: a white blood cell.` (*a red blood cell.*, *a platelet.*).
- **Aceita só** `[x1, y1, x2, y2]`: 4 decimais simples não negativos, espaços nas pontas tolerados. Qualquer outra coisa → `TrainingFormatError` (`format_mismatch`) → `invalid_response`.
- **Converte** para `[{"cls": <classe do prompt>, "box": [...]}]`. O `TextDetectionParser` existente, **sem mudança**, valida o intervalo [0, 1] e converte para pixels (`normalized_padded_square`).
- **A classe vem do prompt**, não do modelo (`class_source = "prompt"`). É localização condicionada à classe, e **não** equivale à detecção e classificação do YOLO.

## Avaliação

- **Um único caminho para os dois modelos:** as detecções salvas de cada execução bem-sucedida passam por `evaluate_detection_references()`. Ela usa o `evaluate()` existente, **sem alteração**, com `TextDetectionParser("pixel")` e sem `conf`.
- Execuções com `invalid_response` ou `infrastructure_failure` não dão predições: todas as anotações da imagem viram FN. As categorias são contadas à parte no `summary`.
- **Formato do treino:** avaliado **por classe**, com as anotações filtradas para a classe do prompt (`training_grounding:WBC` etc.), separado do experimento JSON.
- **Campos derivados no `summary`** (contagens, não métricas novas):
  - `runs`, `succeeded_runs`, `invalid_responses`, `infrastructure_failures`;
  - `valid_response_rate`;
  - `images_with_correct_localization` e `images_with_annotations`;
  - `mean_false_positives_per_image`;
  - `out_of_vocabulary_predictions`.
- **Limitação conhecida:** a correspondência *greedy* do avaliador pode **subestimar** os TP. O contraexemplo e a proposta de correspondência ótima estão no [plano](../plans/2026-11-18-plan-real-models-e2e.md) e no [avaliador](mirage-evaluation.md#limitações).

## Anotações BCCD (`experiments/e2e/bccd_annotations.py`)

- **Seleção determinística:** os IDs da divisão são ordenados; entram as primeiras `--limit` imagens **elegíveis**.
- **Inelegíveis**, pulados e substituídos pelo próximo candidato:
  - ID em `--exclude-ids` (com `--exclude-reason` obrigatório);
  - arquivo ausente ou ilegível;
  - classe desconhecida;
  - tamanho do XML diferente do da imagem;
  - rotação EXIF;
  - caixa inválida;
  - **caixas duplicadas suspeitas**: mesma classe com IoU ≥ 0,95.
- **`selection.json`:** `created_at`, lista e hash da divisão, arquivo e hash de exclusão, `candidate_ids` (lista original), `excluded` (motivo e hashes), `substitutions` e as imagens selecionadas (SHA-256 da imagem e do XML, objetos por classe).
- **Os arquivos do conjunto nunca são alterados** (testado).
- **Ordem garantida:** a ferramenta do relatório **aborta** se alguma execução do MIRAGE começou antes do `created_at` da seleção, ou se uma imagem mudou (SHA-256).
- **`--pixel-origin`** (`one` ou `zero`) é obrigatório; a convenção do BCCD precisa ser conferida nos XML.

## Qwen3-VL (desde 18/11/2026)

- **Identidade:** `kind="llamacpp_gguf"`, pipeline `qwen3vl`.
- **`run_qwen_pipeline` e `qwen_inference_checks`** (`experiments/e2e/pipelines.py`) leem as pastas do `run_qwen.py` (uma por imagem). Cada prompt passa pelas verificações:

  | Verificação | O que confere |
  |---|---|
  | `process_completed` | `returncode` 0 |
  | `image_encoded` | `mtmd batch encoding done` no log |
  | `weights` | SHA-256 dos GGUF |
  | `runtime` | Commit do llama.cpp |
  | `configuration` | Nome e argumentos exatos |
  | `image` | SHA-256 da imagem selecionada |
  | `memory_cap` | Teto ativo, sem swap, sem OOM |
  | `weights_loaded` | Pico de RSS do processo ≥ mínimo |

- **Resultado:**
  - verificação reprovada → `infrastructure_failure`;
  - texto que não é lista de caixas (como *"There are none."*) → `invalid_response`, **"inference completed with invalid output (zero usable detections)"**;
  - as detecções guardam os **rótulos originais**.
- **Rótulos na avaliação:** mapeamento **explícito e registrado**, só por correspondência exata dos 3 textos dos prompts (`red blood cell` → `RBC`, `white blood cell` → `WBC`, `platelet` → `Platelets`). Qualquer outro rótulo continua igual e conta como fora do vocabulário.
- **Experimentos:**
  - **A, `joint_detection`:** prompt das 3 classes; `class_source=model`.
  - **B, `class_conditioned:<classe>`:** um prompt por classe, anotações filtradas para a classe; `class_source=prompt`. **Não** é classificação feita pelo modelo.
- **Avaliações por pipeline e experimento:**
  - sensível à classe e independente de classe (com matriz de confusão), em todas as imagens;
  - as mesmas só nas **inferências concluídas** (`completed_inferences`: exclui só as falhas de infraestrutura; saídas inválidas contam como FN do modelo), quando houver falha de infraestrutura;
  - as mesmas só nas imagens com **resposta válida**, quando alguma execução não teve sucesso;
  - as duas últimas sempre **ao lado** das primeiras.
- **`experiments/e2e/draw_ground_truth.py`:** desenha as anotações humanas (`GT:<classe>`) com o visualizador existente, para conferir o alinhamento de coordenadas (1 teste).
- **Campos derivados novos:** `completed_inferences_with_invalid_output`, `exact_duplicate_boxes`, `near_duplicate_pairs_iou50`.
- **Testes:** `experiments/e2e/tests/test_qwen_pipeline.py` (16).

## Ferramenta do relatório (`experiments/e2e/build_report.py`)

```bash
uv run python -m experiments.e2e.build_report --manifest e2e-manifest.json
```

- O manifesto (JSON, campos estritos) traz `run_id`, `output_dir`, `annotations`, `selection`, `images_dir`, `criteria` (as 8 chaves obrigatórias do E8), `yolo` (`model_path` e limiares), `mirage` (nome, checkpoint e revisões, revisão completa do código oficial, VRAM mínima, experimentos com `prompt_file`, `runs_dir` e `prompt_class` opcional) e `deviations`.
- **Executa o YOLO real** (`YoloDetector`), **lê** as execuções do MIRAGE, avalia cada pipeline e experimento, grava `evaluations/*.json` e `report.json`, e depois **recarrega e confere todos os hashes**.

## Testes (18/11/2026)

| Arquivo | Testes |
|---|---|
| `tests/unit/artifacts/report/test_execution_report.py` | 34 |
| `experiments/e2e/tests/test_yolo_evaluation.py` | 7 |
| `experiments/e2e/tests/test_bccd_annotations.py` | 20 |
| `experiments/e2e/tests/test_training_format.py` | 20 |
| `experiments/e2e/tests/test_pipelines.py` | 26 (1 com o ONNX real) |
| `experiments/e2e/tests/test_build_report.py` | 13 |

- **Teste com modelo real:** pulado, a menos que `DETECTION_MODEL_PATH`, `DETECTION_IMAGE_PATH` **e** `E2E_ALLOW_REAL_MODELS=1` estejam definidos.
- **Simuladores:** o `FakeDetector` e as verificações sintéticas existem **só** nos testes. Nenhum teste carrega o MIRAGE.
