# MIRAGE — prova de conceito isolada

**Estado em 2026-11-17:** scripts e testes locais preparados. **Não foi realizada inferência real.** Nenhum peso ou dependência do MIRAGE foi instalado. A prova de conceito não implementa um detector de objetos, nem se conecta ainda aos componentes de produção.

## Propósito

Investigar o comportamento real do [MIRAGE oficial](https://github.com/visual-haystacks/mirage) com uma imagem e um prompt, preservando a saída bruta e, opcionalmente, testando prompts de localização textual. A documentação do projeto descreve um modelo de visual question answering e recuperação de imagens, **não uma API nativa de bounding boxes**.

A pesquisa experimental está separada de `mlops_workflows/`. A conversão de respostas textuais em `DetectionContent` é responsabilidade exclusiva do `TextDetectionParser` do pacote principal. Ele foi implementado em 17/11/2026, valida o esquema, exige uma convenção de coordenadas explícita e grava `conf: null`. Mesmo assim, uma resposta convertida **não** está validada espacialmente: veja `docs/references/component-text-detection-parsing.md`.

## Conteúdo

- `run_poc.py`: executor da interface CLI original `demo.py`, com **dry run por padrão** e captura auditável de saída quando autorizado.
- `prompts/vqa.txt`: pergunta textual exploratória.
- `prompts/boxes_normalized_padded_square.txt`: tentativa **experimental, não validada**, de obter caixas normalizadas em texto.
- `evaluate_detections.py`: avaliador offline. Compara as respostas, interpretadas pelo `TextDetectionParser`, com anotações humanas: IoU, TP/FP/FN, precisão e revocação. Veja a seção "Avaliação offline".
- `tests/test_evaluate_detections.py`: 47 testes sintéticos do avaliador.
- `tests/test_run_poc.py`: 34 testes locais (+12 em 18/11/2026, da validação do nome do checkpoint). Usam só a biblioteca padrão e o pytest, sem dependências do MIRAGE, e também passam no Python 3.10.
- `ruff.toml`: define Python 3.10 como alvo do Ruff **só nesta pasta**, para que ele não sugira APIs 3.11+ como `datetime.UTC`. A configuração do projeto principal não muda.
- `.gitignore`: impede versionar resultados e imagens de entrada colocados nesta pasta.

## O que foi conferido no código oficial

`demo.py` aceita `--model-path`, `--image-folder`, `--prompt` **como texto literal**, e `--max-num-retrievals`; no código oficial ele imprime `Text Output:` e `Retrieval Image:`. O README do projeto chama `--prompt` de *prompt path*, mas **o código recebe uma string direta**, portanto este wrapper lê um arquivo de prompt e envia seu conteúdo como argumento. Os caminhos em `--image-folder` são lidos da pasta inteira, sem filtragem; nosso wrapper rejeita arquivos estranhos. Veja [demo.py oficial](https://github.com/visual-haystacks/mirage/blob/main/demo.py).

A saída textual não possui esquema garantido para detecções nem confiança de detecção. Não inferir que JSON bem formado implica localização correta.

## Ambiente futuro, em máquina com GPU compatível

O ambiente principal do `mlops-workflows` utiliza outras versões de Python e bibliotecas. **Não instale MIRAGE dentro do `.venv` do projeto.** Segundo o README oficial, a instalação recomendada utiliza conda e Python 3.10:

```bash
# Executar apenas na máquina autorizada para o experimento, com GPU CUDA.
git clone https://github.com/visual-haystacks/mirage.git /workspace/mirage-official
conda create -n mirage python=3.10 -y
conda activate mirage
cd /workspace/mirage-official
python -m pip install --upgrade pip
python -m pip install -e .
```

**Atenção:** essas instruções são transcritas da documentação oficial; a instalação e as versões de dependências **não foram testadas** nesta prova de conceito. O `demo.py` carrega o modelo com `device="cuda"`. Antes de executar, verifique licença do modelo base, driver/CUDA, VRAM, espaço em disco, credenciais de acesso ao modelo e eventuais incompatibilidades de dependências. A quantidade exata de VRAM necessária para nosso caso ainda não foi medida.

## Validar sem GPU e sem baixar nada

A partir da raiz do projeto:

```bash
uv run python -m pytest experiments/mirage/tests -q
# Validar com Python 3.10 sem tocar no .venv do projeto (o uv baixa o interpretador e o pytest para um ambiente temporário):
uv run --no-project --python 3.10 --with pytest --with "pydantic>=2,<3" python -m pytest experiments/mirage/tests -q -p no:cacheprovider
```

Para inspecionar o comando sem executar, é necessário ter uma cópia de `demo.py` oficial e uma pasta contendo **somente** imagens de teste. O caminho do modelo no dry run pode ser um placeholder:

```bash
python3 experiments/mirage/run_poc.py \
  --official-repo /workspace/mirage-official \
  --image-folder /workspace/test-images \
  --prompt-file experiments/mirage/prompts/vqa.txt \
  --model-path /workspace/checkpoints/mirage \
  --output-dir experiments/mirage/outputs/vqa
```

**Sem `--execute` não há inferência, downloads nem escrita de resultados.**

## Executar um experimento real (somente mediante autorização)

No ambiente conda **da máquina com GPU** e com o checkpoint local disponível:

```bash
python experiments/mirage/run_poc.py \
  --official-repo /workspace/mirage-official \
  --image-folder /workspace/test-images \
  --prompt-file experiments/mirage/prompts/vqa.txt \
  --model-path /workspace/checkpoints/mirage \
  --output-dir experiments/mirage/outputs/vqa \
  --execute
```

Para o teste exploratório de caixas, substitua `--prompt-file` por `experiments/mirage/prompts/boxes_normalized_padded_square.txt` e use outro `--output-dir`, como `.../outputs/boxes`.

O wrapper **não** executa instaladores. Um `--model-path` local evita passar diretamente um identificador remoto, mas o código oficial **ainda pode acessar outros checkpoints/dependências pela rede**; confirme isso no ambiente isolado e execute apenas com autorização. Caso deseje conscientemente usar um identificador remoto do Hugging Face como `--model-path`, existe `--allow-remote-model`, que pode causar download grande durante a inferência.

**Nome da pasta do checkpoint (validado desde 18/11/2026):** o `builder.py` oficial só monta o modelo multimodal se o nome derivado do `--model-path` contiver `mirage` ou `llava` (e não `lora`). Em qualquer modo, o wrapper recusa outros nomes. Use `--local-dir .../mirage-llama3.1-8.3B` ao baixar, e não a pasta de *snapshot* do cache.

### Arquivos gravados quando `--execute` é usado

- `stdout.txt`: **toda** a saída padrão original do `demo.py`.
- `stderr.txt`: saída de erro original, inclusive em caso de falha.
- `run.json`: metadados para rastrear a execução:
  - `started_at_utc`, `finished_at_utc` e `duration_seconds`;
  - `parameters`: modelo, caminho resolvido, pasta, arquivo de prompt, `max_num_retrievals` e `allow_remote_model`;
  - `prompt` e o `command` exato;
  - `official_repo`: caminho, `revision` (commit Git) e `dirty`, quando for um repositório Git;
  - `environment`: Python, plataforma e GPU via `nvidia-smi`, quando disponível;
  - `images`: uma entrada por imagem com `path`, `width`, `height`, `exif_orientation` e `retrieved`, **na ordem impressa pelo `demo.py`** (`image_order_source`);
  - `answer_image` e `answer_image_rule`;
  - `returncode` e `answer_extracted`.
- `answer.txt`: extraído de `Text Output:` somente quando o marcador existe; pode conter qualquer texto, inclusive JSON inválido.

O wrapper **não** cria um artefato `DetectionReference` nem interpreta os rótulos ou caixas. Conserve os arquivos brutos para rastreabilidade. Não suba imagens ou resultados potencialmente sensíveis para um repositório público.

### Relação entre imagens, resposta e coordenadas

- **Dimensões:** são lidas do cabeçalho do arquivo (PNG, JPEG ou BMP), só com a biblioteca padrão. São as dimensões **armazenadas**, que é o tamanho que o PIL entrega ao MIRAGE antes do padding. A leitura foi conferida contra o OpenCV em PNG, JPEG baseline e progressivo, BMP e na imagem real de células.
- **JPEG com rotação EXIF é recusado** (orientação diferente de 1). O MIRAGE (PIL) ignora a rotação, mas o OpenCV do projeto aplica. As coordenadas ficariam em grades de pixels diferentes. Salve a imagem sem rotação antes.
- **WebP saiu dos formatos aceitos** em 17/11/2026. Ler as dimensões dele exigiria tratar três variantes de cabeçalho, e não há demanda.
- **Associação por caminho, nunca por posição:**
  - a ordem e as imagens recuperadas vêm das linhas `Images:` e `Retrieval Image:` impressas pelo `demo.py`;
  - se não for possível ler essas linhas, usa-se a listagem ordenada (`image_order_source: "wrapper_sorted_listing"`) e `retrieved: null`.
- **`answer_image`** só é preenchido quando a pasta tem **exatamente uma imagem**.
  - Com várias imagens fica `null`, porque a saída do MIRAGE não diz a qual imagem cada frase ou caixa se refere.
  - Que o LLM veja só as imagens recuperadas é plausível, mas **não foi verificado**. Por isso, essa informação não é usada para fazer a associação.

## Avaliação offline (`evaluate_detections.py`)

Rode **fora** do ambiente conda do MIRAGE, a partir da raiz do repositório, no ambiente do projeto. O motivo é que o avaliador usa o parser do pacote, que precisa de Pydantic 2.

```bash
uv run python -m experiments.mirage.evaluate_detections \
  --ground-truth annotations.json \
  --predictions predictions.json \
  --coordinate-format normalized_padded_square \
  --output report.json
```

- **`annotations.json`:** `{"images": [{"image_id", "width", "height", "objects": [{"cls", "box"}]}]}`, com caixas em pixels da imagem original.
- **`predictions.json`:** `{"predictions": [{"image_id", "run_dir"}]}`. Cada `run_dir` é a pasta de saída de um `run_poc.py --execute` com **uma** imagem. As dimensões no `run.json` precisam coincidir com as da anotação.
- **Política de respostas inválidas:** respostas inválidas ou ausentes **entram** no relatório com zero predições. Todas as anotações dessas imagens viram falsos negativos.
- **Confiança:** não há AP/mAP, porque não existe confiança.

Definições completas: `docs/references/mirage-evaluation.md`.

## Protocolo de avaliação de bounding boxes

Esta parte é uma **hipótese de pesquisa**, não uma funcionalidade validada do MIRAGE.

1. Prepare um conjunto de imagens de teste com **bounding boxes de referência anotadas por humanos**, no espaço de pixels da imagem original. Não use as caixas do YOLO como *ground truth*.
2. Registre dimensões originais `(width, height)`, imagens usadas, prompt exato, modelo e versão do código oficial.
3. Execute primeiro a pergunta VQA e depois a pergunta experimental de caixas, usando uma imagem por pasta para evitar ambiguidade de associação entre imagens e caixas.
4. Salve `stdout.txt`, `answer.txt` e `run.json`, inclusive respostas malformadas. Não transforme saídas incompletas em caixas fictícias.
5. Se o modelo realmente devolver JSON, avalie separadamente: validade sintática, validade de classes/caixas e adequação espacial. **Não pressuponha** que ele respeitou a convenção solicitada.
6. Para caixas normalizadas em espaço quadrado com padding, documente e confirme a transformação de pré-processamento **efetivamente utilizada**. Em princípio, a conversão para pixels originais subtrai as margens de padding após multiplicar pela dimensão quadrada; essa relação só deve ser aplicada depois de verificar o processamento real e a ordem dos arredondamentos.
7. Compare caixas com as anotações humanas: IoU por classe, precisão/recall para limiar de IoU predefinido (ex.: 0,5), casos inválidos, objetos omitidos e falsos positivos. Em imagens com múltiplas caixas, use um pareamento um-para-um das predições com as anotações.
8. Registre resultados **sem** inventar `conf`. Desde 17/11/2026, `Detection.conf` aceita `None` (`"conf": null` no JSON). Esse é o único valor permitido para detecções vindas de texto.

### Critérios para avançar

Avançar para `MirageAnswerer` e usar o parser sobre saídas reais apenas após (a) inferência real em ambiente adequado, (b) verificação de outputs efetivos e (c) validação do formato e do sistema de coordenadas. O item (d), sobre a representação de confiança ausente, foi decidido em 17/11/2026: `conf: null`. Um resultado de JSON estruturalmente válido, sozinho, **não aprova** o uso para localização.

## Próximas decisões

- Onde executar o checkpoint real (GPU local remota/cloud), com autorização e custos conhecidos.
- Como isolar dependências no futuro adaptador (subprocesso ou serviço HTTP).
- Quais anotações serão usadas como referência para avaliar caixas.
- ~~Como interpretar a ausência de confiança~~: decidido em 17/11/2026 (`conf: null`).

## Problemas corrigidos em 17/11/2026 (aprovados pelo usuário)

- **Incompatibilidade com Python 3.10:**
  - `datetime.UTC` foi trocado por `timezone.utc`;
  - antes da correção, o erro foi reproduzido com o Python 3.10.21 (`ImportError`);
  - depois da correção, os 22 testes passam no 3.10.21 e no 3.12.14.
- **Rastreabilidade do `run.json`:** agora registra dimensões, orientação EXIF, revisão do repositório oficial, parâmetros, ambiente e duração.
- **Ordem das imagens:** passa a ser lida da saída do `demo.py`, e a associação é feita por caminho.
- **Extração da resposta:** se o texto da resposta contiver "Retrieval Image:", ele não é mais cortado; o corte usa a última ocorrência.

## Limitações que permanecem

- **Execução:** não tem `timeout` e a saída só aparece no fim. O carregamento do modelo pode levar minutos sem nenhum progresso visível.
- **Testes fora da suíte principal:** os testes desta pasta (81) não entram em `uv run python -m pytest`, porque `testpaths = ["tests"]`. Rode-os explicitamente, da raiz do repositório.
- **Repositório oficial:** `revision` e `dirty` ficam `null` se ele não for um repositório Git.
- **PNG:** um chunk `eXIf` não é verificado. Esse caso é raro.
- **Instalação:** o ambiente conda do MIRAGE e a instalação oficial **continuam sem teste**.

## Fontes

- [Implementação e instalação oficial](https://github.com/visual-haystacks/mirage)
- [Código da CLI demo.py](https://github.com/visual-haystacks/mirage/blob/main/demo.py)
- [Cartão do checkpoint](https://huggingface.co/tsunghanwu/mirage-llama3.1-8.3B)
- [Paper Visual Haystacks](https://arxiv.org/abs/2407.13766)
