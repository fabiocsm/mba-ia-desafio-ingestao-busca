# Pesquisa: Busca fundamentada (002)

Data: 2026-10-16. Base: spec 002, constituição v1.0.0, README e implementação da 001.
Pesquisa de geração/LCEL e armazenamento delegada em paralelo e consolidada aqui.
Sem API paga, chave real, conexão ao banco ou alteração de dependências.

## 1. Continuidade da ingestão

**Decisão:** manter OpenAI, `text-embedding-3-small`/1536, CPython 3.12.12 e pins existentes.
Reutilizar configuração, embeddings e validação de manifesto da 001.

**Justificativa:** a 001 registra instalação, embeddings e persistência reais aprovados.
Modelo/dimensão/pipeline identificam o espaço vetorial. Trocar modelo de resposta não
exige reindexação; trocar embeddings exige novo destino/reindexação, mesmo com dimensão igual.

**Alternativas consideradas:** segundo provedor/atualização de LangChain ampliariam
escopo sem necessidade; outro embedding de consulta invalidaria a recuperação.

**Fontes:** [guia de embeddings](https://developers.openai.com/api/docs/guides/embeddings),
[modelo](https://developers.openai.com/api/docs/models/text-embedding-3-small),
[contrato da 001](../001-pdf-ingestion/contracts/ingestion.md), `src/config.py`,
`src/vector_store.py` e `plans/validacao.md`.

## 2. Modelo de resposta e transporte

**Decisão:** `OPENAI_CHAT_MODEL=gpt-6-luna`; Chat Completions por `ChatOpenAI` 0.3.30/SDK
1.102.0, `reasoning_effort="low"`, `temperature=None`, `use_responses_api=False`,
timeout 60 s, `max_retries=0`, `max_completion_tokens=2048`. Omitir top_p/logprobs;
detectar truncamento, pois o limite também inclui raciocínio.

**Justificativa:** a documentação atual apresenta Luna como modelo eficiente para tarefas
focadas, com Chat Completions/esforço low. Com esse esforço, os parâmetros de amostragem
citados devem ser omitidos. A pilha instalada serializa esse modelo sem atualização.
Disponibilidade documentada não comprova acesso/quota da conta; gratuidade não é presumida.

**Alternativas consideradas:** GPT-4o mini e GPT-4.1 mini foram depreciados em 14/10/2026
com encerramento anunciado para 14/01/2027, portanto não serão o padrão de nova adoção.
Modelo maior só se a bateria demonstrar necessidade. Responses/ferramentas acrescentariam
diferenças desnecessárias à integração do SDK antigo.

**Fontes oficiais consultadas em 2026-10-16:**
[GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna),
[parâmetros](https://developers.openai.com/api/docs/guides/latest-model),
[descontinuações](https://developers.openai.com/api/docs/deprecations),
[ChatOpenAI 0.3.30](https://github.com/langchain-ai/langchain/blob/langchain-openai%3D%3D0.3.30/libs/partners/openai/langchain_openai/chat_models/base.py).

**Verificação executada:** Python e versões instaladas confirmados. Smoke LCEL com
modelo dublê retornou `str`. Outro smoke usou SDK real com `httpx.MockTransport`:
interceptou `/v1/chat/completions`, conferiu payload e converteu resposta simulada por
`StrOutputParser`. Timeout/zero retries e fechamento de transportes foram conferidos.
Chaves literais em dados não sofreram segunda interpretação do template.

Isso comprova construção/composição/serialização local, não aceitação pelo servidor ou
qualidade factual. A página publica o alias `gpt-6-luna`; não inventar snapshot datado.

## 3. PGVector e base existente

**Decisão:** acrescentar `open_search_store` com preflight SELECT e engine com
`default_transaction_read_only=on`, preservando abertura de escrita da ingestão.
Reutilizar `validate_manifest(actual, settings)` sem manifesto esperado.

**Justificativa:** o wheel 0.0.15 instalado mostra que o construtor chama criação de
tabelas/collection; `from_existing_index` também instancia a classe.
`create_extension=False` não desliga as demais criações. Preflight precisa conferir
extensão, tabelas, collection, manifesto, quantidade e dimensões. Ausência/vazio inicial
orienta ingestão, não gera recusa factual.

SQLAlchemy usa `MetaData.create_all(checkfirst=True)`: tabelas existentes evitam DDL.
`CollectionStore.get_or_create` retorna após SELECT se a collection existe; commit de
sessão limpa não produz DML. Remoção na janela da construção provoca rejeição de DDL/DML
pelo engine de leitura e erro operacional. Dispensa subclasse e atributos privados.

O validador existente confere versão, provedor, modelo, dimensão, hash bem formado e
pipeline sem PDF_PATH. A busca não recalcula hash nem altera manifesto. Conferir também
dimensões persistidas, pois a coluna compartilhada da 001 não fixa dimensão global.

**Alternativas consideradas:** abertura da ingestão exige manifesto esperado e permite
criação; `from_existing_index` não resolve efeitos; subclasse com métodos sobrescritos
acrescentaria acoplamento evitável; recuperação SQL própria não atende o método exigido.

**Fontes:** código instalado em `venv/lib/python3.12/site-packages/langchain_postgres/vectorstores.py`,
[release 0.0.15](https://pypi.org/project/langchain-postgres/0.0.15/),
[SQLAlchemy create_all](https://docs.sqlalchemy.org/en/20/core/metadata.html#sqlalchemy.schema.MetaData.create_all),
[PostgreSQL 17 read-only](https://www.postgresql.org/docs/17/runtime-config-client.html#GUC-DEFAULT-TRANSACTION-READ-ONLY).
Inspeção estática executada; operação protegida com banco real pendente.

## 4. Recuperação e evidência

**Decisão:** uma chamada `similarity_search_with_score(pergunta, k=10)` por pergunta.
Preservar ordem/resultados disponíveis, excluir só texto vazio/branco e concatenar
`page_content` original com `\n\n---\n\n`. Não adicionar filtro numérico.

**Justificativa:** PGVector 0.0.15 chama `embed_query`, restringe por collection e ordena
distância crescente; padrão cosseno. Proximidade não prova presença de resposta.
Recuperação vazia após inicialização válida gera recusa direta; falha de acesso é erro.

**Alternativas consideradas:** embedding manual duplicaria trabalho; retriever padrão
esconderia contrato obrigatório; limiar sem métrica/bateria validada seria arbitrário.
Reranking e verificador adicional não são necessários ao desenho mínimo.

**Fontes:** constituição II/V, spec FR-003/004/008/014 e implementação PGVector instalada.

## 5. Prompt e saída

**Decisão:** preservar `PROMPT_TEMPLATE` renderizado com regras, três exemplos e ordem do
README. Uma constante fornece a recusa. Sistema estático declara autoridade; pergunta e
contexto entram como dados somente na mensagem humana. Sem memória ou reinterpretação.

**Justificativa:** texto recuperado não recebe autoridade de sistema. O sistema explicita
insuficiência, contradição não resolvível e proibição de opiniões/conhecimento externo,
exigindo a frase sem aspas/explicações. Exemplos do enunciado não substituem evidência.

Antes de `StrOutputParser`, validar mensagem textual, não vazia, concluída, sem ferramentas
e sem recusa técnica do provedor. Truncamento (`length`), bloqueio (`content_filter`) e
formato inesperado viram erro operacional. O parser converte texto, não verifica fatos.

**Alternativas consideradas:** interpolar PDF no sistema daria autoridade indevida;
usar só o template não explicita a hierarquia; parser não certifica evidência. Papéis e
delimitadores não eliminam ataques; respostas indevidas bloqueiam aceite na bateria real.

**Fontes:** [prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering),
[validação adversarial](https://developers.openai.com/api/docs/guides/safety-best-practices),
[StrOutputParser 0.3.74](https://github.com/langchain-ai/langchain/blob/langchain-core%3D%3D0.3.74/libs/core/langchain_core/output_parsers/string.py),
README e constituição II/V/VIII.

## 6. Configuração, recursos e erros

**Decisão:** acrescentar `require_chat=False` em `load_settings` e modelo opcional em
`Settings`, obrigatório nesse fluxo. Cadeia `SearchChain` contém LCEL e `ExitStack`,
com `invoke`, `close` e protocolo de contexto; injeção por fábricas/context managers.

**Justificativa:** Runnable simples não define fechamento dos recursos possuídos pela
fábrica. A classe resolve só essa necessidade. Transportes explícitos seguem o padrão
de `embedding_session`, sem depender de coleta de lixo/atributos privados. Construção
parcial fecha recursos adquiridos; `close` é idempotente; ingestão não exige chat.

Zero retries evita cobrança duplicada automática. Traduzir exceções específicas sem
texto bruto; `SearchError.retryable` informa possibilidade de nova pergunta à 003.
Quota esgotada difere de 429 transitório; interrupções propagam para a fronteira CLI.

**Alternativas consideradas:** globals/atexit não garantem isolamento/fechamento;
alterar defaults antigos quebraria ingestão; hierarquias de repositórios são dispensáveis.

**Fontes:** `src/config.py`, testes da 001 e
[contextlib.ExitStack](https://docs.python.org/3.12/library/contextlib.html#contextlib.ExitStack).

## Pendências de execução

Não há decisão técnica sem resolução. Integração real, proteção de leitura contra
PostgreSQL, regressão e validação factual ocorrerão após tarefas/análise/implementação.
Nenhuma resposta real é declarada aprovada nesta pesquisa; bloqueios serão registrados.


## Confirmação na implementação (2026-10-16)

Fontes oficiais acima reconfirmadas. Instalação manteve todos os pins; teste com
httpx.MockTransport verificou o payload do SDK real, uma chamada de embeddings e uma
de Chat Completions, parâmetros de geração e fechamento. Execução real confirmou
acesso e alias devolvido `gpt-6-luna`, finish_reason stop. Preflight protegido PGVector
observou somente SELECTs e transaction_read_only=on. Baterias e persistência passaram;
veja `plans/validacao.md`, seção 002. Não se presume gratuidade nem qualidade universal.
