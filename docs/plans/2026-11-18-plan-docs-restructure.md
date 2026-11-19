---
type: Plan
title: Reorganização da documentação no padrão OKF
description: Plano aprovado em 18/11/2026 para mover o bundle para docs/ no padrão do new-visio-research-models, com decisões D1–D6, execução e validação.
tags:
- documentation
- okf
- plan
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:34:40-03:00"
evidence_basis: [approved, verified]
sources:
- id: reference-repo
  resource: https://github.com/Visio-ai/new-visio-research-models
  title: Repositório de referência
---

# Reorganização da documentação (18/11/2026)

- **Pedido (17/11/2026):** criar a estrutura e as diretrizes de documentação com base no `new-visio-research-models`, adaptadas ao projeto.
- **Plano apresentado:** 17/11/2026. **Decisões D1–D6 aprovadas e execução autorizada:** 18/11/2026.
- **Decisão registrada em:** [ADR 007](../adr/007-okf-documentation-structure.md). **Diretrizes resultantes:** [diretrizes OKF](../references/okf-guidelines.md).

## Decisões aprovadas

| # | Tema | Escolha |
|---|---|---|
| D1 | Local | Mover `docs/mlops-workflows-okf-0.2/` para `docs/`, sem arquivos de redirecionamento |
| D2 | Handoff | `docs/handoff.md`, extensão local na raiz |
| D3 | Autoria | `generated: {by: "human:iago.pirone", at: "<ISO -03:00>"}`; agentes em [proveniência](../references/provenance.md) |
| D4 | Evidência | `evidence_basis` como extensão local: `verified`, `approved`, `hypothesis`, `proposal` |
| D5 | Validação | `scripts/okf_lint.py` só com biblioteca padrão, documentando exatamente o que verifica |
| D6 | `mirage-poc.md` | Incorporar o relevante na documentação principal e remover depois de conferir que nada se perdeu |

## Requisitos do usuário

1. Preservar integralmente o conhecimento técnico, as decisões, o histórico e os resultados de testes.
2. Atualizar todos os links e as referências no `CLAUDE.md` da raiz e no README do experimento.
3. Manter `docs/handoff.md` completo.
4. Registrar este plano e as decisões.
5. Padronizar o frontmatter (D3).
6. Preservar em proveniência a rastreabilidade dos agentes.
7. Verificar links, metadados e estrutura.
8. Executar Ruff e a suíte completa.
9. Não modificar código funcional dos componentes.
10. Não instalar dependências, não fazer commits nem pushes.

## Execução

1. **Backup** do `docs/` antigo, do `CLAUDE.md` e do README do experimento no scratchpad da sessão (fora do repositório; pode ser apagado pelo sistema). **Atualização de 18/11/2026:** a pedido do usuário, a cópia passou a ter um arquivo persistente, descrito em [proveniência](../references/provenance.md).
2. **Migração automática** de 30 documentos do bundle (o `architecture/adr.md` foi tratado à mão, o `index.md` reescrito e o `mirage-poc.md` incorporado): novo caminho, `type` da categoria, `generated` humano, `evidence_basis` no vocabulário fixo, remoção de `updated`, conversão de todos os links relativos em absolutos. Os valores antigos foram gravados na tabela de [proveniência](../references/provenance.md#autoria-e-histórico-de-agentes-registrado-em-18112026), que tem o mapeamento completo de caminhos.
3. **Partes manuais:**
   - ADR versionado → `adr/001-workflow-architecture.md`, com o texto original intacto e o resumo de `architecture/adr.md` anexado;
   - `docs/diagrams/*.mmd` → `diagrams/{workflow-flow,class-model,execution-sequence}.md`, com o Mermaid idêntico (conferido por `diff`);
   - plano de commits extraído de `quality/tooling.md` para `plans/2026-11-17-plan-commits.md`;
   - `integrations/mirage-poc.md` incorporado em `references/mirage.md`.
4. **Documentos novos:** `docs/CLAUDE.md`, `index.md` por pasta, [diretrizes OKF](../references/okf-guidelines.md), [invariantes](../references/invariants.md), [mecanismos transitórios](../references/transitional-mechanisms.md), ADRs 002–007, playbooks [criar artefato](../playbooks/create-artifact.md), [criar componente](../playbooks/create-component.md), [criar adaptador de modelo](../playbooks/create-model-adapter.md) e [documentar uma mudança](../playbooks/document-a-change.md).
5. **Fora de `docs/`:** `CLAUDE.md` da raiz, `experiments/mirage/README.md`, `scripts/okf_lint.py`, `tests/unit/scripts/test_okf_lint.py`.
6. **Validação** e atualização de log, status e handoff.

## Diferenças em relação ao plano apresentado

- **Pesquisa do MIRAGE e revisão do parser não viraram relatórios separados.** O plano previa `reports/2026-11-17-mirage-capabilities.md` e `reports/2026-11-17-parser-and-poc-review.md`. Para não arriscar perda de conteúdo (requisito 1), as seções continuam em [MIRAGE](../references/mirage.md) e [parser](../references/component-text-detection-parsing.md). A separação pode ser feita depois, com aprovação.
- **`quality/testing.md` não foi dividido** entre playbook e referência: virou [suíte de testes](../references/test-suite.md) inteiro; os comandos ficam no playbook [testar localmente](../playbooks/test-locally.md), que já os tinha.
- **Testes do validador** (`tests/unit/scripts/test_okf_lint.py`) foram acrescentados por ele ser código; entram na suíte principal.
- O plano fora datado de 17/11/2026; foi registrado com a data da aprovação e execução (18/11/2026).

## Validação planejada

- `uv run python scripts/okf_lint.py`;
- `uv run ruff check .` e `uv run ruff format --check .`;
- `uv run python -m pytest -q -rs`, com e sem ONNX real, e os testes de `experiments/mirage/tests`;
- `git status`: só documentação, `CLAUDE.md`, README do experimento, `scripts/` e o teste novo mudaram.

Resultados reais: no [log](../log.md) de 18/11/2026 e no [handoff](../handoff.md).
