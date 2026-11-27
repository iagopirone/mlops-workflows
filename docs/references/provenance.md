---
type: Reference
title: Fontes, limites e confiança desta documentação
description: Identificação das evidências, lacunas de acesso e estado de revisão humana.
tags:
- provenance
- sources
- documentation
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:28:27-03:00"
evidence_basis: [verified]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d0fb7f2 + alterações não commitadas), inspecionado e testado em 17/11/2026
  title: Código, testes e execuções locais
- id: repo-snapshot
  resource: https://github.com/iagopirone/mlops-workflows/tree/666fbb5a210a3cc4143e745bce888eebfe8dc2b2
  title: Snapshot da branch feature/implementar-componentes em 09/11/2026 (commit
    666fbb5)
- id: conversation
  resource: Relatos de desenvolvimento e saídas de terminal fornecidos pelo usuário
    nesta conversa, 10–16/11/2026
  title: Evidências da conversa de desenvolvimento
- id: mirage-repo
  resource: https://github.com/visual-haystacks/mirage
  title: Repositório oficial MIRAGE
- id: okf-spec
  resource: https://github.com/devlooped/okf/blob/main/specs/okf-0.2.md
  title: Especificação OKF 0.2
---

# Como este bundle foi produzido

Esta documentação foi elaborada para registrar o projeto **até 16/11/2026**. As fontes têm níveis de acesso diferentes:

1. **Snapshot inspecionado do repositório:** arquivo ZIP da branch `feature/implementar-componentes`, commit `666fbb5a210a3cc4143e745bce888eebfe8dc2b2`, conteúdo datado de 09/11/2026. Este snapshot confirma interfaces de artefato, imagem, vídeo, contratos de componente, ADR, dependências e ferramentas, mas **é anterior às refatorações relatadas**.
2. **Conversa e terminais do usuário:** trechos de código, instruções de design, logs de `pytest`/`ruff`, comandos e imagem anotada compartilhados até 16/11/2026. Confirmam resultados relatados pelo usuário, **sem acesso direto ao checkout final**.
3. **Documentação externa:** repositório oficial do MIRAGE e especificação OKF 0.2, usados apenas para seus respectivos domínios.

4. **Checkout local (a partir de 17/11/2026):** o código, os testes e o Git foram inspecionados diretamente na máquina de desenvolvimento, e as suítes foram executadas. **Esta é a fonte de verdade** e substitui as afirmações das fontes 1 e 2 quando houver divergência.
5. **Fontes oficiais do MIRAGE (17/11/2026):** repositório clonado (README, `demo.py`, `llava/`, `pyproject.toml`), model card e `config.json` no Hugging Face, paper arXiv 2407.13766 e amostras de `mirage_ft.json`. Nenhuma inferência foi executada.

## Convenções de status

- `status: draft`: documento ainda não passou por revisão humana formal; **não inventamos** `verified`.
- `evidence_basis: snapshot do repositório`: afirmações verificadas em arquivos do ZIP antigo.
- `evidence_basis: relato da conversa`: situações descritas pelo usuário, incluindo testes e refatorações.
- `evidence_basis: misto`: combinação dos dois.
- `evidence_basis: código local verificado`: inspecionado e/ou executado no checkout local.
- `evidence_basis: proposta (sem código)`: plano ainda não implementado.
- ~~Campo `updated`: data da última revisão da página.~~ Removido em 18/11/2026; a data passou para `generated.at`.
- ~~Em `generated.by`, `openai/gpt-6` foi o gerador original do bundle; páginas novas e revisões a partir de 17/11/2026 são de `anthropic/claude-opus-5-5`.~~ Desde 18/11/2026, `generated.by` é `human:iago.pirone` (decisão D3). O histórico dos agentes está na seção abaixo.
- Os valores textuais de `evidence_basis` listados acima foram trocados em 18/11/2026 pelo vocabulário fixo `verified`, `approved`, `hypothesis` e `proposal` (decisão D4). O valor antigo de cada documento está na tabela abaixo.

## Confirmação local necessária

~~Na máquina de desenvolvimento, conferir `git status`, branch atual, estrutura real, alterações não commitadas, execução de testes após decisões finais e situação do PR #3.~~ **Feito em 17/11/2026** (checkout local, suítes executadas, PR #3 aberto via `gh`); repetido a cada etapa desde então. Trechos que continuam só com base em relato levam o rótulo "relato do usuário" no corpo.

## Sobre OKF

O formato v0.2 utiliza arquivos Markdown com frontmatter YAML em documentos de conceito, um `type` obrigatório e arquivos especiais `index.md` e `log.md`. A ausência de `verified` significa não verificado formalmente; não significa que todos os dados estejam incorretos.

## Autoria e histórico de agentes (registrado em 18/11/2026)

A partir de 18/11/2026, todos os documentos usam autoria humana, `generated.by: human:iago.pirone` (decisão D3, [ADR 007](../adr/007-okf-documentation-structure.md)). O responsável é o desenvolvedor; os agentes que ajudaram a escrever os documentos estão registrados aqui para não se perder a rastreabilidade.

**Agentes que contribuíram:**

| Agente (valor antigo de `generated.by`) | Contribuição |
|---|---|
| `openai/gpt-6` | Geração original do bundle OKF em 16/11/2026, a partir do snapshot `666fbb5` e de relatos da conversa. Também gerou `integrations/mirage-poc.md`. Os arquivos iniciais de `experiments/mirage/` foram criados no mesmo horário (14:54 de 17/11/2026), fora da sessão do Claude Code; que tenham o mesmo autor é **hipótese** |
| `anthropic/claude-opus-5-5` (Claude Code) | Desde 17/11/2026: sincronização com o checkout local, páginas novas (VQA, parser, avaliador, handoff), revisões, correções, esta reorganização e os documentos de avaliação de modelos locais (incluindo o resumo de 19/11/2026) |
| Humano (Iago Pirone) | Texto original do ADR 001 e dos diagramas `.mmd` (commit `6a30f8b`, 15/10/2026); todas as decisões aprovadas registradas no log |

**Migração de 18/11/2026** (bundle `docs/mlops-workflows-okf-0.2/` → `docs/`, [plano](../plans/2026-11-18-plan-docs-restructure.md)). Valores antigos do frontmatter de cada documento:

| Caminho antigo (relativo ao bundle) | Caminho novo | `generated.by` antigo | `updated` antigo | `evidence_basis` antigo |
|---|---|---|---|---|
| `handoff.md` | `/handoff.md` | anthropic/claude-opus-5-5 | 2026-11-17 | código local verificado |
| `log.md` | `/log.md` | — | — | — |
| `project/overview.md` | `/references/overview.md` | openai/gpt-6 | 2026-11-17 | misto |
| `project/status.md` | `/references/status.md` | openai/gpt-6 | 2026-11-17 | código local verificado |
| `project/structure.md` | `/references/repository-structure.md` | openai/gpt-6 | 2026-11-17 | código local verificado |
| `project/getting-started.md` | `/playbooks/test-locally.md` | openai/gpt-6 | 2026-11-17 | misto |
| `quality/testing.md` | `/references/test-suite.md` | openai/gpt-6 | 2026-11-17 | código local verificado |
| `quality/tooling.md` | `/references/tooling.md` | openai/gpt-6 | 2026-11-17 | misto |
| `quality/demos.md` | `/reports/2026-11-16-yolo-visualization-demo.md` | openai/gpt-6 | 2026-11-17 | misto |
| `architecture/contracts.md` | `/references/contracts.md` | openai/gpt-6 | 2026-11-17 | código local verificado |
| `architecture/lifecycle.md` | `/references/artifact-lifecycle.md` | openai/gpt-6 | 2026-11-17 | código local verificado |
| `architecture/dependency-injection.md` | `/references/dependency-injection.md` | openai/gpt-6 | 2026-11-17 | código local verificado |
| `architecture/diagrams.md` | `/diagrams/current-pipeline.md` | openai/gpt-6 | 2026-11-17 | misto |
| `artifacts/overview.md` | `/references/artifacts.md` | openai/gpt-6 | — | misto |
| `artifacts/image.md` | `/references/artifact-image.md` | openai/gpt-6 | — | snapshot do repositório |
| `artifacts/video.md` | `/references/artifact-video.md` | openai/gpt-6 | — | snapshot do repositório |
| `artifacts/text.md` | `/references/artifact-text.md` | openai/gpt-6 | 2026-11-17 | código local verificado |
| `artifacts/detection.md` | `/references/artifact-detection.md` | openai/gpt-6 | 2026-11-17 | código local verificado |
| `components/overview.md` | `/references/components.md` | openai/gpt-6 | 2026-11-17 | código local verificado |
| `components/yolo-detector.md` | `/references/component-yolo-detector.md` | openai/gpt-6 | — | relato da conversa |
| `components/object-detection-component.md` | `/references/component-object-detection.md` | openai/gpt-6 | 2026-11-17 | código local verificado |
| `components/detection-visualization-component.md` | `/references/component-detection-visualization.md` | openai/gpt-6 | 2026-11-17 | código local verificado |
| `components/visual-question-answering-component.md` | `/references/component-visual-question-answering.md` | anthropic/claude-opus-5-5 | 2026-11-17 | código local verificado |
| `integrations/text-detection-parsing.md` | `/references/component-text-detection-parsing.md` | anthropic/claude-opus-5-5 | 2026-11-17 | código local verificado |
| `integrations/mirage.md` | `/references/mirage.md` | openai/gpt-6 | 2026-11-17 | documentação oficial verificada; nenhuma inferência executada |
| `integrations/mirage-evaluation.md` | `/references/mirage-evaluation.md` | anthropic/claude-opus-5-5 | 2026-11-17 | código local verificado |
| `integrations/roadmap.md` | `/plans/2026-11-17-plan-mirage-integration.md` | openai/gpt-6 | 2026-11-17 | misto |
| `integrations/risks.md` | `/references/risks-and-open-questions.md` | openai/gpt-6 | 2026-11-17 | misto |
| `references/provenance.md` | `/references/provenance.md` | openai/gpt-6 | 2026-11-17 | misto |
| `references/resources.md` | `/references/resources.md` | openai/gpt-6 | 2026-11-17 | misto |
| `architecture/adr.md` | incorporado em `/adr/001-workflow-architecture.md` | openai/gpt-6 | 2026-11-17 | misto |
| `index.md` | `/index.md` (reescrito no formato da referência) | — | — | — |
| `integrations/mirage-poc.md` | **removido**; conteúdo válido incorporado em `/references/mirage.md` | openai/gpt-6 | 2026-11-17 | código preparado localmente; nenhuma inferência real executada |
| `docs/ADR-001-workflow-architecture.md` (versionado) | `/adr/001-workflow-architecture.md` | humano (commit `6a30f8b`) | — | — |
| `docs/diagrams/0{1,2,3}-*.mmd` (versionados) | `/diagrams/{workflow-flow,class-model,execution-sequence}.md` | humano (commit `6a30f8b`) | — | — |

**Cópia persistente do bundle anterior (18/11/2026, aprovada pelo usuário):** `/home/visioer/Projetos/backups/mlops-workflows-docs-before-okf-2026-11-18.tar.gz`, fora do repositório e não versionada, com o SHA-256 em `.sha256` ao lado (conferido com `sha256sum -c`). Contém 49 entradas: o `docs/mlops-workflows-okf-0.2/` antigo, o ADR e os `.mmd` antigos, o `CLAUDE.md` e o README do experimento como estavam antes da reorganização. Os 4 arquivos versionados também continuam recuperáveis pelo Git (`git show HEAD:docs/ADR-001-workflow-architecture.md`).

**Mapeamento de `evidence_basis` (julgamento feito na migração):** os valores antigos "misto", "snapshot do repositório" e "relato da conversa" foram convertidos em `verified` porque essas páginas foram sincronizadas com o checkout local em 17/11/2026. Isso foi uma decisão de quem migrou. **Revisão de 18/11/2026, a pedido do usuário:** para não apresentar como verificado o que veio só de relato ou snapshot, as afirmações dessas páginas foram conferidas no código local e cada página recebeu a nota "Conferido no código em 18/11/2026" ou o texto foi corrigido:

- [artefatos](artifacts.md), [imagem](artifact-image.md), [vídeo](artifact-video.md): código de `artifacts/`;
- [visão geral](overview.md): `pyproject.toml`;
- [ferramentas](tooling.md): `.pre-commit-config.yaml`, `hooks/pre-push` e `git log`;
- [YOLO](component-yolo-detector.md): `yolo_detector.py` e os metadados do `best.onnx` local;
- [recursos](resources.md) e [testar localmente](../playbooks/test-locally.md): textos de "relatado" e contagens desatualizadas corrigidos;
- [relatório da demo](../reports/2026-11-16-yolo-visualization-demo.md): a execução de 16/11 ficou rotulada como **relato do usuário**; só a revalidação de 17/11 é verificada.

Páginas de origem "misto" que descrevem planos ou riscos ([plano da integração](../plans/2026-11-17-plan-mirage-integration.md), [riscos](risks-and-open-questions.md), [pipeline atual](../diagrams/current-pipeline.md)) já separam no corpo o verificado do proposto e do hipotético. Não foi criado um quinto valor de `evidence_basis` (o vocabulário aprovado na D4 tem quatro). Os valores originais estão na tabela acima.

O `generated.at` dos documentos migrados é o horário da migração, e não o da escrita original. As datas originais estão no corpo de cada documento e no [log](../log.md).
