---
type: Reference
title: Contratos centrais
description: Interfaces ArtifactReference, ArtifactContent, Component e as interfaces de modelo injetadas.
tags:
- architecture
- contracts
- pydantic
- component
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:28:27-03:00"
evidence_basis: [verified, approved]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d0fb7f2 + alterações não commitadas), inspecionado e testado em 17/11/2026
  title: Código, testes e execuções locais
- id: conversation
  resource: Relatos de desenvolvimento e decisões do usuário, 10–17/11/2026
  title: Evidências da conversa de desenvolvimento
---

# Contratos de software

## `ArtifactReference` (`mlops_workflows/artifacts/interface.py`)

```python
class ArtifactReference(BaseModel, ABC):
    name: str = Field(min_length=1)
    location: str = Field(min_length=1)

    @abstractmethod
    def materialize(self) -> ArtifactContent: ...
```

- Configuração Pydantic: `strict=True`, `extra="forbid"` e `validate_assignment=True`.
- `location` não pode ser só espaços.

## `ArtifactContent` (`mlops_workflows/artifacts/content.py`)

- `data: object` na interface; cada subtipo define o tipo concreto:
  - `np.ndarray` na imagem;
  - `list[np.ndarray]` + `fps` no vídeo;
  - `str` no texto;
  - `list[Detection]` nas detecções.
- `dematerialize(reference) -> str` salva o conteúdo no destino da referência e devolve a localização.

## `Component` (`mlops_workflows/components/interface.py`)

```python
class Component(ABC):
    @abstractmethod
    def prepare(self, input_artifacts: list[ArtifactReference]) -> object: ...

    @abstractmethod
    def execute(self, prepared_data: object) -> list[ArtifactReference]: ...
```

- `prepare()` valida as referências (quantidade, ordem e tipo) e as materializa.
- `execute()` valida o que recebeu, processa, salva as saídas e devolve as referências.
- A anotação `object` foi mantida. Os componentes concretos especializam o retorno de `prepare()` e validam a entrada de `execute()` em tempo de execução. Não foi criado um `Component` genérico com `TypeVar`.

## Convenção aprovada: `prepare()` devolve conteúdos

`prepare()` deve devolver os **objetos `ArtifactContent`**, e o `.data` só é acessado dentro de `execute()`. Situação em cada componente:

| Componente | `prepare()` retorna | Situação |
|---|---|---|
| `DetectionVisualizationComponent` | `tuple[ImageContent, DetectionContent]` | Aplicado em 17/11/2026 |
| `VisualQuestionAnsweringComponent` | `tuple[ImageContent, TextContent]` | Nasceu assim (17/11/2026) |
| `TextDetectionParsingComponent` | `tuple[ImageContent, TextContent]` | Nasceu assim (17/11/2026) |
| `ObjectDetectionComponent` | `np.ndarray` | **Divergente.** Não alterado por decisão do usuário (não refatorar outros componentes automaticamente) |

## Interfaces de modelo (injetadas pelo construtor)

| Interface | Método | Implementações |
|---|---|---|
| `ObjectDetector` | `detect(image: np.ndarray) -> list[Detection]` | `YoloDetector`; `FakeDetector` nos testes |
| `VisualQuestionAnswerer` | `answer(image: np.ndarray, question: str) -> str` | `FakeAnswerer` nos testes; `MirageAnswerer` **não existe ainda** |

## Classes auxiliares concretas (sem interface)

`TextDetectionParser.parse(text, image_width, image_height) -> list[Detection]` é puro e injetado no `TextDetectionParsingComponent`. Não tem ABC porque só existe uma implementação.

## `Detection.conf`

Desde 17/11/2026 é `float | None`: obrigatório, entre 0 e 1 quando numérico, e `null` quando a fonte não fornece confiança. Veja [detecções](artifact-detection.md).

Veja [ciclo de vida](artifact-lifecycle.md), [injeção de dependência](dependency-injection.md) e [artefatos](artifacts.md).
