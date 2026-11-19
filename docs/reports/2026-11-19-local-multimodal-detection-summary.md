---
type: Report
title: Alternativas locais ao MIRAGE para localização de objetos — relatório técnico resumido
description: Síntese para a liderança da investigação de modelos multimodais locais (Florence-2-base-ft e Qwen3-VL-2B Q4_K_M) como detectores em CPU, com a avaliação quantitativa no BCCD (20 imagens) contra o YOLO de referência, limitações e conclusão.
tags:
- qwen3-vl
- florence2
- yolo
- bccd
- evaluation
- summary
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-19T13:09:14-03:00"
evidence_basis: [verified, hypothesis]
sources:
- id: evaluation-report
  resource: docs/reports/2026-11-18-qwen3vl-bccd-evaluation.md
  title: Relatório completo da avaliação no BCCD (fonte de todas as métricas deste resumo)
- id: outputs
  resource: outputs/e2e/2026-11-18-qwen3vl-bccd/ (fora do Git; 474 arquivos em SHA256SUMS; report.json SHA-256 bbad3aec2a0f92aca545e3c7654f53ce72e50a9237307dc6900288a389fa468b)
  title: Evidências de execução da avaliação
- id: bccd
  resource: https://github.com/Shenggan/BCCD_Dataset (commit d272fb14cdff6e473fafeeeba32aba5f560e9e43, MIT)
  title: BCCD
---

# Alternativas locais ao MIRAGE para localização de objetos (resumo, 19/11/2026)

> **Natureza deste documento:** síntese dos relatórios de 18/11/2026. **Nenhum modelo foi executado e nenhuma métrica foi recalculada** para escrevê-lo. Todos os números vêm, sem alteração, do [relatório completo da avaliação](2026-11-18-qwen3vl-bccd-evaluation.md), que continua sendo a fonte de verdade.

## Sumário executivo

- **Pergunta:** existe um modelo multimodal **local**, executável em CPU nesta máquina, que receba imagem + texto e devolva **localizações de objetos** utilizáveis, como alternativa ao MIRAGE (que exige GPU NVIDIA e nunca foi executado neste projeto)?
- **Resposta, nesta configuração e amostra:** a execução local é **tecnicamente viável**, mas o desempenho como **detector** é **insuficiente** para adoção.
  - No BCCD (20 imagens, 308 objetos anotados), o Qwen3-VL-2B obteve precisão **0,307** e revocação **0,286**, contra **0,763** e **0,731** do YOLO de referência; não localizou nenhuma plaqueta (0/27) e gerou ~10 falsos positivos por imagem, a ~35 s por imagem.
  - Pelos critérios definidos **antes** da execução, o resultado formal é **inconclusivo** (nenhum sinal positivo; o sinal negativo não foi atingido por pouco). A seção 7 explica por que, mesmo assim, ele não justifica a adoção.

## 1. Objetivo

Investigar uma alternativa **local** ao MIRAGE capaz de receber uma imagem e um texto e produzir **caixas delimitadoras** (bounding boxes) de objetos, integrável ao pipeline existente:

`imagem + prompt → modelo → resposta em texto → JSON de detecções → DetectionContent → imagem anotada → avaliação`

O caso de uso é a contagem e localização de células sanguíneas em três classes: hemácias (RBC), leucócitos (WBC) e plaquetas (Platelets).

## 2. Modelos avaliados

| Modelo | Papel | Como foi executado | Profundidade da avaliação |
|---|---|---|---|
| **Florence-2-base-ft** (Microsoft, MIT; revisão `f6c1a258…`) | Candidato multimodal | PyTorch, CPU, float32, ambiente isolado | **Triagem qualitativa em 1 imagem, sem anotação humana** ([relatório](2026-11-18-florence2-cpu-poc.md)) |
| **Qwen3-VL-2B-Instruct Q4_K_M** + `mmproj` F16 (revisão `52d6c8ff…`) | Candidato multimodal | llama.cpp `b12119`, CPU, binário próprio ([relatório](2026-11-18-qwen3vl-cpu-poc.md)) | **Avaliação quantitativa no BCCD, 20 imagens** |
| **YOLO `v0`** (ONNX, commit `b37eca2`) | **Referência**, não candidato | ONNX Runtime, CPU | Mesma avaliação do Qwen |

**Por que o Florence-2 não seguiu para a avaliação quantitativa** (observado em uma imagem, sem anotação):
- a tarefa `<OD>` rotulou a imagem inteira como *"jellyfish"*: o vocabulário genérico não conhece as classes de hematologia;
- o grounding devolveu **a mesma caixa** para "red blood cells" e "white blood cells" (o leucócito), mais uma caixa da imagem inteira;
- nenhuma hemácia nem plaqueta foi localizada.

O Qwen3-VL segue instruções e devolve JSON com rótulo e coordenadas, por isso foi o escolhido para a medição.

## 3. Ambiente

| Item | Valor (verificado) |
|---|---|
| CPU | Intel Core i5-1235U (10 núcleos, 12 threads); inferência só em CPU (`-t 10`) |
| Memória | ~15 GiB de RAM |
| GPU | Nenhuma NVIDIA; a Iris Xe integrada **não** foi usada |
| Isolamento | Cada modelo em ambiente próprio, fora do `.venv` do projeto; Qwen com teto de **3,5 GiB sem swap** (`systemd-run --user --scope`), um processo por vez |

## 4. Metodologia

**Dados:**
- **BCCD** (commit `d272fb14…`, MIT), divisão `test`.
- **20 imagens** escolhidas por regra fixa (as primeiras elegíveis, em ordem), **excluídas** as 20 imagens do *seed* do kit, que o autor do YOLO declara ter usado no treino (ver seção 7). A seleção foi **congelada e registrada com hash antes de qualquer predição**.
- **308 objetos anotados por humanos:** RBC 260, WBC 21, Platelets 27.

**Configuração do Qwen:**
- parâmetros oficiais de amostragem (`temp 0.7`, `top-p 0.8`, `top-k 20`, `presence-penalty 1.5`), **semente 42**;
- prompt no formato do cookbook oficial; coordenadas relativas 0–1000 convertidas para pixels;
- dois experimentos:
  - **A (detecção conjunta):** um prompt pede as três classes; **o rótulo vem do modelo**. É o experimento principal.
  - **B (condicionado à classe):** um prompt por classe; **a classe vem do prompt**, então não é classificação feita pelo modelo.

**Configuração do YOLO:** confiança ≥ 0,25, NMS 0,5.

**Métricas:**
- Uma predição é **verdadeiro positivo (TP)** se tiver IoU ≥ 0,5 com uma anotação; predições sem par são **falsos positivos (FP)**; anotações sem par são **falsos negativos (FN)**.
- **Pareamento ótimo um-para-um** (algoritmo húngaro): maximiza o número de pares e, depois, a soma de IoU. Uma predição não cobre duas anotações ([ADR 010](../adr/010-optimal-bipartite-matching.md)).
- Duas leituras:
  - **com classe** (detecção): o par também exige a mesma classe;
  - **sem classe** (localização): ignora o rótulo, com matriz de confusão.
- Rótulos do Qwen mapeados **só por igualdade exata** (`red blood cell`→RBC, `white blood cell`→WBC, `platelet`→Platelets).
- **Respostas inválidas contam como FN**, nunca são excluídas.
- **Sem AP/mAP:** o Qwen não fornece confiança por caixa, e o YOLO entra com limiar fixo ([ADR 006](../adr/006-offline-detection-evaluation.md)).

**Integridade:**
- código congelado durante a execução (`code-frozen.SHA256SUMS`, conferido depois);
- resultados registrados num `ExecutionReport` ([ADR 009](../adr/009-execution-report-artifact.md)) com a identidade dos modelos reais, relido e com **todos os hashes conferidos**;
- 80/80 inferências do Qwen e 20/20 do YOLO concluídas, **0 falhas de infraestrutura**.

## 5. Resultados

### 5.1 Comparação geral (detecção com classe, IoU ≥ 0,5)

| Medida | YOLO `v0` (referência) | Qwen3-VL A | Leitura |
|---|---:|---:|---|
| TP / FP / FN | 225 / 70 / 83 | 88 / 199 / 220 | |
| **Precisão** | **0,763** | 0,307 | ~2,5× menor |
| **Revocação** | **0,731** | 0,286 | ~2,6× menor |
| IoU médio dos pares | **0,816** | 0,693 | caixas do Qwen menos justas |
| FP por imagem | **3,5** | 9,95 | |
| Revocação **sem classe** (só localização) | 0,734 | 0,331 | o limite principal do Qwen é localizar, não só classificar |
| Pares com IoU ≥ 0,75 (sem classe) | 82% | 26% | |
| Respostas válidas | não se aplica | A: **20/20**; todos os prompts do Qwen (A + B): **79/80** | a inválida (prompt B "white blood cell", JSON cortado pelo limite de tokens) conta como FN |
| Confiança por caixa | Sim | **Não** | sem limiar, ranqueamento nem AP |
| **Latência por imagem** | ~0,1 a 0,2 s | **35,3 s** (A; até 60 s) | ~180 a 350× mais lento |
| **Memória** | não medida (pequena) | pico do cgroup ≤ **2,90 GiB**; RSS ~3,26 GiB (inclui o GGUF mapeado) | cabe na máquina |

### 5.2 Por classe (TP / FP / FN · precisão / revocação)

| Classe (anotados) | YOLO | Qwen A |
|---|---|---|
| RBC (260) | 194 / 66 / 66 · 0,746 / 0,746 | 68 / 151 / 192 · 0,311 / 0,262 |
| WBC (21) | 21 / 3 / 0 · 0,875 / **1,000** | 20 / 41 / 1 · 0,328 / **0,952** |
| Platelets (27) | 10 / 1 / 17 · 0,909 / 0,370 | **0 / 7 / 27** · 0 / 0 |

**Experimento B** (classe dada no prompt; só localização): revocação WBC **0,905**, RBC 0,254, plaquetas **0,074** (precisão 0,014).

### 5.3 Leitura

- O Qwen **localiza bem o leucócito**, a célula grande e saliente (revocação 0,95), mas com ~2 FP por imagem nessa classe: marca hemácias como "white blood cell".
- Ignorando a classe, recupera 14 localizações a mais (11 hemácias e 3 plaquetas rotuladas como leucócito). Ainda assim, a revocação de localização fica em 0,33.
- O YOLO é superior em todas as medidas desta amostra, com as ressalvas da seção 7.

## 6. Principais dificuldades observadas

1. **Hemácias sobrepostas:** são 84% dos objetos. O Qwen omite muitas, gera caixas que cobrem mais de uma célula e, às vezes, uma caixa de quase a imagem inteira (no experimento B-RBC: 3 caixas ≥ 80% da imagem e 26 pares quase duplicados).
2. **Plaquetas pequenas:** 0/27 no experimento A. Quando pedidas explicitamente (B), o modelo devolve em geral **a caixa do leucócito rotulada "platelet"** (as 148 caixas têm área mediana ~4,6% da imagem, tamanho de hemácia). O YOLO também tem a pior revocação nessa classe (0,37).
3. **Falsos positivos:** ~10 por imagem no Qwen A, sobretudo hemácias rotuladas como leucócito e caixas imprecisas.
4. **Limitações estruturais da geração de caixas por modelos multimodais:**
   - as coordenadas são **texto gerado** token a token, sem cabeça de detecção nem NMS;
   - **não há confiança por caixa**, o que impede limiar, ranqueamento e AP/mAP;
   - a saída longa pode ser **cortada** (1/80 com `-n 1024`) ou degenerar em repetição;
   - a resposta varia com a **amostragem**, e só uma semente foi medida;
   - depende de um adaptador estrito (JSON puro, convenção de coordenadas explícita) para não inventar dados.

## 7. Limitações metodológicas e leitura formal

**Limitações:**
- **Amostra:** 20 imagens e 308 objetos (21 WBC, 27 plaquetas), sem intervalos de confiança; os resultados são **exploratórios**.
- **Uma semente** (42): a variabilidade entre execuções do Qwen não foi medida.
- **Possível sobreposição com dados de treino:**
  - YOLO: as 20 imagens não estão no conjunto que o autor declara ter usado no treino, mas o `dataset/` real não está disponível. Risco **baixo**, ausência **não comprovada** ([proveniência](2026-11-18-qwen3vl-bccd-pilot.md#proveniência-do-yolo-v0-investigada-em-18112026-só-leitura-aprovada-pelo-usuário)).
  - Qwen: o pré-treino não é público; o BCCD é um conjunto público e antigo.
- **Arquiteturas com objetivos distintos:** o YOLO é um detector especializado, treinado nas três classes; o Qwen é um modelo geral de linguagem e visão, sem ajuste. A comparação mede a **distância até um detector de referência**, não uma disputa entre modelos equivalentes.
- **Anotações do BCCD:** hemácias sobrepostas possivelmente não anotadas podem inflar os FP dos dois modelos (**hipótese** não medida).
- **Configuração única do Qwen:** um tamanho de modelo (2B), uma quantização (Q4_K_M) e a resolução original; versões maiores não foram testadas (que caibam nesta máquina é **hipótese** não verificada).

**Critérios pré-registrados (definidos antes da execução):**

| Critério | Qwen A |
|---|---|
| Respostas válidas ≥ 0,8 | 1,00 ✔ |
| **Sinal positivo:** em alguma classe, precisão ≥ 0,5, revocação ≥ 0,5, IoU médio ≥ 0,6 e FP/imagem ≤ 1 | **Não atingido** (melhor classe: WBC, precisão 0,33 e ~2 FP/imagem) |
| **Sinal negativo:** respostas válidas < 0,5 **ou** precisão < 0,2 em **todas** as classes | Não atingido (RBC 0,31 e WBC 0,33) |
| **Leitura formal** | **Inconclusivo** |

**Por que o resultado inconclusivo não justifica a adoção como detector:** o critério negativo foi pensado para descartar um modelo que **não funciona**; ele não diz que o modelo é **suficiente**. Para adotar, seria preciso um sinal positivo, e nenhuma classe chegou perto dele. Além disso, fatores fora dos critérios pesam contra:
- ~10 FP por imagem e plaquetas não localizadas (0/27), inaceitáveis para contagem celular;
- ausência de confiança por caixa, que impede ajustar o ponto de operação;
- latência ~180 a 350× maior que a do detector de referência;
- o melhor resultado (WBC) cobre só 7% dos objetos e é justamente o caso mais fácil.

## 8. Conclusão

- **Viabilidade técnica: confirmada.** Um modelo multimodal quantizado roda localmente em CPU (~35 s por imagem, ≤ 3 GiB), devolve caixas reais em JSON válido (79 de 80 respostas; 20/20 no experimento A) e o pipeline completo funcionou de ponta a ponta: `TextReference` → adaptador → `DetectionReference` → visualizador → avaliador → `ExecutionReport`.
- **Desempenho como detector: insuficiente** neste caso de uso, nesta configuração e nesta amostra.
- **Recomendação:** não adotar o Qwen3-VL-2B como detector de células. O Florence-2-base-ft **não foi avaliado quantitativamente**; a triagem qualitativa em uma imagem não justificou levá-lo adiante. Os modelos multimodais generativos continuam candidatos para **perguntas e respostas sobre a imagem** (VQA), não para localização precisa.

## 9. Referências e evidências

**Relatórios e decisões (no Git, em `docs/`):**
- [Avaliação completa no BCCD, 20 imagens](2026-11-18-qwen3vl-bccd-evaluation.md): fonte de todas as métricas.
- [Piloto em 2 imagens e proveniência do YOLO](2026-11-18-qwen3vl-bccd-pilot.md).
- [Qwen3-VL em CPU](2026-11-18-qwen3vl-cpu-poc.md) e [Florence-2 em CPU](2026-11-18-florence2-cpu-poc.md): provas de conceito.
- [Plano da avaliação](../plans/2026-11-18-plan-qwen3vl-bccd-evaluation.md), com os critérios pré-registrados.
- [ADR 006](../adr/006-offline-detection-evaluation.md) (avaliador offline), [ADR 009](../adr/009-execution-report-artifact.md) (`ExecutionReport`), [ADR 010](../adr/010-optimal-bipartite-matching.md) (pareamento ótimo).

**Evidências de execução (fora do Git, nesta máquina):**
- `outputs/e2e/2026-11-18-qwen3vl-bccd/report.json`: `ExecutionReport` (100 execuções, 12 avaliações), SHA-256 `bbad3aec2a0f92aca545e3c7654f53ce72e50a9237307dc6900288a389fa468b` (conferido em 19/11/2026).
- `outputs/e2e/2026-11-18-qwen3vl-bccd/SHA256SUMS`: hashes de 474 arquivos.
- `outputs/e2e/2026-11-18-qwen3vl-bccd/code-frozen.SHA256SUMS`: código congelado durante a execução.
- `.../evaluations/*.json`: métricas por imagem, pares, IoU e matriz de confusão.
- `.../qwen3vl/<experimento>/<imagem>/annotated.png`, `.../yolo/<imagem>/annotated.png` e `.../ground-truth/`: imagens anotadas para inspeção visual. Exemplos: `qwen3vl/class_conditioned-Platelets/BloodImage_00041/annotated.png` (leucócito rotulado "platelet") e `qwen3vl/joint_detection/BloodImage_00041/annotated.png` (hemácias rotuladas "white blood cell").
- `.../qwen3vl-runs/<imagem>/`: respostas brutas do modelo e evidências de inferência real.

**Código (no repositório, não commitado):** `experiments/e2e/` (pipelines, relatório, anotações do BCCD), `experiments/qwen3vl/` (executor e adaptador), `experiments/mirage/evaluate_detections.py` (avaliador).
