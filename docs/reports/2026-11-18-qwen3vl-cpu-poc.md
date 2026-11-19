---
type: Report
title: Qwen3-VL-2B-Instruct (GGUF Q4_K_M) em CPU com llama.cpp — prova de conceito com BloodImage_00236
description: Segunda inferência real de um modelo multimodal local alternativo ao MIRAGE — memória com teto, tempos, respostas originais, convenção de coordenadas verificada, caixas, falhas e comparação inicial com o Florence-2.
tags:
- qwen3-vl
- llama.cpp
- poc
- cpu
- detection
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T15:36:19-03:00"
evidence_basis: [verified, hypothesis]
sources:
- id: weights
  resource: https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct-GGUF (revisão 52d6c8ffea26cc873ac5ad116f8631268d7eb503)
  title: Pesos GGUF oficiais da Qwen (Apache-2.0)
- id: runtime
  resource: https://github.com/ggml-org/llama.cpp/releases/tag/b12119
  title: llama.cpp b12119 (binário oficial, só CPU)
- id: grounding-cookbook
  resource: https://github.com/QwenLM/Qwen3-VL/blob/main/cookbooks/2d_grounding.ipynb
  title: Cookbook oficial de grounding 2D do Qwen3-VL
- id: run
  resource: experiments/qwen3vl/outputs/2026-11-18-cpu-q4km/ (fora do Git; hashes em outputs/SHA256SUMS)
  title: Saídas brutas da execução
---

# Qwen3-VL-2B-Instruct em CPU (18/11/2026)

**Inferência real executada** com os pesos oficiais. Sem simulador nem resposta sintética. É uma imagem só: resultado **exploratório**. Experimento separado do Florence-2.

## Preparação (verificada)

| Item | Valor |
|---|---|
| Máquina | i5-1235U (10 núcleos, 12 threads), 15 GiB de RAM; **MemAvailable 4,6 GiB** na preparação e 5,4 GiB na execução; swap com cerca de 5,5 GiB usados de 12,3 GiB; 150 GB livres; Iris Xe **não usada** |
| Runtime | llama.cpp `b12119` (04/11/2026, commit `6f1e6543`), binário oficial `ubuntu-x64` só CPU, digest conferido. Uma release de duas semanas, e não a do dia, por prudência; o README da Qwen pede ≥ `b6907` |
| Pesos | `Qwen3VL-2B-Instruct-Q4_K_M.gguf` (1,107 GB) e `mmproj-Qwen3VL-2B-Instruct-F16.gguf` (0,819 GB), revisão `52d6c8ff…`, Apache-2.0, sem acesso restrito, SHA-256 iguais aos publicados. O codificador visual F16 foi escolhido por ser o do exemplo oficial |
| Limite de memória | **Proposto e aplicado:** escopo `systemd --user` com `MemoryMax=3584M` e `MemorySwapMax=0`, para que só o processo seja encerrado se passar do limite, sem empurrar o sistema para o swap. Estimativa prévia: 2,7 a 3,0 GiB |
| Parâmetros | `-c 4096` (o padrão `-c 0` usaria o contexto de 256K tokens), `--temp 0 --seed 42` (greedy, para reprodutibilidade; o README sugere amostragem), `-n 1024`, `-t 10` |
| Prompts | Descrição simples + grounding no texto do cookbook oficial: `Locate every instance that belongs to the following categories: "<classe>". Report bbox coordinates in JSON format.`, para "red blood cell", "white blood cell", "platelet" e as três juntas |

## Memória e tempo (verificados)

| Medida | Valor |
|---|---|
| Carregamento | 5 de 5 com sucesso; cerca de 1,6 s até o modelo pronto, pelo timestamp do log |
| Codificação da imagem (`mmproj`) | 4,4 a 6,2 s por execução |
| Tempo total por prompt (carga + imagem + geração) | descrição 11,7 s; WBC 12,5 s; plaqueta 12,6 s; RBC 54,8 s; combinado 59,3 s (respostas longas) |
| **Pico de memória do cgroup** (`memory.peak`) | **2,95 GiB** (3 167 096 832 bytes), abaixo do teto de 3,5 GiB |
| Pico de RSS do processo (`VmHWM`) | cerca de 3 260 MiB (inclui páginas do arquivo mapeado) |
| Swap do processo | **0** (`VmSwap 0`; teto sem swap; nenhum evento de OOM) |
| Swap do sistema | O `SwapFree` caiu de 6 989 para 6 461 MiB (~0,5 GiB) durante a execução. Foi o kernel movendo **outros** processos para o swap, porque o processo do modelo estava proibido de usar swap |

**Margem:** o pico de 2,95 GiB deixou ~0,5 GiB de folga no teto de 3,5 GiB.

## Convenção de coordenadas (verificada)

- **Documentação oficial** (cookbook `2d_grounding`): *"relative coordinates ranging from 0 to 1000"*, convertidas para pixels **por eixo**: `x/1000·largura` e `y/1000·altura`.
- **Evidência empírica nesta execução:** as caixas trazem x até 980 e y até 999, valores impossíveis em pixels para 640 × 480. Isso **descarta pixels**. Nenhum valor passa de 1000.
- **Conferência visual:** com a escala de 0 a 1000, a caixa do glóbulo branco, `[314, 454, 679, 925]` → `[201, 218, 435, 444]` px, envolve com precisão a célula. Lida como pixels, a mesma caixa sairia da imagem.

**Convenção usada:** `relative_1000`. É válida para estes pesos e esta configuração; deve ser confirmada de novo se algo mudar.

## Respostas originais e caixas

| Prompt | Resposta (íntegra em `outputs/.../<prompt>.stdout.txt`) | Estado | Caixas válidas |
|---|---|---|---|
| Descrição | *"This is a microscopic image of blood cells, showing a prominent, large, multi-lobed cell with a purple nucleus and a granular cytoplasm, which is characteristic of a neutrophil. It is surrounded by smaller, rounder, pale pink cells, which are likely red blood cells…"* | Imagem processada | — |
| "red blood cell" | JSON com ~13 caixas plausíveis; a primeira, `[315, 444, 679, 944]`, é o **glóbulo branco rotulado como hemácia**. Depois, **repetição**: a mesma caixa `[355, 0, 555, 265]` cerca de 17 vezes. Por fim, **JSON malformado** (`"bbox_2d": 355, 0, …]`) e texto **cortado** | `invalid_output` | Nenhuma (rejeitada inteira) |
| "white blood cell" | `[{"bbox_2d": [314, 454, 679, 925], "label": "white blood cell"}]` | `detections` | 1: glóbulo branco, **localização visualmente correta** |
| "platelet" | `[{"bbox_2d": [314, 454, 679, 925], "label": "platelet"}]` | `detections` | 1: **a mesma caixa do glóbulo branco, rotulada como plaqueta**. As plaquetas reais não foram localizadas |
| As três juntas | A primeira caixa é o glóbulo branco; depois, **todas** as caixas, incluindo hemácias, vêm rotuladas "white blood cell", com repetições. JSON **cortado** | `invalid_output` | Nenhuma |

**Problemas observados:**
- **Erros de rótulo:** o modelo chama o glóbulo branco de "red blood cell" e de "platelet". A descrição diz "neutrophil", mas os grânulos avermelhados sugerem eosinófilo; isso é observação visual, sem anotação.
- **Repetição** e JSON cortado nas respostas longas. Causa provável, **não verificada**: decodificação greedy sem a penalidade de presença recomendada (1,5) e/ou o limite `-n 1024`.
- **Aviso do llama.cpp** em todas as execuções: *"Qwen-VL models require at minimum 1024 image tokens to function correctly on grounding tasks; try adding --image-min-tokens 1024"* (issue ggml-org/llama.cpp#16842). Rodamos com o padrão, que dá menos tokens de imagem para 640 × 480. **Isso pode ter prejudicado a localização.** Usar 1024 tokens aumentaria a memória e o tempo, e a margem atual é de ~0,5 GiB. **Fica para decisão.**
- **Aviso de carga:** *"control-looking token: 128247 '</s>' was not control-type; this is probably a bug in the model"*. Sem efeito visível nas respostas.

**Nenhuma confiança foi atribuída:** todas as detecções têm `conf: null`. Os rótulos são os do modelo, sem mapeamento.

## Arquivos (fora do Git; hashes em `experiments/qwen3vl/outputs/SHA256SUMS`)

- `experiments/qwen3vl/outputs/2026-11-18-cpu-q4km/run.json`
- `.../{describe,ground_rbc,ground_wbc,ground_platelet,ground_all}.stdout.txt`: respostas originais
- `.../*.stderr.txt`: logs do llama.cpp
- `.../ground_wbc-annotated.png` e `.../ground_platelet-annotated.png`: imagens anotadas
- `.../ground_wbc-detections.json` e `.../ground_platelet-detections.json`
- `.../summary.json`: estados, evidência de coordenadas e hashes

## Comparação inicial com o Florence-2 (uma imagem; **sem** conclusão sobre qual é melhor)

| Aspecto | Florence-2-base-ft ([relatório](2026-11-18-florence2-cpu-poc.md)) | Qwen3-VL-2B Q4_K_M |
|---|---|---|
| Roda nesta CPU | Sim | Sim |
| Runtime | `transformers` em `venv` próprio, com 2 contornos de compatibilidade | Binário oficial do llama.cpp, sem contornos |
| Pico de memória | ~1,7 GiB | ~2,95 GiB (cgroup) |
| Tempo por pergunta | 7,8 a 12,4 s (sem cache KV) | 11,7 a 12,6 s nas respostas curtas; 55 a 59 s nas longas (recarrega o modelo a cada prompt) |
| Saída | Estruturada pelo processador (pixels, a partir de *bins* 0–999) | Texto JSON (escala relativa 0–1000), sujeito a malformação |
| Glóbulo branco | Localizado (grounding), com caixa quase idêntica | Localizado, com rótulo correto quando pedido |
| Discriminação de classe | Não: a mesma caixa para "red" e "white" | Não: a mesma caixa para "white" e "platelet"; glóbulo branco chamado de hemácia |
| Hemácias | Não localizadas | Caixas plausíveis, mas a resposta degenerou e foi rejeitada |
| Plaquetas | Não localizadas | Não localizadas |
| Descrição da cena | (não testada) | Correta no geral (esfregaço, célula granulada multilobulada, hemácias) |

Nos dois modelos, o **objeto mais saliente** é localizado com boa precisão visual, mas **a classe pedida não muda o resultado** de forma confiável. Medir de verdade exige anotações humanas e várias imagens, como nos pipelines E2E já preparados para o BCCD.

## Atualização de 18/11/2026 (noite): configuração com 1024 tokens de imagem

**Objetivo:** testar o aviso do llama.cpp (*"Qwen-VL models require at minimum 1024 image tokens… for grounding"*) mudando **só** `--image-min-tokens 1024` em relação à configuração original (greedy, `-c 4096`, `-n 1024`, seed 42). Mesma imagem, mesmos prompts, mesmo teto (3,5 GiB, sem swap no processo). O executor ganhou configurações nomeadas (`original`, `tokens1024`, `official_sampling`, `combined`) e `--prompts`, e os testes verificam que cada configuração muda uma única variável.

**Etapas:**
1. Teste de entrada, só com "white blood cell" (`outputs/2026-11-18-tokens1024/`).
2. Os 4 prompts de localização (`outputs/2026-11-18-tokens1024-all/`).

O aviso **desapareceu** dos logs com 1024 tokens.

| Prompt | Configuração | Tempo total (codificação da imagem) | JSON | Caixas brutas (duplicadas) | Rótulos | Coordenadas brutas (0–1000) → pixels |
|---|---|---|---|---|---|---|
| white blood cell | original | 12,5 s (5,8 s) | válido | 1 (0) | white blood cell | `[314, 454, 679, 925]` → `[201, 218, 435, 444]` |
| white blood cell | 1024 tokens | 40,9 s (26,9 s) | válido | 1 (0) | white blood cell | `[314, 454, 675, 900]` → `[201, 218, 432, 432]` (idêntica no teste de entrada: greedy reprodutível) |
| red blood cell | original | 54,8 s (4,8 s) | **inválido** (repetição, cortado) | 28 (14) | red blood cell ×30 | x até 980 e y até 999; a 1ª caixa é o glóbulo branco |
| red blood cell | 1024 tokens | 38,7 s (25,2 s) | **válido** | 1 (0) | red blood cell | `[0, 214, 998, 998]` → `[0, 103, 639, 479]`: **uma região que cobre ~78% da imagem**, não uma célula |
| platelet | original | 12,6 s (5,7 s) | válido | 1 (0) | platelet | `[314, 454, 679, 925]`: a caixa do glóbulo branco |
| platelet | 1024 tokens | 40,8 s (26,8 s) | válido | 1 (0) | platelet | `[314, 454, 672, 898]` → `[201, 218, 430, 431]`: **ainda a caixa do glóbulo branco** |
| as três juntas | original | 59,3 s (6,2 s) | **inválido** (cortado) | 29 (13) | white blood cell ×29 | x até 978 e y até 998 |
| as três juntas | 1024 tokens | 100,9 s (31,7 s) | **inválido** (cortado) | 30 (10) | red blood cell ×24, white blood cell ×5 | x até 988 e y até 999; a 1ª caixa é o glóbulo branco, as outras "white blood cell" estão em regiões de hemácias |

**Memória: pico por processo × pico do cgroup**

| Medida | Original | 1024 tokens |
|---|---|---|
| Pico do **cgroup** (`memory.peak` do escopo, o que conta para o teto) | 2,95 GiB | 2,46 GiB (só "white blood cell"); **3,21 GiB** (4 prompts) |
| Pico **por processo** (`VmHWM` do `llama-mtmd-cli`) | ~3 257 a 3 260 MiB | ~3 559 a 3 561 MiB (+~300 MiB) |
| Swap do processo / OOM | 0 / 0 | 0 / 0 |

- O `VmHWM` inclui as páginas dos GGUF mapeados em memória (~1,9 GB, *page cache* compartilhado), que podem estar cobradas a outro cgroup ou ser recuperadas sem OOM. Por isso ele pode passar do `memory.peak`.
- O `memory.peak` é o valor efetivamente cobrado ao teto, e soma os processos e o *page cache* atribuído ao escopo durante a execução.
- Com 1024 tokens, o RSS do processo (3 561 MiB) fica perto do teto (3 584 MiB). A folga do cgroup foi de ~0,3 GiB.

**Leitura preliminar** (uma imagem; **observação**, não medição de precisão):
- **Observado:**
  - o aviso some;
  - o JSON de "red blood cell" passa a ser válido, mas com uma caixa de região inteira;
  - "white blood cell" não muda;
  - "platelet" continua errado;
  - no prompt combinado, há menos duplicatas (13 → 10) e uma mistura de rótulos mais plausível, mas o JSON continua cortado e os rótulos continuam errados em várias caixas;
  - custo: codificação da imagem ~4 a 5 vezes mais lenta e ~+0,3 GiB.
- **Não observado:** localização de células individuais (hemácias ou plaquetas) melhor do que na configuração original.
- **Hipótese em aberto:** a repetição e o corte nas respostas longas vêm da decodificação greedy e do `-n 1024`, e não da resolução. A configuração `official_sampling` testa isso.

**Incidente registrado:** a execução `official_sampling` foi **iniciada por engano** às 15:49, no mesmo minuto em que o usuário pediu para não iniciá-la ainda. O agente a interrompeu ao ler a mensagem. Só o prompt "red blood cell" terminou. A pasta está preservada como `outputs/2026-11-18-official-sampling-INTERRUPTED-not-authorized/` (com `NOTE.txt`, sem `run.json`) e **não entra na análise**.

## Atualização de 18/11/2026 (noite): parâmetros oficiais de geração (`official_sampling`)

**Autorizada pelo usuário** depois da análise dos 1024 tokens.

**O que muda em relação à original:** **só os amostradores** (o teste da configuração verifica isso). Ficam `--temp 0.7 --top-p 0.8 --top-k 20 --min-p 0 --repeat-penalty 1.0 --presence-penalty 1.5`.
- São os hiperparâmetros "VL" do README oficial.
- `--min-p 0` desliga o padrão próprio do llama.cpp (0,05), que não faz parte da recomendação.
- Ficam iguais: resolução original (sem `--image-min-tokens`), `seed 42`, `-n 1024`, `-c 4096`, `-t 10`, mesmo teto.

**Execuções:**
1. "red blood cell" (`outputs/2026-11-18-official-sampling-rbc/`);
2. as três juntas (`outputs/2026-11-18-official-sampling-all/`).

A execução interrompida de antes da autorização segue **fora** da comparação.

A coluna "quase duplicadas" conta pares com o mesmo rótulo e IoU ≥ 0,5 entre caixas diferentes; foi acrescentada ao `compare.py` nesta etapa, com teste.

| Prompt | Configuração | Tempo (codificação) | JSON | Caixas | Duplicadas exatas | Quase duplicadas | Rótulos |
|---|---|---|---|---|---|---|---|
| red blood cell | original | 54,8 s (4,8 s) | **inválido** (repetição, cortado) | 28 | 14 | 0 | red ×30 |
| red blood cell | 1024 tokens | 38,7 s (25,2 s) | válido | 1 (região de ~78% da imagem) | 0 | 0 | red ×1 |
| red blood cell | **official_sampling** | **31,3 s** (4,4 s) | **válido, completo** | **16** | **0** | **0** | red ×16 |
| as três juntas | original | 59,3 s (6,2 s) | **inválido** (cortado) | 29 | 13 | 4 | white ×29 |
| as três juntas | 1024 tokens | 100,9 s (31,7 s) | **inválido** (cortado) | 30 | 10 | 6 | red ×24, white ×5 |
| as três juntas | **official_sampling** | **54,7 s** (5,6 s) | **válido, completo** | **23** | **0** | **1** | red ×21, white ×2, **nenhuma "platelet"** |

**Memória (`official_sampling`):** pico do cgroup 2,18 GiB ("red") e 2,16 GiB (juntas); pico por processo (`VmHWM`) ~3 260 MiB, igual à original; swap do processo 0; nenhum OOM.

**Observação visual** (imagens anotadas; sem anotação humana; **não é medição de precisão**):
- **"red blood cell":**
  - 16 caixas, várias sobre hemácias visíveis (topo, direita, esquerda);
  - o glóbulo branco **não** foi rotulado como hemácia, ao contrário da original;
  - duas caixas na parte de baixo pegam parte dos lobos do glóbulo branco;
  - há sobreposições no agrupamento da esquerda, abaixo de IoU 0,5;
  - não dá para dizer, sem anotação, quantas hemácias ficaram de fora ou foram contadas duas vezes.
- **As três juntas:**
  - a 1ª caixa, `[316, 457, 680, 910]` → `[202, 219, 435, 437]` px, é o glóbulo branco, **com o rótulo correto**;
  - a 2ª caixa "white blood cell", `[165, 474, 378, 983]`, está numa região de hemácias: **rótulo errado**;
  - algumas caixas "red blood cell" se sobrepõem ao glóbulo branco;
  - várias caixas se sobrepõem no canto inferior esquerdo;
  - **nenhuma plaqueta** foi indicada.

**Leitura preliminar:**
- **Observado:** com os parâmetros oficiais, as duas respostas que degeneravam vieram **completas, com JSON válido e sem repetição**, mais rápidas e sem custo extra de memória.
- **Hipótese reforçada, não provada:** a degeneração vinha da decodificação greedy sem penalidade de presença, e não da resolução.
- **Limitações:**
  - **uma amostra com `seed 42`**: com amostragem, outra semente pode dar outra resposta, e a variabilidade não foi medida;
  - uma imagem só;
  - JSON válido **não** significa caixas corretas;
  - as plaquetas continuam sem localização.

## Atualização de 18/11/2026 (noite): `official_sampling` completo e comparação consolidada

"white blood cell" e "platelet" rodaram com a mesma configuração (`official_sampling`, seed 42, resolução original, teto de 3,5 GiB sem swap) em `outputs/2026-11-18-official-sampling-wbc-platelet/`. Pico do cgroup 2,68 GiB, sem OOM. A tabela completa está em `outputs/comparison-2026-11-18.json`.

| Prompt | Configuração | Tempo | JSON | Caixas | Duplicadas exatas / quase | Rótulos | Leitura visual preliminar (sem anotação humana) |
|---|---|---|---|---|---|---|---|
| white blood cell | original | 12,5 s | válido | 1 | 0 / 0 | white | Glóbulo branco, `[201, 218, 435, 444]` px |
| white blood cell | 1024 tokens | 40,9 s | válido | 1 | 0 / 0 | white | Igual, `[201, 218, 432, 432]` |
| white blood cell | official_sampling | **10,4 s** | válido | 1 | 0 / 0 | white | Igual, `[204, 219, 434, 433]` (`[319, 456, 678, 902]` bruto) |
| red blood cell | original | 54,8 s | **inválido** | 28 | 14 / 0 | red ×30 | Degenerada; a 1ª caixa é o glóbulo branco |
| red blood cell | 1024 tokens | 38,7 s | válido | 1 | 0 / 0 | red | Região de ~78% da imagem |
| red blood cell | official_sampling | 31,3 s | válido | 16 | 0 / 0 | red ×16 | Várias caixas sobre hemácias; duas pegam parte do glóbulo branco |
| platelet | original | 12,6 s | válido | 1 | 0 / 0 | platelet | **Caixa do glóbulo branco** |
| platelet | 1024 tokens | 40,8 s | válido | 1 | 0 / 0 | platelet | **Caixa do glóbulo branco** |
| platelet | official_sampling | 9,7 s | **inválido (sem JSON)** | 0 | — | — | Resposta textual *"There are none."*, que é **falsa** (há plaquetas visíveis); um `[]` seria válido |
| as três juntas | original | 59,3 s | **inválido** | 29 | 13 / 4 | white ×29 | Degenerada |
| as três juntas | 1024 tokens | 100,9 s | **inválido** | 30 | 10 / 6 | red ×24, white ×5 | Cortada |
| as três juntas | official_sampling | 54,7 s | válido | 23 | 0 / 1 | red ×21, white ×2 | Glóbulo branco com o rótulo certo; uma caixa "white" em hemácias; sem plaquetas |

**Memória (pico do cgroup / `VmHWM` por processo):**
- original: 2,95 GiB / ~3,26 GiB;
- 1024 tokens: 3,21 GiB / ~3,56 GiB;
- `official_sampling`: 2,16 a 2,68 GiB / ~3,26 GiB.
- Swap do processo 0 e nenhum OOM em todas.

**Leitura preliminar** (uma imagem, uma semente):
- **`official_sampling` foi a melhor configuração observada:** JSON válido em 3 dos 4 prompts, sem degeneração, sem custo extra.
- **Persistem:**
  - **plaquetas** nunca localizadas: caixa do glóbulo branco ou "There are none.";
  - **rótulos trocados** em parte das caixas.
- A qualidade da localização das hemácias **não foi medida**. O próximo passo é a [avaliação quantitativa no BCCD](../plans/2026-11-18-plan-qwen3vl-bccd-evaluation.md), aguardando aprovação.

## Próximos passos possíveis (para decisão)

1. Repetir o Qwen3-VL com **`--image-min-tokens 1024`**, sob o mesmo teto. Pode exigir subir o teto ou trocar o `mmproj` para Q8_0.
2. Usar os **hiperparâmetros oficiais** (amostragem com penalidade de presença) e/ou um `-n` maior, para ver se a repetição some.
3. Avaliar os dois modelos com anotações humanas em várias imagens (BCCD), usando o avaliador e o relatório já implementados.
