---
okf_version: "0.2"
---

# mlops-workflows — base de conhecimento

Documentação técnica do projeto **mlops-workflows**, no formato OKF 0.2 e no padrão do repositório `new-visio-research-models` ([diretrizes](references/okf-guidelines.md)).

- **Base original:** snapshot do repositório de 09/11/2026 e relatos até 16/11/2026 ([proveniência](references/provenance.md)).
- **Sincronização com o código local:** desde 17/11/2026. **Reorganização no padrão OKF:** 18/11/2026.

**Para retomar o trabalho** (sessão nova ou depois de compactação): [handoff](handoff.md) → [status](references/status.md) → [log](log.md). As regras do bundle estão em `docs/CLAUDE.md`; as instruções gerais para agentes, no `CLAUDE.md` da raiz do repositório.

**Leitura importante:** o MIRAGE **nunca foi executado** neste projeto. A geração de bounding boxes confiáveis por ele é **hipótese experimental**.

## Categorias

* [Playbooks](playbooks/index.md) - como fazer: testar localmente, criar artefato, componente ou adaptador de modelo, documentar uma mudança.
* [Referências](references/index.md) - como o projeto é hoje: contratos, artefatos, componentes, MIRAGE, testes, estado e regras.
* [Diagramas](diagrams/index.md) - pipeline atual e diagramas do ADR 001.
* [ADR](adr/index.md) - decisões de arquitetura e de processo, com o porquê.
* [Planos](plans/index.md) - o que se pretende fazer (integração MIRAGE, commits, reorganização da documentação).
* [Relatórios](reports/index.md) - o que foi observado em execuções.

## Comece por aqui

* [Handoff](handoff.md) - estado atual, decisões, próxima ação e arquivos para retomar.
* [Status](references/status.md) - o que está verificado, aprovado, em hipótese ou proposto.
* [Visão geral](references/overview.md) - objetivo e escopo do projeto.
* [Contratos centrais](references/contracts.md) - ArtifactReference, ArtifactContent e Component.
* [Invariantes](references/invariants.md) - regras que nenhuma mudança pode violar.
* [Pipeline atual](diagrams/current-pipeline.md) - fluxo implementado e fluxo-alvo do desafio MIRAGE.
* [MIRAGE](references/mirage.md) - capacidades verificadas, limites e prova de conceito.
* [Testar e executar localmente](playbooks/test-locally.md) - comandos de lint, testes e demo.
* [Mecanismos transitórios](references/transitional-mechanisms.md) - o que é provisório e quando sai.
* [Log](log.md) - histórico, mais recente primeiro.
