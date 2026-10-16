# Tarefas: Chat no terminal e entrega reproduzível

**Entrada**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [contrato](contracts/terminal-chat.md) e
[quickstart.md](quickstart.md), em `specs/003-terminal-chat/`.
**Data**: 2026-10-16 | **Branch Git**: `main` | **Spec ativa**: `003-terminal-chat`.

**Pré-requisitos**: specs 001/002 implementadas e evidências disponíveis; README e
constituição v1.0.0 prevalecem. Executar `$speckit-analyze` antes da implementação e
resolver divergências bloqueantes. Esta geração não executa os itens abaixo.

**Testes**: solicitados nos testes independentes das três histórias, SC-001–SC-007,
plano e constituição VIII. Escrever os testes de cada comportamento antes da respectiva
implementação, observar falha pertinente e então corrigir. Isolados não usam rede,
credencial real, PostgreSQL ou tracing. Integração real é identificada separadamente.

**Formato**: `- [ ] Tnnn [P?] [USn?] descrição com caminho`. Caminhos relativos à raiz.
`[P]` identifica apenas tarefas com arquivos distintos nos lotes explicitados adiante;
não autoriza executar pré-requisitos incompletos. Todos os itens começam pendentes.
Cada conclusão exige evidência; bloqueio mantém o item aberto com motivo registrado.

## Fase 1: Preparação compartilhada

**Objetivo**: conferir ambiente e baseline sem refazer o projeto, mudar modelos/pins
por conveniência ou tocar nos dados existentes.

- [X] T001 Confirmar CPython 3.12.12 no venv, versões de `requirements.txt` e baseline com `python -m unittest discover -s tests -v`, `python -m compileall -q src tests` e `python -m pip check`; abrir seção 003 em `plans/validacao.md` com ambiente, revisão, comandos/códigos e resultado real, preservando os registros 001/002 e sem declarar o chat validado (R01/R10, FR-011/FR-014).
- [X] T002 Conferir escopo e referências de `specs/003-terminal-chat/plan.md` e `specs/003-terminal-chat/research.md` contra `README.md`, `.env.example` e contratos 001/002; manter um PDF/OpenAI, embeddings `text-embedding-3-small`/1536 e chat `gpt-6-luna`, sem variáveis novas; registrar em `plans/validacao.md` dependências de credencial/quota, banco e reprodução pública, sem imprimir arquivos locais ou presumir serviços disponíveis; descobertas materiais atualizam os artefatos antes de comportamento conflitante (FR-009/FR-010/FR-014).

## Fase 2: Fundação — contratos e infraestrutura de teste

**Objetivo**: fixar a fronteira consumida e preparar dublês que permitam implementar as
histórias sem serviços reais. Não criar schema, sessão de domínio ou framework de CLI.

- [X] T003 Conferir `SearchChain`, `search_prompt`, `SearchError`, `QuestionError`, `ConfigurationError` e `StorageError` em `src/search.py`, `src/config.py` e `src/vector_store.py` contra `specs/003-terminal-chat/contracts/terminal-chat.md`; registrar em `plans/validacao.md` fábrica contextual/invoke/fechamento e mensagens públicas sanitizadas, sem reproduzir classificação do SDK; aplicar ao estado da sessão a restrição “Conceitual: inicializando, aguardando, consultando, encerrando, encerrada ou falha. Não exige enum/campo persistido.”, mantendo esses estados como descrição do fluxo, sem modelo persistido (FR-001/FR-006/FR-007/FR-008).
- [X] T004 Preparar `tests/test_chat.py` com dublê contextual de cadeia, fábrica contável, leitor com sequência/exceções e streams `io.StringIO`; permitir configurar resposta, `SearchError` e falha de abertura/liberação, registrar chamadas sem serviços e desativar tracing no escopo dos testes com restauração; evitar inicializar o stub por import ou exigir uma classe/camada nova na aplicação; usar tipos/contratos da 002, não dublê que retorna `None` na fábrica (FR-001–FR-008, fundação das três histórias).

**Checkpoint**: T001–T004 completos permitem histórias isoladas. Banco/credencial não
são bloqueio da fundação; somente tarefas que exigem esses recursos ficam pendentes.

## Fase 3: US1 — Conversar sobre o PDF pelo terminal (P1) — MVP

**Objetivo**: entregar várias perguntas por execução, texto/recusa preservados, branco
ignorado e saída normal, com uma cadeia e sem memória factual.

**Teste independente**: leitor/cadeia dublês fornecem três perguntas e respostas, incluindo
recusa, depois saída; comprovar prompts, payloads, apresentação, uma fábrica e liberação.
Testar separadamente branco, comandos com espaços/caixa, EOF e Ctrl+C. Não exige API/banco.

### Testes da história

- [X] T005 [US1] Acrescentar em `tests/test_chat.py` testes de três perguntas/uma cadeia, prompt `PERGUNTA: `, prefixo `RESPOSTA: `, separador, Unicode/espaços da resposta e recusa importada da busca; aplicar literalmente “`raw_input.strip()`; não vazia, diferente de comandos de saída sem distinguir caixa.”, “Mapping com somente `{"pergunta": question}`; sem histórico ou contexto fornecido pela CLI.” e “`str` não vazia/branca; exibir integralmente sem novo strip, resumo ou complemento.”; conferir branco sem invoke e segunda pergunta sem memória/complemento; confirmar falhas antes de T007–T008 (FR-001/FR-002/FR-003/FR-005, SC-001).
- [X] T006 [US1] Acrescentar em `tests/test_chat.py` testes parametrizados/subTest para `sair`/`exit` com caixa/espaços, EOF/Ctrl+C na leitura, Ctrl+C no invoke e interrupção na inicialização; comprovar código 0 quando a liberação funciona, nenhum invoke para saída, nenhum erro/recusa substituta, recursos liberados e streams emprestados abertos; testar import `src.chat` sem configuração/clientes/conexão/interação e defaults de leitor/streams resolvidos na chamada; confirmar falhas antes de T007–T009 (FR-004/FR-008, SC-002).

### Implementação da história

- [X] T007 [US1] Substituir a composição do stub em `src/chat.py` por `main(...) -> int`, imports compatíveis com pacote/script e guard `raise SystemExit(main())`; receber fábrica `Callable[[], AbstractContextManager[SearchChain]] | None`, leitor/streams opcionais resolvidos em runtime e abrir um único contexto antes do laço; aplicar “`SearchChain`, criada uma vez e possuída por `main`; emprestada ao laço.”, “`Callable[[str], str]`; recebe o prompt e retorna entrada; pode levantar EOF/Ctrl+C.” e “`TextIO`; respostas em stdout, erros em stderr; streams emprestados, não fechados pela CLI.”; remover `if not chain`, não chamar serviços no import nem fazer aquecimento pago (FR-001/FR-002/FR-005, SC-001).
- [X] T008 [US1] Implementar `run_chat(chain, *, read_question, output, error_output) -> int` em `src/chat.py`: ler `PERGUNTA: ` pelo leitor, normalizar somente entrada, ignorar branco, reconhecer saída com casefold e fazer um invoke com chave única; apresentar resposta integral mais linha vazia, sem SQL, embeddings, histórico, constante de recusa duplicada ou fechamento da cadeia emprestada; aplicar as restrições de pergunta/request/answer citadas em T005 (FR-001/FR-002/FR-003/FR-005, SC-001/SC-002).
- [X] T009 [US1] Implementar em `src/chat.py` saída por comandos e captura explícita de EOFError/KeyboardInterrupt na fronteira de `main`, inclusive inicialização/invoke; retornar 0 somente após saída do contexto sem falha, não continuar na cadeia interrompida e não capturar BaseException genericamente; manter a exigência de falhas fatais retornarem 1, que será completada na US2; aplicar o contrato de `exit_code` “`int`: 0 para saída normal, 1 para falha fatal, inclusive liberação que falha.”, sem afirmar sucesso antes da liberação (FR-004, SC-002).
- [X] T010 [P] [US1] Executar os casos US1 de `tests/test_chat.py` e regressão existente de `tests/test_search.py`; registrar em `plans/validacao.md` comandos, falhas pertinentes anteriores, aprovação posterior, quantidade efetiva e limites dos dublês; confirmar que três respostas, recusa, branco e encerramento atendem o contrato sem rede (FR-001–FR-005, SC-001/SC-002).
- [X] T011 [P] [US1] Acrescentar a `README.md` instruções da CLI implementada, `python src/chat.py`, múltiplas perguntas, branco, comandos/EOF/Ctrl+C, ausência de histórico e reutilização/fechamento; preservar enunciado/prompt/exemplos e identificar operação/entrega global ainda em validação, sem publicar exemplos novos como respostas reais antes da US3 (FR-001/FR-009, R09/R10).

**Checkpoint**: US1 oferece MVP demonstrável e testável isoladamente. US2 e US3 continuam
obrigatórias para declarar a entrega validada; nenhum bloqueio externo dispensa seu aceite.

## Fase 4: US2 — Corrigir problemas sem confundir erro com resposta (P2)

**Objetivo**: apresentar erros acionáveis e seguros, aceitar nova pergunta após transiente
e sair em falha para impedimento fatal, distinguindo base vazia de recusa factual.

**Teste independente**: dublês simulam inicialização inválida/base vazia, transiente seguido
de sucesso, fatal, saída inválida e fechamento que falha; conferir stderr/códigos,
continuidade e sigilo. Uso sem PDF/provedor alternativo é protegido isoladamente e
comprovado com base real na US3.

### Testes da história

- [X] T012 [US2] Ampliar `tests/test_chat.py` com `ConfigurationError`/`StorageError` na abertura e banco indisponível por dublê; conferir diagnóstico com prefixo `Erro ao iniciar o chat: `, variável/ingestão/Compose conforme a causa, código 1, nenhum primeiro prompt e liberação da construção parcial contratada; testar exceção inesperada na fábrica sem exposição de mensagem bruta, antes de T015 (FR-006/FR-008, SC-003).
- [X] T013 [US2] Ampliar `tests/test_chat.py` com `SearchError(retryable=True)` seguido de resposta e saída, e `retryable=False` seguido de pergunta que não deve ser lida/invocada; conferir mesma cadeia, sem retry automático, prefixo `Erro na consulta: ` em stderr, nenhum `RESPOSTA:`/recusa no erro, código 0 no primeiro caso após saída normal e 1 no fatal; testar `QuestionError` e retornos None/número/bloco/vazio/branco como falha fatal, antes de T016–T017 (FR-005/FR-007, SC-003).
- [X] T014 [US2] Ampliar `tests/test_chat.py` com falhas inesperadas de leitor/invoke/apresentação e de liberação após sucesso, fatal, EOF e Ctrl+C; inserir sentinelas de chave, URL com senha, pergunta e PDF na exceção e confirmar ausência em stdout/stderr/log/traceback, preservando erro anterior quando o fechamento também falha; aplicar “`str` recebida do leitor; nunca registrada nos logs padrão.” e “Exceção, não resposta; só mensagens internas sanitizadas são públicas.”; comprovar código 1 em falha de liberação antes de T015–T017 (FR-007/FR-008, SC-003).

### Implementação e verificação da história

- [X] T015 [US2] Implementar em `src/chat.py` fronteira de inicialização para ConfigurationError/StorageError com mensagens públicas sanitizadas da 002 e código 1, sem prompt anterior ao sucesso; configurar logging de categoria/nível sem conteúdo sensível e tratar erro inesperado de abertura/leitor/apresentação com a mensagem estática do contrato, sem `str`/`repr` da origem ou `exc_info`; não criar uma segunda leitura/validação de ambiente (FR-006/FR-008, SC-003).
- [X] T016 [US2] Implementar em `src/chat.py` tratamento de SearchError na consulta: diagnóstico operacional em stderr, retryable permite nova pergunta na cadeia atual e fatal retorna 1; não repetir pergunta automaticamente, reconstruir cadeia, analisar texto do SDK ou transformar erro em recusa; base validada com recuperação vazia continua exibindo a string devolvida pela busca (FR-005/FR-007, SC-003).
- [X] T017 [US2] Completar em `src/chat.py` validação da resposta como string não branca, QuestionError como falha fatal de contrato e captura segura de exceção inesperada na fronteira CLI; distinguir falha de liberação com a mensagem estática contratada, código 1 e preservação de falha anterior, inclusive após interrupção; não converter retorno inválido com str, suprimir erro de fechamento nem fechar streams emprestados (FR-004/FR-005/FR-007/FR-008, SC-002/SC-003).
- [X] T018 [US2] Acrescentar em `tests/test_chat.py` comprovação de delegação à configuração de consulta sem PDF_PATH/Google e sem aquecimento pago, usando fábricas/dublês da busca; testar `python src/chat.py` em subprocesso com timeout finito e `OPENAI_API_KEY` exportada vazia para prevalecer sobre arquivos locais e falhar antes de serviços, cobrindo código 1/diagnóstico seguro; não assumir que trocar cwd evita `.env`, pois `src/config.py` resolve a raiz pelo arquivo do módulo (FR-006/FR-008/FR-015, R10).
- [X] T019 [US2] Executar `python -m unittest tests.test_chat -v` e a suíte completa após T015–T018, com regressão de `tests/test_config.py`, `tests/test_vector_store.py`, `tests/test_ingest.py` e `tests/test_search.py`; registrar em `plans/validacao.md` matriz de abertura/transiente/fatal/saída inválida/liberação/sanitização, resultados e limites, sem provocar falhas pagas ou derrubar o banco compartilhado (FR-006/FR-007/FR-008/FR-015, SC-003).

**Checkpoint**: US2 opera e falha de forma observável com dublês. Comprovação real do
entrypoint/base/serviços é da US3; falhas simuladas não são relatadas como incidentes reais.

## Fase 5: US3 — Reproduzir e avaliar a entrega (P2)

**Objetivo**: completar documentação e evidências, reproduzir o fluxo em ambiente novo e
conferir entrega pública, mantendo pendente qualquer verificação não executada.

**Teste independente**: avaliador segue README em clone/venv/banco novos, ingere PDF,
executa chat e bateria, verifica repositório público/fork/segredos e encontra evidência
para todos os requisitos. Depende do fluxo integrado US1/US2; documentação pode avançar
em paralelo após US1 e as verificações externas são separáveis.

### Documentação e verificações da história

- [X] T020 [P] [US3] Completar `README.md` e conferir `.env.example` com preparação CPython 3.12.12/venv/pins, precedência e variáveis por fluxo, Compose/saúde/bootstrap, ingestão/chat/testes, códigos 0/1 e diagnósticos transitório/fatal, custos/timeouts/zero retries e tracing somente explícito; preservar prompt/enunciado e política da 001 de upsert/reindexação em nova collection, documentando efeitos sem fornecer limpeza automática; indicar a seção 003 do relatório e manter exemplos novos como pendentes até verificação (FR-009/FR-010, SC-004, R10/R11).
- [X] T021 [US3] Executar preflight integrado conforme `specs/003-terminal-chat/quickstart.md`: confirmar PDF/hash, modelos/pins atuais, Compose saudável, bootstrap Exited(0), extensão vector e collection ingerida com manifesto/contagem/dimensões corretos; registrar em `plans/validacao.md` ambiente e comandos/códigos sem segredos, reaproveitando destino compatível já existente para a bateria e sem reingerir/limpar por conveniência; falta de acesso/quota/banco mantém tarefas dependentes abertas (FR-010/FR-011/FR-014, R01–R05).
- [X] T022 [US3] Validar `python src/chat.py` com P1–P3 consecutivas e saída no mesmo processo e executar P1–P3/N1–N3/O1/A1 pelo laço real com fábricas observadoras da busca, delegando uma recuperação/geração por pergunta e sem segunda busca para inferir evidência; registrar em `plans/validacao.md` comandos/códigos, modelos solicitados/devolvidos, perguntas/respostas literais e chunks/IDs/trechos/páginas da mesma consulta, com “Para fatos: pergunta/resposta, trecho/ID/página dos chunks da mesma consulta; página humana = índice + 1.”; conferir os três fatos e cinco recusas exatas do quickstart, corrigir/reexecutar casos afetados se houver resposta sem sustentação, sem alegar proteção universal (FR-001/FR-002/FR-005/FR-011/FR-012, SC-001/SC-006, R06–R09).
- [X] T023 [US3] Executar pelo terminal os casos da seção 4 de `specs/003-terminal-chat/quickstart.md`: branco seguido de pergunta válida, ` SAIR `, ` ExIt `, EOF, Ctrl+C na leitura e na consulta; registrar em `plans/validacao.md` prompts/saídas/códigos e liberação observável, sem resposta de erro e sem manter cadeia interrompida; referenciar T006 para contagem sem chamadas em branco e registrar eventual custo de requisição já iniciada (FR-003/FR-004/FR-011, SC-002, R09).
- [X] T024 [US3] Executar entrypoint com variável obrigatória exportada vazia e destinos ausente/vazio comprovados por SELECT delimitado antes/depois, sem tocar na collection do PDF; comprovar orientação/código 1/nenhuma criação nem API e testar consulta real sem arquivo original/PDF_PATH e sem Google usando ambiente/arquivos isolados ou fábricas de configuração previstas, sem mover o PDF real; registrar em `plans/validacao.md` comandos, resultados, ausência de escrita e distinção entre base vazia e recusa factual; preparar destino vazio dedicado somente se necessário e documentar sua criação explícita (FR-006/FR-008/FR-012/FR-015, SC-003/SC-006).
- [X] T025 [US3] Conferir aplicabilidade das evidências de arquivo inválido/sem texto, splitter/metadados, reingestão e incompatibilidades da 001/002; registrar em `plans/validacao.md` referências precisas a seções/casos e justificativa de validade para o candidato, repetindo os procedimentos dos quickstarts anteriores se alterações afetarem os comportamentos; não atribuir ao chat validação de ingestão que ele não executa (FR-010/FR-011/FR-012, SC-005/SC-006, R03–R05).
- [X] T026 [US3] Validar persistência final pela CLI conforme seção 5 de `specs/003-terminal-chat/quickstart.md`: obter snapshot delimitado de contagem/IDs/manifesto/conteúdo/vetores, executar reinício do PostgreSQL do destino de validação, aguardar saúde, comparar snapshot e consultar P1 em processo novo sem reingerir; registrar comandos/códigos/resposta/página em `plans/validacao.md`, sem remover volume ou imprimir vetores; executar fora das demais consultas reais para não invalidá-las por reinício concorrente (FR-011/FR-012, SC-006, R02/R05/R09).
- [X] T027 [US3] Preparar reprodução em clone separado e venv novo do candidato identificado conforme seção 6 de `specs/003-terminal-chat/quickstart.md`, sem copiar venv/arquivos locais ocultos; selecionar Python validado, configurar credencial somente pelos meios documentados e banco/volume novos, preferindo contexto Docker limpo/porta 5432 livre; se necessário usar projeto Compose/configuração copiada com container_name/porta/volume distintos, registrar exatamente essa variação em `plans/validacao.md` e preservar base existente; clone deve conter a revisão candidata, não origin desatualizado sem as alterações (FR-009/FR-014, SC-004, R01/R02/R10).
- [X] T028 [US3] No ambiente de T027, executar os comandos do `README.md` em ordem desde `python3 -m venv venv`, ativação e instalação até Compose/saúde/vector, `python src/ingest.py` e `python src/chat.py`, depois verificadores adotados e três perguntas; comprovar destino inicialmente ausente, ingestão/manifesto/registros válidos e uso sem editar código-fonte, registrando em `plans/validacao.md` revisão, ambiente, arquivos de configuração documentados, modelos, comandos/códigos e respostas/evidências; não declarar bootstrap novo se reutilizou banco anterior (FR-009/FR-010/FR-011/FR-014, SC-004, R01–R05/R09/R10).
- [ ] T029 [US3] Conferir candidato público no GitHub e origem do fork `devfullcycle/mba-ia-desafio-ingestao-busca`, revisão disponível e acesso anônimo; revisar estrutura obrigatória, `.env.example`, ignores, arquivos versionados e histórico para credenciais reais sem imprimir valores, distinguindo senha local de exemplo do Compose de tokens reais; registrar método/escopo/URL/revisão/resultado ou bloqueio em `plans/validacao.md`, sem presumir publicação/visibilidade correta nem alterar visibilidade ou publicar automaticamente (FR-008/FR-013/FR-014, SC-007, R10/R11).

**Checkpoint**: há evidências reais da CLI e reprodução, ou pendências explícitas.
Se o candidato ainda não estiver disponível publicamente, T029 permanece aberto;
comprovação local de T028 não substitui revisão/acesso do candidato público.

## Fase 6: Acabamento e verificações transversais

**Objetivo**: sincronizar documentação com o resultado executado, rodar gates e conferir
convergência sem transformar bloqueios externos em conclusão indevida.

- [X] T030 Atualizar `README.md` e `specs/003-terminal-chat/quickstart.md` com procedimentos/exemplos realmente executados, referências a páginas e ao relatório, diagnósticos e limitações; substituir avisos de stub/teste inexistente somente após implementação efetiva, preservar enunciado/prompt e alinhar spec/plan/contrato se descobertas alterarem requisitos ou fronteiras, sem declarar conclusão global enquanto houver critério obrigatório pendente (FR-009/FR-010/FR-014, SC-004/SC-007).
- [X] T031 Revisar responsabilidades/tipos/recursos/segurança de `src/chat.py` e sua integração com `src/search.py`, sem SQL/prompt/configuração duplicados, estado global mutável ou novas dependências não justificadas; executar `python -m unittest discover -s tests -v`, `python -m compileall -q src tests`, `python -m pip check` e `git diff --check`, registrando em `plans/validacao.md` resultados, limites reais e regressões corrigidas; repetir verificações apenas quando mudanças posteriores afetarem sua validade (FR-001–FR-008/FR-015, R01/R04/R06/R07/R10).
- [X] T032 Consolidar em `plans/validacao.md` matriz dos 15 FR, sete SC e R01–R11, relacionando T001–T031 e evidências novas/001/002 com revisão e seção precisas; aplicar “ID de requisito R/FR/SC, cenário, spec produtora e revisão avaliada.”, “Data, plataforma, Python/pins, serviços, modelos solicitados e devolvidos.”, “Collection, identidade do PDF quando aplicável, comando, código de saída e resultado observado.”, “Aprovado, reprovado ou pendente; pendência inclui motivo/dependência e próximo passo.” e “Execução nova ou referência precisa a evidência válida da 001/002, com justificativa de aplicabilidade.”; preservar todos os bloqueios/itens não executados abertos, sem confundir aprovação isolada com factual/publicação (FR-011/FR-012/FR-013/FR-014, SC-005/SC-006/SC-007).
- [X] T033 Aplicar `$speckit-converge` à 003 após as verificações e atualizar `specs/003-terminal-chat/tasks.md`/`plans/validacao.md` com lacunas e trabalho restante; implementar/verificar novas tarefas antes de declarar convergência e só marcar verificações bloqueadas concluídas quando houver evidência; relatar alterações, comandos executados, cobertura e limitações reais, mantendo a spec ativa em `.specify/feature.json` (FR-014, SC-005).

## Dependências e ordem de execução

### Grafo das histórias

```text
T001 → T002 → T003 → T004
                       ↓
                   US1 T005–T011 (MVP isolado)
                       ├──────────────→ T020 (documentação US3)
                       ↓
                   US2 T012–T019
                       ↓
            US3 T021–T029 + T020
                       ↓
              T030 → T031 → T032 → T033
```

US2 integra o laço da US1, mas sua matriz é testável isoladamente sem serviços.
US3 depende do comportamento integrado para reprodução; sua documentação pode avançar
antes do término da US2. Essas dependências refletem os dois arquivos compartilhados,
não requerem segundo modelo/serviço nem execução paralela por agentes.

### Dependências específicas

| Tarefa/lote | Pré-requisitos e condições |
| --- | --- |
| T001–T004 | Sequenciais; T003 consome T002, T004 usa os contratos conferidos. |
| T005 → T006 → T007 → T008 → T009 | Após T004; testes no mesmo arquivo são sequenciais, antes do código que verificam. |
| T010 e T011 [P] | Após T009; podem rodar juntos: relatório/testes versus instruções no README, sem copiar resultados ainda não verificados. |
| T012 → T013 → T014 → T015 → T016 → T017 → T018 → T019 | Após US1; mesmo arquivo de testes/código, execução sequencial para não sobrepor edições. |
| T020 [P] | Após T011; pode rodar com T012–T019, pois altera apenas README/.env.example. Não alegar testes ainda não executados. |
| T021 | Após T019 e disponibilidade dos serviços/credencial; leitura de base já ingerida compatível. |
| T022, T023, T024 | Após T021 e T019; executar sequencialmente, pois escrevem o mesmo relatório e usam os serviços/terminal. |
| T025 | Após T019; independente de credencial e pode avançar se T021–T024 bloquearem; não editar relatório simultaneamente. |
| T026 | Após T021/T022 e nenhuma consulta real em curso; pode usar banco do ambiente novo após T028 se essa opção isolar melhor o reinício. |
| T027 | Após T019/T020; pode avançar se o banco original estiver bloqueado, desde que o ambiente novo esteja disponível. |
| T028 | Após T027; requer credencial, banco novo saudável e revisão candidata correta. |
| T029 | Após T019/T020; conferir a revisão pública efetivamente candidata; repetir se a revisão mudar. Bloqueio não impede testes/reprodução local. |
| T030 | Após resultados disponíveis da US3; pendências precisam ser descritas, não ocultadas. |
| T031 | Após T030 e código final; falhas exigem correção e repetição das verificações afetadas. |
| T032 | Após T031 e registro dos resultados/bloqueios de todas as verificações; não conclui itens bloqueados. |
| T033 | Após T032; convergência verifica também as tarefas abertas e não autoriza conclusão indevida. |

Se integração estiver bloqueada, registrar motivo, continuar tarefas independentes e
manter os respectivos checkboxes abertos. Não executar limpeza, retentativas cobradas
indiscriminadas ou publicar o candidato para contornar uma pendência automaticamente.

## Exemplos de paralelismo por história

- **US1:** depois de T009, executar T010 (testes/`plans/validacao.md`) enquanto T011
  escreve instruções básicas em `README.md`; não editar o relatório a partir de T011.
  T005/T006 e T007–T009 compartilham arquivos e não são paralelos.
- **US2:** seu código/testes são sequenciais. Depois de T011, T020 `[P]` pode atualizar
  `README.md`/`.env.example` enquanto T012–T019 trabalham em testes, código e relatório.
  Não dividir edições concorrentes de `tests/test_chat.py` entre tarefas.
- **US3:** T020 é o mesmo lote documental paralelo com US2. T021–T029 são verificações
  separáveis, mas ficam sequenciais para evitar disputa pelo relatório e pelo banco;
  não reiniciar PostgreSQL enquanto a bateria real consulta o destino.

Os exemplos definem oportunidades de execução; não exigem agentes adicionais. O marcador
`[P]` aparece em T010/T011 e T020, nos lotes e condições explicitados acima.

## Estratégia de implementação

1. **MVP:** concluir fundação e US1 (T001–T011), validar três interações e encerramento
   com dublês. Esse incremento demonstra o chat; ainda não é entrega global validada.
2. **Operação:** concluir US2 (T012–T019), incluindo erros/recursos/sanitização e regressão;
   T020 pode avançar em paralelo sem editar os mesmos arquivos.
3. **Evidência:** executar US3 (T020–T029), distinguindo serviço real, simulação e prova
   anterior aplicável. Conferir reprodução e acesso público da revisão correta.
4. **Conclusão:** sincronizar documentação, executar gates, consolidar matriz e convergir
   (T030–T033). Se a convergência revelar lacunas, implementar/verificar antes do aceite.

## Rastreabilidade de aceite

| Requisito | Tarefas principais |
| --- | --- |
| FR-001 | T005/T007/T008/T010/T011/T022 |
| FR-002 | T005/T007/T008/T010/T022 |
| FR-003 | T005/T008/T010/T023 |
| FR-004 | T006/T009/T014/T017/T023 |
| FR-005 | T005/T008/T010/T013/T016/T017/T022 |
| FR-006 | T003/T012/T015/T018/T024 |
| FR-007 | T003/T013/T014/T016/T017/T019 |
| FR-008 | T006/T012/T014/T015/T017/T018/T019/T024/T029/T031 |
| FR-009 | T002/T011/T020/T027/T028/T030 |
| FR-010 | T002/T020/T021/T025/T028/T030 |
| FR-011 | T001/T021–T028/T032 |
| FR-012 | T022/T024/T025/T026/T032 |
| FR-013 | T029/T032 |
| FR-014 | T001/T002/T021/T027/T028/T029/T030/T032/T033 |
| FR-015 | T018/T019/T024 |
| SC-001 | T005/T007/T008/T010/T022 |
| SC-002 | T005/T006/T008/T009/T017/T023 |
| SC-003 | T012–T019/T024 |
| SC-004 | T020/T027/T028/T030 |
| SC-005 | T025/T032/T033 |
| SC-006 | T022/T024/T025/T026/T032 |
| SC-007 | T029/T030/T032 |
| R01 | T001/T021/T027/T028/T031 |
| R02 | T021/T026/T027/T028 |
| R03/R04/R05 | T021/T025/T026/T028/T031, conforme escopo de cada prova |
| R06/R07/R08 | T010/T019/T022/T031, regressão 002 e bateria factual |
| R09 | T005–T011/T022/T023/T026/T028 |
| R10 | T001/T011/T018/T020/T027/T028/T029/T031 |
| R11 | T020/T029/T030/T032 |

## Conferência desta geração

33 tarefas: preparação 2, fundação 2, US1 7, US2 8, US3 10, acabamento 4.
Todas começam pendentes, com IDs sequenciais, rótulos e caminhos definidos.
Esta conferência é estrutural, não substitui `$speckit-analyze` nem comprova execução.

## Phase 7: Convergence

- [ ] T034 [US3] Após a revisão candidata 003 estar disponível publicamente por fluxo autorizado, complementar T029: conferir anonimamente a revisão exata, comparar `src/chat.py`, `tests/test_chat.py`, estrutura obrigatória e documentação com o candidato validado, repetir inspeção de credenciais dessa revisão e registrar URL/revisão/comandos/resultados em `plans/validacao.md`; atualizar a matriz e somente então concluir T029/FR-013/SC-007/R11, sem publicar nem alterar visibilidade automaticamente per FR-013, SC-007, US3/AC4 (partial). Bloqueio atual: o candidato permanece no diff local; público observado não contém esta implementação.


## Phase 8: Convergence

- [ ] T035 [US3] Concluir o gate público já rastreado em T029/T034 após a disponibilização autorizada do candidato: confirmar por acesso anônimo que a revisão de entrega inclui `src/chat.py` e `tests/test_chat.py` do candidato validado, conferir estrutura/fork/documentação/segredos dessa revisão e registrar URL, identidade, comandos e resultados em `plans/validacao.md`; sincronizar os avisos de pendência em `README.md`, `specs/003-terminal-chat/spec.md`, `plan.md` e `quickstart.md` somente após comprovação, preservando registros históricos, e executar nova convergência antes de declarar entrega integral per FR-013, FR-014, SC-007, US3/AC4 (partial, HIGH). Reavaliação desta rodada: API anônima HTTP 200 confirma público/fork correto; o chat público difere do candidato local e o teste público retorna HTTP 404. Complementa o fechamento documental de T029/T034, sem nova implementação funcional, publicação automática ou alteração de visibilidade.
