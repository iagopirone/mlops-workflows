---
type: Plan
title: Pipelines de ponta a ponta com modelos reais (YOLO e MIRAGE)
description: Plano para executar o MIRAGE oficial em GPU e o YOLO real até a imagem anotada, avaliar os dois contra anotações humanas e persistir um relatório como artefato. E1–E7 aprovadas (com condições); preparação local implementada; E4 (adaptador) e E8 (critérios) em proposta; nenhum modelo executado.
tags:
- mirage
- yolo
- e2e
- report
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T14:30:00-03:00"
evidence_basis: [proposal, verified, hypothesis]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage, conferido em 18/11/2026
  title: Código local
- id: mirage-official
  resource: https://github.com/visual-haystacks/mirage (commit 617751c, clone lido em 17–18/11/2026)
  title: Código oficial do MIRAGE
- id: mirage-checkpoint
  resource: https://huggingface.co/tsunghanwu/mirage-llama3.1-8.3B (revisão 100ea29f5fb9dbd35d52390075abd9f60b225478; metadados lidos pela API em 18/11/2026, nada baixado)
  title: Checkpoint oficial do MIRAGE
- id: clip
  resource: https://huggingface.co/openai/clip-vit-large-patch14-336 (revisão ce19dc912ca5cd21c8a653c79e251e808ccabcd1; metadados lidos pela API)
  title: Torre de visão CLIP
- id: bccd
  resource: https://github.com/Shenggan/BCCD_Dataset (commit d272fb14cdff6e473fafeeeba32aba5f560e9e43; estrutura lida pela API)
  title: Conjunto BCCD (anotações VOC, licença MIT)
---

# Pipelines de ponta a ponta com modelos reais

**Situação:** veja a [seção 12](#12-atualização-de-18112026-noite-e4-relatório-correções-e-plano-exato-de-execução) (a mais recente) e a [seção 11](#11-atualização-de-18112026-decisões-do-usuário-e-preparação-local): decisões aprovadas, preparação local feita e propostas de E4 e E8. **Nenhum modelo executado para gerar resultados.** Texto original: Escopo do usuário (18/11/2026): os dois pipelines usam **modelos reais**, e o relatório traz **resultados reais**, mesmo que o MIRAGE não produza nenhuma caixa válida. O `FakeAnswerer` fica **só** nos testes. **Não se presume** que o MIRAGE detecta objetos: é isso que o experimento testa.

| Pipeline | Fluxo |
|---|---|
| 1. YOLO real | imagem → `ObjectDetectionComponent` (`YoloDetector`, `best.onnx`) → `DetectionReference` → `DetectionVisualizationComponent` → imagem anotada |
| 2. MIRAGE real | imagem + prompt → MIRAGE oficial (`run_poc.py --execute`, GPU) → `answer.txt` (`TextReference`) → `TextDetectionParsingComponent` → `DetectionReference` → `DetectionVisualizationComponent` → imagem anotada |

## 1. Implementado × a desenvolver

| Parte | Estado |
|---|---|
| `ObjectDetectionComponent` + `YoloDetector` com ONNX real | **Implementado e verificado** |
| `DetectionVisualizationComponent` (`ImageContent` + `DetectionContent`) | **Implementado e verificado** |
| Artefatos de imagem, texto e detecção (`conf: null` permitido) | **Implementado e verificado** |
| `TextDetectionParser` + `TextDetectionParsingComponent` | **Implementado**, testado só com respostas simuladas |
| `run_poc.py` (grava `stdout.txt`, `stderr.txt`, `answer.txt`, `run.json`) | **Implementado**; dry run real verificado; **nunca rodou com `--execute`** |
| Prompts `vqa.txt` e `boxes_normalized_padded_square.txt` | **Implementados**, nunca usados com o modelo |
| `evaluate_detections.py` (IoU, TP/FP/FN, precisão, revocação; inválidas e ausentes = FN) | **Implementado**, testado só com dados sintéticos |
| Ambiente conda do MIRAGE na GPU | **A fazer** (instalação oficial nunca testada) |
| Conversor VOC XML → `annotations.json` | **A desenvolver** |
| Driver do pipeline 1 (o `examples/demo_detection.py` desenha sozinho e **não** usa o visualizador) | **A desenvolver** |
| Driver do pipeline 2 a partir das pastas do `run_poc.py` | **A desenvolver** |
| Avaliação do YOLO com o mesmo avaliador | **A desenvolver** (E5) |
| Artefato `ExecutionReport` + gerador do relatório | **A desenvolver** (E6) |
| Guarda do nome da pasta do checkpoint no `run_poc.py` | **Proposta** (E3) |
| `MirageAnswerer` no `VisualQuestionAnsweringComponent` | **Fora deste plano** (seção 6) |

## 2. Memória e GPU (E1)

**Conferido nos metadados oficiais em 18/11/2026, sem baixar nada:**
- Checkpoint MIRAGE: 4 arquivos `safetensors` em fp16, **18,43 GB** no total (`total_size` = 18 426 347 522 bytes, cerca de 9,2 bilhões de parâmetros). Inclui o Llama 3.1 8B, o recuperador, o Q-Former e o projetor. **Não** inclui a torre de visão. Não é *gated*; licença MIT.
- A torre de visão é baixada **por nome**: `mm_vision_tower = "openai/clip-vit-large-patch14-336"` no `config.json`. Download de cerca de 1,71 GB (`pytorch_model.bin`, fp32, CLIP inteiro); na GPU, só a parte de visão (cerca de 0,3 bilhão de parâmetros, cerca de 0,6 GB em fp16).
- O Q-Former é montado localmente com `Blip2QFormerConfig`, e os pesos dele estão no checkpoint. *Correção:* o `bert-base-uncased` que eu citei antes aparece só numa amostra dos dados de treino, não no código.
- `demo.py`: GPU única (`device="cuda"`), fp16 fixo, sem quantização, `max_new_tokens=512`.

**Estimativa de VRAM (calculada; medir na fase 1):**

| Parcela | Tamanho |
|---|---|
| Pesos MIRAGE (fp16) | 18,4 GB |
| CLIP de visão (fp16) | cerca de 0,6 GB |
| Cache KV: 32 camadas × 8 cabeças KV × 128 × 2 (K, V) × 2 bytes = 128 KiB por token; contexto de até 2048 tokens | até 0,27 GB |
| Contexto CUDA, ativações, fragmentação | cerca de 1 a 1,5 GB (estimado) |
| **Pico estimado** | **cerca de 20 a 21 GB** |

**Outros requisitos (estimativas):** 32 GB de RAM (16 GB provavelmente basta, porque os pesos vão direto para a GPU por *shard*; não verificado) e 50 GB livres em disco (18,4 + 1,7 + o ambiente conda com torch e CUDA). Driver compatível com CUDA 12.1 ou 11.8. Arquitetura até Hopper: o `torch 2.1.2` **não** suporta Blackwell (RTX 50xx, B200).

| Alternativa | Avaliação |
|---|---|
| **A. GPU de 24 GB** (RTX 3090/4090, A5000, L4, A10G) | Cabe pela estimativa, com cerca de 3 GB de folga. Menor custo |
| B. GPU de 40 a 80 GB (A100, H100) | Folga grande; é a configuração do paper. Custo maior |
| C. GPU de 16 GB ou menos (T4, Colab gratuito) | **Não cabe** em fp16, e quantizar exigiria editar o código oficial, o que muda as respostas |
| D. Duas GPUs pequenas | O `demo.py` fixa uma GPU só |

**Recomendação:** **A**, de preferência numa máquina própria ou institucional. Se não houver, nuvem com o custo aprovado por você. Se a fase 1 mostrar falta de memória (OOM), passar para B. **Preciso saber:** existe uma máquina assim disponível?

## 3. Ambiente oficial e incompatibilidades (E2)

**Conflitos conhecidos:**
- o `pyproject` oficial fixa `torch==2.1.2` e `torchvision==0.15.2`, mas a 0.15.2 foi feita para o torch 2.0.1;
- `pydantic<2`;
- `transformers==4.43`.

O MIRAGE fica **fora** do ambiente `uv` do projeto ([ADR 004](../adr/004-mirage-out-of-process.md)).

**Preparação proposta (na máquina com GPU, depois da autorização):**

```bash
git clone https://github.com/visual-haystacks/mirage.git /workspace/mirage-official
git -C /workspace/mirage-official checkout 617751c
conda create -n mirage python=3.10 -y && conda activate mirage
cd /workspace/mirage-official && python -m pip install -e .
huggingface-cli download tsunghanwu/mirage-llama3.1-8.3B \
  --revision 100ea29f5fb9dbd35d52390075abd9f60b225478 \
  --local-dir /workspace/checkpoints/mirage-llama3.1-8.3B
huggingface-cli download openai/clip-vit-large-patch14-336 \
  --revision ce19dc912ca5cd21c8a653c79e251e808ccabcd1
conda env export > /workspace/evidence/conda-env.yml
pip freeze > /workspace/evidence/pip-freeze.txt
nvidia-smi -q > /workspace/evidence/nvidia-smi.txt
```

- Depois dos downloads, toda execução roda com `HF_HUB_OFFLINE=1`. Isso prova que nada mais foi baixado durante a inferência e que a torre de visão vem da revisão fixada.
- **Nome da pasta do checkpoint:** o `builder.py` só monta o modelo multimodal se o último segmento do caminho contiver `mirage` ou `llava` (e não `lora`). Por isso, `--local-dir .../mirage-llama3.1-8.3B`, e **não** a pasta de *snapshot* do cache, cujo nome é um hash.

| Alternativa para o conflito do torchvision | Avaliação |
|---|---|
| A. Instalação oficial exata; se falhar, parar e reportar | Mais fiel, mas pode não instalar |
| **B. Oficial + arquivo de *constraints* fora do repositório oficial** (`torch==2.1.2`, `torchvision==0.16.2`, o par correto) | Não edita o código oficial; desvio mínimo e registrado. O `demo.py` usa PIL e o processador do CLIP, não o torchvision |
| C. Imagem Docker com CUDA 12.1 | Mais reprodutível, mais trabalho (YAGNI agora) |

**Recomendação:** tentar **A**; se o pip recusar o par, aplicar **B** e registrar o desvio no relatório. Qualquer outro conflito: **parar e trazer para decisão**.

## 4. Imagens, anotações e comparação válida com o YOLO (E1, E5)

- **Fonte das anotações humanas:** BCCD (`Shenggan/BCCD_Dataset`, licença MIT, commit `d272fb1`). Tem anotações VOC XML de RBC, WBC e Platelets, e imagens JPEG de 640×480. O nome `BloodImage_00236` vem desse conjunto.
- **Atenção, verificado pela API:** `BloodImage_00236` está no **`trainval.txt`** do BCCD, não no `test.txt` (72 imagens). Se o `best.onnx` foi treinado na divisão padrão do BCCD, essa imagem estava no treino do YOLO, e as métricas do YOLO nela ficariam otimistas. Os metadados do ONNX dizem só "dataset de desafio". **Preciso saber:** você conhece a divisão usada no treino do YOLO?
- **Proposta de imagens:**
  - `BloodImage_00236` só como teste de fumaça (fases 1–2), **fora das métricas**;
  - as métricas usam **20 imagens do `test.txt`**, escolhidas de forma determinística (as 20 primeiras em ordem alfabética) e registradas no relatório.
- **Comparação válida:** as mesmas imagens, as mesmas anotações, o mesmo avaliador (`evaluate()`), o mesmo limiar de IoU (0,5), a mesma correspondência um-para-um por classe e os mesmos nomes de classe.
  - As caixas do YOLO **nunca** servem de verdade.
  - As imagens do pipeline 1 são carregadas pelo OpenCV, que aplica a rotação EXIF. O `run_poc.py` recusa JPEG com rotação EXIF, então as duas grades de pixels coincidem.
- **Limitação conhecida do BCCD:** muitas hemácias (RBC) não estão anotadas, o que gera falsos positivos e baixa a precisão de **ambos** os modelos. Proposta: relatar as métricas por classe e destacar WBC, que é bem anotada (normalmente 1 por imagem).
- **Conversor (a desenvolver):** VOC XML → `annotations.json` do avaliador.
  - Pela convenção VOC, os pixels começam em 1, e o projeto usa caixa contínua; então a conversão subtrai 1 de `xmin` e `ymin`. **Conferir nos XML do BCCD** antes de fixar, e documentar.
  - A validação é feita pelo `TextDetectionParser("pixel")`, como o avaliador já faz.
  - Caixa inválida ou classe desconhecida **aborta**; não se corrige anotação.

## 5. Execução do MIRAGE com `run_poc.py` e preservação

Uma pasta com **uma imagem** por execução (exigência do avaliador). Cada execução recarrega o modelo.

| Fase | Imagens | Prompt | Objetivo |
|---|---|---|---|
| 1 | `00236` | `vqa.txt` | Instalação, tempo de carga, VRAM de pico, resposta crua |
| 2 | `00236` | `boxes_normalized_padded_square.txt` | Primeira resposta real de caixas (fora das métricas) |
| 3 | 20 do `test.txt` | `boxes_normalized_padded_square.txt` | Execução avaliada |
| 4 (E4) | 20 do `test.txt` | Frase de *grounding* do treino, por classe (`"Please provide the bounding box coordinate of the region this sentence describes: a white blood cell."`) | Observação; o parser aceita só JSON |

```bash
# Durante cada execução, registrar a VRAM:
nvidia-smi --query-gpu=timestamp,memory.used --format=csv -lms 500 > "$OUT/gpu-memory.csv" &
HF_HUB_OFFLINE=1 python experiments/mirage/run_poc.py \
  --official-repo /workspace/mirage-official \
  --image-folder /workspace/images/BloodImage_00236 \
  --prompt-file experiments/mirage/prompts/boxes_normalized_padded_square.txt \
  --model-path /workspace/checkpoints/mirage-llama3.1-8.3B \
  --output-dir "$OUT" --execute
```

**Tempo:** cerca de 42 execuções (2 + 20 + 20). O tempo por execução só será conhecido na fase 1. Se for de 2 a 3 minutos, o total fica em 1,5 a 2 horas de GPU (estimativa).

**Preservação:**
- os arquivos do `run_poc.py` não são alterados;
- ao lado de cada execução ficam `gpu-memory.csv` e o ambiente (`conda-env.yml`, `pip-freeze.txt`, `nvidia-smi.txt`);
- no fim, `sha256sum` de todos os arquivos (manifesto), um `.tar.gz` copiado para fora da máquina de GPU e guardado em `/home/visioer/Projetos/backups/`;
- respostas inválidas, vazias e erros são preservados **iguais** aos demais.

## 6. Ligação aos componentes e artefatos, sem `FakeAnswerer`

**Pipeline 2, por pasta de execução (driver a desenvolver, no ambiente `uv`):**
1. A imagem indicada em `answer_image` no `run.json` vira `ImageReference`, e `answer.txt` vira `TextReference`.
2. `TextDetectionParsingComponent(TextDetectionParser("normalized_padded_square"))` → `DetectionReference`. O avaliador recebe a mesma convenção.
3. Se o parser rejeitar, o resultado é `invalid_response`, com a mensagem; **nenhuma caixa** e nenhuma imagem anotada. Sem `answer.txt`, `missing_response`.
4. `DetectionVisualizationComponent` → imagem anotada (rótulo sem confiança).

**Pipeline 1:** `ImageReference` → `ObjectDetectionComponent(YoloDetector(best.onnx))` → `DetectionReference` → `DetectionVisualizationComponent`.

**Por que o pipeline 2 não passa pelo `VisualQuestionAnsweringComponent`:**
- o MIRAGE roda fora do processo, num ambiente incompatível com o do projeto ([ADR 004](../adr/004-mirage-out-of-process.md));
- o README do experimento só admite um `MirageAnswerer` depois de validar saídas reais.

A resposta real entra no pipeline pelo artefato `TextReference`, que é o mesmo contrato que o VQA produziria.

**Como o simulado fica de fora:**
1. os drivers não importam `Fake*`;
2. o relatório **exige** a identidade de cada modelo:
   - YOLO: SHA-256 do `best.onnx`;
   - MIRAGE: revisão do checkpoint, revisão do CLIP, commit do código oficial e o `run.json` de cada execução;
3. o driver do pipeline 2 só aceita pastas com `run.json` de `returncode` registrado e `stdout.txt` presente.

## 7. Relatório como artefato (E6)

- **Onde:** `mlops_workflows/artifacts/report/`, com `ExecutionReportReference` e `ExecutionReportContent`.
  - `materialize()` lê e valida o JSON;
  - `dematerialize(reference)` grava JSON UTF-8 e devolve o local;
  - Pydantic `strict=True` e `extra="forbid"`, como os outros artefatos.
- **Esquema (`data: ExecutionReport`):**

```text
ExecutionReport
  run_id, created_at, environment {python, platform, gpu, packages}
  models: [ModelIdentity {key, kind: "onnx" | "mirage", name, source, revision_or_sha256}]  # obrigatório, não vazio
  pipelines: [PipelineRun
    pipeline: "yolo" | "mirage", model_key, image_id, prompt_file | null
    status: "succeeded" | "invalid_response" | "missing_response" | "failed"
    error: str | null, detection_count: int | null
    inputs / outputs / evidence: [ArtifactRecord {kind: "image" | "text" | "detection" | "file", name, location}]
  ]
  evaluations: [{pipeline, ground_truth, iou_threshold, coordinate_format, report_location, summary}]
  deviations: [str]   # ex.: torchvision 0.16.2
```

- **Armazenamento:** `outputs/e2e/<run_id>/report.json`, com `yolo/<image_id>/` e `mirage/<fase>/<image_id>/` ao lado. Tudo fora do Git.
- **Recuperação:**
  1. `ExecutionReportReference(name=..., location=".../report.json").materialize()` devolve o conteúdo validado;
  2. cada saída é recuperada pelo registro dela, `ImageReference(name, location).materialize()` ou `DetectionReference(...)`.
  As imagens **não** são embutidas no JSON.
- **Resumo legível:** `docs/reports/YYYY-MM-DD-real-models-e2e.md`, com as métricas, a tabela por imagem, as respostas cruas mais relevantes e os caminhos (E7).
- Decisão registrada num ADR novo e na página de referência do artefato.

| Alternativa | Avaliação |
|---|---|
| **A. Artefato `ExecutionReport` tipado** | Atende ao pedido (`ArtifactReference`/`ArtifactContent`); o esquema impõe a identidade dos modelos |
| B. JSON escrito pelo driver, sem artefato | Mais simples, mas não cumpre o pedido e não valida nada |
| C. `TextContent` com JSON dentro | Reaproveita código, mas perde a validação |

**Recomendação:** A.

## 8. Testes automatizados

O MIRAGE e os pesos **nunca** são carregados no pytest (invariante I5).

- **Artefato de relatório** (`tests/unit/artifacts/report/`):
  - ida e volta;
  - extras e tipos errados recusados;
  - `models` vazio recusado;
  - pipeline com `model_key` inexistente recusado.
- **Driver do pipeline 2**, com pastas falsas escritas pelo teste:
  - resposta válida, inválida, ausente e `[]`;
  - `answer_image: null`;
  - dimensões divergentes;
  - sem `stdout.txt`.
- **Driver do pipeline 1:**
  - com `FakeDetector`;
  - com o ONNX real, pulado sem `DETECTION_MODEL_PATH` (como hoje).
- **Conversor VOC:**
  - XML válido;
  - caixa fora da imagem;
  - classe desconhecida;
  - conversão de 1-based.
- **Guarda do `run_poc.py` (E3):** nomes aceitos e recusados.
- **Verificação final:**
  - `okf_lint`, `ruff check` e `ruff format --check`;
  - suíte principal, com e sem ONNX;
  - testes do experimento no Python 3.10 e no 3.12.

## 9. Critérios de sucesso, falha e conclusão

**O experimento está concluído quando:**
1. Os dois pipelines rodaram com modelos reais em todas as imagens previstas (YOLO nas 20; MIRAGE nas fases 1–3, e na 4 se E4 for aprovada).
2. Toda execução tem status e evidência completa: `stdout.txt`, `stderr.txt`, `run.json`, VRAM e ambiente.
3. O avaliador rodou sobre todas as imagens anotadas, para os dois pipelines.
4. O `report.json` foi gravado, rematerializado e validado, e cada saída listada nele existe.
5. As evidências foram arquivadas com manifesto SHA-256, e a documentação foi atualizada.

**Isso vale qualquer que seja o resultado do MIRAGE.** Zero caixas válidas é um resultado, não uma falha do experimento.

**O experimento falha (é inválido, e não se tiram conclusões) se:**
- não for possível instalar dentro dos limites aprovados em E2;
- faltar memória (OOM) na GPU aprovada;
- algo for baixado durante uma execução com `HF_HUB_OFFLINE=1`;
- as dimensões ou a associação entre imagem e resposta divergirem;
- faltar evidência de alguma execução;
- algum resultado não vier de um modelo real.

**Interpretação da hipótese "o MIRAGE localiza células" (E8, limiares a pré-registrar antes de ver os dados).** Proposta, com IoU ≥ 0,5:

| Resultado | Critério |
|---|---|
| **Promissor:** justifica o `MirageAnswerer` | ≥ 90% de respostas válidas **e** revocação de WBC ≥ 0,7 |
| **Inconclusivo** | Respostas válidas, mas abaixo desses limiares; ou só as respostas no formato do treino (fase 4) parecem localizar |
| **Negativo:** seguir com OWLv2 ou Grounding DINO como `ObjectDetector` | < 50% de respostas válidas **ou** revocação de WBC < 0,3 |

As métricas do YOLO nas mesmas imagens servem de referência, não de verdade.

## 10. Decisões pendentes

| # | Decisão | Recomendação |
|---|---|---|
| E1 | Máquina com GPU e autorização dos downloads: checkpoint (18,4 GB), CLIP (1,7 GB), BCCD (cerca de 7,5 MB) | GPU de 24 GB, própria ou institucional; nuvem só com custo aprovado |
| E2 | Conduta no conflito `torch`/`torchvision` | Oficial; se falhar, *constraints* com `torchvision==0.16.2`, registrado |
| E3 | Guarda do nome da pasta do checkpoint no `run_poc.py` | Sim |
| E4 | Fase 4: frase de *grounding* do treino, por classe | Sim, como observação |
| E5 | Avaliar o YOLO com o mesmo avaliador, nas mesmas 20 imagens do `test.txt` | Sim |
| E6 | Artefato `ExecutionReport` no pacote principal | Sim (alternativa A) |
| E7 | Versionar imagens anotadas e respostas | Não versionar as saídas brutas; versionar só o relatório em `docs/reports/` com as métricas e trechos das respostas |
| E8 | Limiares de interpretação da seção 9 | Aprovar ou ajustar **antes** da execução |

**Ordem depois da aprovação:**
1. Localmente: conversor, drivers, artefato de relatório, guarda e testes. Sem GPU e sem downloads além do BCCD, se autorizado.
2. Na GPU, com autorização: ambiente e downloads; fases 1–4.
3. Localmente: avaliação, relatório e documentação (ADR, referências, status, log, handoff).

## 11. Atualização de 18/11/2026: decisões do usuário e preparação local

### Decisões do usuário

| # | Decisão |
|---|---|
| E1 | **Aprovada com condição:** GPU NVIDIA de 24 GB inicialmente. Começar com **uma imagem**, registrar a VRAM e **interromper** se faltar memória. Nada pago sem autorização |
| E2 | **Aprovada:** ambiente oficial separado; todo ajuste documentado. Par compatível do PyTorch: `torch 2.1.2` + `torchvision 0.16.2` |
| E3 | **Aprovada e implementada:** validação do nome do checkpoint, com testes |
| E4 | **Aprovada com ajuste:** prompt JSON **e** formato do treino, como **experimentos separados**. Avaliar a qualidade espacial das respostas no formato do treino sem confundir formato com localização. **Não flexibilizar o parser**; propor um adaptador separado |
| E5 | **Aprovada com condição:** BCCD, mesmas imagens e anotações para os dois modelos; `00236` só como teste inicial; **antes** da comparação quantitativa, investigar a origem do treino do YOLO e possíveis vazamentos; 20 imagens, como avaliação **exploratória**, com a seleção exata registrada; verificar a integridade das anotações e a correspondência das classes |
| E6 | **Aprovada e implementada:** artefato tipado ([ADR 009](../adr/009-execution-report-artifact.md)) |
| E7 | **Aprovada:** saídas brutas e SHA-256 fora do Git; versionar só os relatórios resumidos, quando os commits forem autorizados |
| E8 | **Revisar:** critérios definidos antes dos resultados, não só com a revocação de WBC (incluir precisão, FP, taxa de respostas válidas e qualidade das caixas); 20 imagens são exploratórias |

Outros requisitos:
- os resultados finais vêm só de modelos reais;
- a resposta do MIRAGE é persistida como `TextReference` e processada pelos componentes existentes;
- não afirmar que o VQA está integrado ao MIRAGE;
- validar o reúso do avaliador para o YOLO;
- separar falha de infraestrutura, resposta inválida e detecção incorreta;
- manter o `CLAUDE.md` e a documentação atualizados.

### Preparação local implementada (só com dados sintéticos)

| Etapa | Arquivos | Testes |
|---|---|---|
| 1. E3: nome do checkpoint | `experiments/mirage/run_poc.py` (`official_model_name`, `validate_model_name`, que espelham o `get_model_name_from_path` oficial) | +12 em `test_run_poc.py`; 81 passed no 3.12 e no 3.10 |
| 2. Reúso do avaliador para o YOLO | `experiments/e2e/yolo_evaluation.py` | 7 |
| 3. E6: artefato de relatório | `mlops_workflows/artifacts/report/` | 25 |
| 4. E5: anotações BCCD | `experiments/e2e/bccd_annotations.py` | 15 |
| 5. Drivers dos pipelines | `experiments/e2e/pipelines.py` | 14 (1 com o ONNX real, pulado) |

Detalhes em [relatório de execução e drivers](../references/artifact-execution-report.md). Validação na [log](../log.md).

**Resposta ao requisito 4 (reúso do avaliador):** **sim, sem alterar o avaliador.** A `evaluate()` recebe respostas em texto e um parser. O adaptador mínimo `detections_to_response()` escreve as detecções do YOLO como JSON em pixels, sem `conf`, e as métricas continuam vindo só do avaliador. Ressalva: o resultado depende do `confidence_threshold` do YOLO, que entra no relatório.

### Proposta E4: adaptador experimental para o formato do treino (não implementado)

- **Prompt:** um por classe, com a frase do treino: `Please provide the bounding box coordinate of the region this sentence describes: a white blood cell.` (o mesmo para *red blood cell* e *platelet*). No treino, a resposta é **uma** caixa `[x1, y1, x2, y2]` normalizada.
- **Adaptador** (`experiments/e2e/training_format.py`, separado do parser, que **não muda**):
  - **aceita só** uma lista de exatamente 4 números entre colchetes (espaços nas pontas tolerados);
  - qualquer outra coisa vira `invalid_response`, com o motivo `format_mismatch`, e o texto é preservado;
  - a classe vem **do prompt**, e não do modelo; isso fica registrado (`class_source: "prompt"`);
  - devolve o texto JSON `[{"cls": "<classe do prompt>", "box": [...]}]`, que segue **pelo mesmo** `TextDetectionParser("normalized_padded_square")` e pelo mesmo `evaluate()`;
  - nenhuma métrica nova é calculada.
- **Avaliação por classe:**
  - O `evaluate()` recebe **uma** resposta por imagem, e este experimento gera três por imagem, uma por classe.
  - **Juntar as três numa lista seria errado:** se uma estivesse malformada, a imagem inteira viraria `invalid_response` e as outras duas classes seriam zeradas, misturando formato com localização.
  - **Proposta:** chamar o `evaluate()` **uma vez por classe**, com as anotações filtradas para aquela classe e a resposta daquela classe em cada imagem. Rótulos de experimento: `training_grounding:WBC`, `training_grounding:RBC`, `training_grounding:Platelets`.
  - O avaliador não muda, e o `PipelineRun.experiment` já é texto livre.
- **Por que separa formato de localização:**
  - no experimento JSON, uma resposta entre colchetes conta como inválida (falha de formato);
  - no experimento do treino, o formato esperado **é** o de colchetes, então só a qualidade espacial é medida.
  - O relatório mostra os dois experimentos lado a lado, nunca somados.
- **Limitação por desenho:** uma caixa por classe e por imagem. Por isso a revocação de RBC (dezenas por imagem) é baixa **por construção**. As métricas principais desse experimento são **precisão** (a caixa cai num objeto anotado da classe?) e **IoU médio**; a revocação aparece, mas não é interpretada.
- **Testes previstos:** colchetes válidos, texto em volta, 3 ou 5 números, valores fora de [0, 1], JSON em vez de colchetes, e a classe vinda do prompt.

### Proposta E8 revisada: critérios pré-registrados (exploratórios)

Para cada experimento (JSON e formato do treino), cada classe e IoU ≥ 0,5:
- **Medidas:**
  - taxa de respostas válidas;
  - falhas de infraestrutura;
  - TP, FP e FN;
  - FP por imagem;
  - precisão;
  - revocação;
  - IoU médio dos pares (qualidade das caixas).
- **Referência:** o YOLO nas mesmas imagens, com o mesmo avaliador.

| Leitura | Critério (todos com n = 20 imagens; **não** são conclusões sobre o desempenho geral) |
|---|---|
| **Execução inválida** | Qualquer falha de infraestrutura não resolvida: refazer, não interpretar |
| **Sinal positivo** (justifica uma avaliação maior, não a adoção) | ≥ 80% de respostas válidas **e**, em pelo menos uma classe, precisão ≥ 0,5, revocação ≥ 0,5 (dispensada no experimento do treino) e IoU médio ≥ 0,6, **e** FP por imagem ≤ objetos anotados por imagem |
| **Sinal negativo** (priorizar OWLv2 ou Grounding DINO) | < 50% de respostas válidas **ou** precisão < 0,2 em todas as classes |
| **Inconclusivo** | Qualquer outro caso |

**Diagnósticos de formato, relatados à parte (não são falhas de localização):**
- **Rótulos fora do vocabulário** (por exemplo, `Platelet`, `platelets`, `red blood cell`): a correspondência exata conta cada um como 1 FP + 1 FN. Eles aparecem como chaves próprias em `per_class` e a **taxa de rótulos fora do vocabulário** é relatada separadamente. **Não há remapeamento**, porque isso afrouxaria o parser.
- **Opcional (oferecido, não construído):** uma passada **sem classe**, que troca as classes das anotações e das predições por uma só antes do `evaluate()`. Separa "achou a célula" de "deu o nome certo", sem mudar o avaliador, e fica rotulada como diagnóstico.

**Políticas fixadas antes dos dados:**
- **Imagem selecionada com anotação inválida:** hoje o conversor **aborta**. Escolher a regra **agora**, para não ser escolha *post hoc*:
  - (a) parar e decidir caso a caso;
  - (b) excluir a imagem e registrar;
  - (c) pegar a próxima da lista ordenada e registrar.
  - Recomendação: **(c)**. A regra é determinística, e a exclusão fica visível na `selection.json`.
- **Caixas duplicadas nas anotações:** são **contadas e mantidas**. Aumentam os FN dos **dois** modelos igualmente; é uma escolha declarada.

Os limiares e as políticas precisam ser aprovados **antes** da primeira execução real e ficam gravados no relatório.

### Próximos passos (aguardando aprovação)

1. Aprovar E4 (adaptador) e E8 (critérios).
2. Implementar o adaptador E4 e a CLI que monta o relatório, com dados sintéticos.
3. **Investigar a origem do treino do YOLO** (E5): a quem perguntar, onde está o `data.yaml` do desafio. Os metadados do ONNX citam `/home/apucci73/dev/mlops-pipeline-challenge/dataset/data.yaml`.
4. **Antes de qualquer execução real:** apresentar os comandos e o ambiente exatos (GPU, conda, downloads), para aprovação.

**Correção do orçamento de GPU:** a fase 4 com prompts por classe dá 20 × 3 = 60 execuções. Total: 2 (fases 1–2) + 20 (fase 3) + 60 (fase 4) = **cerca de 82 execuções**, não 42. Com 2 a 3 minutos por execução (não medido), são **cerca de 3 a 4 horas de GPU**. O tempo real por execução só será conhecido na fase 1.

**Correspondência de classes:** o `check_class_names()` está implementado e testado, mas **ainda não é chamado**. Ele será ligado na CLI do relatório, onde confere as `class_names` do YOLO com as classes do BCCD.

## 12. Atualização de 18/11/2026 (noite): E4, relatório, correções e plano exato de execução

### Decisões do usuário (terceira rodada)

- **E4:** aprovada. Adaptador separado; o parser não muda; resposta original preservada; classe vinda do prompt registrada; resultados separados do prompt JSON.
- **E8:** aprovada com ajustes. Separar:
  - validade e infraestrutura;
  - qualidade espacial;
  - precisão, revocação e FP;
  - imagens com pelo menos uma localização correta;
  - classe do modelo × classe do prompt.

  Não equiparar o experimento condicionado à classe com o YOLO. **Revisar o critério de FP proporcional**. Os limiares são exploratórios.
- **Anotações:** substituir imagem inválida pela próxima elegível, **antes** de qualquer predição. **Excluir** imagens com duplicação suspeita, com substituição documentada. Nunca modificar os originais. Registrar a lista original, as exclusões, as substituições, os motivos e os hashes.
- **Proteção extra** para inferência real nos testes de `experiments/e2e`.
- **Avaliador:** verificar se o *greedy* subestima os TP; propor a correspondência ótima.
- **Ferramenta do relatório:** implementar, sem aceitar um identificador de modelo como prova de inferência.

### Implementado (só com dados sintéticos; nenhum modelo executado)

| Item | Arquivos | Testes |
|---|---|---|
| Proteção `E2E_ALLOW_REAL_MODELS=1` | `experiments/e2e/tests/test_pipelines.py` | Verificada com caminhos inexistentes: o teste real é pulado |
| Exclusão e substituição de anotações | `experiments/e2e/bccd_annotations.py` (`select_images`, `find_duplicates`, `--exclude-ids`) | 20 |
| E4: adaptador do formato do treino | `experiments/e2e/training_format.py` e `experiments/mirage/prompts/grounding_{wbc,rbc,platelets}.txt` | 20 |
| Evidência de inferência no `run_poc.py` | `gpu-memory.csv` amostrado **durante** a execução; `gpu_memory_peak_mib` e `hf_hub_offline` no `run.json` | +3 (37 no total), no 3.12 e no 3.10 |
| Esquema do relatório | `sha256` em cada arquivo, `class_source`, `inference_checks` (exigidas para resposta de modelo), `inputs` e `criteria` | 34 |
| Drivers | Verificações de inferência do MIRAGE; caminho do formato do treino com o texto convertido à parte | 26 |
| Ferramenta do relatório | `experiments/e2e/build_report.py` (manifesto, YOLO real, leitura do MIRAGE, avaliação por experimento e por classe, `verify_report`) | 13 |

Detalhes em [relatório e drivers](../references/artifact-execution-report.md).

### Correspondência *greedy*: verificado que pode subestimar os TP

Contraexemplo executado no `match_detections` atual:
- **Anotações:** A0 = `[5, 0, 15, 10]`, A1 = `[7, 0, 17, 10]`.
- **Predições:** P0 = `[5.5, 0, 15.5, 10]` (IoU 0,905 com A0 e 0,739 com A1) e P1 = `[2, 0, 12, 10]` (IoU 0,538 com A0 e 0,333 com A1).
- **Resultado:** o *greedy* pega P0–A0 e para em **1 TP**. A correspondência ótima, P0–A1 + P1–A0, dá **2 TP**.
- **Onde pesa:** em células que se sobrepõem, como aglomerados de hemácias.

**Proposta (não implementada; muda o método do [ADR 006](../adr/006-offline-detection-evaluation.md) e exige ADR novo):**
- correspondência bipartida **ótima** por classe e por imagem: primeiro o **maior número** de pares com IoU ≥ limiar, depois a **maior soma de IoU**;
- algoritmo húngaro (O(n³)), só com a biblioteca padrão e compatível com o Python 3.10, com peso `M + IoU` (M > número de pares possíveis), para que a quantidade de pares domine a soma de IoU;
- desempate determinístico pelos índices;
- o *greedy* pode continuar disponível só como comparação nos testes;
- **testes:** o contraexemplo acima; igualdade com o *greedy* nos casos sem conflito; força bruta em casos pequenos aleatórios com semente fixa;
- aplica-se igualmente ao YOLO e ao MIRAGE, porque os dois usam o mesmo `evaluate()`.

**Recomendação:** aprovar e implementar **antes** de qualquer métrica real.

### Origem do YOLO (E5): investigação local, sem treinar e sem baixar nada

| Achado | Evidência |
|---|---|
| Os três `best.onnx` locais são o **mesmo arquivo** | SHA-256 `0e9bcbd6713705cdd1b97e03305decdcaa8d22dbd563eee64db2ba3b167556ae` em `~/Downloads/`, `~/Documentos/mlops-pipeline-challenge/models/v0/` e na cópia em `~/Documents/Codex/.../mlops-pipeline-challenge/models/v0/` |
| É o checkpoint **`v0` do kit do desafio** | Versionado no commit `b37eca2` (16/06/2026 09:00, "Starter kit"), em `models/v0/best.onnx`, junto com `best.pt` (SHA-256 `5697a402…`) |
| Metadados do ONNX | `date 2026-06-16T09:00:11`, Ultralytics 8.4.60, YOLO11n, `imgsz` 640, classes RBC/WBC/Platelets, *"trained on /home/apucci73/dev/mlops-pipeline-challenge/dataset/data.yaml"* |
| Metadados do `best.pt` | Lidos como texto, **sem desserializar o pickle**: `date 2026-06-16T08:59:55`, `train_args.data = .../dataset/data.yaml`, `save_dir = .../runs/v0_train`; `epochs` provavelmente 40 (lido do byte do opcode, não confirmado) |
| **Não é o teste de 1 época de 17/06** | Datas internas de 16/06 e `save_dir` `runs/v0_train`, não `runs/smoke_test`. Nenhum `runs/smoke_test` foi encontrado na máquina |
| `data.yaml`, `args.yaml`, logs e `results.csv` do treino | **Não existem localmente**. O caminho é de outra máquina (`/home/apucci73`) |
| Divisão dos dados no kit | `ATTRIBUTION.md`: BCCD convertido para YOLO e dividido em `data/raw` (91 imagens, "seed rotulado") e `data/stream` (273 imagens) + `data/oracle` (rótulos do stream); 91 + 273 = 364. O README chama o `raw` de seed e o `v0` de checkpoint inicial |
| `BloodImage_00236` | Está em `data/stream`, **não** no `raw` |

**Conclusão:** o modelo é o `v0` do kit, mas **com quais imagens ele foi treinado não está comprovado**, porque o `data.yaml` está ausente.
- **Hipótese:** o treino usou o seed `raw` (91 imagens).
- **Proposta (E9):** excluir da avaliação os IDs do `data/raw` do kit (`--exclude-ids`, motivo registrado), para reduzir o risco de vazamento. Mesmo assim, as métricas do YOLO ficam marcadas como **"origem do treino não verificada"**.
- **Para comprovar:** pedir o `dataset/data.yaml` (ou o `args.yaml` de `runs/v0_train`) a quem preparou o kit.

### E8 revisada: critérios pré-registrados (exploratórios, n = 20)

Medidos por pipeline e experimento, e por classe, com IoU ≥ 0,5 e a correspondência aprovada (de preferência a ótima):

| Dimensão | Medidas | Leitura |
|---|---|---|
| 1. Execução | `infrastructure_failures` | **Precisa ser 0.** Se não for, a execução é inválida: corrigir e refazer, sem interpretar |
| 2. Formato | `valid_response_rate`, `invalid_responses` (com motivo), `out_of_vocabulary_predictions` | É falha de **formato**, não de localização |
| 3. Localização (qualidade espacial) | `mean_matched_iou`, TP | Caixas corretas e o quanto se sobrepõem |
| 4. Detecção | precisão, revocação, FP, `mean_false_positives_per_image` | O FP é medido em **valor absoluto**, não em proporção ao número de objetos anotados |
| 5. Cobertura por imagem | `images_with_correct_localization` / `images_with_annotations` | Proporção de imagens com pelo menos um TP |
| 6. Origem da classe | `class_source` | `model` (JSON e YOLO) ≠ `prompt` (formato do treino). **Nunca** comparar diretamente o experimento condicionado à classe com o YOLO |

**Limiares propostos (vão no manifesto e no relatório antes da primeira execução):**

| Chave | Valor | Uso |
|---|---|---|
| `iou_threshold` | 0,5 | Correspondência |
| `positive_min_valid_response_rate` | 0,8 | Sinal positivo |
| `positive_min_precision` | 0,5 | Sinal positivo, na classe avaliada |
| `positive_min_recall` | 0,5 | Sinal positivo; **não se aplica** ao formato do treino (uma caixa por prompt) |
| `positive_min_mean_matched_iou` | 0,6 | Sinal positivo |
| `positive_max_false_positives_per_image` | 1,0 | Sinal positivo: no máximo 1 FP por imagem na classe, **valor absoluto** (substitui o critério proporcional) |
| `negative_max_valid_response_rate` | 0,5 | Sinal negativo se ficar abaixo |
| `negative_max_precision` | 0,2 | Sinal negativo se ficar abaixo em todas as classes |

**Leitura:**
- **Sinal positivo** em uma classe: todos os critérios "positive" atendidos. Justifica uma avaliação maior, **não** a adoção.
- **Sinal negativo:** algum critério "negative" atingido. Priorizar OWLv2 ou Grounding DINO.
- **Inconclusivo:** qualquer outro caso.
- **RBC:** o BCCD tem muitas hemácias sem anotação, o que infla os FP dos **dois** modelos. A leitura de RBC fica marcada como "anotação incompleta conhecida", e os sinais se baseiam em WBC e Platelets.
- **Nenhuma conclusão sobre o desempenho geral** com 20 imagens.

### Plano exato de execução real (para aprovação; nada foi executado)

**Recursos:**

| Recurso | Requisito |
|---|---|
| GPU | 1 NVIDIA com ≥ 24 GB (Ampere, Ada ou Hopper; **não** Blackwell), driver compatível com CUDA 12.1 (≥ 530) ou 11.8. Pico estimado de 20 a 21 GB, **a medir** |
| RAM / disco | ≥ 32 GB (estimativa) / ≥ 50 GB livres |
| Sistema | Linux x86_64, `git`, conda (Miniforge), acesso à internet **só** na preparação |
| Downloads (autorização) | Checkpoint 18,43 GB (`100ea29f…`); CLIP cerca de 1,7 GB (`ce19dc91…`); BCCD cerca de 7,5 MB (`d272fb14…`); pacotes pip do ambiente (torch 2.1.2 com CUDA, alguns GB) |
| Tempo | Cerca de 82 execuções do MIRAGE (2 de fumaça + 20 JSON + 60 do formato do treino); de 2 a 3 min cada, **não medido**: cerca de 3 a 4 h de GPU |
| Custo | Nenhum em GPU própria; nuvem só com autorização |

**Etapa A, local, sem GPU (exige autorizar o download do BCCD):**

```bash
git clone https://github.com/Shenggan/BCCD_Dataset.git /data/BCCD_Dataset
git -C /data/BCCD_Dataset checkout d272fb14cdff6e473fafeeeba32aba5f560e9e43
# Conferir a convenção de pixels (1-based) em alguns XML antes de fixar --pixel-origin.
RUN=outputs/e2e/2026-MM-DD-real-models
mkdir -p $RUN
ls ~/Documentos/mlops-pipeline-challenge/data/raw/images | sed 's/\.jpg$//' > $RUN/yolo-seed-ids.txt  # E9
uv run python -m experiments.e2e.bccd_annotations \
  --voc-root /data/BCCD_Dataset/BCCD --image-list test.txt --limit 20 \
  --pixel-origin one --output-dir $RUN/annotations \
  --exclude-ids $RUN/yolo-seed-ids.txt \
  --exclude-reason "in the challenge kit raw seed (possible YOLO v0 training data)"
```

Isso gera `annotations.json` e `selection.json`, que são **congelados** antes de qualquer predição. As 20 imagens viram uma pasta por imagem, para levar à GPU.

**Etapa B, na GPU (exige autorizar a máquina e os downloads):**

```bash
git clone https://github.com/visual-haystacks/mirage.git /workspace/mirage-official
git -C /workspace/mirage-official checkout 617751c4ceb6393ca5a73036c41fae2cdf232f29
conda create -n mirage python=3.10 -y && conda activate mirage
cd /workspace/mirage-official
python -m pip install -e .   # tentativa oficial; o pip deve recusar torch 2.1.2 + torchvision 0.15.2
```

Se falhar (esperado), aplicar o desvio aprovado na E2, **sem editar o código oficial**:
- `pip install --no-deps -e .`;
- depois, `pip install -r /workspace/requirements-mirage.txt`, um arquivo **fora** do repositório com as dependências do `pyproject` oficial, trocando só `torchvision==0.15.2` por `0.16.2` e acrescentando **`numpy<2`**.

O `numpy` não é fixado no oficial, mas o `torch 2.1.2` não funciona com `numpy 2`. Esse limite é um **novo desvio a aprovar**. Os dois desvios vão para `deviations` no relatório.

```bash
huggingface-cli download tsunghanwu/mirage-llama3.1-8.3B \
  --revision 100ea29f5fb9dbd35d52390075abd9f60b225478 \
  --local-dir /workspace/checkpoints/mirage-llama3.1-8.3B
huggingface-cli download openai/clip-vit-large-patch14-336 \
  --revision ce19dc912ca5cd21c8a653c79e251e808ccabcd1
mkdir -p /workspace/evidence
conda env export > /workspace/evidence/conda-env.yml
pip freeze > /workspace/evidence/pip-freeze.txt
nvidia-smi -q > /workspace/evidence/nvidia-smi.txt
```

**Etapa C, fases na GPU** (cópia do `experiments/mirage/` deste repositório na máquina; `HF_HUB_OFFLINE=1` sempre):

```bash
export HF_HUB_OFFLINE=1
run() {  # $1 = prompt file, $2 = image folder, $3 = output dir
  python experiments/mirage/run_poc.py --official-repo /workspace/mirage-official \
    --image-folder "$2" --prompt-file "$1" \
    --model-path /workspace/checkpoints/mirage-llama3.1-8.3B --output-dir "$3" --execute
}
# Fase 1: uma imagem, prompt descritivo. PARAR e reportar se faltar memória (E1).
run experiments/mirage/prompts/vqa.txt /workspace/images/BloodImage_00236 /workspace/runs/smoke/vqa
# Fase 2: uma imagem, prompt JSON (fora das métricas).
run experiments/mirage/prompts/boxes_normalized_padded_square.txt /workspace/images/BloodImage_00236 /workspace/runs/smoke/json
# >>> Ponto de parada: apresentar run.json (VRAM de pico, duração) e as respostas antes de seguir. <<<
# Fase 3: 20 imagens, prompt JSON.
for d in /workspace/images/selected/*/; do id=$(basename "$d"); run experiments/mirage/prompts/boxes_normalized_padded_square.txt "$d" /workspace/runs/json/$id; done
# Fase 4: 20 imagens × 3 classes, formato do treino.
for c in wbc rbc platelets; do for d in /workspace/images/selected/*/; do id=$(basename "$d"); \
  run experiments/mirage/prompts/grounding_$c.txt "$d" /workspace/runs/grounding_$c/$id; done; done
cd /workspace && find runs evidence -type f -exec sha256sum {} + > runs-manifest.sha256
tar -czf mirage-runs.tar.gz runs evidence runs-manifest.sha256
```

**Etapa D, local (YOLO real + relatório; exige autorizar a execução do YOLO):**
1. Trazer `mirage-runs.tar.gz`, conferir com `sha256sum -c` e guardar uma cópia em `/home/visioer/Projetos/backups/`.
2. Escrever o manifesto (`$RUN/manifest.json`):
   - `criteria` da tabela acima;
   - `yolo.model_path`: `~/Downloads/best.onnx`;
   - `mirage`: `checkpoint_name: mirage-llama3.1-8.3B`, as revisões completas, `official_revision: 617751c4ceb6393ca5a73036c41fae2cdf232f29`, `min_gpu_memory_mib: 16000`;
   - os 4 experimentos: `json_prompt` e `training_grounding:{WBC,RBC,Platelets}`, com `prompt_class`;
   - `deviations`.
3. `uv run python -m experiments.e2e.build_report --manifest $RUN/manifest.json`. Ele grava e confere `$RUN/report.json` e `$RUN/evaluations/*.json`.
4. Resumo em `docs/reports/YYYY-MM-DD-real-models-e2e.md`, com as métricas por dimensão da E8, as respostas cruas representativas e as limitações. Versionar só quando os commits forem autorizados.

### Decisões pendentes para a execução real

| # | Decisão | Recomendação |
|---|---|---|
| R1 | Implementar a correspondência ótima (ADR novo) **antes** das métricas reais | Sim |
| R2 (E9) | Excluir da avaliação os IDs do `data/raw` do kit | Sim, e marcar a origem do treino do YOLO como não verificada |
| R3 | Aprovar os limiares da tabela E8 | Aprovar ou ajustar |
| R4 | Desvios do ambiente: `torchvision 0.16.2` (já aprovado) **e `numpy<2`** (novo) | Aprovar |
| R5 | Autorizar a máquina com GPU e os downloads (checkpoint, CLIP, BCCD, pacotes) | Conforme a disponibilidade |
| R6 | Autorizar a execução do YOLO real na etapa D | Sim, junto com a etapa D |
