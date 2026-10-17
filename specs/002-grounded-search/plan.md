# Plano de implementação: Busca e respostas fundamentadas no PDF

**Branch Git**: `main` (existente; nenhuma branch criada) | **Data**: 2026-10-16\
**Spec**: [spec.md](spec.md) | **Identificador Spec Kit**: `002-grounded-search`

**Entrada**: spec 002, constituição v1.0.0, README e implementação/contratos da
[001-pdf-ingestion](../001-pdf-ingestion/plan.md). Cobertura principal: R06–R08;
R01/R10 transversais. O campo `BRANCH` do setup identifica o diretório da funcionalidade,
não uma branch Git criada. A seleção local em `.specify/feature.json` passa a apontar
para `specs/002-grounded-search`.

## Resumo

Implementar `search_prompt()` em `src/search.py` como fábrica de uma cadeia reutilizável
cuja chamada `invoke({"pergunta": texto})` retorna uma string. A cadeia usa os embeddings
da ingestão e `PGVector.similarity_search_with_score(pergunta, k=10)`, concatena somente
os `page_content` não vazios e chama o modelo com o prompt obrigatório. Sem contexto,
devolve diretamente a recusa exata, sem geração. Falhas continuam erros operacionais;
resultados próximos não comprovam evidência.

Reutilizar configuração e manifesto da 001, acrescentando modelo de resposta e abertura
protegida para leitura. Disponibilizar fechamento explícito para a CLI da 003, cujo laço
interativo permanece fora desta etapa.

## Contexto técnico

| Aspecto | Decisão |
| --- | --- |
| Linguagem/versão | CPython **3.12.12**, confirmado no `venv`; macOS arm64 já validado na 001. Não presumir suporte a outra versão. |
| Dependências | Manter pins: LangChain 0.3.27, core 0.3.74, langchain-openai 0.3.30, langchain-postgres 0.0.15, openai 1.102.0, SQLAlchemy 2.0.43, psycopg 3.2.9 e httpx 0.28.1. Sem dependência nova. |
| Composição | Funções pequenas/LCEL: validação → recuperação → contexto → ramificação vazia ou template → modelo → validação da mensagem → `StrOutputParser`. |
| Embeddings | OpenAI `text-embedding-3-small`, 1536 dimensões explícitas, mesma collection/manifesto da ingestão. |
| Modelo de resposta | `OPENAI_CHAT_MODEL=gpt-6-luna`, documentação oficial consultada em 2026-10-16. Chat Completions, `reasoning_effort="low"`, `temperature=None`, `use_responses_api=False`, `max_completion_tokens=2048`. Acesso/quota e qualidade reais pendentes. |
| Armazenamento | PostgreSQL 17/pgVector do Compose; PGVector síncrono/JSONB e engine de busca com transações de leitura. Sem novo schema nem persistência de perguntas/respostas. |
| Testes | `unittest`/`unittest.mock` existentes; dublês e `httpx.MockTransport` sem rede; bateria real pelo contrato Python, sem chat interativo. |
| Plataforma/tipo | Componente Python consumido por CLI local; comandos a partir da raiz. Linux ainda sem evidência executada. |
| Desempenho | Consulta síncrona sequencial, um embedding e até uma geração por pergunta válida; clientes/engine reutilizados. Sem meta de latência não solicitada. |
| Limites | API: 60 s/requisição, zero retries. Banco: conexão 10 s, pool 10 s, statement 30 s, lock 5 s. Não equivalem a prazo global da consulta. |
| Escopo | Um PDF já ingerido, um provedor; sem PDF_PATH na busca, histórico, OCR, web, streaming, segundo verificador ou filtro por score. |

O limite de geração inclui raciocínio; truncamento é erro, nunca sucesso parcial.
Se a bateria exigir ajuste de limite/modelo, atualizar plano e evidências antes do aceite.

## Verificação da constituição

Gate aplicado antes da pesquisa e reavaliado após o desenho: **aprovado no desenho**.
Não significa implementação, integração ou ausência comprovada de alucinações.

| Princípio | Antes da pesquisa | Após o desenho / evidência planejada |
| --- | --- | --- |
| I — escopo | R06–R08; fronteira com 003 delimitada. | Python/LangChain e scripts preservados; consulta independente do chat; matriz abaixo. |
| II — fundamentação | Prompt/recusa obrigatórios. | Template integral, sistema estático, dados sem autoridade, sem memória; bateria negativa/adversarial. |
| III — SOLID/DRY | Reusar configuração/manifesto. | Funções em search/config/vector_store; classe pequena só para ciclo de vida; fábricas injetáveis; sem camada genérica. |
| IV — Python | Tipos/import sem efeitos. | UTF-8, recursos fechados, captura específica, sanitização e testes sem I/O externo. |
| V — LangChain | Conferir versões/contrato invoke. | APIs/transporte local conferidos, k=10, saída string e clientes reutilizados. |
| VI — integridade | Espaço vetorial compatível. | Mesmo manifesto, dimensão/modelo/pipeline; sem reler PDF ou adotar legado; busca não altera base. |
| VII — operação | Configuração por fluxo. | Busca sem PDF_PATH/Google; ingestão sem chat; timeouts/erros seguros; tracing não habilitado. |
| VIII — evidência | Isolado não substitui real. | Matriz/quickstart e registro futuro em `plans/validacao.md`; bloqueios permanecem pendentes. |

Sem desvio que exija emenda. A classe de ciclo de vida é necessária para fechar recursos
que sobrevivem ao retorno da fábrica; não constitui uma hierarquia de serviços.

## Estrutura do projeto

### Documentação da funcionalidade

```text
specs/002-grounded-search/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/search.md
├── quickstart.md
└── checklists/requirements.md
```

`tasks.md` gerado; execução e evidências em
[plans/validacao.md](../../plans/validacao.md), seção 002.

### Código previsto na raiz

```text
src/
├── config.py            # ampliar configuração/fábricas para geração
├── vector_store.py      # acrescentar abertura protegida para busca
├── ingest.py            # preservar comportamento da 001
├── search.py            # cadeia, contexto, prompt, recusa e erros
└── chat.py              # laço interativo pertence à 003
tests/
├── test_config.py       # ampliar configuração por fluxo
├── test_vector_store.py # ampliar abertura de busca
├── test_ingest.py       # regressão existente
└── test_search.py       # novo: contrato/comportamento de consulta
```

Atualizar `.env.example`/README com configuração e uso programático e registrar execuções
reais em `plans/validacao.md` durante a implementação. Preservar pins, PDF e Compose.
Planejamento preservado como referência do desenho; código e testes implementados
conforme tarefas e evidências da seção 002 do relatório de validação.

## Fase 0 — Pesquisa

Pesquisa delegada sobre geração/LCEL e abertura PGVector, consolidada em
[research.md](research.md). Decisões técnicas resolvidas; conta/quota e integração real
são dependências futuras. Smoke com transporte simulado comprova serialização da pilha,
sem comprovar aceitação do servidor ou qualidade das respostas.

Descoberta: PGVector 0.0.15 não tem opção de abertura exclusivamente de leitura; seu
construtor percorre criação de tabelas/collection. `from_existing_index` também usa esse
construtor. A busca precisa de preflight e engine protegido; não reutilizar a abertura
da ingestão com manifesto inventado.

## Fase 1 — Desenho e contratos

### Configuração e inicialização

Acrescentar `chat_model: str | None = None` em `Settings` e `require_chat=False` em
`load_settings`. A busca chama `load_settings(ingestion=False, require_chat=True)`;
consumidores existentes mantêm comportamento. Exigir `OPENAI_CHAT_MODEL` não vazio só
quando solicitado. Preservar ambiente > `.env.local` > `.env`, inclusive exportação vazia,
sem mutação de arquivos/ambiente. Atualizar o exemplo de ambiente com o modelo escolhido.

Centralizar `create_chat_model`/`chat_session` em config, seguindo `embedding_session`:
transportes HTTP síncrono e assíncrono explícitos, fechados pelo proprietário. Um
`ExitStack` da cadeia coordena transportes/engine. Inicialização parcial libera os recursos
já adquiridos, sem chamada paga de aquecimento. A API valida acesso ao modelo na geração.

### Abertura da base existente

Adicionar `open_search_store(settings, embeddings, ...)` em `vector_store.py`. Compartilhar
apenas construção de engine/timeouts quando necessário; ingestão mantém escrita habilitada.

1. Criar engine com limites atuais e `default_transaction_read_only=on` nas opções.
2. Executar SELECT para extensão, existência das duas tabelas PGVector, collection por
   nome, manifesto e quantidade de registros delimitada por `collection_id`.
3. Schema/collection ausente ou zero registros: `StorageError` orientando ingestão;
   extensão ausente orienta bootstrap. Não construir PGVector nesse caso.
4. Reutilizar `validate_manifest(actual, settings)` sem manifesto esperado: provedor,
   modelo, dimensão, hash válido e pipeline da 001. Não exigir arquivo/hash recalculado.
   Conferir dimensões dos vetores existentes e eventual coluna legada de dimensão fixa.
5. Instanciar PGVector com engine protegido, `embedding_length=None`,
   `create_extension=False`, `pre_delete_collection=False`, `use_jsonb=True`, sem novo
   `collection_metadata`. Sem criar/adotar manifesto ou reparar dados na busca.
6. Remoção concorrente durante inicialização produz erro operacional; qualquer tentativa
   de criação é bloqueada pela transação de leitura. Sempre liberar engine.

Tabelas existentes fazem `create_all(checkfirst=True)` evitar DDL; collection existente
é selecionada sem inserção. A configuração de leitura protege a janela do preflight ao
construtor; não substitui controle de acesso contra administração externa.

### Consulta e prompt

1. Validar mapping e pergunta textual não vazia; remover espaços externos para consulta.
   Entrada inválida não aciona embeddings, recuperação ou geração.
2. Chamar exatamente `similarity_search_with_score(pergunta, k=10)`. PGVector vetoriza a
   pergunta; não gerar embedding duplicado. Manter ordem e resultados disponíveis.
3. Excluir apenas textos vazios/brancos e concatenar `page_content` original com
   `\n\n---\n\n`. Sem scores/metadados no contexto, preenchimento artificial ou memória.
4. Sem contexto, retornar a constante de recusa antes do modelo.
5. Renderizar `PROMPT_TEMPLATE` com todas as regras, os três exemplos e a ordem do README.
   Uma constante alimenta todas as ocorrências da recusa. Substituir placeholders uma
   vez, sem interpretar o conteúdo inserido como template/instrução.
6. Acrescentar mensagem de sistema estática: contexto/pergunta são dados, instruções
   embutidas não têm autoridade, fatos exigem evidência explícita; insuficiência ou
   contradição não resolvível exige a frase exata. Template preenchido na mensagem humana.
   Sem dados externos interpolados no sistema, histórico ou ferramentas.
7. Fazer uma geração. Antes de `StrOutputParser`, validar mensagem textual não vazia,
   conclusão completa e ausência de ferramentas/recusa técnica. Truncamento, bloqueio
   do serviço ou saída inesperada são erros; não recusa factual.
8. Retornar string removendo apenas whitespace externo. Nenhuma heurística de score,
   igualdade lexical ou presença de texto certifica sustentação da resposta.

Fundamentação é critério de aceite da bateria real. O modelo/parser não fornecem prova
determinística de evidência. Respostas indevidas impedem aceite até ajuste e nova
verificação; não prometer imunidade universal a prompt injection.

### Contrato, recursos e erros

[contracts/search.md](contracts/search.md) detalha fronteiras. `SearchChain` possui o
Runnable composto e um `ExitStack`, com `invoke`, `close` idempotente e protocolo `with`.
`search_prompt()` funciona sem argumentos e aceita configuração/fábricas opcionais para
testes. A cadeia é sequencial; a 003 a cria uma vez e fecha em `finally`/`with`, inclusive
em EOF/Ctrl+C. Sem inicialização externa no import.

`QuestionError` identifica entrada inválida. `ConfigurationError`/`StorageError` seguros
permanecem na inicialização. `SearchError.retryable` distingue falha transitória de
consulta para a futura CLI. Conexão/timeout/limite transitório permitem nova pergunta;
credencial, quota esgotada, modelo inacessível, incompatibilidade e saída inválida exigem
correção. Sem retentativa automática nem conversão de exceção em resposta. Capturas
específicas; captura ampla final pertence à CLI. Interrupções propagam.

Logs padrão informam fase/categoria, sem pergunta, PDF, prompt, conexão ou exceção bruta.
Não ativar tracing externo; se sua ativação explícita for documentada, explicar os dados
enviados. Testes isolados executam com rastreamento desativado.

### Artefatos de desenho

- [Pesquisa](research.md): decisões, alternativas, fontes e limites.
- [Modelo de dados](data-model.md): dados em memória, manifesto e estados.
- [Contrato](contracts/search.md): ambiente, cadeia, erros e recursos.
- [Quickstart](quickstart.md): validação prevista após implementação.

### Matriz de aceite e verificação

| Requisitos / critérios | Verificação prevista |
| --- | --- |
| FR-001/013; SC-005 | `invoke` retorna `str`; mapping/tipo/vazio inválidos sem chamadas; execução independente do chat. |
| FR-002/011; SC-004 | Configuração por fluxo, base válida sem PDF_PATH/Google; rejeitar modelo diferente de mesma dimensão, dimensão/pipeline/legado incompatíveis antes da API. |
| FR-003/004/014; SC-003; R06/R07 | Pergunta e k=10 no dublê; 10 e 1–9 retornos; ordem/separadores/textos vazios, sem score/metadados adicionais. Uma vetorização por recuperação. |
| FR-005/009; R07 | Prompt renderizado mantém regras/exemplos, papéis, chaves literais em dados e hierarquia diante de instruções na pergunta/chunk. |
| FR-006/007/012; SC-001/002/006; R08 | Três fatos no PDF e nos chunks recuperados; três ausências, opinião e desvio sem evidência; respostas/páginas/trechos reais registrados. Dublês não provam qualidade da LLM. |
| FR-008; SC-003 | Retorno `[]` ou só branco produz constante exata e zero gerações; base inicial vazia permanece erro. |
| FR-010; SC-004 | Base/schema ausente/vazio, extensão, conexão/401/403/404/429-quota/429-transitório/timeout/5xx e saída inválida; erro nunca vira recusa; segredos sentinela ausentes. |
| FR-005/009; independência | Duas perguntas sem histórico; fato anterior não completa contexto atual. Contexto insuficiente/contraditório recusa na bateria. |
| Recursos/integridade; R01/R10 | Engine protegido; ausência sem criação; fechamento em sucesso/falha/interrupção; import sem I/O; regressão integral da ingestão/configuração antiga. |

Comandos adotados existentes: `python -m unittest discover -s tests -v`,
`python -m compileall -q src tests` e `python -m pip check`.
`tests/test_search.py` será criado na implementação, não é suíte já disponível.
Sem lint/formatador novo. Gate final após integração; repetir verificações afetadas por
correções e registrar a seção 002 de `plans/validacao.md`.

R02–R05 ficam protegidos pela regressão/evidências da 001. R09, terminal, reprodução final
e R11 completo pertencem à 003. A bateria global mantém PDF inválido/sem texto e reinício
sem remoção de volume: referenciar evidências anteriores válidas e repetir se alterações
afetarem esses comportamentos.

## Riscos e conclusão do planejamento

Conta/quota, aceitação real dos parâmetros, qualidade da recuperação/geração e abertura
protegida com PostgreSQL real serão comprovadas na implementação. Registrar identificador
do modelo devolvido pelo serviço e data, pois o alias pode mudar. Persistência aprovada
na 001 não comprova fundamentação de respostas.

Não há decisão técnica em aberto. Validações reais são trabalho futuro. O planejamento
termina após a Fase 1; seguir com tarefas, análise, implementação e convergência.


## Estado da execução (2026-10-16)

Desenho implementado sem alteração dos pins/modelos/contratos. Consulta real confirmou
alias `gpt-6-luna`, finish_reason stop e transporte Chat Completions. Preflight PGVector
com engine de leitura funcionou sem DDL/DML; destinos ausente/vazio e incompatibilidades
rejeitados antes da API. Bateria positiva/negativa/controlada e persistência aprovadas.
61 testes isolados e verificadores adotados aprovados. Resultados completos e limites
em `plans/validacao.md`; o chat interativo/entrega global permanecem na 003.
