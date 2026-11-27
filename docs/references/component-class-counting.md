---
type: Reference
title: ClassCountingComponent
description: Contagem de detecções por classe, independente do detector, nos modos genérico (todas as classes) e restrito a um domínio configurado.
tags:
- components
- counting
- detection
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-23T13:24:49-03:00"
evidence_basis: [verified, approved]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d3c737c + alterações não commitadas), inspecionado e testado em 23/11/2026
  title: Código, testes e execuções locais
- id: visres-337
  resource: Critérios da tarefa VISRES-337 colados pelo usuário e conferidos no Jira em 23/11/2026 (https://visio-ai.atlassian.net/browse/VISRES-337)
  title: Tarefa VISRES-337
---

# ClassCountingComponent

Tarefa: VISRES-337. Arquivo: `mlops_workflows/components/class_counting/class_counting_component.py` (não commitado). Decisões em [ADR 011](../adr/011-class-counting-component.md).

## Responsabilidade

Receber detecções produzidas por **qualquer** detector e contar quantas existem de cada valor do campo `cls`.

- Conta **predições**: não presume que estejam visualmente corretas.
- Não executa, não altera e não conhece o detector (YOLO, parser de texto, Florence-2, Qwen3-VL…).
- Não filtra por confiança: `conf` baixo e `conf: null` contam igual.
- Não normaliza nomes: `"RBC"`, `"rbc"` e `"RBC "` são classes diferentes.
- Não tem lista de classes embutida: o domínio vem do construtor.

## Construtor

```python
ClassCountingComponent(
    classes=["RBC", "WBC", "Platelets"],  # ou None, ou []
    output_reference=ClassCountReference(name="counts", location="counts.json"),
)
```

- `classes`: `None` ou `list[str]`; outro tipo gera `TypeError` (uma `str` solta, por exemplo, não é aceita como lista). Nomes repetidos geram `ValueError`. A lista é **copiada**, então alterar a original depois não muda o componente.
- `output_reference`: o `ClassCountReference` onde a contagem é gravada.

## Entradas e saída

- **`prepare(input_artifacts)`:** exige exatamente um `DetectionReference`; senão `ValueError`. Devolve o `DetectionContent` materializado (convenção do [ADR 002](../adr/002-prepare-returns-artifact-contents.md)).
- **`execute(prepared_data)`:** exige um `DetectionContent`; senão `TypeError`, sem gravar nada. Monta e valida o `ClassCount` **antes** de gravar, salva com `ClassCountContent.dematerialize(output_reference)` e devolve `[output_reference]`.
- **Saída:** JSON descrito em [artefato de contagem](artifact-class-count.md).

## Modos

| `classes` | `counts` | `total` | `excluded` |
|---|---|---|---|
| `None` (genérico) | todas as classes detectadas, na ordem em que aparecem pela primeira vez | soma de `counts` | sempre vazio |
| lista (restrito) | só as classes configuradas, **na ordem configurada**, com `0` para as ausentes | soma de `counts` | classes detectadas fora do domínio, com a quantidade |
| `[]` (restrito vazio) | vazio | `0` | todas as detecções |

Em todos os modos, `detection_count` é o número de detecções recebidas e vale `total + soma(excluded)`.

### Exemplo — modo A (genérico)

Entrada: `RBC`, `RBC`, `WBC`, `Bacteria`; `classes=None`.

```json
{
  "classes": null,
  "counts": {"RBC": 2, "WBC": 1, "Bacteria": 1},
  "total": 4,
  "excluded": {},
  "detection_count": 4
}
```

### Exemplo — modo B (restrito ao domínio)

Mesma entrada; `classes=["RBC", "WBC", "Platelets"]`.

```json
{
  "classes": ["RBC", "WBC", "Platelets"],
  "counts": {"RBC": 2, "WBC": 1, "Platelets": 0},
  "total": 3,
  "excluded": {"Bacteria": 1},
  "detection_count": 4
}
```

## Uso com outros componentes

```python
detection_component = ObjectDetectionComponent(detector, detection_reference)
detection_outputs = detection_component.execute(
    detection_component.prepare([image_reference])
)

counting_component = ClassCountingComponent(
    ["RBC", "WBC", "Platelets"], count_reference
)
counting_component.execute(counting_component.prepare(detection_outputs))

counts = count_reference.materialize().data.counts
```

Qualquer componente que grave um `DetectionReference` serve de entrada: o `ObjectDetectionComponent` e o `TextDetectionParsingComponent` estão cobertos pelos testes de integração. Não há orquestrador: a ligação entre etapas é feita por quem chama.

### Exemplo executável

`examples/demo_class_counting.py`, executado como módulo:

```bash
# Detecções já salvas por qualquer fonte (não executa modelo)
uv run python -m examples.demo_class_counting --detections caminho/detections.json \
  --classes RBC WBC Platelets --output-dir outputs/class_counting

# YOLO ONNX (ObjectDetectionComponent) seguido da contagem
uv run python -m examples.demo_class_counting --model caminho/best.onnx \
  --image caminho/imagem.jpg --output-dir outputs/class_counting
```

`--classes` omitido → `None`; `--classes` sem nomes → `[]`. O exemplo imprime o JSON gravado em `<output-dir>/class_counts.json`.

**Verificado em 23/11/2026** com `--detections` (nenhum modelo executado), sobre saídas já existentes e fora do Git: o JSON do YOLO em `outputs/` (17 detecções: RBC 15, WBC 1, Platelets 1) e um JSON do Qwen3-VL em `experiments/qwen3vl/outputs/` (23 detecções com `conf: null`). Os arquivos de entrada ficaram com o mesmo SHA-256. O caminho `--model` **não foi executado** nesta tarefa.

## Testes (verificados em 23/11/2026)

- **Unitários** (`tests/unit/components/class_counting/`, 22): modo genérico; modo restrito; ordem configurada; classes configuradas com zero; `[]`; zero detecções nos três modos; várias detecções da mesma classe; confiança não filtrada (`0.0`, `0.01`, `None`); nomes não normalizados; detecções preservadas; cópia da lista configurada; construtor rejeita tipos e duplicatas; `prepare()` devolve conteúdo e rejeita entradas inválidas; `execute()` rejeita dados inválidos sem gravar saída.
- **Integração** (`tests/integration/components/class_counting/`, 2): `ObjectDetectionComponent(FakeDetector)` → contagem restrita (o JSON de detecções fica inalterado); `TextDetectionParsingComponent` → contagem genérica de detecções sem confiança.
- Os testes do artefato estão em [artefato de contagem](artifact-class-count.md).

## Limitações

- Conta o que recebe: duplicatas, caixas sobrepostas e falsos positivos do detector entram na contagem. Não há supressão de não-máximos nem deduplicação aqui.
- A igualdade de classes é exata. Se o detector e o domínio usarem grafias diferentes (`"Platelets"` × `"platelet"`), a classe aparece como zero e a detecção vai para `excluded`. Mapear nomes, se for preciso, é outra responsabilidade (não implementada).
- Uma `DetectionReference` por execução; somar contagens de várias imagens não está implementado.
- Nenhum orquestrador liga os componentes automaticamente (`domain.py` só tem esqueletos).
- Limitações do artefato de saída (chave repetida no JSON, modelo mutável): veja [artefato de contagem](artifact-class-count.md#limitações).
