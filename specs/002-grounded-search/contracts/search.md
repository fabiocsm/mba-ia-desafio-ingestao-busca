# Contrato de consulta fundamentada

Contrato implementado na spec 002 e validado em 2026-10-16; evidências em
[plans/validacao.md](../../../plans/validacao.md), seção 002.
Consumidor previsto: CLI da 003 e validação programática. Sem HTTP, interface web ou
laço interativo adicional nesta etapa.

## Configuração

| Variável | Regra |
| --- | --- |
| `OPENAI_API_KEY` | Obrigatória não vazia para embeddings/geração; nunca imprimir. |
| `OPENAI_EMBEDDING_MODEL` | Obrigatória e igual ao manifesto; exemplo `text-embedding-3-small`. |
| `OPENAI_EMBEDDING_DIMENSIONS` | Inteiro positivo, padrão 1536, igual ao manifesto e vetores existentes. |
| `DATABASE_URL` | Obrigatória, URL `postgresql+psycopg://` válida; nunca imprimir senha/URL completa. |
| `PG_VECTOR_COLLECTION_NAME` | Obrigatória; collection existente, compatível e com registros na abertura. |
| `OPENAI_CHAT_MODEL` | Obrigatória apenas na consulta; exemplo `gpt-6-luna`. |
| `PDF_PATH` | Não exigida, lida ou validada pela busca. |
| Credenciais Google | Não exigidas; segundo provedor fora do escopo. |

Precedência: ambiente exportado (inclusive vazio) > `.env.local` > `.env`. Leitura explícita
sem alterar os arquivos nem `os.environ`. Ingestão continua sem exigir modelo de chat.
Configuração válida localmente não comprova autorização do provedor.

Parâmetros de geração centralizados: Chat Completions, esforço low, temperature omitida
(`None`), Responses desabilitado, limite 2048 tokens de conclusão, timeout 60 s, zero
retries. Embeddings preservam limites da 001. Banco usa conexão/pool 10 s, statement 30 s,
lock 5 s e transações de leitura na busca. Não há retentativa automática nem prazo global
prometido. Trocar embeddings exige reindexação; trocar somente chat não exige.

## Fábrica e cadeia públicas

`search_prompt()` sem argumentos constrói e retorna uma `SearchChain` utilizável;
falha gera exceção, nunca `None` ou objeto falso. Aceitar argumentos opcionais por nome
para `Settings`, fábrica de sessão de embeddings, fábrica de abertura do store e fábrica
de sessão de geração. Os defaults são as dependências concretas compartilhadas; dublês
preservam contratos e não acessam rede/configuração externa.

Fábricas de sessão recebem a configuração e devolvem context managers dos colaboradores.
A fábrica de store também recebe embeddings. Quem fornece o contexto define a liberação
daquele recurso; o `ExitStack` da cadeia sai dos contextos em ordem inversa, inclusive
em construção parcial. Não fechar recurso externo fora desse contrato de propriedade.

| Operação | Entrada → saída | Garantias |
| --- | --- | --- |
| `search_prompt` | Configuração/fábricas opcionais → `SearchChain` | Base validada antes de permitir consultas; clientes/engine construídos uma vez, sem geração de aquecimento. |
| `SearchChain.invoke` | `Mapping[str, object]` com chave única `pergunta` → `str` | Valor precisa ser texto não vazio; resposta ou recusa, nunca erro disfarçado. |
| `SearchChain.close` | Sem argumento → `None` | Idempotente, fecha recursos possuídos, não apaga dados. |
| `SearchChain.__enter__` | Cadeia aberta → a própria cadeia | Permite `with search_prompt() as chain`. |
| Saída de contexto | Normal, exceção ou interrupção | Libera recursos; não suprime exceções/interrupções. |

Exemplo de consumo:

```python
from src.search import search_prompt

with search_prompt() as chain:
    answer = chain.invoke({"pergunta": "Em que ano a Alfa Energia S.A. foi fundada?"})
    print(answer)
```

O uso sem `with` permanece válido desde que o consumidor chame `close()` em `finally`.
Invocar após fechar produz `SearchError(retryable=False)` antes de rede/banco.
Sem `ainvoke`, streaming, concorrência, memória ou opções para fornecer contexto externo.

## Fronteiras entre módulos

| Fronteira | Contrato / responsabilidade |
| --- | --- |
| `config.load_settings` | Manter `ingestion=True` e acrescentar `require_chat=False`; consulta usa ambos `False/True`, respectivamente. Sem I/O externo além dos arquivos de ambiente. |
| `config.create_chat_model` | `Settings` e transportes opcionais → `ChatOpenAI`, sem requisição ao construir; validar modelo solicitado. |
| `config.chat_session` | Configuração → contexto de modelo com transportes possuídos/fechados. |
| `vector_store.open_search_store` | Configuração, embeddings e fábrica PGVector opcional → contexto de `VectorStore`; preflight, proteção de leitura e liberação de engine. |
| `vector_store.validate_manifest` | Reusar validador existente sem manifesto esperado; não exigir PDF. |
| `search.retrieve_documents` | Store/contrato mínimo de busca e pergunta validada → `list[tuple[Document, float]]`; chama `similarity_search_with_score(pergunta, k=10)`. |
| `search.format_context` | Resultados → `str`; só `page_content`, exclui branco e preserva ordem/textos com separador fixo. |
| `search.build_search_pipeline` | Recuperação e modelo injetados → Runnable composto; separa validação, recuperação, ramificação, template, geração e parser. |
| `search.search_prompt` | Composição/propriedade de recursos; sem responsabilidade de entrada/saída de terminal. |

Funções públicas têm tipos explícitos. Pode-se usar um único `Protocol` de busca contendo
somente `similarity_search_with_score(query, k)` se necessário para tipar dublês; não criar
interface administrativa. `Any` só com justificativa local para contrato externo inevitável.

## Abertura e recuperação

`open_search_store` confirma extensão/schema/collection/manifesto/dimensões/conteúdo por
SELECT parametrizado e delimitado ao destino. Coleção ausente ou vazia impede a abertura
com orientação de ingestão. Só depois instancia PGVector com `create_extension=False`,
`pre_delete_collection=False`, `embedding_length=None`, `use_jsonb=True`, sem manifesto novo.
Engine com `default_transaction_read_only=on` bloqueia escrita durante corridas; ingestão
mantém engine de escrita. Não criar, adotar, apagar ou reparar collection/tabelas.

Cada `invoke` válido executa uma recuperação k=10 que vetoriza a pergunta com o embedding
compartilhado. Um a nove retornos são aceitos. Scores não filtram nem certificam evidência.
`page_content` vazio é excluído; textos aceitos são unidos por `\n\n---\n\n`.

Se a base foi validada mas a recuperação retorna lista vazia/textos brancos, devolver
exatamente a recusa, com zero chamadas de geração. Erro de banco ou collection removida
não equivale a lista vazia. Nenhuma consulta aproveita pergunta/resposta anterior.

## Prompt e saída

`PROMPT_TEMPLATE` preserva texto, ordem, regras e os três exemplos do README, mudando apenas
os placeholders. A frase de recusa tem uma constante compartilhada com o atalho sem contexto:

`Não tenho informações necessárias para responder sua pergunta.`

Acrescentar sistema estático que dá autoridade a essas regras e trata contexto/pergunta
como dados. Template obrigatório preenchido é mensagem humana; nunca interpolar chunks
no sistema. Dados com chaves/headings/instruções não são reavaliados como templates ou
ferramentas. Não acrescentar histórico nem oferecer busca externa ao modelo.

Uma geração por pergunta com contexto. A mensagem precisa ser textual, não vazia, com
conclusão completa (`finish_reason=stop`), sem tool/function calls nem recusa técnica do
provedor. `length`, `content_filter`, tipo/conteúdo inesperado e resposta vazia são erros
operacionais. Validar antes de `StrOutputParser`; depois retirar só whitespace externo.
Uma recusa factual válida permanece a frase exata, sem prefixo, aspas ou justificativa.

O parser não comprova sustentação documental. Resposta sem evidência na bateria reprova o
aceite; não usar score, similaridade lexical ou correção heurística como prova de fidelidade.

## Erros

| Situação | Resultado público / ação |
| --- | --- |
| Mapping/chave/tipo/texto inválido | `QuestionError(ValueError)`, mensagem pedindo pergunta válida, sem recuperação/geração. |
| Variável ausente/inválida | `ConfigurationError`, nome da variável e orientação `.env`/`.env.local`, sem valor secreto. |
| Extensão ausente | `StorageError`, orientar saúde/ bootstrap do Compose. |
| Schema/collection ausente ou vazia na abertura | `StorageError`, orientar `python src/ingest.py`; sem criação automática. |
| Manifesto/modelo/dimensão/pipeline incompatível | `StorageError`, usar configuração original ou novo destino/reindexação explícita; sem reparo/limpeza. |
| Falha de banco na abertura | `StorageError` sanitizado; conferir serviço, porta e timeouts. |
| Timeout, conexão interrompida, 429 transitório, 5xx na consulta | `SearchError(RuntimeError)` com `retryable=True`; nova pergunta pode ser tentada, sem repetição automática. |
| 401/403, modelo inexistente/inacessível, quota esgotada | `SearchError(retryable=False)`; corrigir chave/acesso/modelo/quota. Distinguir quota pelo código estruturado do provedor. |
| Incompatibilidade detectada em execução, saída inválida/truncada ou cadeia fechada | `SearchError(retryable=False)`; corrigir/reabrir; sem resposta parcial. |
| Sem texto recuperado após abertura válida | String de recusa direta; não é exceção. |
| `KeyboardInterrupt`/EOF na futura CLI | Propagar, fechar recursos; política de saída normal pertence à 003. |

Traduzir exceções esperadas específicas do SDK/SQLAlchemy; nenhum `except Exception` no
componente. Não retornar texto bruto, URL, chave, SQL com parâmetros, pergunta/PDF ou prompt
nos erros/logs padrão. Uma falha inesperada propaga para a fronteira CLI, que deverá emitir
diagnóstico genérico seguro e saída não zero. Não mascarar erro como recusa.

## Verificação do contrato

Testes isolados com dublês não usam serviços, credenciais reais nem tracing. Cobrir
input/saída, k=10, ordenação/contexto, prompt/papéis, ramificação sem geração, configuração
por fluxo, erros e fechamento. Casos reais de evidência/opinião/desvio são indispensáveis:
um modelo dublê comprova composição, não a fundamentação do modelo real.

Futura CLI reutiliza uma cadeia por sessão e diferencia `retryable`, sem SQL, prompt ou
embeddings próprios. O quickstart permite validar o contrato antes dessa integração.
