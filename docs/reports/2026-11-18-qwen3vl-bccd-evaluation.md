---
type: Report
title: Avaliação quantitativa do Qwen3-VL-2B no BCCD (20 imagens) com YOLO de referência
description: Métricas reais com anotações humanas, pareamento ótimo, com e sem classe, experimentos A (detecção conjunta) e B (condicionado à classe), custo em CPU, viabilidade como alternativa ao MIRAGE e limitações. Exploratório.
tags:
- qwen3-vl
- yolo
- evaluation
- bccd
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T17:05:14-03:00"
evidence_basis: [verified, hypothesis]
sources:
- id: outputs
  resource: outputs/e2e/2026-11-18-qwen3vl-bccd/ (fora do Git; 474 arquivos com SHA-256 em SHA256SUMS; report.json SHA-256 bbad3aec…)
  title: Execuções, avaliações, imagens anotadas e ExecutionReport verificado
- id: bccd
  resource: https://github.com/Shenggan/BCCD_Dataset (commit d272fb14cdff6e473fafeeeba32aba5f560e9e43, MIT)
  title: BCCD
---

# Avaliação do Qwen3-VL-2B no BCCD (20 imagens, 18/11/2026)

> **Como ler:**
> - O **Qwen3-VL-2B** é avaliado como **alternativa multimodal local ao MIRAGE** (imagem + texto → caixas em texto).
> - O **YOLO `v0`** é um **detector especializado**, treinado para as três classes, com confiança por caixa; está aqui só como **referência**.
> - A procedência do treino do YOLO é **incompleta**: risco de vazamento **considerado baixo**, ausência **não comprovada** (veja a [proveniência](2026-11-18-qwen3vl-bccd-pilot.md#proveniência-do-yolo-v0-investigada-em-18112026-só-leitura-aprovada-pelo-usuário)). O pré-treino do Qwen não é público.
> - **20 imagens e uma semente** (Qwen com amostragem, seed 42): resultados **exploratórios**, sem intervalos de confiança.

## 1. Configuração (verificada)

- **Dados:** 20 imagens da divisão `test` do BCCD (commit `d272fb14…`), as primeiras elegíveis em ordem, excluídas as 20 que estão no seed do kit.
  - Seleção **congelada** às 19:09:51Z; hashes `d60d4be9…` (anotações) e `2e106326…` (seleção), conferidos antes e depois.
  - **308 objetos:** RBC 260, WBC 21, Platelets 27.
  - Pixels com origem em 1, **inferido**; a sensibilidade testada no piloto não mudou TP/FP/FN.
- **Qwen3-VL-2B-Instruct:** Q4_K_M + `mmproj` F16, revisão `52d6c8ff…`; llama.cpp `b12119` (commit `6f1e6543`); `official_sampling` (`temp 0.7`, `top-p 0.8`, `top-k 20`, `min-p 0`, `presence-penalty 1.5`), seed 42; resolução original; `-c 4096`, `-n 1024`; teto de 3,5 GiB sem swap; um processo por vez.
  - **A, `joint_detection`:** um prompt com as três classes; **o rótulo vem do modelo**.
  - **B, `class_conditioned:<classe>`:** um prompt por classe; **a classe vem do prompt**, e **não** é classificação feita pelo modelo.
  - Prompts no formato do cookbook oficial; coordenadas relativas de 0 a 1000 → pixels.
- **YOLO:** `models/v0/best.onnx` do commit `b37eca2` (SHA-256 `0e9bcbd6…`), confiança ≥ 0,25, NMS 0,5, CPU.
- **Avaliação:**
  - pareamento **ótimo** um-para-um, com IoU ≥ 0,5 ([ADR 010](../adr/010-optimal-bipartite-matching.md));
  - **com classe** (detecção) e **sem classe** (localização), com matriz de confusão;
  - rótulos do Qwen mapeados só por correspondência exata (`red blood cell`→RBC, `white blood cell`→WBC, `platelet`→Platelets), com os originais preservados;
  - **sem AP/mAP**: o Qwen não dá confiança, e o YOLO entra no limiar fixo.
- **Integridade:**
  - código congelado durante a execução (`code-frozen.SHA256SUMS` conferido depois);
  - piloto preservado e conferido;
  - `ExecutionReport` gravado, **relido** e com **todos os hashes conferidos**: 100 execuções, 12 avaliações, `verify_report` = [].

## 2. Execução

| Item | Resultado |
|---|---|
| Inferências do Qwen | **80/80** prompts com `returncode 0`, **8/8 verificações de inferência real** em todas |
| YOLO | 20/20 imagens, 4/4 verificações |
| **Falhas de infraestrutura** | **0** |
| **Inferência concluída com saída inválida** | **1/80**: "white blood cell" em BloodImage_00068, com ~10 caixas "white blood cell" sobre hemácias e JSON **cortado** (provável limite de `-n 1024`). Zero detecções utilizáveis, contadas como FN |
| Memória do Qwen | Pico do cgroup **2,16 a 2,90 GiB** por imagem; `VmHWM` ~3,26 GiB; **swap do processo 0**; **0 OOM** |

## 3. Desempenho (todas as imagens; IoU ≥ 0,5; pareamento ótimo)

### 3.1 Detecção com classe

| Modelo / experimento | TP | FP | FN | Precisão | Revocação | IoU médio | FP/imagem |
|---|---:|---:|---:|---:|---:|---:|---:|
| **YOLO** | 225 | 70 | 83 | **0,763** | **0,731** | **0,816** | 3,5 |
| **Qwen A** (conjunto) | 88 | 199 | 220 | 0,307 | 0,286 | 0,693 | 9,95 |

**Por classe (TP / FP / FN · precisão / revocação):**

| Classe (anotados) | YOLO | Qwen A |
|---|---|---|
| RBC (260) | 194 / 66 / 66 · 0,746 / 0,746 | 68 / 151 / 192 · 0,311 / 0,262 |
| WBC (21) | 21 / 3 / 0 · 0,875 / **1,000** | 20 / 41 / 1 · 0,328 / **0,952** |
| Platelets (27) | 10 / 1 / 17 · 0,909 / 0,370 | **0 / 7 / 27** · 0 / 0 |

### 3.2 Localização sem classe e confusão (resposta à pergunta 3)

| Modelo | TP | FP | FN | Precisão | Revocação | IoU médio | IoU mediano | Pares com IoU ≥ 0,75 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| YOLO | 226 | 69 | 82 | 0,766 | 0,734 | 0,816 | 0,829 | 82% |
| Qwen A | **102** | 185 | 206 | 0,355 | 0,331 | 0,684 | 0,674 | 26% |

**Matriz de confusão (anotada → prevista):**
- **Qwen A:**
  - RBC → RBC 68, **RBC → WBC 11**;
  - WBC → WBC 20;
  - **Platelets → WBC 3**.
- **YOLO:** RBC → RBC 194, WBC → WBC 21, Platelets → Platelets 10, Platelets → WBC 1.

**Leitura:** sim, o Qwen **localiza alguns objetos que classifica errado**. Sem classe, ele recupera **14 localizações a mais** (102 contra 88): 11 hemácias e 3 plaquetas chamadas de glóbulo branco. Mesmo assim, a revocação de localização fica em 0,33, contra 0,73 do YOLO, e as caixas casadas são menos justas (IoU mediano 0,67 contra 0,83).

### 3.3 Localização condicionada à classe (Qwen B; a classe vem do prompt)

| Prompt | TP | FP | FN | Precisão | Revocação | IoU médio | Imagens com ≥ 1 acerto | Observação |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| red blood cell | 66 | 183 | 194 | 0,265 | 0,254 | 0,675 | 15/20 | 249 caixas; 26 pares quase duplicados; 3 caixas ≥ 80% da imagem |
| white blood cell | 19 | 45 | 2 | 0,297 | **0,905** | 0,738 | 17/19 | 64 caixas: acha o glóbulo branco, mas marca hemácias como "white blood cell"; 1 saída inválida |
| platelet | **2** | 146 | 25 | **0,014** | 0,074 | 0,719 | 2/14 | 148 caixas de área mediana ~4,6% da imagem (tamanho de hemácia); em geral **a caixa do glóbulo branco rotulada "platelet"** |

- **Visões complementares** do prompt "white blood cell" (registradas no relatório):
  - **inferências concluídas**: igual a todas as imagens, porque não houve falha de infraestrutura;
  - **só respostas válidas** (18 imagens com WBC anotado): TP 19, FN 1, revocação 0,95.
- **Formato:** JSON válido em 99/100 respostas; **nenhuma caixa duplicada exata**; quase duplicadas (mesmo rótulo, IoU ≥ 0,5): A 5, B-RBC 26, B-WBC 1, B-plaquetas 3; nenhum rótulo fora do vocabulário.

### 3.4 Critérios pré-registrados (E8; exploratórios)

| Critério | Qwen A |
|---|---|
| Taxa de respostas válidas ≥ 0,8 | 1,00 ✔ |
| Em alguma classe: precisão ≥ 0,5, revocação ≥ 0,5, IoU médio ≥ 0,6 e FP/imagem ≤ 1 | **Não**: melhor classe WBC com precisão 0,33 e ~2 FP/imagem; RBC e plaquetas abaixo |
| Sinal negativo: respostas válidas < 0,5 **ou** precisão < 0,2 em **todas** as classes | Não atingido (RBC 0,31 e WBC 0,33) |
| **Leitura formal** | **Inconclusivo**: nenhum sinal positivo; o critério negativo não é atingido por pouco |

## 4. Custo computacional na CPU (pergunta 4)

| Medida | Valor |
|---|---|
| Máquina | i5-1235U (10 núcleos, `-t 10`), 15 GiB de RAM; sem GPU |
| Qwen, por imagem (4 prompts) | média **110,6 s** (63 a 156 s); total **36,9 min** para 20 imagens |
| Qwen, só o experimento A (1 prompt) | média **35,3 s** por imagem (até 60 s) |
| Qwen, por prompt | RBC 32,6 s; WBC 19,3 s; plaquetas 23,4 s; conjunto 35,3 s (médias) |
| Memória do Qwen | Pico do cgroup ≤ 2,90 GiB; RSS do processo ~3,26 GiB (inclui ~1,9 GB de GGUF mapeado); teto de 3,5 GiB, sem swap |
| YOLO | ~0,1 a 0,2 s por imagem; memória pequena |

O Qwen (experimento A) é **~180 a 350 vezes mais lento** que o YOLO por imagem nesta CPU.

## 5. Respostas às perguntas

1. **Desempenho do Qwen (A, com classe):**
   - **RBC:** precisão 0,31, revocação 0,26;
   - **WBC:** precisão 0,33, **revocação 0,95**;
   - **Platelets:** 0 acertos.

   Com a classe dada no prompt (B): WBC com revocação 0,90; RBC 0,25; plaquetas 0,07.
2. **Comparação com o YOLO:** o YOLO é muito melhor em todas as medidas nestas 20 imagens: precisão 0,76 contra 0,31, revocação 0,73 contra 0,29, IoU 0,82 contra 0,69, e 3,5 contra ~10 FP por imagem. Isso vale **com as ressalvas** de arquitetura (especializado × geral), procedência do treino e tamanho da amostra.
3. **Localiza mesmo classificando errado?** **Parcialmente:** 14 localizações a mais quando se ignora a classe (RBC→WBC 11, Platelets→WBC 3). O limite principal, porém, é a **localização** (revocação 0,33 sem classe), e não só a classificação.
4. **Custo:** viável nesta CPU. ~35 s por imagem com um prompt (~111 s com os 4), ~3 GiB de RAM, sem GPU e sem swap.
5. **Alternativa viável ao MIRAGE?**
   - **Tecnicamente executável e integrável:** roda localmente, devolve caixas reais em JSON válido (99%), e o pipeline completo funcionou (`TextReference` → adaptador → `DetectionReference` → visualizador → avaliador → `ExecutionReport`). O MIRAGE nunca foi executado neste projeto.
   - **Qualidade insuficiente** para contar ou localizar células nesta configuração e amostra: muitos FP, plaquetas não localizadas, rótulos trocados. Serve, no máximo, para localizar a célula grande e saliente (o glóbulo branco), ainda com FP.
6. **Limitações para adoção no pipeline atual:**
   - **sem confiança por caixa**: não há limiar, AP/mAP nem ranqueamento;
   - **FP alto** (~10 por imagem) e **plaquetas** não localizadas (objetos pequenos);
   - **latência** de dezenas de segundos por imagem na CPU;
   - **amostragem**: com uma semente, a variabilidade entre execuções não foi medida;
   - **saída em texto livre**: 1% cortado com `-n 1024`; depende do adaptador estrito;
   - **runtime externo** (binário do llama.cpp) e ~3 GiB de RAM; o `VisualQuestionAnsweringComponent` **não está integrado** (não há adaptador real);
   - **dados:** 20 imagens; o BCCD tem hemácias sobrepostas e possivelmente não anotadas, o que pesa sobre os FP e FN dos dois modelos (hipótese não medida);
   - **comparação limitada** pela procedência do YOLO e pelo pré-treino desconhecido do Qwen.

## 6. Imagens anotadas e arquivos (fora do Git)

Em `outputs/e2e/2026-11-18-qwen3vl-bccd/`, com `SHA256SUMS` de 474 arquivos:
- **Qwen:** `qwen3vl/<experimento>/<image_id>/annotated.png` e `detections.json` (rótulos originais); respostas brutas e evidências em `qwen3vl-runs/<image_id>/`.
- **YOLO:** `yolo/<image_id>/annotated.png`.
- **Anotações humanas:** `ground-truth/<image_id>-ground-truth.png`.
- **Avaliações:** `evaluations/*.json` (com e sem classe; por imagem, pares, IoU e matriz de confusão).
- **Relatório:** `report.json` (`ExecutionReport`, recuperável com `ExecutionReportReference`).
- **Exemplos ilustrativos** (inspeção visual, não medição):
  - `qwen3vl/class_conditioned-Platelets/BloodImage_00041/annotated.png`: a caixa do glóbulo branco rotulada "platelet";
  - `qwen3vl/joint_detection/BloodImage_00041/annotated.png`: hemácias com rótulo "white blood cell".
