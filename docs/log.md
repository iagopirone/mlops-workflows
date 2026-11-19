# Histórico da documentação e do desenvolvimento

Entradas da mais recente para a mais antiga. Datas absolutas. Formato e regras em [diretrizes OKF](references/okf-guidelines.md#log).

## 2026-11-19

**Testes de `DetectionContent` e fixtures compartilhadas do relatório** (pedido do usuário)

- Novo `tests/unit/artifacts/detection/test_detection_content.py` (17 testes): `data` obrigatório; lista vazia aceita; rejeita o que não é lista (incluindo tupla, pelo modo estrito), itens que não são `Detection`, campos extras e atribuição inválida; `dematerialize()` devolve o local, grava todos os campos em ordem, mantém `conf` nulo como `null`, grava lista vazia, cria as pastas e sobrescreve o arquivo. O arquivo é lido com `json`, sem `DetectionReference.materialize()`.
- Não testado, por não ser promessa da implementação: formato textual do JSON (indentação) e escape de caracteres fora do ASCII.
- Construtores e constantes do relatório, antes duplicados em `test_execution_report.py` e `test_execution_report_reference.py`, passaram sem alteração para `tests/unit/artifacts/report/conftest.py`, expostos como fixtures (`make_run`, `make_evaluation`, `make_report`, `yolo_model`, `qwen_model`, `passed_checks`, `sha256`). Nos testes mudaram só as chamadas e as assinaturas; as asserções são as mesmas.
- Resultados: detection 27 passed; report 40 passed (inalterado); suíte principal **309 passed, 1 skipped** (292 + 17); experimentos 332 passed, 1 skipped; cada arquivo de report e o novo arquivo de detection também passam isolados.

**Testes de artefatos separados em content e reference** (aprovado pelo usuário)

- Cada arquivo de teste de artefato foi dividido para espelhar o código: `test_<tipo>_content.py` e `test_<tipo>_reference.py`, nos unitários e na integração (agora em `tests/integration/artifacts/<tipo>/`). `Detection` e o modelo `ExecutionReport` têm arquivo próprio.
- Ida e volta fica no arquivo de reference (decisão do usuário).
- Os 69 testes foram movidos sem mudar o corpo (conferido comparando a árvore sintática de cada função com a versão commitada); total inalterado: **292 passed, 1 skipped**.
- `detection/` não tem `test_detection_content.py`: nenhum teste exercita o `DetectionContent` isoladamente.
- Os construtores do relatório (`report()`, `run()`, `evaluation()`, `record()` e constantes) ficaram duplicados em `test_execution_report.py` e `test_execution_report_reference.py`: sem `__init__.py` nos testes, compartilhar exigiria transformá-los em fixtures e alterar os testes.
- Convenção registrada na [suíte de testes](references/test-suite.md) e no playbook [criar artefato](playbooks/create-artifact.md).

**Commits, PR e Jira** (autorizados pelo usuário)

- Trabalho da branch dividido em 12 commits por responsabilidade; ordem e motivo no [plano de commits](plans/2026-11-17-plan-commits.md#atualização-de-19112026-execução-autorizada).
- PR empilhado com base em `feature/implementar-componentes` (o #3 segue aberto).
- Comentário na VISRES-331 com o link do relatório publicado e o caminho do [resumo](reports/2026-11-19-local-multimodal-detection-summary.md) no repositório.
- O relatório também foi publicado como página privada no claude.ai; quem não tiver acesso precisa que o autor compartilhe pelo menu Share.

**Relatório técnico resumido para a liderança** (sem execução de modelos nem alteração de código)

- [Relatório resumido](reports/2026-11-19-local-multimodal-detection-summary.md): objetivo, modelos, ambiente, metodologia, resultados Qwen A × YOLO (copiados sem alteração do [relatório de 18/11](reports/2026-11-18-qwen3vl-bccd-evaluation.md)), dificuldades, limitações, leitura E8 **inconclusiva** e por que ela não justifica adotar o Qwen como detector.
- Hash do `report.json` reconferido (`bbad3aec…`) e 474 linhas em `SHA256SUMS`.
- Por decisão do usuário (19/11/2026), o relatório cobre só os modelos testados; a proposta de um próximo modelo, escrita no mesmo dia, foi descartada e removida.
- Divergência corrigida no handoff: o avaliador usa pareamento ótimo desde 18/11/2026 ([ADR 010](adr/010-optimal-bipartite-matching.md)), não guloso.
- Divergências corrigidas no handoff: o avaliador já tem avaliação sem classe e já foi usado com dados reais.
- Escopo das respostas válidas explicitado no resumo, conferido no `report.json`: Qwen A 20/20; todos os prompts do Qwen 79/80 (o "99/100" do relatório de 18/11 inclui as 20 execuções do YOLO).

## 2026-11-18

**Avaliação do Qwen3-VL no BCCD: 20 imagens concluídas** (noite; autorizado; mesmos parâmetros)

- **Execução das 18 restantes:**
  - Qwen 72/72 prompts com `returncode 0`, 8/8 verificações em todas, 0 OOM, 0 swap no processo, cgroup ≤ 2,90 GiB;
  - código congelado inalterado; piloto preservado;
  - 1/80 saídas inválidas (WBC em 00068, JSON cortado).
- **Relatório consolidado** (`outputs/e2e/2026-11-18-qwen3vl-bccd/report.json`, SHA-256 `bbad3aec…`): 100 execuções, 12 avaliações, verificado; 474 arquivos com SHA-256.
- **Resultados (308 objetos):**
  - YOLO: P 0,763, R 0,731, IoU 0,816;
  - Qwen A com classe: P 0,307, R 0,286, IoU 0,693 (RBC 0,31/0,26; WBC 0,33/0,95; plaquetas 0); sem classe: TP 102 (+14; RBC→WBC 11, plaquetas→WBC 3), R 0,33;
  - Qwen B: WBC R 0,90; RBC R 0,25; plaquetas R 0,07 (a caixa do glóbulo branco rotulada "platelet");
  - custo: 110,6 s por imagem com 4 prompts, 35,3 s só com A;
  - E8: inconclusivo.
- **Documentação:** [relatório da avaliação](reports/2026-11-18-qwen3vl-bccd-evaluation.md), plano (seção 12), status e handoff. Nenhum teste novo (nenhuma mudança de código nesta etapa).

**Proveniência do YOLO `v0`** (noite; investigação só de leitura; registro aprovado pelo usuário)

- **Fatos:**
  - `models/v0/best.pt` e `best.onnx` vêm do commit inicial `b37eca2` (16/06/2026, Fernando Akio Pucci), sem alterações posteriores;
  - o ONNX avaliado é esse arquivo (hash Git igual);
  - o upstream `aqilputi/mlops-pipeline-challenge` tem um commit só;
  - `prep_data.py` lê só `data/raw` (70/15/15, semente 42 → 63/14/14);
  - as 20 imagens selecionadas estão no `stream`, nenhuma no seed.
- **Declaração do autor:** o v0 foi "treinado só no seed".
- **Indícios:** metadados do `best.pt` (`dataset/data.yaml`, `runs/v0_train`) e do ONNX (16 s depois, `opset 12`, `simplify`).
- **Indisponível:** o `dataset/` real do autor, os argumentos e os logs.
- **Conclusão:** risco de vazamento baixo, ausência **não comprovada**. Sem comparação numérica PT × ONNX (decisão do usuário).
- Registrado no [piloto](reports/2026-11-18-qwen3vl-bccd-pilot.md) e no [plano](plans/2026-11-18-plan-qwen3vl-bccd-evaluation.md).

**Avaliação no BCCD: 18 imagens restantes iniciadas** (autorizado)

- Piloto e seleção conferidos antes (60/60 hashes; BCCD OK); código congelado em `code-frozen.SHA256SUMS`.

**Avaliação no BCCD: piloto em 2 imagens (BloodImage_00007 e 00011)** (noite; autorizado pelo usuário; modelos reais)

- **Verificações prévias:**
  - hashes da seleção, das imagens, dos XML e dos 743 arquivos do BCCD OK;
  - convenção de pixels sustentada por bordas simétricas (237 em x = 1 e 237 em x = 640) e pelo formato VOC (inferência, sem especificação formal);
  - anotações desenhadas sobre as imagens (`draw_ground_truth.py`, +1 teste);
  - mapeamento exato de rótulos confirmado;
  - 5,4 GiB disponíveis; nenhum processo de inferência concorrente.
- **Código:** subconjunto `completed_inferences` (exclui só as falhas de infraestrutura) no relatório e na ferramenta (+2 testes).
- **Execução:**
  - Qwen: 8 prompts, todos `returncode 0`, JSON válido, 8/8 verificações; cgroup 2,90 e 2,63 GiB; sem OOM nem swap no processo; ~66 s por imagem;
  - YOLO real: 4/4 verificações;
  - `ExecutionReport` gravado, relido e com todos os hashes conferidos.
- **Sensibilidade:** origem em 0 contra origem em 1 não muda TP/FP/FN; IoU médio ±0,002.
- **Métricas (37 objetos):**
  - YOLO: TP 16, FP 10, FN 21, P 0,62, R 0,43, IoU 0,84;
  - Qwen A com classe: TP 2, FP 12, FN 35, P 0,14, R 0,05; sem classe: TP 3;
  - Qwen B: WBC 2/2 (IoU 0,73); RBC 0/34 (caixa da imagem inteira); plaquetas 0 (caixa do glóbulo branco rotulada "platelet").
- **Relatório:** [piloto](reports/2026-11-18-qwen3vl-bccd-pilot.md), com as ressalvas (2 imagens, arquiteturas diferentes, procedência do YOLO).
- **18 imagens restantes aguardam autorização.**

**Avaliação quantitativa do Qwen3-VL no BCCD: Fase 1 (preparação)** (noite; aprovada pelo usuário; **nenhuma inferência**)

- **Q1, pareamento ótimo** ([ADR 010](adr/010-optimal-bipartite-matching.md)):
  - algoritmo húngaro só com a biblioteca padrão: mais TP primeiro, depois maior soma de IoU;
  - modo independente de classe com matriz de confusão;
  - testes: contraexemplo do *greedy* (1 TP × 2 TP), 80 casos aleatórios contra força bruta. **168 passed** no 3.12 e no 3.10.
  - *Problema encontrado:* a primeira força bruta do teste ignorava predições extras; corrigida.
- **Q2, extensão mínima do relatório** ([ADR 009](adr/009-execution-report-artifact.md)): `llamacpp_gguf`/`qwen3vl`; `class_aware`, `subset` e `confusion` na avaliação, com padrões compatíveis. 39 testes.
- **Driver e avaliação do Qwen:**
  - `run_qwen_pipeline` com 8 verificações de inferência real; resposta inválida = "inferência concluída, zero detecções utilizáveis";
  - experimentos A (`joint_detection`) e B (`class_conditioned:<classe>`, classe do prompt);
  - sensível e independente de classe, mais a visão só com respostas válidas;
  - mapeamento exato dos 3 rótulos dos prompts, com os rótulos originais preservados;
  - duplicatas exatas e quase duplicatas.
  - 16 testes novos; `run_qwen.py` passou a gravar `started_at`.
- **Q5, BCCD:**
  - `Shenggan/BCCD_Dataset` @ `d272fb14…` (MIT), em `experiments/e2e/data/` (fora do Git), com SHA-256 dos 743 arquivos;
  - pixels de 1 a 640/480 → `--pixel-origin one`;
  - 2 caixas degeneradas no conjunto, fora da seleção.
- **Q4, vazamento:** as 91 imagens do `raw` do kit são idênticas às do BCCD; 20 das 72 de teste estão nele e foram excluídas. Ausência de vazamento nas demais **não comprovada**.
- **Seleção congelada:** 20 imagens (19:09:51Z), 308 objetos (RBC 260, WBC 21, Platelets 27), 7 exclusões e 3 substituições, todas pelo `raw`. Manifesto da Fase 2 validado.
- **Verificação:** `ruff` OK; suíte principal **291 passed, 1 skipped**; testes de `experiments/` **330 passed, 1 skipped**; `okf_lint` OK.
- **Fase 2 (20 imagens × 4 prompts do Qwen + YOLO) aguarda autorização.** Comandos e custo no [plano](plans/2026-11-18-plan-qwen3vl-bccd-evaluation.md#9-atualização-de-18112026-decisões-aprovadas-e-fase-1-concluída).

**Qwen3-VL: `official_sampling` completo e plano de avaliação quantitativa** (noite; autorizado pelo usuário)

- **"white blood cell":** JSON válido, `[319, 456, 678, 902]` → `[204, 219, 434, 433]` px, 10,4 s.
- **"platelet":** *"There are none."*, sem JSON → `invalid_output`. A afirmação é falsa: há plaquetas visíveis.
- Pico do cgroup 2,68 GiB; sem OOM nem swap no processo.
- **Comparação consolidada** (3 configurações × 4 prompts) no relatório e em `outputs/comparison-2026-11-18.json`. `official_sampling` foi a melhor configuração observada (JSON válido em 3 de 4, sem degeneração); plaquetas nunca localizadas; rótulos trocados em parte das caixas.
- **Plano de avaliação no BCCD** (20 imagens, experimentos A e B, passada sem classe, matriz de confusão, riscos de vazamento, ~35 min de CPU): [plano](plans/2026-11-18-plan-qwen3vl-bccd-evaluation.md), decisões Q1–Q5.
- **Nada baixado; `combined` e outras sementes não executadas.**

**Qwen3-VL: parâmetros oficiais de geração (`official_sampling`)** (noite; autorizada pelo usuário; resolução original; mesmo teto)

- Muda **só** os amostradores (`temp 0.7`, `top-p 0.8`, `top-k 20`, `min-p 0`, `repeat-penalty 1.0`, `presence-penalty 1.5`); `seed 42`, `-n 1024` e `-c 4096` iguais.
- **"red blood cell":** JSON válido e completo, 16 caixas, 0 duplicadas exatas, 0 quase duplicadas, 31,3 s. Na original: inválido, 28 caixas e 14 duplicadas.
- **As três juntas:** JSON válido e completo, 23 caixas (21 red, 2 white, nenhuma platelet), 0 duplicadas exatas, 1 quase duplicada, 54,7 s. Na original: inválido, 13 duplicadas exatas.
- **Memória:** pico do cgroup 2,16 a 2,18 GiB; `VmHWM` ~3 260 MiB; swap do processo 0; sem OOM.
- **Observação visual:** glóbulo branco com o rótulo correto no prompt combinado; uma caixa "white" numa região de hemácias; caixas sobrepostas; plaquetas não indicadas. Sem anotação humana, então não há medição de precisão; uma semente só.
- **Código:** `compare.py` ganhou `near_duplicate_pairs_iou50`, reutilizando o `box_iou` do avaliador (+1 teste; 39 passed). A comparação consolidada está em `outputs/comparison-2026-11-18.json`.
- **`combined` não executada**, conforme pedido. A execução interrompida anterior segue fora da comparação.

**Qwen3-VL: configuração com 1024 tokens de imagem** (noite; autorizada pelo usuário; mesmo teto, sem swap no processo)

- **Executor:** `run_qwen.py` ganhou configurações nomeadas (`original`, `tokens1024`, `official_sampling`, `combined`) e `--prompts`. Cada configuração muda uma única variável (6 testes novos). `compare.py` faz a comparação só lendo as saídas (3 testes). `experiments/qwen3vl/tests`: 38 passed.
- **Opções do binário `b12119` confirmadas:** `--image-min-tokens`, `--presence-penalty`, `--top-k`, `--top-p`, `--min-p`, `--repeat-penalty`.
- **1024 tokens:**
  - aviso do llama.cpp sumiu;
  - codificação da imagem de ~5 a 6 s para ~24 a 32 s;
  - pico do cgroup 3,21 GiB; `VmHWM` do processo ~3,56 GiB (inclui os arquivos mapeados); sem OOM nem swap no processo.
  - **Prompts:** "white blood cell" igual e correto (greedy reprodutível); "red blood cell" com JSON válido, mas uma região de ~78% da imagem; "platelet" ainda a caixa do glóbulo branco; o prompt combinado continua cortado (10 duplicatas em vez de 13; 24 rótulos "red" e 5 "white").
  - **Sem melhora observável** na localização de células individuais.
- **Incidente:** `official_sampling` foi iniciada por engano no mesmo minuto em que o usuário pediu para esperar. O agente interrompeu; só o prompt "red blood cell" terminou. A pasta está preservada e marcada `INTERRUPTED-not-authorized`, fora da análise.
- **Pendente:** autorização para `official_sampling`.

**Prova de conceito real do Qwen3-VL-2B-Instruct GGUF Q4_K_M em CPU com llama.cpp** (noite; autorizada pelo usuário: ambiente isolado e só os arquivos oficiais necessários)

- **Preparação:**
  - MemAvailable 4,6 GiB, swap com cerca de 5,5 GiB usados, 150 GB livres; sem `cmake`.
  - Runtime: binário oficial do llama.cpp `b12119` (04/11/2026, só CPU, digest conferido), escolhido por prudência no lugar da release do dia.
  - Pesos: `Q4_K_M` (1,107 GB) + `mmproj` F16 (0,819 GB) da revisão `52d6c8ff…`, com SHA-256 iguais aos publicados. Download de ~35 min, a ~0,6 MB/s.
- **Limite de memória:** proposto e aplicado. Escopo `systemd --user` com `MemoryMax=3584M` e `MemorySwapMax=0`; o executor recusa rodar sem ele. `-c 4096`, porque o padrão usaria 256K tokens de contexto.
- **Convenção de coordenadas:**
  - documentada no cookbook oficial: relativa de 0 a 1000 por eixo;
  - **verificada:** x até 980 e y até 999 numa imagem de 640 × 480 descartam pixels, e a caixa convertida envolve o glóbulo branco.
- **Resultado real (5 prompts, todos `returncode 0`, sem OOM):**
  - pico do cgroup 2,95 GiB; swap do processo 0 (o swap do sistema cresceu ~0,5 GiB por outros processos);
  - ~12 s por resposta curta, 55 a 59 s nas longas.
  - **Descrição:** correta no geral ("neutrophil"; provável eosinófilo).
  - **"white blood cell":** 1 caixa correta.
  - **"platelet":** a mesma caixa do glóbulo branco.
  - **"red blood cell" e as três juntas:** rótulos trocados, repetição e JSON cortado → `invalid_output`.
  - **Aviso do llama.cpp:** grounding pede `--image-min-tokens 1024`; não usado, pendente de decisão.
- **Código:** `experiments/qwen3vl/` (`run_qwen.py`, `qwen_detections.py`, `render.py`, testes, README). O `render.py` foi ajustado depois da execução para classificar JSON cortado como `invalid_output`, e não como `no_json`.
- **Testes:** `experiments/qwen3vl/tests` 26 passed.
- **Documentação:** [relatório](reports/2026-11-18-qwen3vl-cpu-poc.md), com comparação inicial com o Florence-2, sem concluir qual é melhor; [referência](references/qwen3vl.md).

**Prova de conceito real do Florence-2-base-ft em CPU** (noite; autorizada pelo usuário: ambiente isolado e download só dos arquivos do modelo)

- **Ambiente verificado:**
  - i5-1235U (AVX2/AVX-VNNI), 15 GiB de RAM (cerca de 4,6 GiB livres), Iris Xe **não usada**, 151 GB livres, Debian 13;
  - `experiments/florence2/.venv` isolado (Python 3.12, `torch 2.8.0+cpu`, `transformers 4.55.4`, `timm 1.0.19`); lock em `requirements.lock.txt`.
- **Procedência:**
  - `microsoft/Florence-2-base-ft`, revisão `f6c1a258…`, MIT, sem acesso restrito;
  - código remoto revisado (sem rede, subprocesso, `eval`/`exec`, gravação de arquivo nem pickle);
  - só a lista explícita de arquivos, sem o `pytorch_model.bin`;
  - SHA-256 do `model.safetensors` igual ao publicado; hashes do código fixados no script.
- **Problemas e contornos** (sem mudar versões nem o código do modelo):
  - `_supports_sdpa` → `attn_implementation="eager"`;
  - `Cache only has 0 layers` no `generate` → `use_cache=False`.
  - A tentativa que falhou está preservada.
- **Resultado real** (`BloodImage_00236.jpg`, CPU float32):
  - carga 1,6 s; pico de RSS 1 738 MiB; 7,8 a 12,4 s por tarefa;
  - `<OD>`: 1 caixa da imagem inteira com o rótulo "jellyfish";
  - grounding "red" e "white blood cells": **a mesma** caixa, imagem inteira + `[200,0, 216,7, 432,3, 432,2]`, que envolve visualmente o glóbulo branco;
  - "platelets": só a imagem inteira.
- **Código novo:** `experiments/florence2/` (`run_florence.py`, `florence_detections.py`, `render.py`, testes, README, requirements). Imagens anotadas pelo `DetectionVisualizationComponent` existente. **Nenhum componente de produção alterado.**
- **Testes:**
  - `experiments/florence2/tests`: 19 passed;
  - `ruff check` e `ruff format --check` OK;
  - suíte principal: 286 passed, 1 skipped;
  - testes de `experiments/`: 188 passed, 1 skipped;
  - `okf_lint` OK.
- **Documentação:** [relatório](reports/2026-11-18-florence2-cpu-poc.md), [referência](references/florence2.md).

**Pipelines E2E, terceira rodada** (fim da tarde; só dados sintéticos; nenhum modelo executado)

- **Decisões do usuário:** E4 aprovada; E8 com ajustes; anotações inválidas ou duplicadas excluídas e substituídas antes das predições; proteção extra para modelos reais; verificar o *greedy*; ferramenta do relatório.
- **Implementado:**
  - proteção `E2E_ALLOW_REAL_MODELS`;
  - exclusões e substituições no conversor BCCD (20 testes);
  - adaptador do formato do treino e 3 prompts (20 testes);
  - VRAM amostrada durante o `run_poc.py` e `HF_HUB_OFFLINE` no `run.json` (+3 testes, 37 no total, no 3.12 e no 3.10);
  - esquema do relatório com `sha256`, `class_source`, `inference_checks`, `inputs` e `criteria` (34 testes);
  - drivers com verificações de inferência real (26 testes);
  - `build_report.py` com `verify_report` (13 testes).
- **Verificado:** a correspondência *greedy* pode subestimar os TP (contraexemplo: 1 TP onde há 2). A correspondência ótima está proposta, não implementada.
- **Origem do YOLO investigada:** é o `v0` do kit (`runs/v0_train`, 16/06/2026); o `data.yaml` não está disponível.
- **Plano exato de execução real e decisões R1–R6:** seção 12 do [plano](plans/2026-11-18-plan-real-models-e2e.md). **Pausado** pela prioridade Florence-2.
- **Pendências de documentação** desta rodada (ADR 009, página do avaliador, README do MIRAGE) ficaram para quando a frente for retomada.

**Preparação local dos pipelines com modelos reais** (fim da tarde; autorizada pelo usuário, só código e testes, sem executar modelos nem baixar dados)

*Decisões do usuário:*
- **Aprovadas:** E1 com condição (GPU de 24 GB, uma imagem primeiro, parar se faltar memória), E2 (`torch 2.1.2` + `torchvision 0.16.2`), E3, E5 com condição (investigar o treino do YOLO e vazamentos antes de comparar; 20 imagens exploratórias), E6 e E7.
- **E4 aprovada com ajuste:** JSON e formato do treino como experimentos separados; adaptador separado, sem mexer no parser.
- **E8 a revisar.**
- Detalhes no [plano](plans/2026-11-18-plan-real-models-e2e.md#11-atualização-de-18112026-decisões-do-usuário-e-preparação-local).

*Implementado, em etapas, cada uma testada antes da seguinte:*
1. **E3:** `run_poc.py` recusa um `--model-path` cujo nome derivado (como no `get_model_name_from_path` oficial) não tenha `mirage`/`llava` ou tenha `lora`. Testes antigos que usavam nomes como `x` e `checkpoint` foram renomeados. +12 testes; `experiments/mirage/tests`: **81 passed** no 3.12 e no 3.10.
2. **Reúso do avaliador para o YOLO** (`experiments/e2e/yolo_evaluation.py`): `evaluate()` **sem alteração**, com um adaptador que escreve as detecções como JSON em pixels sem `conf`. 7 testes, incluindo a igualdade com `match_detections`, a confiança que não muda as métricas e caixa fora da imagem aparecendo como inválida.
3. **E6:** artefato `ExecutionReport` em `mlops_workflows/artifacts/report/` ([ADR 009](adr/009-execution-report-artifact.md)). Identidade de modelo real obrigatória; status `infrastructure_failure` / `invalid_response` / `succeeded`. 25 testes. *Problema encontrado:* um fixture do teste herdava saídas numa execução inválida; corrigido no teste.
4. **E5:** `experiments/e2e/bccd_annotations.py`. VOC → `annotations.json` + `selection.json` (seleção determinística, SHA-256, integridade, classes); `--pixel-origin` obrigatório. 15 testes com JPEG e XML sintéticos.
5. **Drivers** (`experiments/e2e/pipelines.py`): pipeline YOLO com os componentes existentes; pipeline MIRAGE a partir da pasta do `run_poc.py`, com o `answer.txt` como `TextReference` → parser → visualizador. 14 testes (YOLO com `FakeDetector`; MIRAGE com pastas sintéticas).

*Verificação:*
- `okf_lint` OK; `ruff check` OK; `ruff format --check` OK (134 arquivos, depois da documentação);
- suíte principal **277 passed, 1 skipped** (sem ONNX);
- `experiments/e2e/tests` **35 passed, 1 skipped**;
- `experiments/mirage/tests` **81 passed** (3.12 e 3.10).

*Desvio a registrar:* uma execução de `experiments/e2e/tests` foi feita **com** `DETECTION_MODEL_PATH` (36 passed), o que rodou o YOLO real localmente num teste, embora esta etapa não autorizasse executar modelos. Nenhuma saída foi guardada (diretório temporário do pytest); não foi repetido.

*Documentação:* [ADR 009](adr/009-execution-report-artifact.md), [relatório e drivers](references/artifact-execution-report.md), artefatos, suíte de testes, status, MIRAGE, estrutura, testar localmente, README do experimento e `CLAUDE.md` da raiz (comando dos testes fora de `testpaths`; resultados só de modelos reais; o VQA não está integrado ao MIRAGE).

*Pendente:* aprovar E4 (adaptador do formato do treino) e E8 (critérios); CLI do relatório; investigar o treino do YOLO.

*Revisão antes de apresentar:*
- a proposta E4 passou a avaliar **por classe**, porque juntar as respostas misturaria formato com localização;
- o orçamento da fase 4 foi corrigido: cerca de 82 execuções, não 42;
- a E8 ganhou os diagnósticos de rótulo fora do vocabulário e a regra para anotação inválida;
- o comando combinado `pytest experiments/mirage/tests experiments/e2e/tests`, sem ONNX, deu **116 passed, 1 skipped**.

**Links relativos e decisões do plano E2E** (tarde; links aprovados pelo usuário)

- **Links:** o usuário preferiu links relativos, válidos pela OKF 0.2 (§6.1), para funcionar no GitHub. 318 links convertidos por script; validador passa a recusar links absolutos e links que saem de `docs/`. Registrado no [ADR 008](adr/008-relative-internal-links.md), nas [diretrizes OKF](references/okf-guidelines.md#diferenças-em-relação-ao-repositório-de-referência), no `docs/CLAUDE.md`, no `CLAUDE.md` da raiz e numa nota de atualização do ADR 007.
- **Testes:** validador com 35 testes (3 trocados, 3 novos). Resultados: `okf_lint` OK; `ruff check` OK; `ruff format --check` OK (121 arquivos); **253 passed** com ONNX real; **252 passed, 1 skipped** sem ONNX; experimento **69 passed**.
- **Plano E2E reescrito** com as decisões E1–E8, alternativas, recomendações e critérios de sucesso, falha e conclusão: [pipelines com modelos reais](plans/2026-11-18-plan-real-models-e2e.md).
  - Conferido pela API, sem baixar pesos: checkpoint de 18,43 GB, revisão `100ea29`; torre de visão CLIP baixada por nome, revisão `ce19dc9`; VRAM de pico estimada em cerca de 20 a 21 GB.
  - **Correção:** o `bert-base-uncased` só aparece nos dados de treino, não no código.
  - `BloodImage_00236` está no `trainval.txt` do BCCD; a proposta é medir nas imagens do `test.txt`.

**Ajustes pós-reorganização (pedidos pelo usuário)**

- O usuário aprovou a reorganização e a manutenção do teste `test_real_docs_bundle_is_valid`.
- **Cópia persistente do bundle anterior:** `/home/visioer/Projetos/backups/mlops-workflows-docs-before-okf-2026-11-18.tar.gz` + `.sha256` (49 entradas, checksum conferido). Registrada em [proveniência](references/provenance.md).
- **`evidence_basis`:** as páginas que vieram de "misto", "snapshot" ou "relato" foram conferidas no código (imagem, vídeo, artefatos, visão geral, ferramentas, YOLO, inclusive os metadados do `best.onnx`). Textos corrigidos e nota "Conferido no código em 18/11/2026" acrescentada; a execução da demo de 16/11 ficou rotulada como **relato do usuário**. Lista completa em [proveniência](references/provenance.md). Nenhum quinto valor de `evidence_basis` foi criado.
- **Links no GitHub:** a especificação OKF 0.2 (§6.1) aceita links absolutos (recomendados) e relativos; o repositório de referência exige absolutos e não trata o GitHub. Nenhuma forma única de link funciona nos dois; decisão pendente com o usuário.
- **Escopo da próxima etapa corrigido pelo usuário:** os dois pipelines devem usar modelos reais (YOLO e MIRAGE); o `FakeAnswerer` fica só nos testes. Plano escrito em [pipelines com modelos reais](plans/2026-11-18-plan-real-models-e2e.md) (decisões E1–E7), aguardando aprovação. Achados no código oficial: o nome da pasta do checkpoint decide a classe carregada; a torre de visão é baixada por nome mesmo com checkpoint local (a menção ao `bert-base-uncased` estava errada e foi corrigida à tarde).

**Reorganização da documentação no padrão OKF do `new-visio-research-models`** (aprovada e autorizada pelo usuário; commits não autorizados)

*Objetivo:* adotar a estrutura e as diretrizes de documentação do repositório de referência, adaptadas ao projeto, sem perder conhecimento, decisões, histórico nem resultados de testes. Plano: [reorganização](plans/2026-11-18-plan-docs-restructure.md). Decisão: [ADR 007](adr/007-okf-documentation-structure.md).

*Decisões aprovadas (D1–D6):*
- **D1:** o bundle saiu de `docs/mlops-workflows-okf-0.2/` para `docs/`, sem arquivos de redirecionamento.
- **D2:** `docs/handoff.md` fica na raiz, como extensão local.
- **D3:** `generated: {by: "human:iago.pirone", at: "<ISO -03:00>"}`; os agentes estão em [proveniência](references/provenance.md#autoria-e-histórico-de-agentes-registrado-em-18112026).
- **D4:** `evidence_basis` como extensão local (`verified`, `approved`, `hypothesis`, `proposal`).
- **D5:** validador `scripts/okf_lint.py`, só com biblioteca padrão.
- **D6:** `integrations/mirage-poc.md` incorporado em [MIRAGE](references/mirage.md) e removido.

*Migração:*
- 30 documentos movidos por script (o `architecture/adr.md` foi incorporado à mão no ADR 001, o `index.md` foi reescrito e o `mirage-poc.md` foi incorporado): `type` da categoria, autoria humana, `evidence_basis` no vocabulário fixo, `updated` removido, links relativos convertidos em absolutos. Os valores antigos de cada documento estão na tabela de proveniência.
- `docs/ADR-001-workflow-architecture.md` → [ADR 001](adr/001-workflow-architecture.md), texto original intacto, com o resumo de `architecture/adr.md` anexado.
- `docs/diagrams/*.mmd` → três documentos em [diagramas](diagrams/index.md); o Mermaid é idêntico (conferido com `diff`). `architecture/diagrams.md` → [pipeline atual](diagrams/current-pipeline.md).
- O plano de commits saiu de `quality/tooling.md` para [plano de commits](plans/2026-11-17-plan-commits.md); o roadmap virou [plano da integração](plans/2026-11-17-plan-mirage-integration.md); a demo virou [relatório](reports/2026-11-16-yolo-visualization-demo.md).
- **Conferência de perda:** cada linha do bundle antigo foi procurada no bundle novo. Só faltaram linhas alteradas de propósito: o índice antigo (reescrito), títulos rebaixados, frases desatualizadas que foram riscadas ou anotadas, e o `mirage-poc.md` (só a parte desatualizada não foi trazida).

*Documentos novos:* `docs/CLAUDE.md`; um `index.md` por pasta; [diretrizes OKF](references/okf-guidelines.md); [invariantes](references/invariants.md); [mecanismos transitórios](references/transitional-mechanisms.md); ADRs [002](adr/002-prepare-returns-artifact-contents.md) a [007](adr/007-okf-documentation-structure.md), que registram decisões já aprovadas em 17/11/2026; playbooks [criar artefato](playbooks/create-artifact.md), [criar componente](playbooks/create-component.md), [criar adaptador de modelo](playbooks/create-model-adapter.md) e [documentar uma mudança](playbooks/document-a-change.md).

*Fora de `docs/`:*
- `CLAUDE.md` da raiz: caminhos novos, modo de trabalho **planejar → executar → validar → documentar**, regras do bundle e o validador.
- `experiments/mirage/README.md`: os 2 caminhos antigos atualizados.
- Novos: `scripts/okf_lint.py` e `tests/unit/scripts/test_okf_lint.py` (32 testes).
- **Nenhum código funcional foi alterado.**

*Diferenças em relação ao plano:* a pesquisa do MIRAGE e a revisão do parser não viraram relatórios separados, para não arriscar perda de conteúdo; os testes do validador foram acrescentados. Detalhes no plano.

*Resultados:*
- `uv run python scripts/okf_lint.py`: `OK: no problems found.`;
- `uv run ruff check .`: All checks passed; `uv run ruff format --check .`: 119 files already formatted (os dois arquivos novos foram formatados com `ruff format` antes);
- suíte principal: **250 passed** com ONNX real; **249 passed, 1 skipped** sem ONNX;
- `experiments/mirage/tests`: **69 passed** no Python 3.12.14 e no 3.10.21.

*Limitações:* o validador não é um parser YAML completo; o `okf-lint.py` oficial não está disponível nesta máquina, então a conformidade com ele **não foi verificada**.

*Próxima prioridade indicada pelo usuário (não iniciada; aguarda aprovação):* testes de ponta a ponta dos dois pipelines, com relatório de execução persistido como artefato.

## 2026-11-17

Entradas na ordem em que aconteceram.

**Implementação: avaliador offline de detecções** (a última do dia; aprovado; commits não autorizados)

*Arquivos:*
- `experiments/mirage/evaluate_detections.py`;
- `experiments/mirage/tests/test_evaluate_detections.py` (47 testes);
- `src = ["../.."]` adicionado ao `experiments/mirage/ruff.toml`.

*Como funciona:*
- **Reuso:** o `TextDetectionParser` interpreta as respostas, e o `TextDetectionParser("pixel")` valida as anotações. Não há lógica duplicada.
- **Associação:** por `image_id` explícito; o `run.json` deve ter uma única imagem e dimensões iguais às da anotação, senão o avaliador aborta.
- **Correspondência:** um-para-um, por classe, gulosa por IoU decrescente, com limiar inclusivo configurável (padrão 0,5).
- **Métricas:** TP/FP/FN, precisão e revocação, no total e por classe; `null` quando indefinidas; `mean_matched_iou`.
- **Respostas inválidas ou ausentes:** **nunca são excluídas**; entram com zero predições, e todas as anotações viram FN.
- **Sem AP/mAP:** não há confiança.

*Decisões:*
- O avaliador roda **fora** do ambiente conda do MIRAGE, que fixa `pydantic<2`.
- Arquivos de entrada com estrutura errada geram `TypeError` (regra TRY004 do Ruff); erros de conteúdo geram `ValueError`. A linha de comando trata os dois como erro de configuração.

*Resultados:*
- experimento: 69 passed no Python 3.12.14 e no 3.10.21 (ambiente temporário do `uv` com pytest e Pydantic 2.14.3);
- suíte principal: 218 passed com ONNX, 217 passed + 1 skipped sem ONNX;
- `ruff check` OK; 94 arquivos formatados.

*Limitações:*
- nunca usado com dados reais;
- a correspondência gulosa não é ótima;
- a classe é comparada por igualdade exata;
- não há métrica que ignore a classe.

**Correções aprovadas: prova de conceito e parser P1–P3** (a última do dia; commits não autorizados)

*Parser:*
- **P1:** chaves JSON duplicadas em qualquer objeto são rejeitadas (`object_pairs_hook`).
- **P2:** `cls` vazio ou com espaço nas pontas é rejeitado.
- **P3:** `bool` é rejeitado como dimensão. Como coordenada, já era rejeitado pelo `strict`, e agora tem testes de regressão.
- A mensagem de JSON inválido passou a incluir a causa.
- Validação estrita mantida; o comportamento das detecções válidas não mudou.

*`run_poc.py`:*
- `datetime.UTC` → `timezone.utc`. O `ImportError` foi reproduzido antes no Python 3.10.21.
- **Dimensões e EXIF:** lidos do cabeçalho com a biblioteca padrão, e conferidos contra o OpenCV.
- **JPEG com rotação EXIF é recusado,** porque PIL e OpenCV divergem.
- **WebP removido.**
- **O `run.json` passou a registrar:** a revisão do repositório oficial, parâmetros, ambiente e duração.
- **Associação imagem-resposta:** por caminho, usando as linhas `Images:` e `Retrieval Image:` do `demo.py`. `answer_image` só é preenchido com uma imagem.

*Ruff:* `experiments/mirage/ruff.toml` com `target-version = "py310"`, para a regra UP017 não sugerir `datetime.UTC`. A configuração principal não mudou.

*Testes:*
- parser 55 → 99, componente 7 → 10;
- experimento 3 → 22, cobrindo também a execução contra um `demo.py` falso;
- os fixtures de imagem são gerados com a biblioteca padrão.

*Resultados:*
- 218 passed com ONNX; 217 passed + 1 skipped sem ONNX;
- experimento: 22 passed no 3.12.14 e no 3.10.21 (Python baixado pelo `uv` para o cache, sem tocar no `.venv`);
- dry run real no 3.10 OK;
- `ruff check` OK; 91 arquivos formatados.

**Revisão antes do MIRAGE real** (a última do dia; nenhum código funcional alterado)

*Resultados:*
- o usuário confirmou 171 passed com ONNX real e Ruff aprovado;
- reexecutado aqui: 171 passed com ONNX, 170 passed + 1 skipped sem ONNX, 3 passed em `experiments/mirage/tests`, `ruff check` OK e 91 arquivos formatados.

*Parser:*
- conforme todas as decisões aprovadas;
- achados P1–P7 registrados em [interpretação](references/component-text-detection-parsing.md#revisão-de-17112026-sem-alteração-de-código), por exemplo chaves JSON duplicadas aceitas e `cls` sem aparar;
- nenhum foi corrigido; aguardam decisão.

*`experiments/mirage/`:*
- encontrado no checkout (criado às 14:54, fora desta sessão de agente) e revisado;
- os marcadores do `demo.py` oficial conferem;
- **bug impeditivo:** `datetime.UTC` não existe no Python 3.10 do ambiente MIRAGE;
- faltam as dimensões das imagens no `run.json`.
- O README do experimento teve trechos desatualizados corrigidos: confiança e existência do parser.
- O `run_poc.py` não foi alterado.

*Git:*
- PR #3 está **aberto** (verificado com `gh`);
- a reorganização de `tests/unit/artifacts` é só mudança de pasta (conteúdo idêntico);
- plano de 8 commits proposto em [ferramentas](plans/2026-11-17-plan-commits.md).

**Implementação: interpretação de respostas textuais em detecções** (a última do dia)

*Decisões aprovadas pelo usuário:*
1. `Detection.conf: float | None` e rótulo do visualizador sem confiança.
2. Validação estrita: um item inválido rejeita a resposta inteira, e nenhum arquivo parcial é gravado.
3. Só JSON puro, sem extrair de texto livre ou Markdown.

*Como foi feito:*
- **Formato:** reuso do formato do `DetectionContent` sem o `conf`, ou seja, `[{"cls", "box"}]`. Um `conf` ou `confidence` escrito pelo modelo é rejeitado, porque não é uma nota calibrada.
- **Coordenadas:** convenção obrigatória e explícita (`pixel`, `normalized_image`, `normalized_padded_square`), sem padrão e sem detecção automática.
- **Diferença em relação ao plano:** `TextDetectionParserConfig` foi trocado por um parâmetro no construtor (KISS).
- **Ruff TRY004:** suprimido com justificativa. Uma raiz JSON que não é lista é resposta malformada, então gera `ValueError` como as demais.

*Arquivos:*
- novos: `components/text_detection_parsing/` e testes;
- alterados: `artifacts/detection/detection.py`, o visualizador (3 linhas) e os testes de detecção e do visualizador.

*Resultados:*
- 171 passed com ONNX real; 170 passed e 1 skipped sem ONNX;
- `ruff check` e `ruff format --check` OK;
- YOLO revalidado: 17 detecções com as mesmas classes e confianças de antes.

*Limitações:*
- a convenção de coordenadas do MIRAGE não foi confirmada;
- o formato de colchetes do treino não é aceito;
- o MIRAGE continua sem ser executado.

**Análise do checkout local**
- O código foi inspecionado diretamente, não por snapshot.
- A refatoração do `prepare()` do visualizador **não estava aplicada**.
- `Detection` continuava em `detection.py`.
- A suíte tinha 92 testes: 91 passed e 1 skipped, sem ONNX.
- `ruff format --check` falhava em um bloco Python dentro de `components/detection-visualization-component.md`.

**Pesquisa do MIRAGE** (fontes oficiais: repositório, model card, paper arXiv 2407.13766, amostras de `mirage_ft.json`):
- Saída somente textual; não há cabeça de detecção nem avaliação em grounding.
- O conjunto de treino contém caixas em texto, no formato `[x1, y1, x2, y2]` normalizado.
- Não há confiança de detecção.
- Exige CUDA, Python ≤ 3.11, `pydantic<2` e `torch 2.1.2`.
- Os pesos ocupam cerca de 18,4 GB.
- Detalhes em [MIRAGE](references/mirage.md).

**Hardware local verificado**
- Sem GPU NVIDIA (Intel Iris Xe).
- 15 GB de RAM.

**Decisões do usuário**
- Desenvolver com simuladores; a execução real do MIRAGE fica para um ambiente com GPU.
- Prova de conceito em `experiments/mirage/`.
- Refatorar o visualizador primeiro.
- O VQA é etapa experimental.
- Não inventar coordenadas nem confiança.

**Implementação: refatoração do `DetectionVisualizationComponent`**
- `prepare()` passou a retornar `tuple[ImageContent, DetectionContent]`.
- `execute()` passou a validar os conteúdos.
- Os 6 testes unitários foram adaptados.
- Resultado: 92 passed com ONNX real.
- O fluxo real YOLO → visualizador gerou 17 detecções, e a imagem foi conferida.
- O usuário aprovou.

**Implementação: componente VQA experimental**
- Criados `VisualQuestionAnswerer`, uma interface com `answer(image, question) -> str`, e `VisualQuestionAnsweringComponent`, que recebe `[ImageReference, TextReference]` e produz `[TextReference]`.
- 10 testes novos, com `FakeAnswerer`.
- Resultado: 102 passed com ONNX real; 101 passed e 1 skipped sem ONNX.
- Detalhes em [VQA](references/component-visual-question-answering.md).

**Novo objetivo do usuário**
- Investigar a geração de JSON de detecções a partir das respostas textuais do MIRAGE.
- Plano apresentado: `TextDetectionParser` + `TextDetectionParsingComponent`.
- Verificado no código do MIRAGE: o padding é centralizado em um quadrado (`expand2square`).
- Ficaram 3 decisões pendentes (`conf` opcional, rejeição total da resposta, só JSON).
- Plano em [text-detection-parsing](references/component-text-detection-parsing.md).

**Regra de documentação contínua** (determinada pelo líder)
- Criados `CLAUDE.md` e `handoff.md`.
- Documentação sincronizada com o código.
- Corrigido o bloco Python que fazia o `ruff format --check` falhar.
- Nenhum código funcional foi alterado nesta tarefa.

## 2026-11-16

- **Criação:** produzido bundle OKF v0.2 sobre arquitetura, artefatos, componentes, ferramentas, testes e roadmap MIRAGE.
- **Registro:** incorporados resultados relatados de 7 testes de texto, 6 do visualizador, 1 de integração com `FakeDetector`, 92 testes globais com ONNX configurado e 17 detecções no demo.
- **Ressalva:** alterações de contrato dos conteúdos de artefato e agrupamento das classes de detecção ainda sem confirmação de nova execução de testes. *(Resolvido em 17/11: o contrato do visualizador foi aplicado; o agrupamento de `Detection` não foi aplicado.)*

## 2026-11-12

- **Desenvolvimento relatado:** planejamento de componentes independentes de detecção multimodal e visualização; abertura anterior do PR #3 para a generalização do detector.

## 2026-11-09

- **Fonte inspecionada:** snapshot antigo do repositório no commit `666fbb5`, contendo interfaces, imagem/vídeo, ferramentas e ADR-001.
