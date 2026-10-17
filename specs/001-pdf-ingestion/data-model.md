# Modelo de dados — 001: Ingestão do PDF

**Data**: 2026-10-16 | **Referências**: [spec](spec.md), [plano](plan.md),
[contrato](contracts/ingestion.md). Desenho previsto, sem tabelas criadas nesta fase.

## Documento de origem e páginas

| Campo | Tipo | Regra |
| --- | --- | --- |
| `source` | `str` | Caminho local resolvido do PDF; obrigatório, sem URL remota. |
| `document_sha256` | `str` | SHA-256 dos bytes do arquivo; 64 caracteres hexadecimais. |
| `loaded_pages` | `int` | Todas as páginas retornadas pelo loader, incluindo vazias. |
| `page` | `int` | Índice original baseado em zero; apresentação humana pode somar 1 explicitamente. |
| `page_content` | `str` | Texto extraído; somente conteúdo com `strip()` não vazio origina chunks. |

Um documento contém páginas; cada página origina zero ou mais chunks. Não concatenar
páginas antes da divisão. O hash identifica a revisão; caminho não identifica conteúdo.
Leitura e hash devem usar o mesmo arquivo estável; alteração detectada durante o
processamento deve causar falha e orientação para estabilizar o arquivo e reexecutar.

## Trecho documental e representação semântica

Usar `langchain_core.documents.Document` para texto/metadados, sem modelo paralelo.
O vetor é `list[float]`, com todos os valores finitos.

| Campo persistido | Local | Regra |
| --- | --- | --- |
| `id` | PK em `langchain_pg_embedding` | String determinística, única em toda a tabela. |
| `document` | Coluna da integração | `page_content` não vazio, até 1000 caracteres. |
| `embedding` | Coluna `vector` | Dimensão igual ao manifesto da collection. |
| `source` | JSONB `cmetadata` | Origem preservada. |
| `page` | JSONB `cmetadata` | Página original baseada em zero. |
| `document_sha256` | JSONB `cmetadata` | Revisão do PDF. |
| `chunk_index` | JSONB `cmetadata` | Posição global baseada em zero, em ordem página/trecho após filtrar vazios. |
| `chunk_id` | JSONB `cmetadata` | Mesmo valor do `id`, para rastreabilidade. |
| `collection_id` | FK da integração | UUID da collection. |

Preservar demais metadados úteis do loader, usando valores serializáveis em JSON.
Não gerar embedding de texto vazio nem vetor fictício. Validar cardinalidade antes
de associar entradas e vetores.

### Identificador determinístico

SHA-256 de uma serialização JSON canônica UTF-8, com chaves ordenadas e formato estável,
contendo: nome exato da collection, versão do contrato, provedor, modelo, dimensão,
hash do PDF, assinatura da extração/divisão, página, índice global e hash do texto do
chunk. Usar o hexadecimal como `id` e `chunk_id`.

O nome da collection é obrigatório: IDs do PGVector 0.0.15 são globais e seu upsert
não altera `collection_id`. Não usar somente texto, caminho ou posição. Trechos repetidos
são registros distintos; outra collection não pode sobrescrevê-los. Não incluir timestamp
aleatório. A mesma entrada/configuração deve produzir os mesmos IDs.

## Coleção documental e manifesto

`langchain_pg_collection`: `uuid`, `name` único e `cmetadata` JSON. Este último conterá
o manifesto abaixo, gravado somente na criação da collection:

| Campo | Tipo | Valor/regra inicial |
| --- | --- | --- |
| `schema_version` | `int` | `1`, versão do contrato. |
| `provider` | `str` | `openai`. |
| `embedding_model` | `str` | `text-embedding-3-small` no ambiente de referência. |
| `embedding_dimensions` | `int` | `1536` no ambiente de referência; positivo. |
| `document_sha256` | `str` | Revisão única de PDF aceita nesse destino. |
| `pipeline` | objeto JSON | Identidade de extração/divisão abaixo. |

`pipeline` registra `PyPDFLoader`, `langchain-community=0.3.27`, `pypdf=6.0.0`, modo
por página, `extract_images=False`, `RecursiveCharacterTextSplitter`,
`langchain-text-splitters=0.3.9`, `chunk_size=1000`, `chunk_overlap=150`,
`length_function=len` e separadores padrão `["\n\n", "\n", " ", ""]`.
Comparar valores estruturados, sem depender da ordem das chaves.

**Validações**:

- Ausente: criar com manifesto completo e reler a linha persistida antes de usar.
- Existente: conferir integralmente o manifesto; nunca substituí-lo pela configuração
  solicitada. Collection vazia incompatível também é rejeitada.
- Sem manifesto/contrato conhecido: rejeitar, sem inferir modelo pelos vetores nem adotar
  dados legados automaticamente.
- Modelo diferente com dimensão igual continua incompatível. Dimensão incorreta ou valor
  não finito do vetor é erro antes da persistência.
- Modelo, PDF ou pipeline alterado: nova collection explícita ou procedimento administrativo
  separado; sem apagar nem mesclar revisões automaticamente.

Usar `embedding_length=None` no schema compartilhado; sem índice ANN ou migração nesta
entrega. A aplicação valida o espaço vetorial por collection. Tabela já existente com
dimensão fixa incompatível produz erro acionável, sem `ALTER TABLE` ou exclusão automática.

## Resultado e estados

Resultado em memória, sem tabela adicional: `source: Path`, `loaded_pages: int`,
`stored_chunks: int`, `collection_name: str`. Uma `dataclass` imutável pequena pode
representar o contrato entre orquestração e CLI.

Estados conceituais: configuração válida → PDF extraído → chunks preparados → collection
compatível → vetores completos → escrita confirmada → sucesso. Uma falha interrompe
a sequência. Manifesto/collection criados antes de falha da API podem permanecer vazios;
isso não representa ingestão concluída.

Após commit sem resposta ou falha na conferência, o estado durável pode ser indeterminado.
Não inventar quantidade gravada ou afirmar rollback. Retornar erro e orientar reexecução
com a mesma entrada/configuração. O upsert recupera sem duplicação, mas pode repetir
custos de embeddings.

## Contrato para a spec 002

A busca recebe a configuração comum e valida o espaço vetorial do manifesto
(`schema_version`, provedor, modelo e dimensão), sem exigir `PDF_PATH` nem recalcular hash.
Revisão/pipeline do manifesto devem ser válidos, sem acesso ao PDF original. Collection
ausente/vazia orienta ingestão. Resultados preservam `Document.page_content` e metadados.
Não se altera `search_prompt().invoke({"pergunta": texto}) -> str`.
