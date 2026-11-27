---
type: ADR
title: "ADR 008 — Links internos relativos para funcionar no GitHub"
description: Os links entre documentos de docs/ passam a ser relativos, permitidos pela OKF 0.2, para que funcionem no GitHub; é uma adaptação consciente em relação ao repositório de referência.
tags:
- adr
- documentation
- links
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T14:05:00-03:00"
evidence_basis: [approved, verified]
sources:
- id: okf-spec
  resource: https://github.com/devlooped/okf/blob/main/specs/okf-0.2.md
  title: Especificação OKF 0.2, §6.1 (links) e §7 (index.md)
- id: reference-repo
  resource: https://github.com/Visio-ai/new-visio-research-models/blob/main/docs/CLAUDE.md
  title: Regras do bundle no repositório de referência
---

# ADR 008 — Links internos relativos

- **Status:** Aceito (decisão do usuário em 18/11/2026)
- **Altera:** a parte de links do [ADR 007](007-okf-documentation-structure.md). O resto do ADR 007 continua valendo.

## Contexto

- O [ADR 007](007-okf-documentation-structure.md) adotou links **absolutos ao bundle** (`/references/contracts.md`), como no `new-visio-research-models`.
- Na interface web do GitHub, um link que começa com `/` é resolvido a partir da **raiz do repositório**, não de `docs/`. Por isso, nenhum link interno abria ao navegar pelo GitHub ou num PR.
- A especificação OKF 0.2 (§6.1) aceita **duas** formas: absoluta ao bundle (recomendada) e relativa (`./other.md`). Os exemplos de `index.md` da própria especificação (§7) usam URLs relativas.
- Não existe uma forma única de link que funcione no padrão absoluto e no GitHub ao mesmo tempo.

## Decisão

1. Links internos de `docs/` são **relativos ao arquivo que os contém**: `../references/contracts.md`, `contracts.md`, `references/status.md#âncora`.
2. Links absolutos (`/...`) passam a ser **erro** do validador, para que nenhum link quebrado no GitHub volte a entrar.
3. Um link não pode sair do bundle (`docs/`). Caminhos de código continuam entre crases, não como link.
4. `index.md` usa o mesmo formato: `* [Título](arquivo.md) - descrição`.

## Por quê

- **Funciona nos dois lugares:** o GitHub e qualquer leitor de Markdown resolvem links relativos; consumidores OKF também, porque a forma é válida pela §6.1.
- **Custo aceito:** mover um documento exige atualizar os links relativos que apontam para ele, que é a razão de a OKF recomendar a forma absoluta. O validador detecta todo link quebrado, então o custo é visível.

## Diferença em relação ao repositório de referência

O `new-visio-research-models` exige links absolutos (`docs/CLAUDE.md` de lá). Este projeto diverge disso; categorias, `type`, `status`, `generated`, índices e log continuam como na referência. As outras diferenças são acréscimos locais já aprovados (`handoff.md` na raiz, `evidence_basis`). A divergência está registrada nas [diretrizes OKF](../references/okf-guidelines.md#diferenças-em-relação-ao-repositório-de-referência).

## Consequências

- 318 links foram convertidos por script em 18/11/2026; o validador confirmou que todos resolvem.
- `scripts/okf_lint.py`: rejeita links absolutos e links que saem do bundle; resolve links e itens de índice a partir da pasta do arquivo. A exceção antiga de `docs/CLAUDE.md` deixou de ser necessária.
- Atualizados: `docs/CLAUDE.md`, `CLAUDE.md` da raiz, [diretrizes OKF](../references/okf-guidelines.md) e os testes do validador.
