---
type: Reference
title: Interpretação de respostas textuais em detecções
description: TextDetectionParser e TextDetectionParsingComponent — formato aceito, convenções de coordenadas, confiança ausente, validação estrita e testes.
tags:
- parser
- detection
- mirage
- component
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:28:27-03:00"
evidence_basis: [verified, approved, hypothesis]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d0fb7f2 + alterações não commitadas), inspecionado e testado em 17/11/2026
  title: Código, testes e execuções locais
- id: mirage-repo
  resource: https://github.com/visual-haystacks/mirage
  title: expand2square em llava/mm_utils.py
---

# Situação

**Implementado e testado em 17/11/2026, com respostas simuladas. Não commitado.**

O parser transforma uma resposta textual em `DetectionContent` **estruturalmente válido**. Ele **não** comprova que as caixas estejam corretas. Gerar caixas úteis com o MIRAGE continua sendo **hipótese experimental**, porque o MIRAGE nunca foi executado.

## Fluxo

```text
ImageReference + TextReference(prompt) → VisualQuestionAnsweringComponent → TextReference(resposta)
ImageReference + TextReference(resposta) → TextDetectionParsingComponent → DetectionReference(JSON, conf=null)
ImageReference + DetectionReference → DetectionVisualizationComponent → ImageReference(anotada)
```

Esse encadeamento foi verificado com um `FakeAnswerer` em `tests/integration/components/text_detection_parsing/test_text_detection_pipeline.py`.

## Arquivos

| Arquivo | Mudança |
|---|---|
| `mlops_workflows/components/text_detection_parsing/text_detection_parser.py` | **Novo:** `CoordinateFormat`, `TextDetection`, `TextDetectionParser` |
| `mlops_workflows/components/text_detection_parsing/text_detection_parsing_component.py` | **Novo:** `TextDetectionParsingComponent` |
| `mlops_workflows/components/text_detection_parsing/__init__.py` | **Novo** (vazio) |
| `mlops_workflows/artifacts/detection/detection.py` | `conf: float \| None`, obrigatório |
| `mlops_workflows/components/detection_visualization/detection_visualization_component.py` | Rótulo só com `cls` quando `conf is None` |
| `tests/unit/components/text_detection_parsing/test_text_detection_parser.py` | **Novo**, 55 testes (parametrizados); 99 após as correções P1–P3 |
| `tests/unit/components/text_detection_parsing/test_text_detection_parsing_component.py` | **Novo**, 7 testes; 10 após as correções P1–P3 |
| `tests/integration/components/text_detection_parsing/test_text_detection_pipeline.py` | **Novo**, 2 testes |
| `tests/unit/artifacts/detection/test_detection_artifacts.py` (desde 19/11/2026, `test_detection.py` e `test_detection_reference.py`) | +4 testes (`conf` nulo, obrigatório, intervalo) |
| `tests/unit/components/detection_visualization/test_detection_visualization_component.py` | +1 teste (desenho sem confiança) |

Não foi adicionada nenhuma dependência: só `json`, `typing` e Pydantic, que já estavam no projeto.

## Formato aceito (reuso do `DetectionContent`)

O formato do `DetectionContent` (`[{"cls", "conf", "box"}]`) foi reutilizado **sem o campo `conf`**:

```json
[
  {"cls": "WBC", "box": [0.1, 0.35, 0.5, 0.65]},
  {"cls": "RBC", "box": [0.6, 0.2, 0.8, 0.4]}
]
```

- **Só JSON puro**, decisão aprovada em 17/11/2026. Espaços nas pontas são aceitos.
- **Rejeitados com `ValueError("The response is not valid JSON.")`:**
  - texto livre;
  - JSON dentro de bloco Markdown;
  - JSON precedido de texto, como `Answer: [...]`.
- **A raiz precisa ser uma lista.** Um objeto, `null` ou um número geram `ValueError`.
  - Aqui usei `ValueError` em vez de `TypeError`, contrariando a regra TRY004 do Ruff (há `noqa` com justificativa).
  - Motivo: é uma resposta malformada do modelo, e quem chama trata qualquer resposta inválida com um único tipo de exceção.
- **`[]`** é uma resposta válida sem objetos e gera `DetectionContent(data=[])`.
- **Diferença entre resposta vazia e malformada:** só `[]` explícito significa "nenhum objeto". Texto como "não há células" é **malformado**, porque não dá para distinguir de um modelo que ignorou o formato.

**Modelo de validação de cada item:** `TextDetection`, com Pydantic `strict=True` e `extra="forbid"`.
- `cls`: `str`, não pode ser vazio, só espaços, nem ter espaço nas pontas (P2).
- `box`: exatamente 4 números finitos (`allow_inf_nan=False`).
  - **Aceitos:** `int` e `float`.
  - **Rejeitados:** `bool`, strings, `null`.
- **Campos extras rejeitados,** incluindo `conf` e `confidence` escritos pelo modelo. Uma confiança escrita em texto não é uma nota calibrada de detecção.
- **`NaN`/`Infinity`** são bloqueados no `json.loads(parse_constant=...)`.
- **`1e400`** vira infinito no `json.loads` e é rejeitado pela validação de número finito.
- **Chaves duplicadas** em qualquer objeto são rejeitadas (P1).

## Convenções de coordenadas (explícitas, sem padrão)

`TextDetectionParser(coordinate_format)` exige uma das três convenções abaixo. **Não há valor padrão nem detecção automática.** Motivo: `[0, 0, 1, 1]` é uma caixa válida em pixels, então adivinhar o formato seria arriscado.

| `coordinate_format` | Significado de `[x1, y1, x2, y2]` | Validação no espaço declarado | Conversão para pixels |
|---|---|---|---|
| `pixel` | Pixels da imagem original | `0 ≤ x ≤ W`, `0 ≤ y ≤ H` | Nenhuma |
| `normalized_image` | Entre 0 e 1, relativo à imagem original | Todos os valores entre 0 e 1 | `x·W`, `y·H` |
| `normalized_padded_square` | Entre 0 e 1, relativo a um quadrado `S = max(W, H)` com a imagem centralizada (o `expand2square` do LLaVA/MIRAGE) | Todos os valores entre 0 e 1 | `x·S − (S−W)//2`, `y·S − (S−H)//2`, depois recorte em `[0, W] × [0, H]` |

- **Em todas as convenções**, a caixa precisa ter `x1 < x2` e `y1 < y2` no espaço declarado. O parser não reordena coordenadas.
- **No `normalized_padded_square`:**
  - uma caixa que invade o padding é recortada à imagem;
  - uma caixa **inteira** no padding fica sem área e é rejeitada.
- **Qual convenção o MIRAGE usa ainda não foi comprovado.** A hipótese mais provável é `normalized_padded_square`, porque o modelo usa `image_aspect_ratio: "pad"` e `expand2square` (verificado no código). Isso só será confirmado com inferência real. O parser não presume nada: quem cria o componente escolhe a convenção.

## Confiança ausente (aprovado em 17/11/2026)

- `Detection.conf` passou a ser `Annotated[float, Field(ge=0.0, le=1.0)] | None`, **sem valor padrão**.
  - Quem cria uma `Detection` precisa passar `conf` explicitamente, mesmo que seja `None`.
  - Valores numéricos continuam limitados a [0, 1].
- **No JSON**, a confiança ausente aparece como `"conf": null`.
- **Compatibilidade verificada:**
  - os JSONs existentes continuam sendo carregados;
  - o `YoloDetector` sempre preenche `conf`;
  - o fluxo real (17 detecções) produziu as mesmas classes e confianças de antes.
- **Visualizador:** quando não há confiança, o rótulo mostra só `cls`. A única mudança foram três linhas no `execute()`.

## Validação estrita (aprovado em 17/11/2026)

- Se **qualquer** item for inválido, `parse()` lança `ValueError("Invalid detection at index N: …")` e não devolve nada.
- O componente faz o parse **inteiro antes** de chamar `dematerialize`. Por isso, uma resposta inválida não cria arquivo JSON, nem parcial.

## Classes e responsabilidades

**`TextDetectionParser`** é uma classe concreta e pura: não faz I/O e não depende do MIRAGE nem do visualizador.
- Assinatura: `parse(text: str, image_width: int, image_height: int) -> list[Detection]`.
- Valida a entrada (texto `str`, dimensões inteiras positivas), interpreta o JSON, valida cada item e converte as caixas.
- Sempre devolve `conf=None`.
- **Sem ABC:** só existe uma implementação (YAGNI). Ele é injetado no componente pelo construtor (DI).
- **Desvio do plano inicial:** o plano previa uma classe `TextDetectionParserConfig`. Ela foi substituída por um parâmetro `coordinate_format` no construtor, validado contra o `Literal` (KISS).

**`TextDetectionParsingComponent(Component)`** recebe `parser: TextDetectionParser` e `output_reference: DetectionReference`.
- `prepare([ImageReference, TextReference]) -> tuple[ImageContent, TextContent]`, seguindo a convenção de devolver conteúdos.
- `execute()`:
  - valida a tupla de conteúdos (senão gera `TypeError`);
  - lê `H, W` da imagem;
  - chama `parse`;
  - salva com `DetectionContent(...).dematerialize(...)`;
  - retorna `[output_reference]`.

## Validade estrutural não é confiabilidade espacial

- **O parser garante:** formato, tipos, números finitos, ordem, intervalos e caixas com área dentro da imagem.
- **O parser não garante:** que a caixa contenha o objeto nem que `cls` esteja correto.
- **Como medir:** inferência real + IoU, precisão e revocação contra anotações verdadeiras (prova de conceito em `experiments/mirage/`).
- **`conf: null`** identifica detecções sem nota calibrada.

## Testes (verificados em 17/11/2026)

- **Parser (55):**
  - caixas em pixels mantidas, com `conf=None`;
  - espaços nas pontas;
  - `[]`;
  - normalizado em relação à imagem (2 casos);
  - quadrado com padding: paisagem, retrato, quadrado, deslocamento ímpar e recorte;
  - caixa inteira no padding;
  - texto livre, JSON quebrado, bloco Markdown e JSON precedido de texto;
  - raiz que não é lista (4 casos);
  - 14 itens inválidos, incluindo `conf`/`confidence` vindos do modelo;
  - `NaN`, `Infinity`, `-Infinity` e `1e400`;
  - 10 caixas fora de ordem ou fora do intervalo;
  - item inválido no meio de válidos;
  - formato de coordenadas desconhecido;
  - dimensões inválidas;
  - resposta que não é `str`.
- **Componente (7):**
  - `prepare()` retorna conteúdos e rejeita entradas inválidas;
  - JSON salvo no formato existente com `"conf": null`;
  - `[]` gera um artefato vazio;
  - resposta inválida ou parcial não cria arquivo;
  - dados preparados inválidos.
- **Integração (2):**
  - `FakeAnswerer` → VQA → parser → visualizador, com caixa convertida para `[10, 10, 50, 40]` e pixel verde;
  - resposta não JSON interrompe o fluxo, sem JSON de detecções nem imagem anotada.
- **Artefatos (+4):** round-trip com `null`; `conf` obrigatório; intervalo 0 a 1 mantido.
- **Visualizador (+1):** desenha sem confiança, e o rótulo difere do caso com confiança.

## Limitações e pendências

- Não aceita o formato de colchetes do treino do MIRAGE (`[0.07, 0.13, 0.7, 0.86]` sem chaves) nem JSON dentro de texto ou Markdown. Reavaliar após ver respostas reais.
- Uma imagem por resposta. O modo de várias imagens do MIRAGE não indica a qual imagem cada caixa pertence.
- `cls` é texto livre do modelo, sem verificação contra uma lista de classes. Se for necessário, isso entra como opção futura, só com demanda.
- A convenção de coordenadas do MIRAGE está **por confirmar**.

## Revisão de 17/11/2026 (sem alteração de código)

### Conformidade com as decisões aprovadas

| Decisão | Verificação |
|---|---|
| `conf: None`; nunca inventar | Conforme. O parser sempre cria `Detection(conf=None)`; `conf`/`confidence` do modelo são rejeitados |
| Validação estrita, sem artefato parcial | Conforme. A primeira falha interrompe `parse()`; o componente só chama `dematerialize` depois do parse completo |
| Só JSON puro | Conforme. Markdown, texto em volta e texto livre geram `not valid JSON` |
| `[]` válido ≠ resposta malformada | Conforme. `[]` gera um artefato vazio; texto livre e raiz que não é lista geram `ValueError` |
| Convenção de coordenadas explícita | Conforme. Parâmetro obrigatório, sem padrão; valor desconhecido gera `ValueError` |
| Independência do MIRAGE e da visualização | Conforme. O parser importa só `Detection`; o componente importa só artefatos e o parser |
| `prepare()` devolve conteúdos | Conforme: `tuple[ImageContent, TextContent]` |
| YOLO inalterado | Conforme. 17 detecções idênticas (classes e confianças) às do `outputs/detections.json` anterior |

### Coordenadas (confirmado)

- `pixel` e `normalized_image` **rejeitam** valores fora do espaço declarado, sem recortar.
- `normalized_padded_square` **recorta** à imagem, porque invadir a área de padding é legítimo nesse espaço. Uma caixa inteira no padding é rejeitada.
- Essa assimetria é intencional.

### Achados (casos-limite testados manualmente; nenhum corrigido, aguardando decisão)

| # | Achado | Impacto | Sugestão |
|---|---|---|---|
| P1 | Chaves JSON duplicadas são aceitas, e a última vence: `{"cls": "a", "cls": "b"}` gera `"b"` | Médio: ambiguidade na saída do modelo passa despercebida | **Corrigido em 17/11/2026** |
| P2 | `cls` não é aparado: `" WBC "` é mantido com os espaços | Baixo a médio: rótulo feio; comparação futura com uma lista de classes falharia | **Corrigido em 17/11/2026** (rejeitado) |
| P3 | `bool` é aceito como dimensão (`True` vira 1), porque `bool` é subclasse de `int` | Baixo: o componente passa `shape` (inteiros) | **Corrigido em 17/11/2026** |
| P4 | Texto com BOM UTF-8 dá `not valid JSON` | Baixo: nossos artefatos são gravados sem BOM | Documentado; nenhuma ação |
| P5 | Caixas microscópicas são aceitas (área próxima de 0); o visualizador as trunca para 0 px | Baixo | Documentado; tamanho mínimo só com demanda (YAGNI) |
| P6 | Detecções duplicadas ou sobrepostas são mantidas (sem NMS) | Intencional: o parser não altera o conteúdo do modelo | Documentado |
| P7 | `except (ValidationError, ValueError)` é redundante, porque `ValidationError` já é `ValueError` | Cosmético | Simplificar em uma futura alteração autorizada |

## Correções P1–P3 (17/11/2026, aprovadas pelo usuário)

| # | Correção | Como |
|---|---|---|
| P1 | Rejeita chaves duplicadas em **qualquer** objeto JSON, inclusive internos | `json.loads(object_pairs_hook=_reject_duplicate_keys)`. A mensagem fica `The response is not valid JSON: Duplicate JSON key: 'cls'` |
| P2 | Rejeita `cls` vazio, só com espaços ou com espaço **nas pontas** (incluindo `\t`, `\n`, `\u00a0`) | `value != value.strip()` no validador de `TextDetection`. Espaços internos continuam válidos (`"white blood cell"`) |
| P3 | Rejeita `bool` como coordenada e como dimensão da imagem | **Coordenadas:** já eram rejeitadas pelo `strict=True`; ganharam testes de regressão em todas as posições, nos três formatos e com `true`/`false`. **Dimensões:** `isinstance(x, bool)` excluído explicitamente |

- **Mensagem de JSON inválido:** agora inclui a causa (`The response is not valid JSON: <detalhe>`). O prefixo não mudou.
- **Validação estrita mantida:** uma chave duplicada em qualquer item rejeita a resposta inteira, e o componente não grava arquivo.
- **Detecções válidas:** o comportamento não mudou. Todos os testes anteriores passam sem alteração, e o YOLO não é afetado, porque o parser é independente.

**Testes de regressão:** +44 no parser (55 → 99) e +3 no componente (7 → 10).
- **P1:** chave duplicada em `cls`, em `box`, em objeto interno e no segundo item. Também confirma que as mesmas chaves em objetos diferentes continuam permitidas.
- **P2:** 9 variações de espaço ou vazio, e espaços internos aceitos.
- **P3:** 24 combinações de booleano em coordenada (3 formatos × 2 valores × 4 posições) e 4 de booleano em dimensão.
- **Componente:** chave duplicada, `cls` com espaço e `true` em coordenada não criam arquivo.

Resultado: **218 passed** com ONNX real; 217 passed + 1 skipped sem ONNX.
