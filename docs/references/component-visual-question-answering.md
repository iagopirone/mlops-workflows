---
type: Reference
title: VisualQuestionAnsweringComponent (experimental)
description: Componente genérico imagem + prompt → resposta textual, com modelo injetado por VisualQuestionAnswerer.
tags:
- vqa
- multimodal
- component
- di
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

# Objetivo

Receber uma imagem e um prompt como artefatos, perguntar a um modelo multimodal injetado e salvar a **resposta textual** como artefato.

- É uma **etapa experimental** da integração do MIRAGE.
- **Não** gera detecções, caixas nem confiança.
- Implementado e aprovado em 17/11/2026, ainda não commitado.

## Arquivos

- `mlops_workflows/components/visual_question_answering/visual_question_answerer.py`
- `mlops_workflows/components/visual_question_answering/visual_question_answering_component.py`
- Testes:
  - `tests/unit/components/visual_question_answering/test_visual_question_answerer.py` (1)
  - `tests/unit/components/visual_question_answering/test_visual_question_answering_component.py` (8)
  - `tests/integration/components/visual_question_answering/test_visual_question_answering_pipeline.py` (1)

Não foi adicionada nenhuma dependência.

## `VisualQuestionAnswerer` (interface)

```python
class VisualQuestionAnswerer(ABC):
    @abstractmethod
    def answer(self, image: np.ndarray, question: str) -> str: ...
```

- Recebe uma imagem **BGR** e a pergunta; devolve texto livre.
- É o mesmo papel do `ObjectDetector`: permite trocar o MIRAGE real por um simulador nos testes.
- O nome é genérico de propósito, para respeitar o OCP: outros modelos de VQA podem entrar sem mudar o componente.
- Converter BGR para RGB é responsabilidade do futuro adaptador `MirageAnswerer`.

## `VisualQuestionAnsweringComponent`

- **Construtor:** `answerer: VisualQuestionAnswerer`, `output_reference: TextReference`.
- **`prepare(input_artifacts)`:**
  - exige exatamente `[ImageReference, TextReference]`, nessa ordem; senão gera `ValueError`;
  - retorna `tuple[ImageContent, TextContent]`, seguindo a convenção de devolver conteúdos e não `.data`.
- **`execute(prepared_data)`:**
  1. exige `(ImageContent, TextContent)`; senão gera `TypeError`;
  2. recusa prompt vazio ou só com espaços com `ValueError`, **antes** de chamar o modelo, para evitar inferência cara inútil;
  3. entrega ao answerer **uma cópia** dos pixels, garantindo que nem um modelo descuidado altere a imagem carregada;
  4. exige que a resposta seja `str`; senão gera `TypeError`;
  5. `TextContent(data=answer).dematerialize(output_reference)` e retorna `[output_reference]`.
  - Exceções do answerer são repassadas, e **nenhum arquivo de saída é criado**.

## Testes (verificados em 17/11/2026)

- **Interface:** é abstrata e não pode ser instanciada.
- **`prepare()`:**
  - retorna conteúdos com os dados corretos;
  - rejeita lista vazia, item faltando, ordem invertida, `DetectionReference` e item extra.
- **`execute()`:**
  - repassa pixels e pergunta e salva a resposta (Unicode e quebra de linha);
  - preserva a imagem, mesmo com um `MutatingAnswerer`;
  - rejeita dados preparados inválidos, prompt vazio e resposta que não é texto;
  - com um `FailingAnswerer`, não grava saída.
- **Integração:** arquivos reais de imagem e prompt → componente com `FakeAnswerer` → arquivo de resposta; entradas preservadas.
- **Resultado:** 10 passed. Na entrega do VQA, a suíte completa deu 102 passed com ONNX real; veja [testes](test-suite.md) para a contagem atual.

## Limitações

- Uma imagem por chamada. O modo de várias imagens do MIRAGE fica para depois (YAGNI).
- Ainda não existe implementação real da interface. Veja [MIRAGE](mirage.md).
