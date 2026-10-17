# Contrato — Ingestão por terminal e armazenamento

**Versão**: 1 | **Data**: 2026-10-16 | **Escopo**: [spec 001](../spec.md).
Contrato implementado e verificado; evidências em [validacao.md](../../../plans/validacao.md).

## Interface do operador

Comando obrigatório na raiz, com ambiente virtual ativo:

```bash
python src/ingest.py
```

Entrada por variáveis exportadas, `.env` e complemento opcional `.env.local`, com precedência
ambiente exportado > `.env.local` > `.env`, inclusive para valor vazio explicitamente
exportado (que deve falhar na validação se obrigatório). Resolver arquivos na raiz do
projeto, sem sobrescrevê-los; `.env.local` pode conter só a chave. Não exige argumentos,
modelo de chat, credencial Google ou execução de busca/chat.

| Variável | Obrigatória na ingestão | Regra/exemplo sem segredo |
| --- | --- | --- |
| `OPENAI_API_KEY` | Sim | Não vazia; valor real somente no ambiente, `.env` ou `.env.local` ignorados. |
| `OPENAI_EMBEDDING_MODEL` | Sim | `text-embedding-3-small`; deve aceitar dimensão explícita e estar acessível na conta. |
| `OPENAI_EMBEDDING_DIMENSIONS` | Não | Inteiro positivo; padrão `1536`; igual na ingestão/busca. |
| `DATABASE_URL` | Sim | `postgresql+psycopg://postgres:postgres@localhost:5432/rag`; senha local do Compose. |
| `PG_VECTOR_COLLECTION_NAME` | Sim | Nome não vazio; exemplo `pdf_ingestion_validation_v1`. |
| `PDF_PATH` | Sim, apenas ingestão | Arquivo local; exemplo `document.pdf`; relativo à raiz de execução. |

Configuração inválida falha antes de chamadas externas. Interpretar URL pela biblioteca;
SQL sempre parametrizado. Mensagens podem citar nomes de variáveis, nunca segredos.
As fábricas aplicam os timeouts do [plano](../plan.md).

### Saídas

- **Sucesso, código 0**: resumo em português com arquivo, páginas carregadas, chunks
  confirmados e collection. Formato previsto, sem números fictícios de execução:
  `Ingestão concluída: arquivo=<origem>; páginas=<n>; chunks confirmados=<n>; collection=<nome>`.
- **Falha, código 1**: diagnóstico via `logging` em stderr, com categoria e orientação;
  sem resumo de conclusão nem exceção bruta com conexão/cabeçalhos.
- **Interrupção**: liberar recursos sem sucesso; código 130 pode representar Ctrl+C.
  Saída normal do chat pertence à spec 003.

| Categoria | Comportamento esperado |
| --- | --- |
| Configuração | Nome da variável ausente/inválida e orientação sobre `.env`/`.env.local`. |
| PDF | Distinguir inexistência, acesso negado, formato inválido e ausência de texto; explicar limite sem OCR. |
| Banco | Orientar Compose, bootstrap, conexão/porta e timeout; não limpar dados. |
| Credencial/quota/API | Orientar revisão de credencial, acesso ao modelo, quota ou conectividade; sem confundir com PDF vazio. |
| Collection incompatível | Orientar configuração original ou novo destino/reindexação explícita. |
| Escrita/conferência | Ingestão não confirmada; quantidades só verificadas; commit incerto exige reexecução idempotente. |

## Fronteiras Python

Funções públicas têm tipos explícitos. Os nomes fixam responsabilidades para
implementação/testes, sem hierarquia de interfaces:

| Módulo/função | Entrada → saída | Efeitos/garantias |
| --- | --- | --- |
| `config.load_settings` | Fluxo requerido → configuração tipada | Carrega ambiente explicitamente; valida só o fluxo pedido, sem rede/banco. |
| `config.create_embeddings` | Configuração comum → `OpenAIEmbeddings` | Modelo, dimensão, timeout e retentativas explícitos. |
| `vector_store.open_vector_store` | Configuração, embeddings e manifesto esperado → store compatível | Extensão, engine/PGVector, leitura/validação do manifesto persistido; fechamento garantido. |
| `ingest.load_pdf_pages` | `Path` → `list[Document]` | Valida/lê PDF, rejeita integralmente vazio; preserva páginas originais. |
| `ingest.split_pages` | Páginas e identidade → chunks com IDs | Splitter real, sem I/O externo, sem chunks vazios. |
| `ingest.ingest_pdf` | Configuração e colaboradores injetáveis → resultado confirmado | Orquestra; propaga erros operacionais identificáveis. |
| `vector_store.persist_chunks` | Store, chunks e vetores → quantidade confirmada | Valida correspondência, escreve e confere registros. |
| `ingest.main` | Sem entrada programática obrigatória → `int` | Fronteira com captura ampla final, logging sanitizado e código de saída. |

Usar tipos concretos LangChain e parâmetros/fábricas para dublês. `Any` exige justificativa.
Não inicializar clientes nem carregar configuração como efeito de import.

## Escrita e preservação

Seguir [data-model.md](../data-model.md). Usar
`PGVector.add_embeddings(texts=..., embeddings=..., metadatas=..., ids=...)` 0.0.15.
Todos os vetores precedem essa chamada; validar cardinalidade para evitar truncamento
silencioso pelo `zip()` interno da integração.

Configurar `pre_delete_collection=False` e `create_extension=False`. Sem `delete_collection`,
`drop_tables`, limpeza de linhas ou remoção de volume no fluxo normal. Consultas de
conferência são delimitadas por collection e IDs, sem expor texto/vetores nos logs.

Nunca atualizar/adotar manifesto em collection existente. Criação concorrente pode falhar
por unicidade com erro acionável, sem continuar com manifesto incompatível. A proteção
cobre escritores da aplicação; SQL administrativo externo não participa desse contrato.

## Reexecução e reindexação

1. Mesmo PDF, collection e pipeline/modelo: mesmos IDs; upsert conserva contagem e relação
   texto/metadados/vetor. Pode cobrar embeddings novamente; não há cache prometido.
2. Outra collection: IDs diferentes, sem sobrescrever registros do destino anterior.
3. PDF, modelo/dimensão/pipeline diferentes ou collection legada: erro na mesma collection;
   operador escolhe novo nome e ingere integralmente no novo destino.
4. Reinício conserva volume/registros. Reindexar em nova collection conserva a anterior,
   consome espaço adicional e exige apontar a busca para a configuração correspondente.

Nenhum comando destrutivo é necessário. Limpeza futura exigirá procedimento administrativo
delimitado, efeitos documentados e validação própria, separado da execução normal.
