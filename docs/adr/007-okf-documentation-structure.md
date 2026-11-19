---
type: ADR
title: "ADR 007 — Documentação contínua no padrão OKF do new-visio-research-models"
description: A documentação faz parte de cada tarefa e fica em docs/, no padrão OKF do repositório de referência, com handoff na raiz.
tags:
- adr
- documentation
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:34:40-03:00"
evidence_basis: [approved, verified]
---

# ADR 007 — Documentação contínua no padrão OKF do `new-visio-research-models`

- **Status:** Aceito (regra do líder em 17/11/2026; estrutura aprovada pelo usuário em 18/11/2026)
- **Plano:** [reorganização da documentação](../plans/2026-11-18-plan-docs-restructure.md)

## Contexto

- 17/11/2026: o líder tornou obrigatória a documentação contínua (página técnica, `log.md`, `status`, `handoff.md` a cada etapa), para que o trabalho possa ser retomado sem o histórico da conversa.
- A documentação estava num bundle próprio (`docs/mlops-workflows-okf-0.2/`), organizado por assunto, com links relativos e frontmatter sem padrão comum.
- O usuário pediu para adotar a estrutura do `new-visio-research-models` e definiu o modo de trabalho **planejar → executar → validar → documentar**.

## Decisão

Estrutura e diretrizes em [diretrizes OKF](../references/okf-guidelines.md). Decisões do usuário (18/11/2026):

| # | Decisão | Opção escolhida |
|---|---|---|
| D1 | Local do bundle | `docs/`, como na referência, sem arquivos de redirecionamento |
| D2 | `handoff.md` | `docs/handoff.md`, extensão local na raiz, ponto fixo de retomada |
| D3 | Autoria | `generated: {by: "human:iago.pirone", at: "<ISO com -03:00>"}`; agentes registrados em [proveniência](../references/provenance.md) |
| D4 | Classificação da evidência | `evidence_basis` como extensão local: `verified`, `approved`, `hypothesis`, `proposal` |
| D5 | Validação | `scripts/okf_lint.py` só com biblioteca padrão, documentando exatamente o que verifica |
| D6 | `integrations/mirage-poc.md` (órfão) | incorporar o conteúdo relevante em [MIRAGE](../references/mirage.md) e remover o arquivo |

## Alternativas consideradas

- D1: manter o bundle em `docs/mlops-workflows-okf-0.2/`.
- D2: `references/handoff.md`.
- D3: manter os agentes em `generated.by`.
- D4: usar só `status`, `verified` e marcadores no texto.
- D5: só validação manual.
- D6: manter como documento `deprecated`.

## Não adotado da referência

jj, CLI `vp`, catálogo e deliveries, Temporal e Ray, famílias de modelos, mapa de zonas, e o subagente `docs-okf` com o hook `scope-guard` (fica como opção futura). O conteúdo continua em português.

## Consequências

- Os arquivos versionados `docs/ADR-001-workflow-architecture.md` e `docs/diagrams/*.mmd` aparecem no Git como removidos; o conteúdo está em `docs/adr/001-workflow-architecture.md` e `docs/diagrams/*.md`.
- Os links internos passaram a ser absolutos ao bundle. *Atualização de 18/11/2026: substituído pelo [ADR 008](008-relative-internal-links.md); os links agora são relativos, para funcionar no GitHub.*
- O `okf-lint.py` oficial não está disponível localmente; a conformidade com ele **não foi verificada**.
