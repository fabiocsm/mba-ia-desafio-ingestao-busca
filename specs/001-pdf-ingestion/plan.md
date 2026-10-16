# Plano de implementação: Ingestão e persistência do PDF

**Branch Git**: `main` (existente; nenhuma branch criada) | **Data**: 2026-10-16
**Spec**: [spec.md](spec.md) | **Identificador Spec Kit**: `001-pdf-ingestion`

**Entrada**: especificação e [plano inicial](../../plans/plano-implementacao.md), etapas 1–2
e partes de ingestão das etapas 5–6. O campo `BRANCH` do setup identifica a funcionalidade
pelo diretório; não representa uma branch Git criada.

## Resumo

Preparar o ambiente Python/LangChain e ingerir um PDF com texto extraível no PostgreSQL 17
com pgVector, usando o Compose fornecido. Ler páginas com `PyPDFLoader`, dividir com
`RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150, length_function=len)`,
gerar embeddings OpenAI e persistir texto, vetor, origem, página e identificador por chunk.

A configuração compartilhada e um manifesto imutável por collection impedirão mistura
de modelos, inclusive de mesma dimensão. IDs determinísticos permitirão repetir a mesma
ingestão sem duplicar registros. Falhas produzirão diagnóstico sem segredos e saída
diferente de zero; nenhuma execução normal apaga dados.

Busca, prompt, modelo de resposta e interação pertencem às specs 002 e 003. Esta spec
entrega seu contrato de dados, sem implementar nem declarar validado o chat.

## Contexto técnico

| Aspecto | Decisão |
| --- | --- |
| Linguagem/versão | CPython **3.12.12**, validado em macOS arm64 durante a pesquisa. Python 3.14.5 do host não aprovado por presunção; ver [research.md](research.md). |
| Dependências | Preservar `requirements.txt`: LangChain 0.3.27, community 0.3.27, core 0.3.74, text-splitters 0.3.9, langchain-openai 0.3.30, langchain-postgres 0.0.15, pypdf 6.0.0, psycopg 3.2.9 e SQLAlchemy 2.0.43. Instalação dos 75 pins e `pip check` aprovados em ambiente temporário. |
| Provedor | OpenAI, confirmado pelo usuário após o planejamento. Credencial fornecida em `.env.local`, sem validação de acesso/quota nesta etapa. Gemini já consta dos requisitos, mas não será implementado. |
| Embeddings | `text-embedding-3-small`, 1536 dimensões explícitas, via `OpenAIEmbeddings`. Disponibilidade documentada oficialmente; acesso/quota da conta ainda requerem validação real. |
| Armazenamento | `pgvector/pgvector:pg17`, volume `postgres_data`, `PGVector` síncrono, driver `postgresql+psycopg://`, JSONB. Coluna vetorial sem dimensão global fixa; dimensão validada por collection. |
| Testes | `unittest` e `unittest.mock` da biblioteca padrão. Integração manual com banco/provedor reais em collection exclusiva de validação. |
| Plataforma/tipo | CLI local em macOS/Linux com Docker e Compose; comandos a partir da raiz. Apenas macOS teve a compatibilidade executada nesta pesquisa. |
| Desempenho | Um PDF em memória, sem meta de latência não solicitada. Gerar todos os vetores antes de uma chamada de persistência. |
| Limites operacionais | API: timeout de 60 s por requisição e `max_retries=0`. Banco: conexão de 10 s, `statement_timeout=30000`, `lock_timeout=5000`, espera de pool de 10 s. Sem retentativa automática de gravação. |
| Escopo | Uma origem por collection, um provedor; sem OCR, web, múltiplos PDFs na mesma collection, chat ou arquitetura genérica de repositório. |

## Verificação da constituição

Gate aplicado antes da pesquisa e reavaliado após o desenho. **Aprovado no desenho**;
isso não significa implementação ou aceite operacional aprovado.

| Princípio/restrição | Antes da pesquisa | Após o desenho / evidência planejada |
| --- | --- | --- |
| I — escopo/requisitos | R02–R05, com R01/R10 transversais. | Python, LangChain, Compose, scripts e PDF mantidos; matriz de aceite abaixo. |
| II — fundamentação | Busca/respostas fora desta spec. | Prompt do README e `search.py` preservados; sem geração de respostas nesta etapa. |
| III — SOLID/DRY | Funções e composição suficientes. | `config.py` centraliza configuração/clientes; `vector_store.py` isola manifesto/persistência para reúso na 002; CLI sem SQL. |
| IV — Python | Contratos tipados, inicialização explícita. | `pathlib`, UTF-8, recursos fechados, exceções específicas, dependências injetáveis, sem conexões/APIs no import. |
| V — compatibilidade | Conferir versões antes da integração. | APIs pesquisadas, imports executados, timeouts finitos; sem atualizar a pilha por conveniência. |
| VI — integridade | Metadados, splitter e preservação obrigatórios. | Manifesto imutável, dimensão validada, IDs por collection, teste de reingestão e reinício preservando volume. |
| VII — operação segura | Exigir somente variáveis do fluxo. | Ingestão sem modelo de chat/chave Google; logging sem senha, chave, PDF ou prompt; tracing externo não habilitado implicitamente. |
| VIII — evidência | Separar testes isolados de integração. | Matriz de testes e quickstart; bloqueios reais permanecerão pendentes no relatório. |

Sem desvios que exijam emenda à constituição. A adoção de IDs determinísticos torna o
teste de idempotência parte do aceite técnico desta implementação, preservando o caráter
de recomendação na constituição e na especificação.

## Estrutura do projeto

### Documentação da funcionalidade

```text
specs/001-pdf-ingestion/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/ingestion.md
└── checklists/requirements.md
```

`tasks.md` será produzido por `$speckit-tasks` após este planejamento.

### Código previsto na raiz

```text
src/
├── config.py           # configuração e composição dos clientes
├── vector_store.py     # manifesto, acesso ao PGVector e confirmação da escrita
├── ingest.py           # leitura, divisão, orquestração e fronteira main
├── search.py           # preservado; implementação na 002
└── chat.py             # preservado; implementação na 003
tests/
├── test_config.py
├── test_ingest.py
└── test_vector_store.py
```

Preservar `docker-compose.yml`, `requirements.txt`, `.env.example`, `document.pdf` e
`README.md`. Atualizar exemplo de ambiente e instruções de ingestão na implementação.
`plans/validacao.md` receberá resultados reais e bloqueios durante a verificação.

**Justificativa**: `vector_store.py` atende FR-010 e permite à busca conferir o mesmo
manifesto sem importar a CLI. Não criar serviço web, ORM próprio, camada de repositórios,
hierarquias de adaptadores nem dependências de teste adicionais.

## Fase 0 — Pesquisa e decisões

[research.md](research.md) registra decisões, fontes, alternativas e resultados de pesquisa.
Não restam decisões técnicas pendentes de esclarecimento. Credencial, quota e integração
real são pré-condições de execução, não decisões de desenho em aberto.

Precisão frente à explicação geral do README: nesta versão do PGVector, `embedding_length`
fixa a dimensão da **tabela compartilhada**, não de uma collection isolada. Usar
`embedding_length=None`, sem índice ANN, com proteção explícita por collection. Não confiar
numa falha automática do banco para detectar troca de modelo. Na documentação da solução,
preservar o enunciado e explicar essa particularidade e a reindexação obrigatória.

## Fase 1 — Desenho e contratos

### Configuração e composição

Carregar `.env` e o complemento opcional `.env.local` explicitamente na inicialização,
com precedência ambiente exportado > `.env.local` > `.env`. Combinar os valores sem
sobrescrever arquivos ou manter estado global mutável compartilhado. `.env.local` pode
conter somente a chave; os demais valores continuam em `.env` ou no ambiente. Validar
os valores comuns (`OPENAI_API_KEY`, `OPENAI_EMBEDDING_MODEL`, `DATABASE_URL`,
`PG_VECTOR_COLLECTION_NAME`) e, apenas na ingestão, `PDF_PATH`.
`OPENAI_EMBEDDING_DIMENSIONS` é opcional, padrão 1536, inteiro positivo e enviado
explicitamente ao modelo escolhido. Mudança de modelo/dimensão exige novo destino ou
reindexação, mesmo com dimensões iguais. Validação local não comprova autorização da API.

Criar engine/clientes após validar configuração e PDF. Confirmar extensão `vector` e
construir `PGVector` com `create_extension=False`, `pre_delete_collection=False`,
`embedding_length=None` e `use_jsonb=True`. O bootstrap do Compose cria a extensão.
Um cliente de embeddings e um engine por execução, liberados em `finally`/context manager.
SQLAlchemy deve usar `echo=False`, `hide_parameters=True` e os timeouts definidos acima;
erros não podem despejar SQL com parâmetros ou a URL de conexão. Não habilitar LangSmith
implicitamente; configuração explícita futura exigirá documentação dos dados enviados.

### Sequência da ingestão

1. Validar caminho local com `Path`, arquivo regular, extensão `.pdf` sem distinção de
   caixa e leitura; extrair páginas com `PyPDFLoader(mode="page", extract_images=False)`.
2. Contar todas as páginas carregadas, filtrar páginas sem texto e rejeitar documento
   integralmente vazio. Preservar número original, sem renumerar após filtrar.
3. Dividir páginas com o splitter obrigatório, filtrar chunks em branco e acrescentar
   metadados/IDs definidos em [data-model.md](data-model.md). Não preencher tamanho ou
   sobreposição artificialmente. Conferir estabilidade do arquivo usado na extração/hash.
4. Criar collection com manifesto esperado se ausente e **reler o manifesto persistido**;
   `collection_metadata` não atualiza collection existente. Rejeitar manifesto ausente
   ou incompatível antes de gerar embeddings. Corrida na criação causa erro acionável,
   nunca continuidade sem validação.
5. Gerar embeddings apenas de chunks não vazios; validar quantidade, dimensão e valores
   finitos de todos os vetores. Não persistir conjunto incompleto.
6. Chamar `PGVector.add_embeddings` uma vez com textos, vetores, metadados e IDs explícitos.
   Conferir IDs retornados, registros e dimensões persistidas antes de anunciar quantidade.
   `get_by_ids` não garante ordem; comparar por ID. SQL de conferência fica no módulo
   de armazenamento, com parâmetros.
7. Emitir resumo: arquivo, páginas carregadas, chunks confirmados e collection. Liberar
   recursos. Tentativas/vetores gerados não equivalem a gravações confirmadas.

O manifesto registra versão do contrato, provedor, modelo, dimensão, SHA-256 do PDF e
assinatura da extração/divisão. É imutável, mesmo se a collection estiver vazia. PDF ou
configuração alterados usam nova collection nomeada explicitamente pelo operador.
Collection legada sem manifesto não é adotada automaticamente.

Desconexão durante commit pode deixar resultado indeterminado: informar falha sem afirmar
rollback ou sucesso. Reexecutar com os mesmos IDs é a recuperação prevista. O mesmo vale
para falha na conferência após commit. Não prometer atomicidade entre API e PostgreSQL.

### Artefatos de desenho

- [Modelo de dados](data-model.md): entidades, metadados, manifesto e IDs.
- [Contrato](contracts/ingestion.md): ambiente, CLI, fronteiras e erros.
- [Quickstart](quickstart.md): preparação, validação real e resultados esperados.

### Matriz de aceite e verificação

| Requisitos | Verificação prevista | Critério de sucesso |
| --- | --- | --- |
| R01, R10; FR-001/011 | Instalação no Python validado; imports; comandos da raiz; configuração sem chat/Google. | SC-004 |
| R02; FR-002 | Compose saudável, bootstrap com saída 0, extensão `vector`. | SC-001/004 |
| R03; FR-003/008 | PDF real; arquivo ausente, extensão incorreta, corrupção, sem texto, páginas vazias/curtas. Dublês para parsing e amostras locais. | SC-001/003 |
| R04; FR-004 | Splitter real em texto longo, português, parágrafos e página curta; tamanho, sobreposição possível, metadados e ausência de vetores vazios. | SC-005 |
| R05; FR-005/006 | Dublês de API/banco: associação de vetores, metadados, IDs, dimensão, escrita e resumo. Banco real: comprovar ausência da collection antes da primeira ingestão, sem limpar destino existente; depois, inspeção completa sem chat. | SC-001/005 |
| R05; FR-007/009 | Comparar quantidade e assinatura de texto, vetores e metadados antes/depois do reinício, sem reingestão nem remoção de volume. | SC-002 |
| FR-008 | Variáveis ausentes, 401, quota, timeout, conexão, falha antes/depois de commit/conferência; saída não zero e sem segredos/sucesso indevido. | SC-003 |
| FR-009/010 | Manifesto ausente, modelo diferente com mesma dimensão, dimensão divergente, PDF alterado: erro sem embedding/escrita/limpeza. Manifesto real, inclusive na criação concorrente. | SC-003 |
| IDs adotados | Duas ingestões iguais: mesmos IDs/contagem; outra collection: IDs disjuntos e destino anterior intacto. | Aceite técnico adicional |
| FR-011; parcela R11 | README, `.env.example`, reindexação, limitações e ambiente novo reproduzíveis. | SC-004 |

R06–R08 pertencem à 002; R09 à 003. R11 completo, revisão global R01–R11 e visibilidade
pública ficam na entrega do fluxo completo, sem marcá-los atendidos nesta etapa.

Comandos futuros: `python -m unittest discover -s tests -v` e
`python -m compileall -q src tests`, após criação da suíte. Não há testes da aplicação
implementados neste planejamento. Não acrescentar lint/formatador sem necessidade.

Execuções antecipadas da suíte servem para diagnóstico. O gate final de qualidade ocorre
após as validações integradas de US2/US3 e suas correções; testes e verificações afetados
devem ser repetidos se houver alteração posterior de código. Integração bloqueada mantém
o gate final pendente, mesmo com testes isolados aprovados.

## Riscos e conclusão

Credencial/quota, provedor real e persistência ainda devem ser verificados e registrados
em `plans/validacao.md` na implementação. Bloqueios mantêm a verificação pendente.
Atualizações de modelo, dependências, schema ou splitter exigem rever manifesto,
contratos e evidências antes de reutilizar uma collection.

O planejamento encerra na Fase 1. Próximos passos: `tasks.md`, análise de consistência,
implementação e convergência. Gates documentais não substituem essas etapas.
