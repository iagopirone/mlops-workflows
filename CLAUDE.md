# CLAUDE.md — instruções para agentes neste repositório

## Ao iniciar uma sessão

1. Leia `docs/handoff.md`, depois `docs/references/status.md` e `docs/log.md`. As regras da documentação estão em `docs/CLAUDE.md`.
2. Rode `git status --short` e `git branch --show-current`; compare com o handoff.
3. Antes de implementar, leia as páginas técnicas relevantes em `docs/` (`docs/index.md` e o `index.md` de cada pasta listam todas), as invariantes (`docs/references/invariants.md`) e o código envolvido.
4. **O código é a fonte de verdade** para o que está implementado. Se a documentação divergir, siga o código, aponte a divergência e corrija a documentação.
5. Não dependa do histórico da conversa: o que não estiver no código ou na documentação deve ser considerado perdido.

## Regras de trabalho

- **Não faça commit, push, reset, clean, rebase nem troque de branch sem autorização explícita do usuário.** Preserve alterações locais e arquivos não versionados.
- **Modo de trabalho obrigatório: planejar → executar → validar → atualizar a documentação.** Antes de executar, analise o contexto e apresente o plano; aguarde aprovação → implemente só o aprovado → valide → documente → apresente → aguarde. Passo a passo em `docs/playbooks/document-a-change.md`.
- Não instale dependências, não baixe pesos de modelos e não altere versões do ambiente sem aprovação.
- Não modifique componentes que já funcionam (YOLO, `ObjectDetectionComponent`, `DetectionVisualizationComponent`) sem justificativa aprovada.
- Respeite SOLID (especialmente SRP, OCP e DIP), KISS, YAGNI e injeção de dependências pelo construtor. Não crie abstrações por antecipação.
- **Nunca invente** coordenadas, classes ou valores de confiança para preencher `DetectionContent`.
- Código, nomes, comentários e docstrings em **inglês**. Explicações ao desenvolvedor e documentação em **português**.

## Contratos centrais (resumo; detalhes em `docs/references/contracts.md`)

- `ArtifactReference.materialize() -> ArtifactContent`; `ArtifactContent.dematerialize(reference) -> str`.
- `Component.prepare(list[ArtifactReference]) -> object` retorna **conteúdos de artefatos**, não `.data`. `Component.execute(object) -> list[ArtifactReference]`.
- Modelos ficam atrás de interfaces injetadas (`ObjectDetector`, `VisualQuestionAnswerer`) e são testados com simuladores (`Fake*`).
- **Resultados de experimentos vêm só de modelos reais.** Simuladores ficam nos testes; o `ExecutionReport` exige a identidade de modelos reais (`docs/adr/009-execution-report-artifact.md`).
- **Experimentos com modelos que precisam de dependências próprias** (MIRAGE, Florence-2, Qwen3-VL) usam ambiente isolado (`experiments/<nome>/.venv`, conda ou binário próprio), nunca o `.venv` principal; modelos e saídas ficam fora do Git. Inferência local pesada roda com teto de memória (`systemd-run --user --scope -p MemoryMax=... -p MemorySwapMax=0`).
- **O `VisualQuestionAnsweringComponent` não está integrado ao MIRAGE** (não existe `MirageAnswerer`); a resposta real entra como `TextReference` lida da saída do `run_poc.py`.

## Verificação (rode ao concluir cada etapa)

```bash
uv run python scripts/okf_lint.py   # estrutura, frontmatter, índices e links de docs/
uv run ruff check .
uv run ruff format --check .      # também verifica blocos de código Python dentro dos .md
uv run python -m pytest -q -rs
uv run python -m pytest -q -rs experiments/mirage/tests experiments/e2e/tests experiments/florence2/tests experiments/qwen3vl/tests   # fora de testpaths
# Modelos reais nos testes de experiments/e2e exigem também E2E_ALLOW_REAL_MODELS=1 (autorização explícita).
# Com o modelo YOLO real (caminhos locais, não versionar):
DETECTION_MODEL_PATH=/caminho/best.onnx DETECTION_IMAGE_PATH=/caminho/imagem.jpg \
  uv run python -m pytest -q -rs
```

Relate os resultados reais. Nunca declare testes como aprovados sem tê-los executado.

## Documentação contínua (obrigatória)

A documentação faz parte de cada tarefa. Ela fica em `docs/`, no formato OKF 0.2 e no padrão do repositório `new-visio-research-models` (regras em `docs/CLAUDE.md`, detalhes em `docs/references/okf-guidelines.md`):

- **Raiz de `docs/`:** só `index.md`, `log.md`, `CLAUDE.md` e `handoff.md`.
- **Documentos vivos:** `playbooks/` (como fazer), `references/` (como é hoje), `diagrams/` (Mermaid).
- **Documentos temporais:** `adr/NNN-slug.md` (decisões), `plans/YYYY-MM-DD-slug.md`, `reports/YYYY-MM-DD-slug.md`.
- **Frontmatter:** `type` obrigatório; `generated: {by: "human:iago.pirone", at: "<ISO com -03:00>"}`; `evidence_basis` com `verified`, `approved`, `hypothesis` ou `proposal`. Agentes que contribuírem são registrados em `docs/references/provenance.md`.
- **Links internos relativos** ao arquivo (`../references/contracts.md`), para funcionarem no GitHub (`docs/adr/008-relative-internal-links.md`); todo documento entra no `index.md` da sua pasta.
- **Uma decisão** gera um ADR (ou plano) **e** atualiza o documento vivo afetado, na mesma mudança.

Ao concluir cada etapa, **e também quando uma decisão importante for tomada mesmo sem código**:

1. Atualize a página técnica correspondente em `docs/references/` (ou o playbook/diagrama afetado), ou crie uma e registre-a no `index.md` da pasta. Decisões viram ADR em `docs/adr/`.
2. Acrescente uma entrada em `docs/log.md`, na seção `## YYYY-MM-DD` do dia, que fica no topo.
3. Atualize `docs/references/status.md`.
4. Atualize `docs/handoff.md` para refletir o estado atual (Git, concluído, em andamento, última tarefa, decisões, limitações, próxima ação, arquivos).
5. Rode `uv run python scripts/okf_lint.py` e apresente ao usuário um resumo do código, da documentação e dos testes.

Em cada implementação, registre quando for relevante:
- objetivo;
- arquivos criados, modificados ou removidos;
- responsabilidades das classes;
- decisões e **por quê**;
- dependências;
- entradas e saídas;
- testes, com comandos e resultados reais;
- problemas encontrados e soluções;
- limitações e pendências;
- próximos passos.

Diferencie sempre: **verificado** (executado ou inspecionado no código), **aprovado** (decisão do usuário), **hipótese** e **proposta** (ainda não implementada).

Se o contexto da conversa estiver perto de ser compactado, atualize `docs/handoff.md` antes de continuar.
