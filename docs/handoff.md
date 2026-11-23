---
type: Reference
title: Contexto de continuidade entre sessões
description: Estado mínimo necessário para outro agente ou desenvolvedor retomar o trabalho sem o histórico da conversa.
tags:
- handoff
- continuity
- status
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:28:27-03:00"
evidence_basis: [verified, approved, proposal]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d0fb7f2 + alterações não commitadas), inspecionado e testado em 17 e 18/11/2026
  title: Código, testes e execuções locais
---

# Handoff — última atualização: 23/11/2026

> Leia este arquivo primeiro. Depois: [status](references/status.md), [log](log.md), as [invariantes](references/invariants.md) e a página técnica da tarefa em curso (índice em [index](index.md)). Regras da documentação: `docs/CLAUDE.md` e [diretrizes OKF](references/okf-guidelines.md). **Modo de trabalho: planejar → executar → validar → documentar, com aprovação do usuário antes de executar.** **O código é a fonte de verdade**; se divergir deste texto, confie no código e corrija este arquivo.

## 1. Objetivo geral

Workflow modular de inferência de ML em Python, com componentes intercambiáveis ligados por artefatos (`Reference`/`Content`).

**Objetivo do desafio atual:** imagem + prompt → MIRAGE → resposta textual → JSON de detecções → imagem com bounding boxes.

## 2. Contratos a preservar

- `ArtifactReference` (`name`, `location`, `materialize()`) e `ArtifactContent` (`data`, `dematerialize(reference) -> str`): Pydantic `strict`, `extra="forbid"`. Veja [contratos](references/contracts.md).
- `Component.prepare(list[ArtifactReference]) -> object` e `Component.execute(object) -> list[ArtifactReference]`.
- **Convenção aprovada:** `prepare()` retorna os **conteúdos** dos artefatos (`ImageContent`, `DetectionContent`, `TextContent`); o `.data` só é acessado dentro de `execute()`. Aplicada no visualizador e no VQA. `ObjectDetectionComponent` **ainda** retorna `np.ndarray`: não alterar sem aprovação.
- Modelos entram por injeção de dependência no construtor (`ObjectDetector`, `VisualQuestionAnswerer`).
- `Detection`: `cls: str`, `conf: float | None` (obrigatório, sem padrão; entre 0 e 1 quando numérico; `null` = fonte sem confiança, **nunca inventar**), `box: [x1, y1, x2, y2]` em pixels da imagem original. Continua em `artifacts/detection/detection.py`.
- `TextDetectionParser(coordinate_format)`:
  - aceita só JSON puro `[{"cls", "box"}]`;
  - a convenção de coordenadas é obrigatória e explícita;
  - rejeita chaves duplicadas, `cls` com espaço nas pontas e `bool`;
  - um item inválido rejeita a resposta inteira.
- `experiments/mirage/run_poc.py`:
  - precisa continuar compatível com Python 3.10 e usar só a biblioteca padrão;
  - o alvo do Ruff para essa pasta está em `experiments/mirage/ruff.toml`.
- `experiments/mirage/evaluate_detections.py`:
  - reutiliza o `TextDetectionParser`, sem duplicar validação nem conversão;
  - roda fora do ambiente conda do MIRAGE (precisa de Pydantic 2);
  - respostas inválidas ou ausentes contam como FN, nunca são excluídas;
  - não calcula AP/mAP.
- Imagens: `np.ndarray` BGR (OpenCV).

## 3. Estado do Git (23/11/2026)

- **VISRES-337 (contagem de classes) aprovada e versionada** em 23/11/2026, num commit próprio sobre `d3c737c` na branch `feature/integracao-mirage`, enviado ao PR #4 (sem force push, base inalterada). Confira o hash com `git log -1`. Arquivos novos: `mlops_workflows/artifacts/class_count/`, `mlops_workflows/components/class_counting/`, `examples/demo_class_counting.py`, `tests/unit/artifacts/class_count/`, `tests/unit/components/class_counting/`, `tests/integration/components/class_counting/`, `docs/references/component-class-counting.md`, `docs/references/artifact-class-count.md`, `docs/adr/011-class-counting-component.md`; documentos vivos atualizados (veja o [log](log.md#2026-11-23)).

Estado anterior (19/11/2026):


- Branch: `feature/integracao-mirage`, criada a partir de `d0fb7f2` (fim de `feature/implementar-componentes`). PR #3 (`feature/implementar-componentes` → `rc`): **aberto**, não mesclado.
- **Versionamento autorizado pelo usuário em 19/11/2026:** todo o trabalho da integração, dos experimentos e da documentação foi dividido em 12 commits por responsabilidade ([plano de commits](plans/2026-11-17-plan-commits.md), atualização de 19/11/2026), enviado para `origin` e aberto como **PR empilhado** com base em `feature/implementar-componentes`. Depois que o #3 for mesclado, a base do PR pode passar para `rc`. Confira o número do PR com `gh pr list`.
- Ficam fora do Git (`.gitignore`): `experiments/*/{.venv,models,bin,data,outputs}`, `outputs/` da raiz e `__pycache__/`.
- Existem 2 stashes antigos (`stash@{0}`, `stash@{1}`) de outras branches: não mexer.
- **Regra:** novos commits, push, reset, clean, rebase ou troca de branch só com autorização do usuário.

## 4. Concluído e verificado

| Item | Verificação |
|---|---|
| Artefatos de imagem, vídeo, texto e detecção | Testes unitários e de integração passando |
| `YoloDetector` (ONNX) + `ObjectDetectionComponent` | Teste com modelo real passando |
| `DetectionVisualizationComponent` com `prepare() -> tuple[ImageContent, DetectionContent]` | 6 testes unitários + 1 de integração; fluxo real YOLO → JSON → visualização com 17 detecções, imagem conferida |
| `VisualQuestionAnswerer` + `VisualQuestionAnsweringComponent` (experimental) | 9 unitários + 1 de integração, com `FakeAnswerer` |
| `TextDetectionParser` + `TextDetectionParsingComponent` (experimental) | 55 + 7 unitários + 2 de integração, com respostas simuladas |
| `Detection.conf` opcional + rótulo sem confiança no visualizador | +4 e +1 testes; YOLO revalidado (17 detecções idênticas) |
| Fluxo simulado completo: `FakeAnswerer` → VQA → parser → visualizador | Teste de integração passando |
| Suíte completa (18/11/2026) | **253 passed** com ONNX real; **252 passed, 1 skipped** sem ONNX; `ruff check` e `ruff format --check` OK (121 arquivos) |
| `experiments/mirage/` | 69 testes offline passando no Python 3.10.21 e no 3.12.14 (fora da suíte principal); dry run real no 3.10 OK; **nunca executado contra o MIRAGE real** |
| Correções P1–P3 do parser + correções da prova de conceito | Aplicadas e testadas em 17/11/2026 |
| Avaliador offline (IoU, TP/FP/FN, precisão e revocação) | 47 testes sintéticos; 69 passed no experimento (3.10.21 e 3.12.14); usado com dados reais na avaliação do BCCD (18/11/2026) |
| Revisão do parser e da prova de conceito | Concluída em 17/11/2026; achados registrados |
| Documentação reorganizada em `docs/` no padrão OKF (D1–D6) | 18/11/2026; `scripts/okf_lint.py` → `OK: no problems found.`; conferência de perda de conteúdo feita |
| `ClassCountingComponent` + artefato `ClassCount` (VISRES-337, 23/11/2026) | 48 testes novos; suíte 357 passed + 1 skipped; experimentos 332 + 1 skipped; exemplo executado com `--detections` sobre JSONs reais já salvos ([contagem](references/component-class-counting.md)) |
| Validador `scripts/okf_lint.py` | 35 testes em `tests/unit/scripts/`, incluindo um que valida o `docs/` real; exige links relativos (ADR 008) |

## 5. Em andamento e pendente

- **VISRES-337 concluída** (23/11/2026): código revisado e aprovado, ADR 011 aceito, commit enviado ao PR #4. Limitações conhecidas mantidas: chave repetida no JSON aceita na leitura; `ClassCount` mutável. Critérios conferidos no Jira em 23/11/2026, sem divergência; comentário na tarefa com o link do PR #4 (status no Jira não alterado).
- **VISRES-305: não iniciada**, por decisão do usuário (encerrar primeiro a VISRES-337).
- **Aguardando o usuário:**
  1. Aprovar o resultado da reorganização.
  2. **Próxima prioridade indicada pelo usuário (não iniciada):** testes de ponta a ponta dos dois pipelines, com um relatório de execução persistido como artefato, contendo os resultados e as evidências de cada pipeline. Começa por um **plano** para aprovação.
  3. Revisar o PR empilhado da branch `feature/integracao-mirage` (commits feitos em 19/11/2026).
  4. A integração real com o MIRAGE exige aprovação explícita.
- **Depende de recursos externos:**
  - uma máquina com GPU NVIDIA;
  - um conjunto de imagens com anotação humana em pixels, sem rotação EXIF, no formato do [avaliador](references/mirage-evaluation.md).
- **Não iniciado:**
  - `MirageAnswerer`, fora do processo;
  - avaliação de OWLv2/Grounding DINO;
  - atualização dos diagramas do ADR;
  - separar a pesquisa do MIRAGE e a revisão do parser em relatórios (opcional, ver [plano da reorganização](plans/2026-11-18-plan-docs-restructure.md)).

## 6. Última tarefa executada

23/11/2026: **VISRES-337 — `ClassCountingComponent`** e artefato `ClassCount` ([contagem](references/component-class-counting.md), [artefato](references/artifact-class-count.md), [ADR 011](adr/011-class-counting-component.md)). Modos genérico (`None`) e restrito (lista; `[]` conta nada), zeros, exclusões à parte, sem filtro de confiança e sem normalizar nomes. 48 testes novos; nenhum modelo executado. Revisada e aprovada pelo usuário (ADR 011 aceito) e versionada no PR #4 no mesmo dia.

19/11/2026 (tarde): **testes de `DetectionContent`** (+17) e **fixtures compartilhadas do relatório** em `tests/unit/artifacts/report/conftest.py`; 309 passed, 1 skipped; commit enviado ao PR #4.

19/11/2026 (depois do PR #4): **testes de artefatos separados em content e reference**, espelhando o código (convenção na [suíte de testes](references/test-suite.md)); 292 passed, 1 skipped; commit enviado ao PR #4.

19/11/2026: **relatório técnico resumido** para a liderança ([resumo](reports/2026-11-19-local-multimodal-detection-summary.md)). Só documentação; nenhum código alterado, nenhum modelo executado. Depois, no mesmo dia e com autorização, o trabalho foi commitado em 12 commits, enviado e aberto como PR; o link do relatório foi comentado na VISRES-331 do Jira.

Tarefa anterior: avaliação do Qwen3-VL no BCCD, 20 imagens (18/11/2026, noite; seção 9). Antes, 18/11/2026: **reorganização da documentação** no padrão OKF do `new-visio-research-models` ([plano](plans/2026-11-18-plan-docs-restructure.md), [ADR 007](adr/007-okf-documentation-structure.md), [log](log.md)).
- Bundle movido para `docs/`; 30 documentos convertidos por script (frontmatter e links), mais o `architecture/adr.md` incorporado à mão no ADR 001, o `mirage-poc.md` incorporado e removido, o `index.md` reescrito e os 4 arquivos versionados (ADR e 3 diagramas) migrados sem alterar o texto.
- Novos: `docs/CLAUDE.md`, índices por pasta, diretrizes, invariantes, mecanismos transitórios, ADRs 002–007, 4 playbooks, plano da reorganização.
- `mirage-poc.md` incorporado em [MIRAGE](references/mirage.md) e removido.
- Fora de `docs/`: `CLAUDE.md` da raiz, `experiments/mirage/README.md`, `scripts/okf_lint.py`, `tests/unit/scripts/test_okf_lint.py`.
- Nenhum código funcional alterado; nada commitado.

Tarefa anterior (17/11/2026): avaliador offline `experiments/mirage/evaluate_detections.py` ([avaliador](references/mirage-evaluation.md)).

## 7. Decisões técnicas recentes

Veja o [log](log.md) para o histórico completo.

- Prova de conceito do MIRAGE em `experiments/mirage/`, isolada do pacote e com ambiente próprio.
- O VQA é **etapa experimental**; o objetivo continua sendo detecções estruturadas.
- **Nunca inventar** coordenadas, classes ou confiança para preencher `DetectionContent`.
- Separar explicitamente duas coisas: (a) respostas textuais multimodais; (b) detecção orientada por texto, com coordenadas.
- Documentação contínua obrigatória (regra do líder, 17/11/2026): veja `CLAUDE.md`.
- **Estrutura da documentação (18/11/2026, D1–D6):** `docs/` no padrão OKF do `new-visio-research-models`; `handoff.md` na raiz; autoria `human:iago.pirone`; `evidence_basis` local; validador só com biblioteca padrão. Veja [ADR 007](adr/007-okf-documentation-structure.md).
- **Modo de trabalho (18/11/2026):** planejar → executar → validar → atualizar a documentação; analisar o contexto e apresentar o plano antes de executar.
- **Parser (aprovado):**
  - `conf: null` quando não há confiança;
  - rejeição total da resposta se algum item for inválido, sem arquivo parcial;
  - só JSON puro, sem extrair de texto livre ou Markdown;
  - um `conf`/`confidence` escrito pelo modelo é rejeitado;
  - a convenção de coordenadas é obrigatória no construtor.

## 8. Problemas e limitações conhecidos

- **MIRAGE:**
  - **Nunca foi executado.** Gerar bounding boxes confiáveis com ele é **hipótese experimental**.
  - A saída é só texto, e o modelo não dá confiança de detecção.
  - Precisa de CUDA, Python ≤ 3.11, `pydantic<2` e `torch 2.1.2`, que são incompatíveis com o ambiente principal.
  - Os pesos ocupam cerca de 18,4 GB.
  - Veja [MIRAGE](references/mirage.md).
- **Hardware local:**
  - Não há GPU NVIDIA (só Intel Iris Xe).
  - 15 GB de RAM, 12 núcleos.
- **Avaliador:**
  - correspondência ótima um-para-um desde 18/11/2026 ([ADR 010](adr/010-optimal-bipartite-matching.md));
  - classe comparada por igualdade exata;
  - avaliação sem classe (localização) e matriz de confusão disponíveis desde 18/11/2026;
  - sem AP/mAP;
  - usado com dados reais pela primeira vez na avaliação do BCCD (18/11/2026).
- **`run_poc.py`:**
  - sem `timeout` nem saída progressiva;
  - recusa JPEG com rotação EXIF e WebP;
  - a instalação oficial do MIRAGE nunca foi testada.
- **Parser:**
  - P4–P7 só documentados (BOM, caixas microscópicas, duplicatas, `except` redundante);
  - a convenção de coordenadas do MIRAGE é **hipótese** (`normalized_padded_square` provável, não comprovada);
  - o formato de colchetes do treino não é aceito;
  - validade estrutural ≠ precisão espacial.
- **Validador da documentação:** não é parser YAML completo (lê só os campos que verifica); a conformidade com o `okf-lint.py` oficial **não foi verificada** (ferramenta ausente nesta máquina).
- **Formatação:** `uv run ruff format --check .` também verifica blocos de código Python dentro dos `.md`. Escreva exemplos já formatados.
- `examples/demo_detection.py` desenha as caixas por conta própria, repetindo o que o visualizador faz. Não foi alterado.
- `domain.py` (`WorkflowRunner` etc.) contém só esqueletos com `NotImplementedError`.

## 9. Próxima ação concreta

**Agora (23/11/2026):** VISRES-337 encerrada e no PR #4. Próximo passo: aguardar o usuário. A VISRES-305 só começa com o pedido dele, por um plano. Os critérios da VISRES-337 já foram conferidos no Jira. O conector Atlassian usa o endpoint V1, obsoleto, que será removido em 01/03/2027; é preciso reconectá-lo pelo endpoint V2.

Histórico da frente anterior:

**Onde paramos (18/11/2026, noite):**

- **Prioridade atual, do líder:** modelos multimodais **locais** alternativos ao MIRAGE, que rodem nesta máquina (i5-1235U, 15 GiB, Iris Xe). Começamos pelo Florence-2-base-ft; o próximo é o Qwen3-VL-2B-Instruct quantizado.
- **Florence-2-base-ft: executado de verdade em CPU float32** ([relatório](reports/2026-11-18-florence2-cpu-poc.md), [referência](references/florence2.md)):
  - ambiente isolado em `experiments/florence2/.venv`; modelo local, revisão `f6c1a258…`, código remoto revisado;
  - contornos de compatibilidade com o `transformers` 4.55.4: `eager` e `use_cache=False`;
  - 1,7 GiB de pico e 8 a 12 s por tarefa;
  - localiza o glóbulo branco, mas dá a mesma caixa para "red" e "white blood cells"; o `<OD>` rotula a imagem inteira como "jellyfish".
  - Saídas em `experiments/florence2/outputs/2026-11-18-cpu-fp32/` (fora do Git, com `SHA256SUMS`).
- **Qwen3-VL-2B-Instruct Q4_K_M: executado de verdade em CPU com llama.cpp `b12119`** ([relatório](reports/2026-11-18-qwen3vl-cpu-poc.md), [referência](references/qwen3vl.md)):
  - teto de memória de 3,5 GiB, sem swap; pico de 2,95 GiB;
  - coordenadas relativas 0–1000 verificadas;
  - o glóbulo branco é localizado, mas os rótulos são trocados e as respostas longas degeneram.
  - Saídas em `experiments/qwen3vl/outputs/2026-11-18-cpu-q4km/`.
  - **1024 tokens testado** (18/11/2026, noite): o aviso some e o pico do cgroup vai a 3,21 GiB, sem melhora observável na localização de células individuais; veja a atualização no relatório.
  - **`official_sampling` testado** ("red blood cell" e combinado): JSON válido e completo, sem repetição, sem custo extra de memória; plaquetas ainda ausentes; uma semente só.
  - **Os 4 prompts com `official_sampling` concluídos:** "white" correto; "platelet" → *"There are none."* (inválido e falso). Comparação consolidada no relatório.
  - **Avaliação no BCCD: Fase 1 concluída** (Q1–Q5 aprovadas): pareamento ótimo ([ADR 010](adr/010-optimal-bipartite-matching.md)), relatório estendido, driver do Qwen, BCCD baixado (`experiments/e2e/data/`), seleção de 20 imagens congelada e manifesto validado em `outputs/e2e/2026-11-18-qwen3vl-bccd/`.
  - **Piloto (2 imagens) concluído sem falhas:** relatório verificado em `outputs/e2e/2026-11-18-qwen3vl-bccd/pilot/report/report.json`; resultados em [relatório do piloto](reports/2026-11-18-qwen3vl-bccd-pilot.md).
  - **Proveniência do YOLO v0:** commit inicial `b37eca2`; o autor declara treino só no seed (91 imagens, 70/15/15); as 20 imagens avaliadas estão no `stream`. **Risco de vazamento baixo, ausência não comprovada.**
  - **Avaliação das 20 imagens concluída** ([relatório](reports/2026-11-18-qwen3vl-bccd-evaluation.md)):
    - Qwen A: P 0,31 / R 0,29 (WBC R 0,95; plaquetas 0);
    - YOLO: P 0,76 / R 0,73;
    - E8: inconclusivo; ~35 s por imagem (só A) e ≤ 2,9 GiB.
  - **Relatório resumido para o líder (19/11/2026):** [resumo](reports/2026-11-19-local-multimodal-detection-summary.md), sem novas execuções nem métricas recalculadas.
  - **Próxima ação:** aguardar a revisão do resumo pelo usuário. Nenhuma execução pendente. Sem `combined` nem outras sementes. A execução interrompida (`INTERRUPTED-not-authorized`) segue fora da comparação.
- **Aguardando o usuário:**
  - avaliar o resultado;
  - decidir se testa o Florence-2 com outro `transformers` (cache KV) ou com o `-large`;
- **Frente MIRAGE/E2E: pausada**, com tudo pronto até o plano exato de execução e as decisões **R1–R6** pendentes (seção 12 do [plano](plans/2026-11-18-plan-real-models-e2e.md)). Documentação incompleta dessa rodada: ADR 009 (atualização do esquema), [avaliador](references/mirage-evaluation.md) (limitação do *greedy*), README do MIRAGE (VRAM e `hf_hub_offline`). Registrado no log.
- **Regras:** resultados só de modelos reais; o VQA **não** está integrado ao MIRAGE; ambientes isolados para cada modelo experimental; commits só com autorização.

## 10. Arquivos para retomar

- Contagem de classes (VISRES-337): `mlops_workflows/artifacts/class_count/`, `mlops_workflows/components/class_counting/`, `examples/demo_class_counting.py`, testes em `tests/{unit,integration}/components/class_counting/` e `tests/unit/artifacts/class_count/`.
- Código: `mlops_workflows/components/interface.py`, `mlops_workflows/artifacts/{interface,content}.py`, `mlops_workflows/artifacts/detection/`, `mlops_workflows/components/{object_detection,detection_visualization,visual_question_answering,text_detection_parsing}/`, `examples/demo_detection.py`.
- Testes: `tests/unit/components/`, `tests/integration/components/`, `tests/unit/scripts/`.
- Docs: [status](references/status.md), [log](log.md), [invariantes](references/invariants.md), [pipeline atual](diagrams/current-pipeline.md), [relatório da demo](reports/2026-11-16-yolo-visualization-demo.md), [MIRAGE](references/mirage.md), [parser](references/component-text-detection-parsing.md), [VQA](references/component-visual-question-answering.md), [suíte de testes](references/test-suite.md), [diretrizes OKF](references/okf-guidelines.md).
- Prova de conceito: `experiments/mirage/README.md`, `run_poc.py`, `evaluate_detections.py`, `prompts/`, `tests/`, `ruff.toml`.
- Validador: `scripts/okf_lint.py`.
- Pipelines E2E: `experiments/e2e/{pipelines,yolo_evaluation,bccd_annotations,training_format,build_report}.py` e `tests/`; artefato `mlops_workflows/artifacts/report/`.
- Qwen3-VL: `experiments/qwen3vl/` (`run_qwen.py` com teto de memória; `render.py`, `qwen_detections.py` e `tests/` no ambiente do projeto; `README.md`).
- Florence-2: `experiments/florence2/` (`run_florence.py` no venv isolado; `render.py`, `florence_detections.py` e `tests/` no ambiente do projeto; `README.md`).
- Variáveis do teste com ONNX real nesta máquina: `DETECTION_MODEL_PATH=/home/visioer/Downloads/best.onnx`, `DETECTION_IMAGE_PATH=/home/visioer/Downloads/BloodImage_00236.jpg` (caminhos locais, não versionar).
- Fontes do MIRAGE clonadas antes (temporárias, podem ter sumido): scratchpad da sessão, `mirage_src/mirage` (commit `617751c`). Podem ser clonadas de novo do GitHub oficial.
- Cópia persistente da documentação anterior: `/home/visioer/Projetos/backups/mlops-workflows-docs-before-okf-2026-11-18.tar.gz`.
