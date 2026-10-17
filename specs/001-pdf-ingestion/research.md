# Pesquisa — 001: Ingestão e persistência do PDF

**Data**: 2026-10-16 | **Base normativa**: [spec](spec.md),
[constituição](../../.specify/memory/constitution.md) e etapas 1–2 do
[plano inicial](../../plans/plano-implementacao.md).

Pesquisa de dependências e persistência realizada em paralelo, conforme a skill
`speckit-plan`, e consolidada neste documento. Nenhuma chamada de embeddings, ingestão
real ou alteração de banco foi executada. Sem pendências técnicas de esclarecimento;
validação integrada permanece necessária na implementação.

## 1. Python e versões fixadas

**Decisão**: CPython **3.12.12**, mantendo todos os 75 pins de `requirements.txt`.

**Justificativa**: o host originalmente resolve `python3` para 3.14.5. Não usar essa
versão sem comprovação: `numpy==2.3.2` exige Python >=3.11 e a presença de versões
binárias compatíveis também importa. Um Python 3.12.12 gerenciado por `uv` foi usado
para instalar e conferir a pilha em ambiente temporário, sem alterar os requisitos.

**Alternativas**: 3.11/3.13 atendem aos metadados publicados, mas não foram executados;
3.14 exigiria investigação adicional sem necessidade para o desafio. Atualização em
massa dos pacotes foi rejeitada porque nenhuma incompatibilidade foi demonstrada.

Compatibilidades conferidas:

- `langchain-openai==0.3.30`: core >=0.3.74,<1, OpenAI >=1.99.9,<2, tiktoken >=0.7,<1.
- `langchain-text-splitters==0.3.9`: core >=0.3.72,<1.
- `langchain-postgres==0.0.15`: core >=0.2.13,<0.4, pgvector >=0.2.5,<0.4, NumPy >=1.21,<3,
  SQLAlchemy >=2,<3 e psycopg >=3,<4. Os pins atuais satisfazem esses limites.

Fontes oficiais: [NumPy 2.3.2](https://pypi.org/project/numpy/2.3.2/),
[LangChain OpenAI 0.3.30](https://pypi.org/project/langchain-openai/0.3.30/),
[Text Splitters 0.3.9](https://pypi.org/project/langchain-text-splitters/0.3.9/),
[Postgres 0.0.15](https://pypi.org/project/langchain-postgres/0.0.15/).

## 2. Provedor e embeddings

**Decisão**: OpenAI com `text-embedding-3-small` e `dimensions=1536`, configurados por
ambiente. Usar `OpenAIEmbeddings` 0.3.30, API de embeddings do SDK OpenAI 1.102.0.

**Justificativa**: modelo já exemplificado no repositório, documentado oficialmente e
compatível com a integração fixada. A documentação informa dimensão padrão 1536 e
suporte a dimensão explícita. Ausência de `.env` não permite inferir credencial, quota
ou autorização da conta. Não presumir gratuidade. A ingestão não exige modelo de chat;
sua escolha será feita na spec 002.

**Alternativas**: Gemini é permitido pelo enunciado, mas exigiria selecionar/validar
outro modelo e não há preferência ou credencial informada. Não implementar dois
provedores. Modelos maiores de embeddings não têm necessidade demonstrada neste PDF.

Fontes: [guia oficial de embeddings](https://developers.openai.com/api/docs/guides/embeddings),
[modelo oficial](https://developers.openai.com/api/docs/models/text-embedding-3-small),
[código da integração fixada](https://github.com/langchain-ai/langchain/blob/langchain-openai%3D%3D0.3.30/libs/partners/openai/langchain_openai/embeddings/base.py).

## 3. Leitura e divisão por página

**Decisão**: `PyPDFLoader(str(path), mode="page", extract_images=False).load()`;
`RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150, length_function=len)`
com separadores padrão e `split_documents`. Filtrar páginas/chunks com `strip()` vazio,
sem transformar o conteúdo restante artificialmente.

**Justificativa**: essas APIs existem nas versões fixadas. O loader preserva `source`,
`page` baseado em zero e `total_pages`; o splitter conserva metadados e divide cada
página separadamente. O loader pode retornar páginas vazias, que a aplicação deve
tratar. Overlap efetivo pode ser menor que 150 por separação e limites de página.

**Alternativas**: concatenar páginas perderia rastreabilidade; OCR e leitura manual
com pypdf no fluxo principal não atendem ao desenho exigido. Não confundir o parâmetro
de lote `OpenAIEmbeddings.chunk_size` com o tamanho em caracteres do splitter.

Fontes: [Community 0.3.27](https://pypi.org/project/langchain-community/0.3.27/),
[pypdf 6.0.0](https://pypi.org/project/pypdf/6.0.0/),
[splitter na versão fixada](https://github.com/langchain-ai/langchain/blob/langchain-text-splitters%3D%3D0.3.9/libs/text-splitters/langchain_text_splitters/character.py).
O código do loader/parser foi também inspecionado no wheel oficial da versão fixada.

## 4. PGVector, schema e identidade da collection

**Decisão**: `PGVector` 0.0.15 síncrono, `use_jsonb=True`, `embedding_length=None`,
`pre_delete_collection=False`, `create_extension=False`, engine SQLAlchemy com psycopg.
O Compose existente fornece PostgreSQL 17, volume, healthcheck e bootstrap da extensão.

**Justificativa**: o schema da integração contém `langchain_pg_collection` (UUID, nome
único, JSON `cmetadata`) e `langchain_pg_embedding` (ID global, FK collection, texto,
vetor e JSONB de metadados). Dimensão fixa em `embedding_length` se aplica à tabela
compartilhada. Sem índice ANN para um único PDF pequeno, a coluna sem dimensão global
permite nova collection com outra dimensão sem destruir dados de destinos anteriores.
A aplicação deve conferir cada vetor e o manifesto, não confiar em erro automático do banco.

**Alternativas**: dimensão global 1536 funciona inicialmente, mas inviabiliza reindexação
não destrutiva em outra dimensão na mesma tabela; tabela vetorial própria, migração e
índice ANN criariam trabalho desnecessário. `PGVectorStore`, de documentação mais recente,
não substitui a API fixada pelo projeto.

Fonte oficial da release: [vectorstores.py, commit 18b1bcd](https://github.com/langchain-ai/langchain-postgres/blob/18b1bcdb75ed152da717e3d624e1ed822d17d60f/langchain_postgres/vectorstores.py).

## 5. Bloqueio de mistura e reingestão

**Decisão**: manifesto imutável na criação da collection, com provedor/modelo/dimensão,
revisão SHA-256 do PDF e assinatura de extração/divisão. Depois de construir PGVector,
ler o manifesto real e comparar antes de gerar embeddings. Rejeitar destino incompatível
ou sem manifesto, mesmo vazio. Outra revisão/configuração usa nova collection explícita.

**Justificativa**: `collection_metadata` só participa da criação; reabrir collection não
compara nem atualiza esses dados. A restrição única do nome torna uma criação concorrente
incompatível segura: uma execução pode falhar, sem continuar sem validação. Como escritores
da aplicação nunca alteram o manifesto, não há troca de identidade após a comparação.

**Decisão adicional**: adotar IDs SHA-256 determinísticos incluindo a collection, identidade
de documento/pipeline e posição/texto do chunk. Testar reingestão e isolamento entre destinos.
O upsert desta versão não muda `collection_id`; IDs sem namespace por collection poderiam
sobrescrever registros de outro destino. Não prometer cache nem economia na reexecução.

**Alternativas**: IDs aleatórios preservariam dados, mas duplicariam reexecuções; hash só do
texto colidiria entre trechos/collections. Atualizar manifesto existente esconderia mistura
de espaços. Limpeza automática viola FR-009. Locks adicionais e tabela de controle são
desnecessários com a política de manifesto imutável; SQL administrativo externo fica fora
do contrato de escrita da aplicação.

Conferir manifesto com SQL parametrizado por nome; `get_by_ids` existe e filtra a collection,
sem garantir ordem. Usar `vector_dims(embedding)` na conferência dos vetores. Fonte:
[código oficial 0.0.15](https://github.com/langchain-ai/langchain-postgres/blob/18b1bcd/langchain_postgres/vectorstores.py).

## 6. Falhas, timeouts e confirmação

**Decisão**: validar lista de vetores completa e chamar `add_embeddings` uma vez. Conferir
retorno/IDs e registros antes do resumo. `add_embeddings` usa um insert com upsert e um
commit por chamada; seu `zip()` interno exige proteção contra cardinalidade desigual.
Não repetir gravação automaticamente. Desconexão durante commit deixa resultado incerto,
tratado como falha sem quantidade inventada; mesma entrada/IDs permite recuperação.

**Decisão**: API com `request_timeout=60`, `max_retries=0`; engine com `pool_timeout=10`,
`connect_timeout=10`, `options="-c statement_timeout=30000 -c lock_timeout=5000"`,
`echo=False`, `hide_parameters=True`. Liberar engine e cliente HTTP no encerramento.

**Justificativa**: limites finitos evitam bloqueio indefinido; zero retries reduz chamadas
cobradas repetidas e incerteza de escrita. Mensagens da aplicação devem sanitizar falhas,
pois só ocultar parâmetros no SQLAlchemy não remove todos os riscos de logs brutos.

**Alternativas**: transação distribuída com provedor é desnecessária/inexistente neste fluxo;
lotes persistidos separadamente exigiriam contabilização parcial mais complexa. Não usar
retentativas genéricas nem capturar erros como sucesso.

Fontes: [PGVector 0.0.15](https://github.com/langchain-ai/langchain-postgres/blob/18b1bcd/langchain_postgres/vectorstores.py),
[SQLAlchemy Engine](https://docs.sqlalchemy.org/en/20/core/engines.html),
[conexão PostgreSQL 17](https://www.postgresql.org/docs/17/libpq-connect.html#LIBPQ-PARAMKEYWORDS),
[timeouts PostgreSQL 17](https://www.postgresql.org/docs/17/runtime-config-client.html),
[ordem de inicialização Compose](https://docs.docker.com/compose/how-tos/startup-order/).

## 7. Evidências executadas nesta pesquisa

| Verificação | Resultado / limite |
| --- | --- |
| Ambiente temporário | CPython 3.12.12, macOS arm64; `/tmp/spec001-dependencies/venv`, sem ambiente da aplicação criado no repositório. |
| Instalação | `uv python install 3.12`, criação de venv temporário e `uv pip install --python <venv>/bin/python -r requirements.txt`: 75 pins instalados sem alteração. |
| Consistência | `python -m pip check`: `No broken requirements found.` |
| Imports | Loader, splitter, `OpenAIEmbeddings` e `PGVector` aprovados. |
| Cliente de embeddings | Construção com chave fictícia, dimensão explícita, timeout finito e zero retries aprovada; nenhuma chamada de rede. |
| PDF fornecido | 34 páginas com texto, 67 chunks, tamanho 429–999 caracteres, `source`/`page` preservados. |
| Revisão do PDF | SHA-256 `487adc82839c525365caa5feef4c7de01be10d3375ee43c9a2dfd24331274ca8`. Números observados se referem somente a essa revisão/pipeline. |
| Amostras | Página intermediária vazia preservou índices originais; texto de 2100 caracteres, página curta e vazia produziu comprimentos `[1000, 1000, 400, 6]`. |
| Compose | `docker compose config --quiet` aprovado; CLI v5.5.1 e daemon 29.8.2 acessíveis. Serviços não foram iniciados para esta pesquisa. |

**Ainda não executado**: instalação pelo fluxo obrigatório `python3 -m venv`/`pip install`
em ambiente novo, teste da aplicação (não implementada), saúde/bootstrap reais, chamada
de embeddings, persistência, reingestão e reinício do banco. Não apresentar esses aceites
como atendidos. Os resultados integrados serão registrados em `plans/validacao.md` na
implementação; este documento registra somente evidência de pesquisa/compatibilidade.

## 8. Contexto atualizado antes de gerar tarefas

Após a pesquisa, o usuário confirmou OpenAI e solicitou `.env.local` para a credencial.
O arquivo local foi criado e ignorado pelo Git, sem testar a chave. O desenho passa a
aceitar `.env.local` opcional, preservando `.env` e variáveis exportadas: precedência
ambiente exportado > `.env.local` > `.env`. Combinar configurações explicitamente na
inicialização, sem efeitos no import ou sobrescrita dos arquivos. Plano, contrato e
quickstart foram alinhados; a implementação desse carregamento terá testes isolados.
