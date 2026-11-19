---
type: Reference
title: Diretrizes de documentação OKF
description: Estrutura, frontmatter, nomes, links, índices, log e validação do bundle docs/, adaptados do new-visio-research-models.
tags:
- documentation
- okf
- guidelines
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:34:40-03:00"
evidence_basis: [approved, verified]
sources:
- id: reference-repo
  resource: https://github.com/Visio-ai/new-visio-research-models (docs/, lido em 17/11/2026)
  title: Repositório de referência do padrão de documentação
- id: okf-spec
  resource: https://github.com/devlooped/okf/blob/main/specs/okf-0.2.md
  title: Especificação OKF 0.2
---

# Diretrizes de documentação

Adotadas em 18/11/2026 ([ADR 007](../adr/007-okf-documentation-structure.md), [plano](../plans/2026-11-18-plan-docs-restructure.md)). Base: o bundle `docs/` do repositório `new-visio-research-models`[^reference-repo], que segue o OKF 0.2[^okf-spec]. O resumo operacional para agentes está em `docs/CLAUDE.md`.

## Princípios

1. **O código é a fonte de verdade.** Se a documentação divergir, siga o código e corrija a documentação.
2. **A documentação faz parte de cada tarefa** (regra do líder, 17/11/2026). Toda etapa e toda decisão relevante atualizam a documentação.
3. **Documentos vivos descrevem o presente; documentos temporais registram um momento.** Não se reescreve a história: muda-se o documento vivo e registra-se a decisão num documento temporal.
4. **Nada fica só na conversa.** O que não estiver no código ou em `docs/` deve ser considerado perdido depois de uma compactação.

## Estrutura

```text
docs/
├── index.md          # mapa do bundle (reservado)
├── log.md            # histórico, mais recente primeiro (reservado)
├── CLAUDE.md         # regras do bundle para agentes (reservado)
├── handoff.md        # ponto de retomada de contexto (extensão local, D2)
├── playbooks/        # viva — como fazer
├── references/       # viva — estado atual, contratos, regras
├── diagrams/         # viva — Mermaid embutido em .md
├── adr/              # temporal — NNN-slug.md
├── plans/            # temporal — YYYY-MM-DD-slug.md
└── reports/          # temporal — YYYY-MM-DD-slug.md
```

Cada pasta tem um `index.md`. Não há subpastas dentro das categorias.

### Onde colocar cada coisa

| Quero registrar… | Crio… | Exemplo |
|---|---|---|
| como executar uma tarefa recorrente | `playbooks/slug.md` | [testar localmente](../playbooks/test-locally.md) |
| como algo funciona hoje (contrato, componente, regra) | `references/slug.md` | [contratos](contracts.md) |
| um diagrama que acompanha o código | `diagrams/slug.md` | [pipeline atual](../diagrams/current-pipeline.md) |
| uma decisão de arquitetura ou de processo e o porquê | `adr/NNN-slug.md` | [ADR 005](../adr/005-strict-json-text-detection-parsing.md) |
| o que pretendo fazer, antes de fazer | `plans/YYYY-MM-DD-plan-slug.md` | [plano de commits](../plans/2026-11-17-plan-commits.md) |
| o que observei numa execução, pesquisa ou revisão | `reports/YYYY-MM-DD-slug.md` | [demo YOLO](../reports/2026-11-16-yolo-visualization-demo.md) |
| algo provisório que deve sumir depois | uma linha em [mecanismos transitórios](transitional-mechanisms.md) | — |

## Arquivos da raiz

- `index.md`, `log.md` e `CLAUDE.md`: reservados, como na referência.
- `handoff.md`: **extensão local** (decisão D2). É o primeiro arquivo lido ao retomar o trabalho e deve sempre conter: objetivo, contratos a preservar, estado do Git, concluído, pendente, última tarefa, decisões recentes, limitações, próxima ação e arquivos para retomar.
- O `index.md` da raiz mantém `okf_version: "0.2"` no frontmatter; os outros reservados não têm frontmatter.

## Frontmatter

| Campo | Obrigatório | Regra |
|---|---|---|
| `type` | sim | `Playbook`, `Reference`, `Diagram`, `ADR`, `Plan` ou `Report`, de acordo com a pasta |
| `title` | recomendado | título curto |
| `description` | recomendado | uma frase; é a mesma usada no `index.md` da pasta |
| `tags` | recomendado | lista YAML |
| `status` | opcional | `draft`, `stable` ou `deprecated`. Sem revisão humana formal, use `draft` |
| `generated` | recomendado | `by: human:<login>` e `at: "<ISO 8601 com fuso>"`, entre aspas para continuar texto |
| `stale_after` | opcional | data a partir da qual um relatório deve ser revisto |
| `verified` | opcional | só quando houver revisão humana formal; **nunca inventar** |
| `sources` | opcional | lista de `id`, `resource` e `title`; o corpo cita com notas de rodapé `[^id]` |
| `evidence_basis` | **extensão local** (D4) | lista com `verified`, `approved`, `hypothesis` ou `proposal` |

### Autoria (D3)

- `generated.by: human:iago.pirone`: o desenvolvedor responde pelo documento, como na referência.
- Os agentes que ajudaram a escrever ficam registrados em [proveniência](provenance.md), não no frontmatter.
- O `generated.at` usa o fuso de Brasília (`-03:00`).

### Classificação da evidência (D4)

O líder exige separar o que foi verificado, aprovado, suposto ou proposto. A referência não tem esse campo; por isso ele é uma extensão local, aceita pelo validador.

| Valor | Significado |
|---|---|
| `verified` | inspecionado no código ou executado, com resultado real registrado |
| `approved` | decisão do usuário, implementada ou não |
| `hypothesis` | suposição ainda não comprovada (ex.: o MIRAGE gera caixas confiáveis) |
| `proposal` | plano ou sugestão ainda não implementada |

O campo resume o documento inteiro. Dentro do texto, cada afirmação importante continua marcada (**verificado**, **aprovado**, **hipótese**, **proposta**).

## Nomes de arquivos

- `kebab-case`, sem acentos, em inglês (como os nomes de código), mesmo com o conteúdo em português.
- ADR: `NNN-slug.md`, numeração sequencial a partir de `001`.
- Plano e relatório: `YYYY-MM-DD-slug.md`, com a data da criação. Planos começam com `plan-` depois da data.

## Links

- Internos: **relativos ao arquivo que contém o link**, como `../references/contracts.md`, `contracts.md` ou `../references/contracts.md#component` ([ADR 008](../adr/008-relative-internal-links.md)). Funcionam no GitHub e são válidos pela OKF 0.2 (§6.1).
- Links absolutos (`/references/x.md`) são **recusados** pelo validador: no GitHub eles apontam para a raiz do repositório e quebram.
- Um link não pode sair de `docs/`. Caminhos de código ficam entre crases (`mlops_workflows/...`), não como link.
- Ao mover um documento, atualize os links relativos que apontam para ele; o validador lista os quebrados.

## Diferenças em relação ao repositório de referência

| Ponto | `new-visio-research-models` | Este projeto | Por quê |
|---|---|---|---|
| Links internos | Absolutos ao bundle (`/x.md`) | **Relativos** | Funcionar no GitHub ([ADR 008](../adr/008-relative-internal-links.md)) |
| `handoff.md` | Não existe | Na raiz de `docs/` | Ponto fixo de recuperação de contexto (D2) |
| `evidence_basis` | Não existe | Extensão local | Separar verificado, aprovado, hipótese e proposta (D4) |

## Índices

Um `index.md` por pasta, com uma linha por documento:

```text
* [Título](arquivo.md) - descrição
```

O `index.md` da raiz aponta para os índices de categoria e para os documentos principais.

## Log

- Seções `## YYYY-MM-DD`, **a mais recente no topo**.
- Dentro do dia, as entradas podem aparecer em ordem de acontecimento, desde que isso esteja dito.
- Cada entrada diz o que mudou, por quê, os arquivos e os resultados reais dos testes.

## Ciclo de trabalho

**Planejar → executar → validar → documentar**, com aprovação do usuário entre as etapas. Veja o playbook [documentar uma mudança](../playbooks/document-a-change.md).

## Validador local

`scripts/okf_lint.py` usa **apenas a biblioteca padrão** (decisão D5). Execute da raiz do repositório:

```bash
uv run python scripts/okf_lint.py
uv run python scripts/okf_lint.py --root docs
```

**O que ele verifica:**

1. A raiz de `docs/` só tem `index.md`, `log.md`, `CLAUDE.md`, `handoff.md` e as seis pastas de categoria.
2. As pastas de categoria não têm subpastas nem arquivos que não sejam `.md`.
3. Os nomes seguem o padrão de cada pasta (`slug.md`, `NNN-slug.md` ou `YYYY-MM-DD-slug.md`).
4. Todo documento (exceto os reservados) começa com um bloco de frontmatter delimitado por `---`.
5. `type` existe e corresponde à pasta (`handoff.md` deve ser `Reference`).
6. Se presentes: `status` está entre os valores permitidos; `generated.by` começa com `human:`; `generated.at` está entre aspas e é uma data ISO 8601 **com fuso**; `evidence_basis` é uma lista com valores permitidos.
7. Todo documento de categoria aparece no `index.md` da sua pasta, e todo item do índice existe.
8. Todo link interno é **relativo**, resolvido a partir da pasta do arquivo, fica dentro de `docs/` e aponta para um arquivo existente; a âncora `#...`, se houver, corresponde a um título do arquivo de destino (slug no estilo do GitHub). Links absolutos (`](/...)`) são erro.
9. As datas das seções `## YYYY-MM-DD` do `log.md` estão em ordem decrescente.

**O que ele não verifica:**

- **Não é um parser YAML completo.** Ele lê o frontmatter linha a linha e entende só o necessário: chaves de primeiro nível, o bloco `generated` e listas em linha (`[a, b]`). YAML válido em outras formas (por exemplo, `evidence_basis` em lista de bloco, âncoras ou multilinha) pode ser recusado, e erros de sintaxe YAML em campos que ele não lê **não** são detectados.
- Não valida links externos (`http...`) nem caminhos de código entre crases.
- Não verifica se o conteúdo está correto, atualizado ou coerente com o código.
- Não substitui o `okf-lint.py` oficial (que fica em `visio-research-context`, ausente nesta máquina); conformidade com ele **não foi verificada**.

[^reference-repo]: https://github.com/Visio-ai/new-visio-research-models
[^okf-spec]: https://github.com/devlooped/okf/blob/main/specs/okf-0.2.md
