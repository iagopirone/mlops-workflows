---
type: Reference
title: Avaliador offline de detecções do MIRAGE
description: Como o evaluate_detections.py compara detecções extraídas de respostas textuais com anotações humanas; métricas, formatos, políticas e limitações.
tags:
- evaluation
- iou
- mirage
- experiment
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:28:27-03:00"
evidence_basis: [verified, approved]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d0fb7f2 + alterações não commitadas), inspecionado e testado em 17/11/2026
  title: Código, testes e execuções locais
---

# Situação

**Implementado e testado em 17/11/2026, só com dados sintéticos. Não commitado.**

- Nenhuma resposta real do MIRAGE foi avaliada, porque o MIRAGE **nunca foi executado**.
- Arquivo: `experiments/mirage/evaluate_detections.py`.
- Testes: `experiments/mirage/tests/test_evaluate_detections.py` (47).

## Objetivo

Medir a **precisão espacial** das caixas que o MIRAGE escreve em texto, comparando com anotações humanas. É isso que transforma a hipótese "o MIRAGE localiza objetos" em um número.

## Onde roda

```text
máquina com GPU, conda MIRAGE (Python 3.10, pydantic<2)    ambiente do projeto (uv) ou Python ≥ 3.10 com pydantic 2
run_poc.py --execute  ──►  runs/<id>/{answer.txt, run.json}  ──►  evaluate_detections.py  ──►  report.json
```

- **Não roda no ambiente conda do MIRAGE.** Ele importa o `TextDetectionParser`, que usa Pydantic 2, e o MIRAGE fixa `pydantic<2`.
- O código é compatível com Python 3.10. Foi verificado no 3.10.21 com apenas `pydantic` 2 e `pytest`.
- Execute da raiz do repositório:

```bash
uv run python -m experiments.mirage.evaluate_detections \
  --ground-truth annotations.json \
  --predictions predictions.json \
  --coordinate-format normalized_padded_square \
  --iou-threshold 0.5 \
  --output report.json
```

- `--coordinate-format` é **obrigatório e sem padrão**. É a mesma regra do parser: a convenção do MIRAGE ainda não foi confirmada, então quem roda precisa declará-la.
- `--iou-threshold` tem padrão 0,5 e precisa estar no intervalo (0, 1].

## Reuso (sem duplicar lógica)

- **Respostas:** são interpretadas **exclusivamente** pelo `TextDetectionParser(coordinate_format)`. Validação, conversão de coordenadas, rejeição estrita e `conf=None` vêm todos dele.
- **Anotações humanas:** são validadas pelo `TextDetectionParser("pixel")`. Assim, valem as mesmas regras das predições: JSON estrito, classe sem espaço nas pontas, números finitos, caixa ordenada e dentro da imagem.
- **Ligação imagem-resposta:** vem do `run.json` produzido pelo `run_poc.py`.

## Formatos de entrada

**Anotações** (`--ground-truth`), com caixas em **pixels da imagem original**, `[x1, y1, x2, y2]`:

```json
{
  "images": [
    {"image_id": "blood_00236", "width": 640, "height": 480,
     "objects": [{"cls": "WBC", "box": [191, 210, 436, 434]}]},
    {"image_id": "blank_01", "width": 640, "height": 480, "objects": []}
  ]
}
```

**Predições** (`--predictions`): cada entrada liga um `image_id` a um diretório de execução do `run_poc.py`. Caminhos relativos são resolvidos a partir da pasta do manifesto.

```json
{"predictions": [{"image_id": "blood_00236", "run_dir": "runs/blood_00236"}]}
```

**Associação explícita, sem depender da ordem dos arquivos.** Para cada entrada, o avaliador exige:
- `image_id` único e presente nas anotações;
- um `run.json` que associe a resposta a **exatamente uma imagem** (`answer_image` não nulo);
- que a largura e a altura gravadas no `run.json` **coincidam** com as da anotação.

Se alguma dessas condições falhar, é **erro de configuração**: o avaliador aborta sem gerar relatório. Isso evita avaliar uma resposta contra a imagem errada.

## Status de cada imagem e políticas

O conjunto avaliado é **sempre o conjunto de imagens anotadas**. Predições de imagens sem anotação abortam a avaliação.

| Status | Quando | Como entra nas métricas |
|---|---|---|
| `valid` | O parser aceitou a resposta, inclusive `[]` | As predições são comparadas normalmente |
| `invalid_response` | O parser rejeitou: JSON inválido, item inválido, coordenada fora do espaço, `conf` escrito pelo modelo etc. A mensagem fica em `error` | **Zero predições:** todas as anotações viram falsos negativos |
| `missing_response` | A imagem não tem entrada no manifesto, ou a execução não gerou `answer.txt`. O motivo fica em `error` | Igual a `invalid_response` |

- **Respostas inválidas e ausentes nunca são excluídas.** Excluí-las aumentaria a revocação artificialmente. Os testes verificam isso: com uma imagem inválida e uma correta, a revocação fica 0,5, e não 1,0.
- **Imagem sem objetos anotados:** qualquer predição nela vira falso positivo. A revocação dessa imagem é `null`.
- **Lista vazia válida (`[]`):** status `valid` com 0 predições. Aparece em `valid_responses_without_detections`.

## Métricas

- **IoU:** `área(A ∩ B) / área(A ∪ B)`, com caixas em pixels contínuos (sem o "+1" de pixels discretos). Caixas que só se tocam na borda têm IoU 0.
- **Correspondência:** um-para-um, **por classe** (comparação exata de `cls`, sensível a maiúsculas).
  - Entram os pares da mesma classe com IoU ≥ limiar (o limite é **inclusivo**).
  - ~~Os pares são escolhidos em ordem decrescente de IoU (greedy).~~ **Desde 18/11/2026, a correspondência é bipartida ótima** (algoritmo húngaro, [ADR 010](../adr/010-optimal-bipartite-matching.md)): primeiro o **maior número de pares**, depois a **maior soma de IoU**. O *greedy* subestimava os TP (contraexemplo no ADR).
  - **Modo independente de classe** (`class_aware=False`): casa as caixas sem olhar a classe. Mede a localização; `confusion` (classe anotada → classe prevista) mede a classificação.
  - Cada predição e cada anotação é usada no máximo uma vez.
  - **Não usa confiança**, que não existe no MIRAGE.
- **Contagens:**
  - **TP:** pares correspondidos;
  - **FP:** predições que sobraram (incluindo várias predições para o mesmo objeto e classe errada);
  - **FN:** anotações que sobraram.
- **Precisão** = TP / (TP + FP). **Revocação** = TP / (TP + FN).
  - Quando o denominador é zero, o valor é **`null`**, nunca 0 ou 1.
  - As duas são calculadas **no total** (somando TP, FP e FN de todas as imagens) e **por classe**. As classes vêm da união das anotações com as predições.
- **`mean_matched_iou`:** média do IoU dos pares correspondidos. Indica a qualidade da localização entre os acertos; é `null` se não houver acerto.
- **Fora do escopo, por decisão:** AP/mAP. Elas exigem ordenar por confiança, e o MIRAGE não fornece uma. Nenhum score é inventado.

## Relatório (`--output`)

- **`parameters`:** data UTC, caminhos, `run_dirs` por imagem, `coordinate_format`, `iou_threshold`, descrição do método de correspondência, política de respostas inválidas, nota sobre a confiança e versão do Python.
- **`summary`:**
  - quantidade de imagens e de respostas válidas, inválidas e ausentes;
  - imagens sem anotação e respostas válidas sem detecções;
  - TP, FP, FN, precisão, revocação e `mean_matched_iou`.
- **`per_class`:** TP, FP, FN, precisão e revocação por classe.
- **`images[]`, por imagem:**
  - `image_id`, `status`, `error`;
  - contagens e métricas;
  - `predictions`, já convertidas para pixels;
  - `matches` (índices, classe e IoU);
  - índices das predições e anotações que ficaram sem par.

## Testes (verificados em 17/11/2026)

**47 testes**, todos com dados sintéticos. Resultado: 47 passed no Python 3.12.14 e no 3.10.21.

- **IoU:** caixas idênticas (1), sem interseção (0), só encostando na borda (0), sobreposição parcial (1/3), contida (0,5) e coordenadas fracionárias.
- **Correspondência:** um-para-um; uma predição não cobre duas anotações; exige a mesma classe (modo padrão); limiar inclusivo e configurável. Desde 18/11/2026 há também os testes da correspondência ótima: contraexemplo do *greedy*, soma de IoU, 80 casos aleatórios contra força bruta, modo independente de classe e matriz de confusão. Total: **168** testes no experimento.
- **Avaliação:**
  - predição perfeita; caixas sem sobreposição;
  - sobreposição parcial com limiar 0,5 e 0,3;
  - classes diferentes, com contagem por classe;
  - várias predições para o mesmo objeto;
  - `[]` com anotações; imagem sem anotações;
  - 5 tipos de resposta inválida contados como FN, com a revocação verificada;
  - resposta ausente pelos dois motivos;
  - associação por `image_id` independente da ordem;
  - `image_id` desconhecido; limiar inválido;
  - os 3 formatos de coordenadas.
- **Carregamento:**
  - anotações válidas;
  - anotações com `image_id` duplicado ou vazio, sem `objects`, com `bool` como dimensão, com caixa fora da imagem, ou com estrutura errada;
  - manifesto com caminho relativo; execução sem `answer.txt`;
  - tamanho divergente; execução com várias imagens; `image_id` duplicado ou sem anotação.
- **Linha de comando:**
  - o relatório traz os parâmetros e a política;
  - `--coordinate-format` é obrigatório;
  - erro de configuração não grava relatório.
- **Ponta a ponta:** `run_poc.py --execute` contra um `demo.py` falso, depois `load_responses` e `evaluate`.

## Limitações

- **Não valida o MIRAGE.** Só mede quando houver respostas reais e anotações humanas, que ainda não existem.
- ~~**Correspondência gulosa por IoU:** não garante o número máximo de pares.~~ **Resolvido em 18/11/2026:** correspondência ótima ([ADR 010](../adr/010-optimal-bipartite-matching.md)). Empates de mesma quantidade e mesma soma têm solução determinística, mas sem regra de desempate especificada.
- **Por classe e com comparação exata:**
  - sinônimos ("white blood cell" × "WBC") contam como erro;
  - não há métrica que ignore a classe e meça só a localização. Ela pode ser útil se o MIRAGE localizar bem e rotular mal, e pode ser adicionada se houver demanda.
- **Sem AP/mAP:** não há confiança, e não inventamos scores.
- **Uma imagem por execução:** execuções com várias imagens são recusadas, porque a saída do MIRAGE não diz a qual imagem cada caixa pertence.
- **Testes fora da suíte principal:** precisam ser rodados explicitamente.
