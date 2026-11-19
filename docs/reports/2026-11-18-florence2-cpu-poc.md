---
type: Report
title: Florence-2-base-ft em CPU — prova de conceito com BloodImage_00236
description: Primeira inferência real de um modelo multimodal alternativo ao MIRAGE na máquina local (CPU, float32) — tempos, memória, saídas brutas, caixas e viabilidade.
tags:
- florence2
- poc
- cpu
- detection
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T14:55:00-03:00"
evidence_basis: [verified, hypothesis]
sources:
- id: model
  resource: https://huggingface.co/microsoft/Florence-2-base-ft (revisão f6c1a25888ffc1d945ee8a1a77ac833c7303d46e)
  title: Florence-2-base-ft (Microsoft, MIT)
- id: run
  resource: experiments/florence2/outputs/2026-11-18-cpu-fp32/ (fora do Git; hashes em outputs/SHA256SUMS)
  title: Saídas brutas da execução
---

# Florence-2-base-ft em CPU (18/11/2026)

**Inferência real executada.** Não houve simulador, mock nem resposta sintética. É uma imagem só: o resultado é **exploratório**.

## Configuração (verificada)

| Item | Valor |
|---|---|
| Máquina | Intel Core i5-1235U (10 núcleos, 12 threads, AVX2/AVX-VNNI), 15 GiB de RAM (cerca de 4,6 GiB livres no início), Debian 13, kernel 6.12. **Iris Xe não usada** |
| Ambiente | `experiments/florence2/.venv`, isolado; Python 3.12.14; `torch 2.8.0+cpu`; `transformers 4.55.4`; `timm 1.0.19`; `einops 0.8.1` (todas em `requirements.lock.txt`) |
| Modelo | `microsoft/Florence-2-base-ft`, revisão `f6c1a258…`, MIT, sem acesso restrito; `model.safetensors` (463 MB, SHA-256 `58757d65…` igual ao publicado); float32, CPU, 10 threads |
| Código remoto | `configuration_`, `modeling_` e `processing_florence2.py` revisados: sem rede, subprocesso, `eval`/`exec`, gravação de arquivo nem pickle. `flash_attn` só se disponível. Hashes fixados no script |
| Imagem | `/home/visioer/Downloads/BloodImage_00236.jpg`, 640×480, sem EXIF de rotação, SHA-256 `413d00ab…` |
| Geração | Parâmetros do README oficial (`max_new_tokens=1024`, `num_beams=3`, `do_sample=False`) **+ `use_cache=False`** |

## Problemas encontrados e como foram contornados

1. **Carregamento:** `AttributeError: 'Florence2ForConditionalGeneration' object has no attribute '_supports_sdpa'`.
   - **Causa:** a propriedade do código remoto lê `self.language_model` antes de ele existir, e o `transformers` 4.55 a consulta durante o `__init__`.
   - **Contorno:** `attn_implementation="eager"`, uma opção oficial da API que pula a checagem.
2. **Geração:** `KeyError: 'Cache only has 0 layers, attempted to access layer with index 0'` nas 4 tarefas, com o modelo já carregado.
   - **Causa:** o código remoto é incompatível com o cache novo do `transformers` 4.5x.
   - **Contorno:** `use_cache=False`. O algoritmo de decodificação não muda, mas fica mais lento.
   - A tentativa que falhou está preservada em `outputs/2026-11-18-attempt1-cache-error/run.json`.

Nenhum dos dois altera o código do modelo nem as versões. **Hipótese não testada:** uma versão anterior do `transformers` (por exemplo, 4.49) dispensaria os dois contornos e permitiria o cache KV, deixando a inferência mais rápida. Trocar de versão fica para decidir com o usuário.

## Tempo e memória (verificados)

| Medida | Valor |
|---|---|
| Importação (`torch`, `transformers`) | 3,8 s |
| Carregamento do modelo + processador | **1,6 s** |
| RSS depois da carga | 1 280 MiB |
| **Pico de RSS do processo** | **1 738 MiB** |
| `<OD>` | 12,4 s (10 tokens gerados) |
| Grounding "red blood cells" | 11,3 s (14 tokens) |
| Grounding "white blood cells" | 8,6 s (14 tokens) |
| Grounding "platelets" | 7,8 s (9 tokens) |

## O que o modelo produziu (saídas brutas reais)

| Tarefa e prompt | Saída bruta | Caixas (pixels) e rótulos | Leitura |
|---|---|---|---|
| `<OD>` | `</s><s>jellyfish<loc_0><loc_0><loc_998><loc_998></s>` | `jellyfish` `[0,3, 0,2, 639,0, 479,3]`: **99,6% da imagem** | Rótulo errado (vocabulário genérico); nenhuma célula detectada |
| `<CAPTION_TO_PHRASE_GROUNDING>red blood cells` | `…red blood cells<loc_3><loc_0><loc_998><loc_998><loc_312><loc_451><loc_675><loc_900></s>` | imagem inteira (99,3%) + `[200,0, 216,7, 432,3, 432,2]` (16,3%) | A segunda caixa é o **glóbulo branco**, não hemácias; nenhuma hemácia foi localizada |
| `…white blood cells` | **idêntica à anterior** | imagem inteira + `[200,0, 216,7, 432,3, 432,2]` | A segunda caixa envolve **visualmente bem** o glóbulo branco (conferido na imagem anotada; sem anotação humana) |
| `…platelets` | `…platelets<loc_3><loc_0><loc_998><loc_998></s>` | só a imagem inteira | Plaquetas não localizadas |

**Interpretação** (exploratória, uma imagem, sem anotação humana):
- O modelo localiza o **objeto mais saliente**, o glóbulo branco, com boa precisão visual, mas **não discrimina a frase**: dá a mesma caixa para "red" e "white blood cells".
- Em todas as tarefas aparece uma caixa da imagem inteira.
- O `<OD>` não conhece as classes de hematologia.
- As classes registradas no grounding vêm do **prompt** (`class_source = prompt`), não de uma classificação do modelo.

## Arquivos (fora do Git; hashes em `experiments/florence2/outputs/SHA256SUMS`)

- `experiments/florence2/outputs/2026-11-18-cpu-fp32/run.json`: execução completa.
- `.../task-{0..3}-raw.txt`: respostas brutas.
- `.../task-{0..3}-detections.json`: `DetectionContent` com `conf: null`.
- `.../task-{0..3}-annotated.png`: imagens anotadas pelo `DetectionVisualizationComponent`.
- `.../summary.json`: status, rótulos e fração de área de cada caixa.

## Viabilidade

| Pergunta | Resposta |
|---|---|
| Roda na CPU desta máquina? | **Sim.** 1,7 GiB de pico e cerca de 8 a 12 s por tarefa, com `use_cache=False` |
| Integração técnica | **Viável.** A saída já vem estruturada em pixels; um adaptador mínimo (`experiments/florence2/florence_detections.py`) produz `DetectionContent` e reutiliza o visualizador. Um `ObjectDetector` futuro ficaria **fora do processo** (ambiente próprio), como o MIRAGE |
| Útil como detector de RBC, WBC e Platelets sem ajuste? | **Não**, nesta amostra: rótulos genéricos, caixa da imagem inteira e a mesma caixa para frases diferentes. Uma avaliação com anotações humanas (BCCD) mediria isso com números |
| Próximo passo sugerido | Testar o **Qwen3-VL-2B-Instruct quantizado**, que segue instruções e produz coordenadas com rótulo. Opcional: repetir o Florence-2 com outro `transformers` (cache KV) e com o `-large` |
