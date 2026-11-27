---
type: Report
title: Piloto da avaliação quantitativa — Qwen3-VL-2B e YOLO em 2 imagens do BCCD
description: Primeiras métricas reais com anotações humanas (BloodImage_00007 e 00011), pareamento ótimo, com e sem classe, experimentos A e B do Qwen e YOLO de referência; integridade do pipeline e análise de erros. Preliminar.
tags:
- qwen3-vl
- yolo
- evaluation
- bccd
- pilot
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T16:19:32-03:00"
evidence_basis: [verified, hypothesis]
sources:
- id: outputs
  resource: outputs/e2e/2026-11-18-qwen3vl-bccd/ (fora do Git; hashes em SHA256SUMS)
  title: Execuções, avaliações e relatório verificado
- id: bccd
  resource: https://github.com/Shenggan/BCCD_Dataset (commit d272fb14cdff6e473fafeeeba32aba5f560e9e43, MIT)
  title: BCCD
---

# Piloto: Qwen3-VL-2B e YOLO em 2 imagens do BCCD (18/11/2026)

> **Leia antes dos números:**
> - **Duas imagens não estabelecem superioridade de nenhum modelo.** Este piloto valida o pipeline e mostra os primeiros erros reais.
> - O **Qwen3-VL** é avaliado como **alternativa multimodal local ao MIRAGE** (imagem + texto → caixas em texto).
> - O **YOLO** é um **detector especializado**, treinado para estas três classes e com confiança por caixa. São arquiteturas e propósitos diferentes.
> - A **procedência do treino do YOLO é incompleta**: o conjunto de dados usado pelo autor não está disponível. Risco de vazamento **considerado baixo**, ausência **não comprovada** (veja a seção "Proveniência do YOLO `v0`"). Isso limita qualquer conclusão comparativa.

## Configuração (verificada)

- **Imagens:** BloodImage_00007 e BloodImage_00011, as duas primeiras da seleção congelada.
  - O piloto é um subconjunto derivado (`pilot/selection-pilot.json`), com o hash da seleção de origem e o mesmo `created_at`. A seleção **não foi alterada**.
  - **37 objetos anotados:** RBC 34, WBC 2, Platelets 1.
- **Qwen3-VL-2B-Instruct:** Q4_K_M + `mmproj` F16, revisão `52d6c8ff…`; llama.cpp `b12119`; `official_sampling`, seed 42; resolução original; `-c 4096`, `-n 1024`; teto de 3,5 GiB sem swap.
  - **Experimento A** (`joint_detection`): um prompt com as três classes; **a classe vem do modelo**.
  - **Experimento B** (`class_conditioned:<classe>`): um prompt por classe; **a classe vem do prompt**, então não é classificação independente.
- **YOLO:** `best.onnx` (SHA-256 `0e9bcbd6…`), limiar de confiança 0,25, NMS 0,5, CPU.
- **Avaliação:** pareamento **ótimo** ([ADR 010](../adr/010-optimal-bipartite-matching.md)), IoU ≥ 0,5, com e sem classe.
  - Rótulos do Qwen mapeados **só por correspondência exata** (`red blood cell`→RBC, `white blood cell`→WBC, `platelet`→Platelets), com os originais preservados.
  - Sem AP/mAP para o Qwen, que não dá confiança.

## Integridade (verificada antes e depois)

| Verificação | Resultado |
|---|---|
| Seleção, imagens, XML e 743 arquivos do BCCD | Hashes conferem; clone sem alterações locais |
| Convenção de pixels do BCCD (origem em 1) | **Inferida:** sem zeros; **237 caixas em x = 1 e 237 em x = 640** (bordas simétricas, recorte em [1, W]); README: "VOC format". Não há especificação formal |
| **Sensibilidade à convenção** | Origem em 0 contra origem em 1: TP, FP e FN **idênticos** nos dois modelos; IoU médio varia ≤ 0,002 |
| Mesmo sistema de coordenadas | Anotações desenhadas sobre a imagem (`pilot/ground-truth/`) caem sobre as células; Qwen (0–1000 → pixels da imagem original) e YOLO (*letterbox* removido) estão em pixels da mesma imagem |
| Associação imagem ↔ prompt ↔ resposta | `run.json` de cada imagem com o SHA-256 da imagem selecionada; o prompt registrado corresponde ao nome |
| Evidência de inferência real | **Qwen: 8/8** verificações em todas as 8 respostas; **YOLO: 4/4** nas 2 imagens |
| Memória | Qwen: pico do cgroup 2,90 GiB (00007) e 2,63 GiB (00011); `VmHWM` ~3,26 GiB; `VmSwap` 0; nenhum OOM. O YOLO e o relatório rodaram dentro do mesmo teto |
| Relatório | `ExecutionReport` gravado, **relido** (`ExecutionReportReference.materialize()`) e **todos os hashes conferidos** (`verify_report` = []) |
| Falhas | **Nenhuma** falha de infraestrutura e **nenhuma** resposta inválida (8/8 JSON válidos) |

Como não houve falhas, as visões "inferências concluídas" e "respostas válidas" coincidem com "todas as imagens" e não foram geradas. Os rótulos sobrepostos nas imagens anotadas podem ficar ilegíveis; por isso as classes foram **conferidas nos dados**, e não nas imagens.

## Métricas reais (2 imagens; IoU ≥ 0,5; pareamento ótimo)

| Pipeline / experimento | Modo | TP | FP | FN | Precisão | Revocação | IoU médio | FP/imagem |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **YOLO** | com classe | 16 | 10 | 21 | 0,62 | 0,43 | 0,84 | 5,0 |
| YOLO | sem classe | 16 | 10 | 21 | 0,62 | 0,43 | 0,84 | 5,0 |
| **Qwen A** (conjunto) | com classe | 2 | 12 | 35 | 0,14 | 0,05 | 0,72 | 6,0 |
| Qwen A | sem classe | 3 | 11 | 34 | 0,21 | 0,08 | 0,69 | 5,5 |
| **Qwen B — WBC** | com classe | 2 | 0 | 0 | 1,00 | 1,00 | 0,73 | 0,0 |
| Qwen B — RBC | com classe | 0 | 2 | 34 | 0,00 | 0,00 | — | 1,0 |
| Qwen B — Platelets | com classe | 0 | 2 | 1 | 0,00 | 0,00 | — | 1,0 |

No experimento B, cada classe é avaliada só contra as anotações daquela classe. Os modos com e sem classe deram os mesmos números.

**Por classe (com classe; TP / FP / FN):**

| Classe | YOLO | Qwen A |
|---|---|---|
| RBC | 14 / 10 / 20 | 0 / 11 / 34 |
| WBC | 2 / 0 / 0 | 2 / 1 / 0 |
| Platelets | 0 / 0 / 1 | 0 / 0 / 1 |

**Matriz de confusão dos pares casados sem classe (anotada → prevista):**
- **YOLO:** RBC→RBC 14, WBC→WBC 2 (diagonal).
- **Qwen A:** WBC→WBC 2, **RBC→WBC 1**, uma hemácia chamada de glóbulo branco.

**Formato e tempo:**
- **Qwen:** 8/8 JSON válidos; 0 duplicatas exatas; 0 quase duplicadas; 0 rótulos fora do vocabulário.
- **Tempo do Qwen por imagem** (4 prompts): 68,2 s (00007) e 63,1 s (00011). Por prompt, de 10,5 a 30,1 s.
- **YOLO:** 0,1 a 0,2 s por imagem.

## Análise dos erros observados (2 imagens; não generalizar)

- **Qwen, hemácias:**
  - **nenhuma** hemácia anotada foi acertada (0/34);
  - no experimento B, o prompt de hemácias devolveu **uma caixa da imagem inteira** nas duas imagens;
  - no A, as caixas "red blood cell" cobrem **grupos de várias células** (por exemplo `[224, 284, 470, 479]` em 00007) e não casam com nenhuma célula individual;
  - em 00011, a resposta A teve só 2 caixas, uma delas a imagem inteira.
- **Qwen, glóbulos brancos:** localizados nas 2 imagens (B: 2/2, IoU médio 0,73). No A, a caixa de 00007 está **deslocada** (IoU 0,51, quase no limiar), e outra caixa "white blood cell" é uma hemácia.
- **Qwen, plaquetas:** **a caixa do glóbulo branco rotulada "platelet"** nas duas imagens (B: 2 FP), o mesmo padrão da imagem 00236. Nenhuma plaqueta localizada.
- **YOLO:**
  - hemácias com precisão 0,58 e revocação 0,41;
  - glóbulos brancos 2/2;
  - a única plaqueta anotada **não foi detectada**.
  - Parte dos FN e FP de hemácias pode refletir as anotações do BCCD, que têm hemácias sobrepostas e possivelmente não anotadas (visível em `pilot/ground-truth/`). **Hipótese não medida.**
- **Coordenadas:** sem sinal de deslocamento sistemático. As caixas do YOLO e o glóbulo branco do Qwen coincidem com as anotações (IoU 0,73 a 0,84).

## Leitura preliminar

- **O pipeline completo funcionou de ponta a ponta com modelos reais:**
  - seleção congelada;
  - inferência com evidências;
  - conversão para `DetectionReference`;
  - imagens anotadas;
  - pareamento ótimo, com e sem classe;
  - `ExecutionReport` persistido, relido e verificado.
- **Observado nestas 2 imagens:**
  - o Qwen localiza bem o glóbulo branco, a célula grande e saliente, quando ela é pedida;
  - **não localiza hemácias individuais nem plaquetas**;
  - confunde a classe de parte das caixas.
- O YOLO acerta muito mais, mas é um detector especializado e com procedência de treino incompleta. **Nenhuma conclusão de superioridade.**

## Arquivos (fora do Git; `outputs/e2e/2026-11-18-qwen3vl-bccd/SHA256SUMS`)

- **Respostas brutas e evidências do Qwen:** `qwen3vl-runs/BloodImage_000{07,11}/` (`run.json`, `*.stdout.txt`, `*.stderr.txt`).
- **Relatório:** `pilot/report/report.json` (`ExecutionReport`); avaliações em `pilot/report/evaluations/*.json`.
- **Imagens anotadas:**
  - `pilot/report/yolo/<id>/annotated.png`;
  - `pilot/report/qwen3vl/<experimento>/<id>/annotated.png`;
  - anotações humanas em `pilot/ground-truth/<id>-ground-truth.png`.
- **Manifesto e seleção do piloto:** `pilot/manifest-pilot.json` e `pilot/selection-pilot.json`.

## Proveniência do YOLO `v0` (investigada em 18/11/2026, só leitura; aprovada pelo usuário)

**Conclusão metodológica:** o risco de vazamento das 20 imagens avaliadas no treino do YOLO é **considerado baixo**, mas **a ausência de vazamento não está comprovada**. O conjunto de dados efetivamente usado pelo autor no treino não está disponível.

**Fatos comprovados:**
- **O v0 está no commit inicial.** `models/v0/best.pt` e `models/v0/best.onnx` estão no **commit inicial `b37eca2`** do kit (16/06/2026 09:00:53 −03:00, autor Fernando Akio Pucci, "Starter kit: desafio de pipeline de MLOps (detector BCCD)"). Nenhum commit posterior alterou `models/v0` nem `data/raw`, e a cópia local é idêntica a esse commit.
- **O upstream não guarda mais histórico.** `aqilputi/mlops-pipeline-challenge` é o repositório original (não é fork; criado em 16/06/2026). Tem **um único commit** (`b37eca2`), 1 branch, nenhuma tag, release, issue ou PR. `iagopirone/mlops-pipeline-challenge` é um fork dele.
- **O ONNX avaliado é o arquivo do commit inicial.** O hash Git de `~/Downloads/best.onnx` é igual ao de `b37eca2:models/v0/best.onnx` (`ec0519be…`; SHA-256 `0e9bcbd6…`).
- **Os scripts do commit inicial só usam o seed.**
  - `src/prep_data.py` lê **apenas `data/raw`** e grava `dataset/data.yaml` com a divisão **70/15/15** (val 0,15, test 0,15, semente 42). Sobre as 91 imagens do seed, isso dá **63 de treino, 14 de validação e 14 de teste** (recalculado).
  - `src/train.py` treina com `project=runs`, 40 épocas por padrão, e exporta para ONNX com `opset=12, simplify=True`.
  - `dataset/` e `runs/` estão no `.gitignore`.
- **Nenhuma das 20 imagens selecionadas está no seed.** As 20 estão em `data/stream`, e nenhuma em `data/raw`. As 91 imagens do `data/raw` são idênticas byte a byte às do BCCD; as 20 de teste do BCCD que estavam nele foram excluídas da seleção.
- **Os treinos posteriores não afetam o v0.** Os retreinos e `storage/datasets/` vêm do pipeline do desafio, não do v0, e não alteraram `models/v0`.

**Declarações documentadas do autor** (README e `ATIVIDADE.md` do commit `b37eca2`; não verificáveis de forma independente):
- *"Modelo inicial v0 … detector já treinado no seed"*;
- *"O modelo `v0` foi treinado só no seed — ele é fraco de propósito"*;
- o enunciado diz que o seed (~10–20% das imagens) *"treina o modelo inicial v0"*.

**Indícios técnicos** (coerentes, não provas):
- **Metadados do `best.pt`** (lidos como texto, **sem desserializar**):
  - dados `…/mlops-pipeline-challenge/dataset/data.yaml`, a saída padrão do `prep_data.py`;
  - `save_dir` `runs/v0_train`;
  - data 2026-06-16T08:59:55;
  - Ultralytics 8.4.60;
  - épocas provavelmente 40 (pelo byte do opcode, não confirmado).
- **Relação PT → ONNX:**
  - o ONNX tem data 09:00:11, **16 s depois** do `best.pt`;
  - mesma versão, descrição, caminho de dados, classes e `imgsz`;
  - `opset 12` e `simplify True`, os parâmetros do `train.py`;
  - os dois foram versionados juntos no commit de 09:00:53.

  Os hashes de `.pt` e `.onnx` **não são comparáveis**, e a exportação funde camadas; a comparação numérica dos pesos **não foi feita**, por decisão do usuário.

**Informações indisponíveis:**
- o conteúdo real de `dataset/` (`data.yaml`, listas de treino, validação e teste) na máquina do autor (`/home/apucci73`);
- se o `data/raw` do autor no momento do treino era igual ao publicado;
- os argumentos efetivos (`--raw`, `--name`, semente) e os logs de `runs/v0_train` (`args.yaml`, `results.csv`).

**Qwen3-VL:** o pré-treino não é público e o BCCD está disponível desde 2017; vazamento **não verificável**.

## Próximo passo (aguarda autorização)

As **18 imagens restantes** da seleção congelada, com a mesma configuração.
- **Custo estimado pelo piloto:** ~66 s por imagem no Qwen, ou **~20 min** (até ~40 min com respostas longas), mais o YOLO em segundos.
