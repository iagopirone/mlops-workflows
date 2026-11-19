---
type: Plan
title: Avaliação quantitativa do Qwen3-VL-2B com anotações humanas do BCCD (20 imagens)
description: Plano para medir localização, classificação e validade de formato do Qwen3-VL (official_sampling) em 20 imagens de teste do BCCD, reutilizando o avaliador, o conversor e o artefato de relatório; custo, riscos e decisões. Não executado.
tags:
- qwen3-vl
- evaluation
- bccd
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T16:00:41-03:00"
evidence_basis: [proposal, verified, hypothesis]
---

# Avaliação quantitativa do Qwen3-VL no BCCD

**Proposta. Nada foi baixado nem executado.** Configuração a avaliar: `official_sampling`, a única sem degeneração nos testes com uma imagem ([relatório](../reports/2026-11-18-qwen3vl-cpu-poc.md)), sem mudar hiperparâmetros.

## 1. O que já existe e é reutilizado (verificado)

| Peça | Uso |
|---|---|
| `experiments/e2e/bccd_annotations.py` | Seleção determinística, exclusões e substituições registradas, hashes, verificação de classes e de duplicatas suspeitas |
| `experiments/mirage/evaluate_detections.py` (`evaluate`) + `experiments/e2e/yolo_evaluation.py` | TP, FP, FN, precisão, revocação e IoU médio, no total e por classe; respostas inválidas e ausentes contam como FN |
| `experiments/qwen3vl/run_qwen.py` | Execução real com teto de memória, hashes, comando exato, tempos e memória por prompt |
| `experiments/qwen3vl/qwen_detections.py` | Conversão estrita (0–1000 → pixels), `conf=None`, rótulos preservados |
| `experiments/qwen3vl/compare.py` | Duplicatas exatas, quase duplicatas e rótulos brutos |
| `DetectionReference`, `DetectionVisualizationComponent`, `ExecutionReport` | Detecções, imagens anotadas e relatório persistido |

## 2. Seleção das imagens (definida antes de qualquer predição)

1. Clonar o BCCD (`Shenggan/BCCD_Dataset`, commit `d272fb14…`, MIT, ~7,5 MB). **Exige aprovação.**
2. Conferir em alguns XML se os pixels começam em 1 ou em 0 e fixar `--pixel-origin`.
3. `bccd_annotations --image-list test.txt --limit 20`, com `--exclude-ids` dos 91 IDs do `data/raw` do kit do desafio (possível treino do YOLO `v0`, decisão E9).
   - Inválidas e com duplicatas suspeitas são excluídas e substituídas.
   - A `selection.json` registra a lista original, as exclusões, as substituições, os motivos, os hashes e o `created_at`.
4. A seleção é **congelada** antes da primeira inferência; o relatório confere a ordem dos tempos.

## 3. Execução (para cada imagem; `official_sampling`, seed 42, teto de 3,5 GiB sem swap)

| Experimento | Prompt | Origem da classe | Como é avaliado |
|---|---|---|---|
| **A. Detecção com classificação** | As três classes juntas | `model` | Comparável ao YOLO (mesmas classes, sem confiança) |
| **B. Localização condicionada à classe** | Um prompt por classe (`red blood cell`, `white blood cell`, `platelet`) | `prompt` | Por classe, com as anotações filtradas para a classe pedida; **não** comparável ao YOLO |

Respostas originais, comandos, tempos e memória ficam em `outputs/<run>/<image_id>/`, com SHA-256.

## 4. Medidas

1. **Formato:**
   - taxa de JSON válido;
   - `invalid_output` com o motivo (não JSON, cortado, fora da faixa, texto como *"There are none."*);
   - rótulos fora do vocabulário;
   - duplicatas exatas e quase duplicatas (IoU ≥ 0,5).
2. **Localização:** uma passada **sem classe**, em que anotações e predições recebem a mesma classe antes do `evaluate()`. Dá TP, FP, FN, precisão, revocação e IoU médio, separando "achou a célula" de "deu o nome certo".
3. **Classificação:** entre as caixas casadas na passada sem classe, a matriz de confusão do rótulo previsto × rótulo anotado (contagem derivada, sem métrica nova).
4. **Detecção completa:** `evaluate()` por classe (TP, FP, FN, precisão, revocação, IoU médio) e cobertura (imagens com pelo menos um TP).
5. **Execução:** `infrastructure_failure` (processo, OOM, saída ausente, sem `mtmd batch encoding done`), tempos e picos de memória (cgroup e processo).
6. **Sem AP/mAP:** o Qwen não dá confiança. O YOLO, se for comparado, entra com o limiar fixo de 0,25 e sem confiança, pelo mesmo `evaluate()`.

## 5. Riscos

| Risco | Tratamento |
|---|---|
| Vazamento no YOLO (kit treinado com parte do BCCD) | Excluir o seed `raw` (E9); a origem do treino continua não verificada (`data.yaml` ausente) |
| **Vazamento no Qwen3-VL** | O BCCD é público desde 2017; o pré-treino do Qwen **não é público**. Impossível verificar: registrar como risco no relatório |
| Correspondência *greedy* subestima os TP (verificado com contraexemplo) | **Decidir (Q1):** implementar a correspondência ótima (R1) antes, ou relatar o *greedy* com a ressalva |
| Anotações incompletas de hemácias no BCCD | Inflam os FP das duas fontes; a leitura de RBC fica marcada |
| Uma semente só | Variabilidade não medida; o resultado é **exploratório** |
| Respostas longas cortadas em `-n 1024` | Ocorreu só com greedy; com `official_sampling` não ocorreu. Contar cortes como `invalid_output` |

## 6. Custo computacional (estimativa a partir das execuções de 18/11/2026)

| Medida | Por imagem | 20 imagens |
|---|---|---|
| A (combinado) | ~55 s (observado 54,7 s) | ~18 min |
| B (3 prompts) | ~51 s (31,3 + 10,4 + 9,7 s) | ~17 min |
| **Total** | ~1,8 min | **~35 min**; pior caso, com respostas longas de ~60 s por prompt, **~80 min** |
| Memória | Pico do cgroup 2,16 a 2,68 GiB; `VmHWM` ~3,26 GiB; teto de 3,5 GiB sem swap | Igual: um processo por vez |
| Disco | Alguns MB de saídas + ~7,5 MB do BCCD | — |

## 7. Código a desenvolver (pequeno, com testes sintéticos; nada roda modelo nos testes)

1. **Executor em lote:** `run_qwen.py` com `--images-dir` + `--image-ids` (da `selection.json`), uma pasta por imagem. Hoje ele aceita uma imagem por chamada; a alternativa sem mudança é um laço de shell.
2. **Driver Qwen:** pasta de execução → `TextReference` → `qwen_to_detections` → `DetectionReference` → visualizador, com verificações de inferência real:
   - `returncode`;
   - hashes dos GGUF;
   - commit do llama.cpp;
   - `encoding done` no log;
   - teto de memória ativo;
   - `VmHWM` mínimo, que prova que os pesos foram carregados.
3. **Avaliação:** experimento A, experimento B (por classe), passada sem classe e matriz de confusão, todos sobre o `evaluate()` existente.
4. **Relatório:** o `ExecutionReport` hoje só aceita `onnx_object_detector` e `mirage_official`. **Decidir (Q2):**
   - (a) acrescentar o tipo `llamacpp_gguf` e o pipeline `qwen3vl` (mudança pequena no pacote, com testes);
   - (b) gravar um relatório JSON próprio do experimento, sem mexer no pacote.

## 8. Decisões pendentes

| # | Decisão | Recomendação |
|---|---|---|
| Q1 | Correspondência ótima (R1) antes das métricas | Sim |
| Q2 | Relatório: estender o `ExecutionReport` (a) ou JSON próprio (b) | (a), se você autorizar mudar o pacote; senão (b) |
| Q3 | Rodar os experimentos A e B, ou só A | A e B (~35 min) |
| Q4 | Incluir o YOLO nas mesmas 20 imagens, como referência | Sim, com a ressalva de origem do treino |
| Q5 | Autorizar o download do BCCD | Necessário para começar |

## 9. Atualização de 18/11/2026: decisões aprovadas e Fase 1 concluída

**Decisões do usuário:**
- **Q1:** pareamento ótimo.
- **Q2:** opção (a), extensão mínima do relatório.
- **Q3:** experimentos A e B.
- **Q4:** YOLO como referência, com ressalvas.
- **Q5:** download do BCCD.

Anotações realmente inválidas ou duplicadas podem motivar substituição; **não descartar caixas por simples sobreposição** (o conversor só exclui pares da mesma classe com IoU ≥ 0,95).

**Fase 1 (feita; nenhuma inferência):**

| Item | Resultado |
|---|---|
| Pareamento | Ótimo (húngaro) + modo independente de classe + matriz de confusão ([ADR 010](../adr/010-optimal-bipartite-matching.md)); 168 testes no 3.12 e no 3.10 |
| Relatório | `llamacpp_gguf`/`qwen3vl`; `class_aware`, `subset` e `confusion` na avaliação ([ADR 009](../adr/009-execution-report-artifact.md)) |
| Driver e avaliação do Qwen | `run_qwen_pipeline`, 8 verificações de inferência real, experimentos A e B, visão só com respostas válidas, mapeamento exato de rótulos ([referência](../references/artifact-execution-report.md)) |
| BCCD | `Shenggan/BCCD_Dataset`, commit `d272fb14cdff6e473fafeeeba32aba5f560e9e43` (21/11/2019), MIT, 364 imagens/XML, em `experiments/e2e/data/` (fora do Git). SHA-256 de todos os 743 arquivos versionados em `experiments/e2e/data/BCCD_Dataset-d272fb1.SHA256SUMS` |
| Convenção de pixels | **Verificada:** coordenadas de 1 a 640 / 480, nenhum 0, máximo igual ao tamanho → `--pixel-origin one` |
| Integridade do conjunto | 640 × 480 em todas; classes exatamente RBC (4 155), WBC (372) e Platelets (361); 2 caixas degeneradas no conjunto inteiro, fora da seleção |
| Vazamento (YOLO) | As 91 imagens do `data/raw` do kit são **idênticas byte a byte** às do BCCD; **20 das 72** de teste estão nele e foram excluídas. As outras 52 estão no `stream` do kit; a ausência de vazamento **não está comprovada** (`data.yaml` ausente) |
| Seleção congelada | `outputs/e2e/2026-11-18-qwen3vl-bccd/annotations/selection.json`, `created_at 2026-11-18T19:09:51Z`; 20 imagens; 7 exclusões (todas do `raw`), 3 substituições; nenhuma exclusão por anotação |
| Anotações | 308 objetos: RBC 260, WBC 21, Platelets 27 |
| Manifesto da Fase 2 | `outputs/e2e/2026-11-18-qwen3vl-bccd/manifest.json`, validado sem inferência |

**Imagens selecionadas:** BloodImage_00007, 00011, 00015, 00016, 00018, 00021, 00031, 00033, 00041, 00057, 00062, 00063, 00065, 00067, 00068, 00074, 00075, 00103, 00135, 00136.

**Comandos da Fase 2 (aguardam autorização):**

```bash
RUN=outputs/e2e/2026-11-18-qwen3vl-bccd
IMAGES=experiments/e2e/data/BCCD_Dataset/BCCD/JPEGImages
for id in $(jq -r '.images[].image_id' $RUN/annotations/selection.json); do
  systemd-run --user --scope -p MemoryMax=3584M -p MemorySwapMax=0 --quiet -- \
    /usr/bin/python3 experiments/qwen3vl/run_qwen.py --image $IMAGES/$id.jpg \
    --output-dir $RUN/qwen3vl-runs/$id --config official_sampling \
    --prompts ground_rbc ground_wbc ground_platelet ground_all
done
# YOLO real (in-process) + leitura do Qwen + avaliação + relatório verificado:
uv run python -m experiments.e2e.build_report --manifest $RUN/manifest.json
```

## 10. Atualização de 18/11/2026: piloto em 2 imagens (Fase 2 parcial)

**Autorizado:** só BloodImage_00007 e 00011 (Qwen A + B e YOLO). **Concluído sem falhas:**
- 8/8 respostas do Qwen com JSON válido e 8/8 verificações de inferência real;
- YOLO com 4/4 verificações;
- pico do cgroup ≤ 2,90 GiB;
- relatório gravado, relido e verificado.

**Antes da execução:**
- convenção de pixels sustentada por bordas simétricas (237 caixas em x = 1 e 237 em x = 640) e pelo formato VOC; **sensibilidade testada depois**, sem mudança em TP/FP/FN;
- alinhamento conferido desenhando as anotações;
- subconjunto `completed_inferences` acrescentado para separar as falhas de infraestrutura.

Resultados e análise: [relatório do piloto](../reports/2026-11-18-qwen3vl-bccd-pilot.md).

**Próximo:** as 18 imagens restantes (~20 a 40 min), **aguardando autorização**. Mesmos comandos da seção 9; o laço do Qwen ignora as duas imagens já executadas.

## 11. Atualização de 18/11/2026: proveniência do YOLO `v0` e continuação

Investigação só de leitura, aprovada. Fatos, declarações do autor, indícios e lacunas estão registrados no [relatório do piloto](../reports/2026-11-18-qwen3vl-bccd-pilot.md#proveniência-do-yolo-v0-investigada-em-18112026-só-leitura-aprovada-pelo-usuário). Em resumo:
- `models/v0` vem do commit inicial `b37eca2` do kit, e o ONNX avaliado é esse arquivo;
- o autor declara que o v0 foi treinado só no seed (91 imagens, divisão 70/15/15);
- as 20 imagens selecionadas estão todas no `stream`.

**Conclusão:** risco de vazamento considerado baixo; ausência **não comprovada**. Sem comparação numérica PT × ONNX nesta etapa, por decisão do usuário.

**Continuação autorizada:** as 18 imagens restantes, com os mesmos parâmetros.
- Antes de começar, conferi: piloto e seleção com 60/60 hashes OK; BCCD OK; seleção inalterada.
- Hashes do código congelado (executor, adaptador, driver, avaliador, ferramenta, parser, YOLO, esquema, manifesto) em `outputs/e2e/2026-11-18-qwen3vl-bccd/code-frozen.SHA256SUMS`.

## 12. Atualização de 18/11/2026: avaliação das 20 imagens concluída

- **Execução das 18 imagens restantes** (16:29 a 17:04): 72 prompts, todos `returncode 0`; 0 OOM; 0 swap no processo; código congelado conferido depois; piloto preservado.
- **Relatório consolidado** (YOLO real + Qwen A/B) gravado, relido e verificado: 100 execuções, 12 avaliações.
- **Resultados e respostas às 6 perguntas:** [relatório da avaliação](../reports/2026-11-18-qwen3vl-bccd-evaluation.md).
- **Leitura pelos critérios E8:** **inconclusivo** para o Qwen A (sem sinal positivo; o critério negativo não é atingido por pouco).
