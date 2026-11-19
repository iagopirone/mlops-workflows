---
type: ADR
title: "ADR 005 — Interpretação estrita de detecções em texto"
description: O TextDetectionParser aceita só JSON puro, com convenção de coordenadas explícita, e rejeita a resposta inteira se algum item for inválido.
tags:
- adr
- parsing
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:34:40-03:00"
evidence_basis: [approved, verified]
---

# ADR 005 — Interpretação estrita de detecções em texto

- **Status:** Aceito (aprovado pelo usuário em 17/11/2026, com as correções P1–P3 aprovadas no mesmo dia; registrado em ADR em 18/11/2026)

## Contexto

O MIRAGE devolve texto livre. Para virar `DetectionContent`, a resposta precisa ser interpretada sem inventar dados e sem esconder falhas do modelo.

## Decisão

1. **Só JSON puro**, no formato `[{"cls": str, "box": [x1, y1, x2, y2]}]`, o mesmo do `DetectionContent` sem `conf`. Nada é extraído de texto livre ou de Markdown.
2. **Validação estrita:** um item inválido rejeita a resposta inteira, e nenhum arquivo parcial é gravado.
3. **Convenção de coordenadas obrigatória e explícita** no construtor: `pixel`, `normalized_image` ou `normalized_padded_square`. Sem padrão e sem detecção automática.
4. `conf`/`confidence` escrito pelo modelo é rejeitado; toda detecção sai com `conf: null` ([ADR 003](003-nullable-detection-confidence.md)).
5. Correções P1–P3: chaves duplicadas, `cls` vazio ou com espaços nas pontas e `bool` como dimensão ou coordenada são rejeitados.

## Alternativas consideradas

- Extrair JSON de texto livre ou de blocos Markdown: descartado (decisão 3 do usuário).
- Aceitar os itens válidos e descartar os inválidos: descartado (decisão 2).
- Um objeto de configuração (`TextDetectionParserConfig`) no lugar do parâmetro: trocado por parâmetro no construtor (KISS).
- Aceitar o formato de colchetes do treino do MIRAGE: não aceito.

## Consequências

- Validade estrutural **não** é precisão espacial: isso só a avaliação mede ([ADR 006](006-offline-detection-evaluation.md)).
- A convenção real do MIRAGE é **hipótese** (`normalized_padded_square` provável, não comprovada).
- Documento vivo: [parser](../references/component-text-detection-parsing.md).
- Origem: [log](../log.md), 17/11/2026, "Implementação: interpretação de respostas textuais em detecções" e "Correções aprovadas: prova de conceito e parser P1–P3".
