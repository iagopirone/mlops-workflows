---
type: Reference
title: MIRAGE — capacidades verificadas e viabilidade
description: O que as fontes oficiais confirmam sobre o MIRAGE, requisitos, limites e prova de conceito planejada.
tags:
- mirage
- multimodal
- vqa
- integration
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:28:27-03:00"
evidence_basis: [verified, hypothesis]
sources:
- id: mirage-repo
  resource: https://github.com/visual-haystacks/mirage
  title: Repositório oficial (README, demo.py, llava/, pyproject.toml), clonado e lido em 17/11/2026
- id: mirage-hf
  resource: https://huggingface.co/tsunghanwu/mirage-llama3.1-8.3B
  title: Model card e config.json
- id: mirage-paper
  resource: https://arxiv.org/abs/2407.13766
  title: Visual Haystacks (ICLR 2025), seções 4.1 e 5
- id: mirage-train
  resource: https://huggingface.co/datasets/tsunghanwu/MIRAGE-training-set
  title: Conjunto de treino (amostras de mirage_ft.json)
---

# Situação

> **O MIRAGE real nunca foi executado neste projeto.** Tudo abaixo vem da leitura das fontes oficiais, feita em 17/11/2026. A geração de bounding boxes confiáveis pelo MIRAGE é **hipótese experimental**.

MIRAGE (*Multi-Image Retrieval Augmented GEneralization*) é um modelo de VQA e de recuperação visual em uma ou várias imagens.

## Arquitetura do modelo (verificado nas fontes)

- **Pipeline:** CLIP ViT-L/14-336 → Q-Former que reduz cada imagem de 576 para 32 tokens → MLP → Llama 3.1 8B (paper, §4.1; `config.json`: `LlavaLlamaForCausalLM`).
- **Recuperador:** uma relevância por imagem (`Linear → sigmoid`, em `llava/model/multimodal_encoder/retriever.py`).
- **Saída:** **só texto**, gerado token a token.
- **Ausências:** não há cabeça de detecção nem tokens especiais para caixas. Em `llava/constants.py` só existe `<image>`.
- **Avaliações publicadas:** VHs, RetVQA, VQAv2, GQA, VizWiz, TextVQA, POPE, MMBench e MM-Vet. **Nenhuma** de detecção ou grounding.

## Bounding boxes: o que se sabe

| Afirmação | Status |
|---|---|
| Capacidade documentada de detecção ou localização | **Não existe** |
| O treino contém caixas em texto | **Verificado.** `mirage_ft.json` tem amostras no estilo LLaVA-1.5/RefCOCO, por exemplo: *"Please provide the bounding box coordinate of the region this sentence describes: …"* → `"[0.07, 0.13, 0.7, 0.86]"` |
| Formato das caixas no treino | `[x1, y1, x2, y2]` normalizado entre 0 e 1, em **texto com colchetes**, não JSON |
| Padding da imagem na inferência | **Verificado.** `image_aspect_ratio: "pad"`; `expand2square` (`llava/mm_utils.py:152`) centraliza a imagem em um quadrado de lado `S = max(W, H)`, com deslocamento `(S − W) // 2` ou `(S − H) // 2` |
| As coordenadas se referem ao quadrado com padding | **Hipótese provável** (convenção do LLaVA-1.5). Confirmar com inferência real |
| O modelo responde coordenadas quando pedido | **Hipótese provável.** Precisão nunca medida |
| O modelo segue um prompt que pede JSON | **Desconhecido** |
| Confiança de detecção | **Não existe.** O recuperador dá relevância **por imagem**, e o `demo()` devolve só uma lista binária |
| Caixas com várias imagens | A saída não diz a qual imagem cada caixa pertence |

A conversão de coordenadas normalizadas no quadrado com padding para pixels, válida se a hipótese se confirmar, é:
`x_px = x·S − (S − W)//2` e `y_px = y·S − (S − H)//2`.

## API real de inferência (verificado em `demo.py`)

- Comando: `python3 demo.py --model-path tsunghanwu/mirage-llama3.1-8.3B --image-folder DIR --prompt "TEXTO" [--max-num-retrievals K]`.
- Entrada: todas as imagens de uma pasta + uma pergunta. A pergunta vai para o Q-Former/recuperador e para o prompt do Llama 3.
- Saída: `(texto, relevância_binária_por_imagem)`. Geração gulosa, com no máximo 512 tokens novos.
- O dispositivo está fixo em `device="cuda"`, em fp16.

## Requisitos e compatibilidade (verificado no `pyproject.toml` do MIRAGE)

- **Versões fixadas:**
  - Python ≥ 3.10 (o README usa 3.10);
  - `torch==2.1.2`, `torchvision==0.15.2`, `transformers==4.43`;
  - `bitsandbytes==0.41.0`, `accelerate==0.34.2`, `peft==0.4.0`;
  - **`pydantic<2`**;
  - `numpy` sem versão fixa.
- **Conflitos:**
  - `torchvision 0.15.2` exige `torch 2.0.1`; as versões parecem incompatíveis entre si (não testado);
  - torch 2.1.2 não tem pacotes compilados para Python 3.12;
  - o pacote é instalado com o nome `llava`.
- **Consequência:** o MIRAGE **não pode** ser importado no ambiente principal (Python 3.12, pydantic 2, numpy 2). Ele precisa de um ambiente isolado e deve ser chamado **fora do processo** (subprocesso ou serviço).
- **Hardware:**
  - CUDA é obrigatório na prática;
  - pesos em fp16 com cerca de 18,4 GB;
  - o paper usa uma A100 de 40 GB;
  - a quantização 4/8-bit (bitsandbytes) também exige CUDA.
- **Máquina local** (verificado em 17/11/2026): sem GPU NVIDIA e com 15 GB de RAM. **Não roda o MIRAGE.**
- **Licença:**
  - código e pesos sob MIT;
  - base Llama 3.1, cuja licença da Meta provavelmente também se aplica.

## Integração no workflow

| Parte | Estado |
|---|---|
| `VisualQuestionAnsweringComponent` + interface `VisualQuestionAnswerer` | **Implementado e testado com simulador** (experimental). Veja [VQA](component-visual-question-answering.md) |
| `MirageAnswerer` (adaptador real, fora do processo, conversão BGR→RGB) | Não iniciado. Depende da GPU |
| Interpretação de texto em `DetectionContent` | **Implementado e testado com respostas simuladas.** Veja [interpretação](component-text-detection-parsing.md) |
| Avaliação contra anotações humanas | **Implementado e testado com dados sintéticos.** Veja [avaliador](mirage-evaluation.md) |
| Prova de conceito em `experiments/mirage/` | **Arquivos presentes** (criados fora desta sessão de agente) e revisados em 17/11/2026. Dry run testado; **nunca executada de verdade** |

Fluxo-alvo: imagem + prompt → MIRAGE → resposta textual → JSON de detecções → imagem anotada.

## Prova de conceito em `experiments/mirage/` (revisada em 17/11/2026)

Os arquivos não foram gerados por esta sessão de agente; a origem foi registrada no log.

**Objetivo da prova de conceito:** permitir experimentos repetíveis com o `demo.py` oficial, preservando prompts, respostas textuais e logs. Ela serve para verificar se o MIRAGE responde adequadamente a imagem + prompt e para investigar, **sem presumir**, se ele produz bounding boxes em texto.

**Contratos preservados:**
- nenhum componente de produção é alterado; `ObjectDetectionComponent`, `DetectionVisualizationComponent`, `VisualQuestionAnsweringComponent` e os artefatos continuam independentes;
- a prova de conceito **não cria `DetectionContent`** e não inventa classes, caixas ou confiança; a conversão é feita depois, pelo `TextDetectionParser`;
- não exige nenhuma dependência nova no ambiente principal;
- instalar dependências, baixar pesos ou executar o modelo real exige aprovação.

*Incorporado em 18/11/2026 de `integrations/mirage-poc.md`, documento órfão do bundle antigo que foi removido. Os trechos dele que estavam desatualizados (por exemplo, "não foram aplicados nem testados") não foram trazidos, porque a seção abaixo registra o estado verificado. O histórico do arquivo está em [proveniência](provenance.md).*

| Arquivo | Função |
|---|---|
| `run_poc.py` | Envolve o `demo.py` oficial. **Por padrão só faz dry run**: valida as entradas e imprime o comando, as dimensões e a revisão. Com `--execute`, executa o `demo.py` em subprocesso e grava `stdout.txt`, `stderr.txt`, `answer.txt` (o trecho após `Text Output:`) e `run.json` |
| `prompts/vqa.txt` | Pergunta descritiva, sem pedir contagens, posições ou confiança |
| `prompts/boxes_normalized_padded_square.txt` | Pede **somente** JSON `[{"cls", "box"}]`, normalizado ao quadrado com padding, ou `[]`. Usa o mesmo esquema do `TextDetectionParser` |
| `tests/test_run_poc.py` | 34 testes offline (22 até 17/11; +12 da validação do nome do checkpoint em 18/11/2026), só com biblioteca padrão e pytest. Passam no Python 3.10.21 e no 3.12.14. Incluem a execução contra um `demo.py` falso, que imita a saída oficial sem modelo |
| `ruff.toml` | Alvo Python 3.10 do Ruff e raiz dos pacotes do projeto (`src = ["../.."]`), **só nesta pasta** |
| `evaluate_detections.py` | **Avaliador offline (17/11/2026).** Compara as respostas, interpretadas pelo `TextDetectionParser`, com anotações humanas: IoU, TP/FP/FN, precisão e revocação, no total e por classe. Veja [avaliador](mirage-evaluation.md) |
| `tests/test_evaluate_detections.py` | 47 testes sintéticos do avaliador |
| `.gitignore` | Ignora `outputs/`, `inputs/` e caches |
| `README.md` | Ambiente, uso, protocolo de avaliação com IoU contra anotação humana e critérios para avançar. Trechos desatualizados sobre confiança e parser foram corrigidos em 17/11/2026 |

**O que foi verificado:**
- os marcadores `---Output---`, `Text Output:` e `Retrieval Image:` batem com o `demo.py` oficial (commit `617751c`);
- `--prompt` recebe texto literal;
- não há download sem `--execute` + `--allow-remote-model` (ou um caminho local inexistente);
- os testes da prova de conceito passam (3 na versão recebida; 22 depois das correções de 17/11/2026);
- Ruff está OK.

**Correções aplicadas em 17/11/2026** (aprovadas pelo usuário):
1. **Compatibilidade com Python 3.10:** `datetime.UTC` → `timezone.utc`.
   - O erro foi reproduzido no Python 3.10.21 (`ImportError`).
   - Os 22 testes passam no 3.10.21 (interpretador do `uv` em ambiente temporário, sem tocar no `.venv`) e no 3.12.14.
   - O dry run real no 3.10, com o clone oficial e `BloodImage_00236.jpg`, mostrou 640x480, a revisão `617751c` e a associação de imagem única, sem criar arquivos.
2. **O `run.json` agora registra:**
   - dimensões armazenadas e orientação EXIF de cada imagem;
   - `revision`/`dirty` do repositório oficial;
   - parâmetros, comando, Python, plataforma, GPU (via `nvidia-smi`) e duração.
3. **Relação entre imagens e resposta:**
   - a ordem e as recuperadas vêm das linhas `Images:` e `Retrieval Image:` do `demo.py`, e a associação é **por caminho**;
   - `answer_image` só é preenchido quando há uma imagem; com várias fica `null`, com a regra explicada;
   - JPEG com rotação EXIF é **recusado**, porque o PIL (MIRAGE) e o OpenCV (projeto) veriam grades de pixels diferentes;
   - WebP saiu dos formatos aceitos.
4. A resposta não é mais cortada se contiver o texto "Retrieval Image:".

**Limitações que permanecem:**
1. **Execução:** sem `timeout` e sem saída progressiva.
2. **Prompts:**
   - o de caixas usa o esquema do parser, mas a redação é diferente da usada no treino;
   - não existe variante com a frase de grounding do treino. A resposta com colchetes seria rejeitada pelo parser, por decisão.
3. **Avaliação:** ~~não há script~~. O avaliador foi implementado em 17/11/2026 ([avaliador](mirage-evaluation.md)), mas **nunca rodou com dados reais**.
4. **Testes fora da suíte principal:** os testes do experimento não entram em `uv run python -m pytest` (`testpaths = ["tests"]`).
5. **Instalação oficial:** o ambiente conda do MIRAGE e a instalação oficial **nunca foram testados**.
6. **Hipótese não verificada:** que o LLM veja só as imagens recuperadas. Por isso, não se associa a resposta a uma imagem quando há várias.

**Validação do nome do checkpoint (18/11/2026, decisão E3):** o `run_poc.py` recusa um `--model-path` cujo nome, derivado como no `get_model_name_from_path` oficial (último segmento, ou `pasta_checkpoint-N`), não contenha `mirage` ou `llava`, ou contenha `lora`. Sem isso, o `builder.py` oficial carregaria a classe errada **sem erro**. Use, por exemplo, `.../mirage-llama3.1-8.3B`, e não a pasta de *snapshot* do cache do Hugging Face (o nome dela é um hash).

## Plano de execução da prova de conceito

1. Ambiente conda com Python 3.10, em máquina com GPU NVIDIA (provavelmente 24 GB ou mais para uma imagem em fp16; não verificado).
2. Rodar o `demo.py` oficial com imagens de células e guardar as respostas exatamente como saírem.
3. Testar o prompt de grounding do treino e um prompt que peça JSON.
4. Medir o IoU, a precisão e a revocação contra **anotações verdadeiras**, não contra a saída do YOLO.
5. Decidir, com base nos números, se o caminho via MIRAGE serve. Alternativa: um detector guiado por texto (OWLv2, Grounding DINO) implementando o `ObjectDetector` que já existe.

## Fora de escopo até a validação

- Tratar o MIRAGE como substituto do YOLO.
- Inventar caixas, classes ou confiança.
- Instalar dependências do MIRAGE no ambiente principal ou baixar pesos sem aprovação.
