# Tarefas: Busca e respostas fundamentadas no PDF

**Entrada**: artefatos em `specs/002-grounded-search/`: [spec.md](spec.md),
[plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md),
[contrato](contracts/search.md) e [quickstart.md](quickstart.md).
**Data**: 2026-10-16 | **Branch Git**: `main` | **Spec ativa**: `002-grounded-search`.

**Pré-requisitos**: ingestão da 001 implementada; respeitar README e constituição v1.0.0.
Antes de implementar, executar `$speckit-analyze` sobre spec/plan/tasks e resolver conflitos
bloqueantes. Esta geração não executa tarefas, testes ou integração da funcionalidade.

**Testes**: requeridos por FR-012, pelos testes independentes/SC-001–SC-006 da spec e
pela constituição VIII. Escrever os testes de cada comportamento antes de implementá-lo,
confirmar a falha pertinente e então implementar. Testes isolados não usam rede, banco,
credencial real, custo ou tracing; somente integração explicitamente identificada usa serviços.

**Formato**: `- [ ] Tnnn [P?] [USn?] descrição com caminho`. `[P]` permite trabalho paralelo
somente nos lotes descritos em dependências, com arquivos distintos. Rótulos US1/US2/US3
correspondem às histórias da spec. Caminhos são relativos à raiz. Todos os itens começam
pendentes; marcar concluído só após executar e registrar sua verificação.

## Fase 1: Preparação compartilhada

**Objetivo**: confirmar a base existente sem refazer inicialização ou alterar dependências
por conveniência. Não abrir arquivos de segredo para impressão nem modificar a seleção ativa.

- [ ] T001 Confirmar CPython 3.12.12 no ambiente virtual e versões de `requirements.txt`; executar a suíte existente `python -m unittest discover -s tests -v`, `python -m compileall -q src tests` e `python -m pip check`, registrando baseline e ambiente na nova seção 002 de `plans/validacao.md`, sem declarar a busca implementada.
- [ ] T002 Reconfirmar antes da integração os parâmetros/modelos escolhidos e APIs das versões instaladas, usando as fontes oficiais e a inspeção local indicadas em `specs/002-grounded-search/research.md`; manter OpenAI, `text-embedding-3-small`/1536, `gpt-6-luna`/low e pins de `requirements.txt` salvo incompatibilidade demonstrada; atualizar research/plan/contrato se houver descoberta material, sem inferir acesso/quota da conta.
- [ ] T003 Acrescentar `OPENAI_CHAT_MODEL=gpt-6-luna` a `.env.example`, preservando as variáveis da ingestão, exemplos públicos sem segredos e os arquivos locais; conferir que nenhuma instrução exige chave Google ou mudança de embeddings para adotar o modelo de resposta.

## Fase 2: Fundação — configuração e leitura da base

**Objetivo**: fornecer dependências compartilhadas a todas as histórias, sem efeitos no
import nem criação de base pela consulta. Esta fase bloqueia a implementação das histórias.

### Testes da fundação

- [ ] T004 [P] Ampliar `tests/test_config.py` com contratos de configuração por fluxo e fábrica/sessão de geração: busca exige chat e não PDF_PATH/Google; chamadas antigas e ingestão não exigem chat; precedência ambiente > `.env.local` > `.env`, exportação vazia, repr seguro, opções do modelo/timeout/zero retries, construção sem API e fechamento dos dois transportes inclusive em falha; confirmar falhas antes de T006.
- [ ] T005 [P] Ampliar `tests/test_vector_store.py` com contratos de `open_search_store`: preflight válido sem PDF, ausência/vazio/incompatibilidade antes da fábrica PGVector/API, dimensões dos vetores, engine de leitura, opções sem criação de extensão/exclusão e liberação em falha/sucesso; provar com dublês que a abertura de ingestão conserva escrita e confirmar falhas antes de T007.

### Implementação da fundação

- [ ] T006 [P] Ampliar `src/config.py` sem quebrar consumidores: adicionar ao final de Settings `chat_model: str | None = None` e `require_chat=False` em load_settings; aplicar literalmente as restrições de `data-model.md`: api_key “`str` não vazia; segredo, excluído de repr/logs.”, embedding_model “`str` não vazia; igualdade com o manifesto.”, embedding_dimensions “`int` positivo, padrão 1536; igualdade com manifesto/vetores.”, database_url “URL `postgresql+psycopg://` válida; segredo, excluído de repr/logs.”, collection_name “`str` não vazia, destino explícito compartilhado com ingestão.”, pdf_path “`None` na busca; não ler/validar o arquivo de origem.” e chat_model “`str` não vazia quando `require_chat=True`; exemplo `gpt-6-luna`.”; validar formatos localmente e realizar as igualdades com manifesto/vetores em T007, sem acesso ao banco na configuração; implementar create_chat_model/chat_session com ChatOpenAI, esforço low, temperature=None, use_responses_api=False, max_completion_tokens=2048, timeout=60 e max_retries=0, com transportes explícitos fechados e leitura de ambiente sem mutação.
- [ ] T007 [P] Implementar `open_search_store` em `src/vector_store.py`, preservando `open_vector_store`: SELECT parametrizado para extensão/tabelas/collection/manifesto/contagem/dimensões antes da fábrica; respeitar “Um nome/UUID existente, referente a uma revisão de um PDF; deve ter registros na inicialização.”, “JSONB imutável, `schema_version=1`, `provider=openai`, modelo/dimensão de embeddings, SHA-256 e pipeline da 001.” e “Conferir que todos os vetores da collection têm a dimensão configurada; não confiar só no tamanho da coluna compartilhada.”; reutilizar validate_manifest sem manifesto esperado/PDF, rejeitar legado/incompatibilidade, configurar default_transaction_read_only=on, timeouts de conexão/pool 10 s, statement 30 s e lock 5 s, PGVector com embedding_length=None/create_extension=False/pre_delete_collection=False/use_jsonb=True e sem manifesto novo; liberar engine e traduzir SQLAlchemyError em StorageError seguro, inclusive corrida de criação bloqueada, sem reparar/criar/apagar dados.
- [ ] T008 Executar os testes de fundação/regressão de `tests/test_config.py`, `tests/test_vector_store.py` e `tests/test_ingest.py` sem serviços; registrar em `plans/validacao.md` as falhas iniciais pertinentes e a aprovação posterior de T004–T007, incluindo ausência de exigência de chat na ingestão e preservação do contrato de escrita.

**Checkpoint**: configuração e abertura protegida utilizáveis com dublês; operação com
PostgreSQL real ainda depende das verificações integradas. Não criar novas tabelas/migrations.

## Fase 3: US1 — Obter resposta sustentada pelo documento (P1) — MVP técnico

**Objetivo**: consultar a base pelo contrato Python, recuperar até dez textos e gerar
resposta sobre evidência explícita, sem interface interativa ou fatos de perguntas anteriores.

**Teste independente**: cadeia com dublês comprova k=10, contexto/prompt/saída e recursos;
base/provedor reais respondem corretamente a três perguntas, cada fato conferido no PDF
e nos chunks da própria consulta. Resultados em `plans/validacao.md`.

### Testes e preparação da história

- [ ] T009 [P] [US1] Criar `tests/test_search.py` com testes de contrato de retrieve_documents/format_context/build_search_pipeline/search_prompt: chamada exata com pergunta e k=10, uma vetorização no transporte dublê, 10 e 1–9 retornos, ordem/Unicode/textos originais, template com todas as regras/três exemplos, substituição única de chaves literais, invoke retornando str, validação básica antes de consulta, duas invocações sem histórico, fábricas injetáveis, reutilização e fechamento em sucesso/falha parcial/interrupção; confirmar falhas antes de T011–T013, sem rede/credencial/ambiente local.
- [ ] T010 [P] [US1] Preparar os casos afirmativos P1–P3 do quickstart em `plans/validacao.md`, conferindo diretamente `document.pdf` e seu hash: faturamento da Alfa Agronegócio Indústria na página 1, fundação da Atlas Biotech S.A. na página 2 e faturamento da SuperTechIABrazil na página 3; registrar pergunta/valor esperado/trecho/página humana e base zero, sem marcar resposta ou recuperação como aprovadas.

### Implementação da história

- [ ] T011 [US1] Implementar retrieve_documents e format_context em `src/search.py` usando `list[tuple[Document, float]]`, sem DTO ou embedding manual; aplicar “Única contribuição factual ao contexto; excluir se vazio/branco.” para page_content e “Preservar a ordem retornada, inclusive quando menos de dez resultados.”; chamar similarity_search_with_score(pergunta, k=10), verificar branco com strip sem reescrever textos aceitos, unir por `\n\n---\n\n` e não incluir scores/metadados ou limiar numérico; manter IDs/origem/página disponíveis para conferência, com “página do loader é base zero, página humana é +1”.
- [ ] T012 [US1] Implementar em `src/search.py` a constante única de recusa e PROMPT_TEMPLATE com texto/regras/três exemplos/ordem do README, mais a composição LCEL do caminho com contexto em build_search_pipeline: pergunta atual/contexto → template → modelo injetado → conversão textual; manter separadas as etapas e os pontos de validação/ramificação previstos no contrato, sem histórico, ferramentas ou reinterpretação dos dados como template; não apresentar o parser como prova factual.
- [ ] T013 [US1] Implementar SearchChain/search_prompt em `src/search.py` com retorno utilizável sem argumentos, configuração opcional e fábricas de sessões injetáveis, ExitStack/propriedade de recursos e invoke tipado; aplicar “mapping com a chave única `pergunta`, de valor `str` não vazio após `strip()`”, rejeitar extras sem consulta, preservar conteúdo interno e declarar QuestionError/SearchError; oferecer close idempotente/protocolo with, falhar antes de I/O se fechada, construir clientes/engine uma vez sem aquecimento pago, liberar construção parcial e propagar interrupções; sem inicialização no import ou captura ampla.
- [ ] T014 [US1] Executar os casos US1 em `tests/test_search.py` com a regressão da fundação, conferindo tipos/retorno string, contexto, prompt, ausência de memória e recursos; registrar resultados e comandos em `plans/validacao.md`, distinguindo aprovação de composição com dublês de fundamentação real ainda pendente.
- [ ] T015 [US1] Documentar em `README.md` a configuração OPENAI_CHAT_MODEL e uso programático `with search_prompt() as chain`/invoke, incluindo import pela raiz, fechamento explícito, custos e limites do modelo; preservar enunciado/comandos e deixar claro que o chat interativo de `src/chat.py` continua na 003.
- [ ] T016 [US1] Executar P1–P3 pelo contrato de `src/search.py` com PostgreSQL/pgVector, PDF e provedor reais conforme `specs/002-grounded-search/quickstart.md`; registrar em `plans/validacao.md` ambiente/versões, comandos, collection, embeddings/dimensão, modelo solicitado/devolvido, perguntas/respostas e IDs/trechos/páginas efetivamente recuperados, capturando a mesma execução com observação local/fábrica injetada se necessário; conferir cada fato sem acréscimos, recusar se a evidência não veio no contexto e manter SC-001 pendente até corrigir recuperação/geração e repetir os casos afetados.

**Checkpoint**: US1 demonstrável sem chat. Aprovação factual exige T016. O MVP técnico
não representa entrega completa: recusa/segurança de US2 e operação de US3 continuam
obrigatórias antes de declarar a spec validada.

## Fase 4: US2 — Receber recusa quando falta evidência (P1)

**Objetivo**: recusar insuficiência, opinião e desvio sem evidência, inclusive com retornos
próximos, e não gerar quando não há texto recuperado.

**Teste independente**: três perguntas sem resposta, uma opinião e uma tentativa de
desvio retornam a frase exata com modelo/base reais; dublês comprovam lista vazia/só
branco com zero gerações. Fixtures adversariais e contraditórias não ampliam autoridade
dos dados nem criam memória factual.

### Testes e preparação da história

- [ ] T017 [P] [US2] Ampliar `tests/test_search.py` com casos US2 antes de T019–T020: []/só branco/mistura de textos, retorno exato sem chamada de geração, resultados próximos sem resposta, recusa textual preservada, opinião, instruções em pergunta/chunk, headings/chaves literais, contradição não resolvível e ausência de fato citado antes; conferir mensagens e hierarquia com dublês, sem atribuir a eles prova de resistência do modelo real.
- [ ] T018 [P] [US2] Preparar os casos N1–N3/O1/A1 e fixtures controladas em `plans/validacao.md`, usando `document.pdf`/quickstart: confirmar ausência de CNPJ da Alfa, número de funcionários da Atlas e clientes em 2024, registrar opinião/desvio e recusa esperada exata; definir também contexto contraditório, fato ausente da recuperação e instrução em chunk para validação do modelo sem alterar a collection real.

### Implementação da história

- [ ] T019 [US2] Completar a ramificação sem contexto em build_search_pipeline de `src/search.py`, antes do modelo/parser, retornando exatamente `Não tenho informações necessárias para responder sua pergunta.` a partir da constante compartilhada; tratar somente retorno sem texto útil como vazio, sem converter falha do banco/API ou base inicialmente inválida em recusa.
- [ ] T020 [US2] Acrescentar/consolidar a mensagem de sistema estática em `src/search.py`: contexto/pergunta são dados sem autoridade, só fatos explícitos, sem opinião/conhecimento externo/histórico, recusa exata sem aspas/explicações para insuficiência/contradição não resolvível; manter o PROMPT_TEMPLATE integral preenchido na mensagem humana e não interpolar chunks/pergunta no sistema; não usar score, presença de texto ou igualdade lexical como certificação de evidência.
- [ ] T021 [US2] Executar testes US1/US2 de `tests/test_search.py` após T019–T020, comprovando zero gerações em contexto vazio e nenhuma contaminação entre perguntas, e registrar resultados em `plans/validacao.md`; corrigir desvios de composição antes da integração sem trocar indevidamente resposta/erro por recusa.
- [ ] T022 [US2] Executar N1–N3/O1/A1 com base e modelo reais e registrar em `plans/validacao.md` perguntas, respostas literais, resultados recuperados, modelos e comparação à frase obrigatória; validar também com modelo real/contexto controlado instrução em chunk, contradição e fato fora do contexto, sem inserir fixtures na base do PDF; resposta indevida impede aceite e exige correção/reexecução dos casos afetados, sem afirmar proteção universal contra alucinações/injeção.

**Checkpoint**: US2 exige T021 e T022; recusa sem contexto é demonstrada isoladamente
sem apagar dados para simular desaparecimento. Não tratar collection vazia inicial como recusa.

## Fase 5: US3 — Identificar impedimentos de consulta (P2)

**Objetivo**: distinguir impedimentos de falta de informação e orientar correção, preservando
segredos e a independência da busca em relação ao PDF original/provedor não utilizado.

**Teste independente**: configuração inválida, collection ausente/vazia/incompatível,
pergunta inválida e falhas simuladas de banco/geração retornam exceções acionáveis;
nenhum caso é recusa ou resposta parcial. Base válida continua consultável sem PDF_PATH/Google.

### Testes da história

- [ ] T023 [P] [US3] Ampliar `tests/test_config.py` com matriz US3 de campos ausentes/brancos/URL/dimensão inválidos e chave/modelo chat por fluxo, mantendo as restrições literais de T006; comprovar ausência de leitura do PDF e exigência de Google, ambiente sem mutação e segredo sentinela ausente de repr/mensagens; testar import de config/search sem carregar ambiente ou construir clientes, preservando os testes antigos.
- [ ] T024 [P] [US3] Ampliar `tests/test_vector_store.py` com matriz US3 de extensão/schema/collection ausente, zero chunks, manifesto ausente/legado/schema_version/provider/hash/pipeline inválidos, modelo diferente com mesma dimensão, dimensões de vetores divergentes e coluna legada incompatível; comprovar erro antes da API/fábrica, SELECT delimitado, corrida/timeout com engine de leitura sem criação/limpeza, erro sanitizado e fechamento, mantendo escrita da ingestão; respeitar “ID, texto, embedding, origem, página e demais metadados da 001; não alterar na busca.”.
- [ ] T025 [P] [US3] Ampliar `tests/test_search.py` com matriz US3 antes de T026–T028: mapping/chave extra/tipo/texto inválidos e cadeia fechada sem serviços, timeout/conexão/429 transitório/5xx versus 401/403/modelo inacessível/quota esgotada, falhas SQL/collection removida, mensagem vazia/não textual/ferramentas/recusa técnica/finish_reason interrompido, segredos sentinela e interrupções; conferir retryable, ausência de recusa/retorno parcial e possibilidade de nova pergunta após entrada inválida/falha transitória.

### Implementação da história

- [ ] T026 [US3] Completar a tradução de exceções específicas do SDK/SQLAlchemy em `src/search.py` para SearchError sanitizado com a restrição “`retryable: bool`, nunca string factual.”: timeout/conexão/429 transitório/5xx são recuperáveis; credencial/acesso/modelo/quota esgotada/incompatibilidade exigem correção; diferenciar quota pelo código estruturado, fornecer ação sem valores brutos, manter QuestionError para entrada inválida e propagar falhas inesperadas/interrupções, sem except Exception ou retries automáticos.
- [ ] T027 [US3] Implementar validação da mensagem antes de StrOutputParser em `src/search.py`: “tipo textual esperado, conteúdo não vazio, sem ferramentas, recusa técnica ou conclusão interrompida”; exigir AIMessage textual com finish_reason=stop, rejeitar length/content_filter/tool/function calls/recusa técnica/formato inesperado como SearchError(retryable=False), retornar somente string com whitespace externo removido e preservar recusa factual exata sem acrescentar conteúdo.
- [ ] T028 [US3] Revisar diagnóstico/logging em `src/search.py`, `src/config.py` e `src/vector_store.py` para mensagens portuguesas acionáveis, capturas específicas e causas externas não expostas em traceback/mensagem padrão; não registrar chave/URL com senha, SQL com parâmetros, pergunta/PDF/prompt completos ou ativar tracing; manter o significado dos erros de inicialização e não capturar interrupção como falha factual.
- [ ] T029 [US3] Executar as matrizes US3 em `tests/test_config.py`, `tests/test_vector_store.py` e `tests/test_search.py`, além da regressão das outras histórias; comprovar mensagens/atributos/recursos e sequência falha transitória → nova pergunta, registrando resultados em `plans/validacao.md` sem simular resposta factual de erro ou anunciar chat implementado.
- [ ] T030 [US3] Validar a abertura protegida contra PostgreSQL real conforme `specs/002-grounded-search/quickstart.md`: confirmar por SELECT nome ausente antes/depois de tentativa de busca; criar explicitamente somente novo destino vazio de validação com manifesto compatível e conferir erro de ingestão/contagem zero; confirmar transações de leitura e ausência de alterações em contagem/manifesto/IDs da base válida, sem DDL/DML da busca ou remoção de dados; registrar comandos/resultados em `plans/validacao.md`, mantendo validação pendente se bloqueada.
- [ ] T031 [US3] Validar configuração incompatível em processos isolados contra a base real, inclusive modelo diferente com mesma dimensão e dimensão divergente, antes de qualquer chamada paga; demonstrar consulta válida com PDF_PATH inexistente/ausente e sem chave Google, sem remover o arquivo versionado; registrar orientações, respostas/evidências, nenhuma mutação e limitações em `plans/validacao.md`, preservando a configuração local original.

**Checkpoint**: US3 requer matrizes e abertura real verificadas. Chave/modelo de geração
inválido pode ser detectado só na primeira geração; não adicionar aquecimento pago para
prometer validação de acesso na construção. A política de saída/códigos da CLI é da 003.

## Fase 6: Documentação, regressão e encerramento da spec

**Objetivo**: consolidar resultados e executar os gates depois das correções da integração,
preservando tarefas de verificações bloqueadas em aberto.

- [ ] T032 Atualizar `README.md` e `specs/002-grounded-search/quickstart.md` conforme o comportamento efetivamente implementado: configuração por fluxo/precedência, uso e fechamento da cadeia, erros/limites, modelos efetivamente validados, respostas/recusas reais, diagnóstico e reindexação; preservar prompt/enunciado/estrutura/ordem de execução, documentar que tracing externo só pode ser ativado explicitamente com os dados enviados, sem habilitá-lo, e manter o laço do chat/entrega global pendentes na 003.
- [ ] T033 Verificar regressão integrada das mudanças compartilhadas de `src/config.py` e `src/vector_store.py` conforme `specs/001-pdf-ingestion/quickstart.md`: ingestão mantém escrita/configuração sem chat, PDF inválido/sem texto continua falhando sem API indevida e destino preservado, repetir idempotência se o caminho de escrita mudou; reiniciar postgres sem remover volume e consultar em novo processo sem reingerir, comparando contagem/manifesto/IDs e resposta sustentada; registrar execução ou referência válida da 001 com justificativa e bloqueios em `plans/validacao.md`.
- [ ] T034 Após integrações e correções, executar `python -m unittest discover -s tests -v`, `python -m compileall -q src tests` e `python -m pip check`; revisar tipagem pública, responsabilidades, DRY e recursos de `src/search.py`, `src/config.py` e `src/vector_store.py`; registrar gate final em `plans/validacao.md`, repetindo verificações afetadas por alterações posteriores e mantendo o gate de integração pendente quando não executado.
- [ ] T035 Consolidar em `plans/validacao.md` a rastreabilidade FR-001–FR-014/SC-001–SC-006 e R06–R08 com comandos, respostas, trechos/páginas/IDs da consulta, ambiente/modelos e limites; conferir R01/R10 transversais, registrar R02–R05 como evidência da 001 e R09/R11/entrega global da 003 sem alegar aceite antecipado; conferir ausência de credenciais nas alterações/arquivos versionados e que nenhuma verificação bloqueada foi marcada concluída.
- [ ] T036 Executar `$speckit-converge` da spec ativa `specs/002-grounded-search`, confrontando implementação e evidências com spec/plan/tasks; acrescentar trabalho restante em `specs/002-grounded-search/tasks.md` e atualizar status documental somente conforme resultados reais, sem encerrar a funcionalidade com critérios obrigatórios pendentes.

## Dependências e ordem de execução

```text
Análise de consistência antes da implementação
  → Preparação T001–T003
  → Fundação: (T004 || T005) → (T006 || T007) → T008
  → US1: (T009 || T010) → T011 → T012 → T013 → T014 → T015 → T016
  → US2: (T017 || T018) → T019 → T020 → T021 → T022
  → US3: (T023 || T024 || T025) → T026 → T027 → T028 → T029 → T030 → T031
  → Consolidação T032 → T033 → T034 → T035 → T036
```

O gráfico indica a ordem padrão, incluindo os checkpoints integrados. T006 depende dos
testes T004 e T007 dos T005; ambos podem ser desenvolvidos depois de escritos os testes,
pois o store usa os campos comuns existentes e não depende do novo campo de chat.

US2 depende do pipeline/contrato US1 (T011–T014); US3 amplia a fundação e o tratamento de
consulta US1/US2. As histórias são testáveis separadamente, mas compartilham `src/search.py`
e não são três implementações independentes que possam ser editadas simultaneamente.

Bloqueio de credencial/quota/banco em T016, T022, T030, T031 ou T033 não impede trabalho
independente com dublês nas fases seguintes; registrar o bloqueio e deixar a tarefa
integrada pendente. Gates finais não podem tratar esse avanço como aprovação da história
ou da spec. T034 pode diagnosticar a suíte durante um bloqueio, mas não fecha integração.

### Exemplos de paralelismo por história

- **US1**: T009 escreve contratos em `tests/test_search.py` enquanto T010 confere PDF e
  registra casos em `plans/validacao.md`. Ambos dependem somente da fundação; T011 começa
  depois dos testes. Alterações seguintes em `src/search.py` são sequenciais.
- **US2**: T017 escreve testes em `tests/test_search.py` enquanto T018 prepara ausência/
  fixtures em `plans/validacao.md`, após o incremento US1. T019/T020 ficam sequenciais no
  mesmo módulo. Não executar observação integrada enquanto outro trabalho modifica o código.
- **US3**: T023, T024 e T025 escrevem matrizes em arquivos de testes distintos. T026–T028
  vêm depois, com serialização das mudanças em `src/search.py`; T030/T031 usam configuração
  e destinos isolados, porém seus registros em `plans/validacao.md` são sequenciais.

Os outros lotes `[P]` são T004/T005 (testes em arquivos distintos) e T006/T007 (config/store).
O marcador descreve oportunidade de execução, não uma instrução para criar agentes ou chats.

## Estratégia de implementação

1. **MVP técnico**: preparação/fundação e US1 até T016, demonstrando três respostas com
   evidência sem iniciar chat. Se T016 bloquear, manter demonstração real pendente.
2. **Fundamentação completa**: incorporar US2, preservar respostas positivas e executar
   as recusas/adversariais; MVP não dispensa esses critérios P1.
3. **Operação**: incorporar US3 com erros identificáveis e proteção do armazenamento;
   a fundação já fornece a abertura compatível necessária às demais histórias.
4. **Conclusão**: atualizar instruções, repetir integração/regressão afetada, executar
   gates finais e convergência. Correções exigem nova verificação correspondente.

Não criar web, OCR, segundo provedor, memória, streaming, filtros arbitrários ou novo
schema/arquitetura. Preservar `src/ingest.py`, `src/search.py`, `src/chat.py`, `document.pdf`,
Compose e requisitos acadêmicos; interação de terminal e entrega global seguem na 003.

## Rastreabilidade do aceite

| Requisito / critério | Tarefas principais |
| --- | --- |
| FR-001 | T009, T012–T016, T025–T029 |
| FR-002 | T004–T008, T011, T024, T031 |
| FR-003 | T009, T011, T016 |
| FR-004 | T009, T011–T012, T017 |
| FR-005 | T009, T012–T013, T017, T020–T022 |
| FR-006 | T010, T016, T018, T020–T022 |
| FR-007 | T012, T017–T022 |
| FR-008 | T017, T019, T021 |
| FR-009 | T009, T013, T017–T018, T020–T022 |
| FR-010 | T004–T008, T023–T031 |
| FR-011 | T004, T006–T008, T023–T024, T031 |
| FR-012 | T010, T014, T016–T018, T021–T022, T029–T035 |
| FR-013 | T009, T013, T025–T026, T029 |
| FR-014 | T009, T011, T016–T022 |
| SC-001 | T010, T016 |
| SC-002 | T018, T022 |
| SC-003 | T009, T011, T017, T019, T021 |
| SC-004 | T004–T008, T023–T031 |
| SC-005 | T009, T013–T016, T022 |
| SC-006 | T010, T016, T018, T022, T030–T035 |
| R01 / R10 transversais | T001–T003, T006–T016, T032–T035 |
| R06 | T007, T009, T011, T016, T024, T031 |
| R07 | T009, T011–T014, T016, T019–T022, T027 |
| R08 | T010, T016–T022, T025–T029 |

**Resumo**: 36 tarefas — preparação 3, fundação 5, US1 8, US2 6, US3 9 e consolidação 5.
Onze tarefas têm `[P]`, em cinco lotes explícitos. Todas estão pendentes; nenhuma execução
real ou implementação foi declarada concluída nesta geração.
