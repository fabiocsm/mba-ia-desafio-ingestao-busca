# Modelo de dados: Busca fundamentada (002)

Este desenho reutiliza o armazenamento da [001](../001-pdf-ingestion/data-model.md).
Não cria tabelas, migrations, histórico ou persistência de consultas.

## Configuração de consulta

Reutilizar a dataclass imutável `Settings` de `src/config.py`, acrescentando o último campo
opcional `chat_model: str | None = None` para preservar chamadas existentes.

| Campo | Tipo / validação no fluxo de busca |
| --- | --- |
| `api_key` | `str` não vazia; segredo, excluído de repr/logs. |
| `embedding_model` | `str` não vazia; igualdade com o manifesto. |
| `embedding_dimensions` | `int` positivo, padrão 1536; igualdade com manifesto/vetores. |
| `database_url` | URL `postgresql+psycopg://` válida; segredo, excluído de repr/logs. |
| `collection_name` | `str` não vazia, destino explícito compartilhado com ingestão. |
| `pdf_path` | `None` na busca; não ler/validar o arquivo de origem. |
| `chat_model` | `str` não vazia quando `require_chat=True`; exemplo `gpt-6-luna`. |

`load_settings(ingestion=False)` mantém o contrato comum da 001 sem exigir chat;
`load_settings(ingestion=False, require_chat=True)` valida a configuração de consulta.
Mudar só o modelo de resposta não altera o espaço vetorial nem o manifesto.

## Base vetorial existente

| Dado | Relação e validação |
| --- | --- |
| Collection | Um nome/UUID existente, referente a uma revisão de um PDF; deve ter registros na inicialização. |
| Manifesto | JSONB imutável, `schema_version=1`, `provider=openai`, modelo/dimensão de embeddings, SHA-256 e pipeline da 001. |
| Chunk | ID, texto, embedding, origem, página e demais metadados da 001; não alterar na busca. |
| Dimensão persistida | Conferir que todos os vetores da collection têm a dimensão configurada; não confiar só no tamanho da coluna compartilhada. |

Usar `validate_manifest(actual, settings)` para comparação sem PDF_PATH. Hash/documento
e pipeline precisam ter estrutura compatível, mas não há leitura do PDF nem hash recalculado.
Collection legada sem manifesto, modelo diferente mesmo de mesma dimensão, pipeline/dimensão
incompatíveis ou vetores divergentes impedem abertura. Não reparar/adotar dados implicitamente.

## Pergunta

Entrada pública: mapping com a chave única `pergunta`, de valor `str` não vazio após
`strip()`. Chaves extras, inclusive histórico/contexto fornecidos pelo consumidor, são
rejeitadas para manter o contrato estreito. O texto normalizado segue à recuperação e ao
template; conteúdo interno é preservado, inclusive Unicode, chaves e instruções adversariais.

Validação é anterior a qualquer chamada de consulta. `QuestionError` não representa
ausência de informação documental e nunca retorna a frase de recusa.

## Trecho recuperado

Representação: `tuple[Document, float]` retornada pelo PGVector, sem DTO adicional.

| Parte | Uso |
| --- | --- |
| `Document.page_content` | Única contribuição factual ao contexto; excluir se vazio/branco. |
| `Document.id` / `metadata.chunk_id` | Identificação para conferência de evidências, sem inclusão automática no prompt. |
| `metadata.source`, `metadata.page` | Origem/página para validação; página do loader é base zero, página humana é +1. |
| `float` de distância | Diagnóstico técnico; sem filtro de suficiência ou inclusão no prompt. |
| Posição | Preservar a ordem retornada, inclusive quando menos de dez resultados. |

Os chunks persistidos permanecem íntegros. A lista da pergunta atual é temporária;
não acumular resultados entre invocações.

## Contexto

`str` formada pela concatenação dos textos originais não vazios, com separador
`\n\n---\n\n`. Verificar branco com `strip()` sem reescrever o texto de chunks aceitos.
Não acrescentar scores, metadados, resumos, exemplos do README, perguntas anteriores ou
conteúdo externo. Resultado sem texto útil equivale a contexto vazio.

O contexto não carrega um atributo `has_evidence`: ser não vazio ou semanticamente próximo
não prova que contém a resposta. Contradição não resolvível para a pergunta exige recusa;
uma pergunta sobre uma contradição explicitamente documentada pode ser respondida.

## Mensagens e resultado

Sistema: instrução estática de fundamentação, autoridade e recusa, sem interpolação de
dados. Humano: `PROMPT_TEMPLATE` integral do README, preenchido uma única vez com contexto
e pergunta atual. Sem mensagens de histórico ou ferramentas.

| Resultado | Representação / regra |
| --- | --- |
| Resposta fundamentada | String com fato explícito sustentado pelos chunks, sem acréscimos. Aceitação depende de conferência real. |
| Recusa factual | Exatamente `Não tenho informações necessárias para responder sua pergunta.`; fonte única em constante da aplicação. |
| Entrada inválida | Exceção `QuestionError`; sem recuperação/geração. |
| Falha de inicialização | `ConfigurationError` ou `StorageError` sanitizado; sem cadeia utilizável. |
| Falha de consulta | Exceção `SearchError` sanitizada com `retryable: bool`, nunca string factual. |

Validar mensagem do serviço antes da conversão: tipo textual esperado, conteúdo não vazio,
sem ferramentas, recusa técnica ou conclusão interrompida. Remover apenas whitespace
externo da string final. Parser/normalização não comprovam fatos nem corrigem semanticamente
uma resposta inventada; tal resultado reprova a validação.

## Estados e recursos da cadeia

`SearchChain` possui pipeline LCEL e recursos externos da sessão, sem memória factual.

| Origem → destino | Evento / efeito |
| --- | --- |
| Não criada → aberta | Configuração e base existentes válidas; transportes/engine adquiridos uma vez. |
| Não criada → falha | Configuração/preflight/construção falha; liberar tudo que já foi adquirido. |
| Aberta → aberta | Pergunta válida resulta em string; próxima pergunta não herda fatos. |
| Aberta → aberta | Entrada inválida ou falha transitória: nenhuma resposta substituta; consumidor pode tentar outra pergunta. |
| Aberta → encerrada pelo consumidor | Erro fatal: consumidor fecha recursos e corrige configuração/serviço antes de reiniciar. |
| Aberta → fechada | `close()` ou saída de `with`, inclusive por exceção/interrupção. |
| Fechada → fechada | `close()` repetido não produz novos efeitos; `invoke` falha antes de qualquer chamada externa. |

Uma cadeia é usada sequencialmente. Não oferecer contrato assíncrono/concorrente nesta
etapa. Transportes emprestados a clientes são fechados pelo proprietário; fábricas
injetadas delimitam propriedade pelo contexto retornado. Nada é inicializado no import.

## Evidência de validação

Registro manual em `plans/validacao.md`, sem nova entidade persistida no banco:
requisito/caso, ambiente/versões, modelo solicitado e devolvido, embeddings/dimensão,
collection, pergunta, resposta obtida/esperada, resultado, IDs/trechos recuperados,
página base zero e humana, comando e limitação/bloqueio. Para afirmativas, confirmar tanto
o PDF quanto o contexto efetivamente recuperado. Conteúdo só é exibido por procedimento
explícito de validação; logs normais não fazem esse registro detalhado.
