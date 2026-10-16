# Tarefas: Ingestão e persistência do PDF

**Funcionalidade**: `001-pdf-ingestion` | **Data**: 2026-10-16 | **Branch atual**: `main`

**Entradas**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/ingestion.md](contracts/ingestion.md) e
[quickstart.md](quickstart.md). Aplicam-se a [constituição](../../.specify/memory/constitution.md),
o [README](../../README.md) e as partes de ingestão do
[plano inicial](../../plans/plano-implementacao.md).

**Estado**: tarefas geradas, nenhuma executada por este comando. A pesquisa prévia não
substitui instalação reproduzível, testes da aplicação nem integração real.

**Testes**: incluídos porque os cenários da especificação exigem verificação com amostras
e dublês, e o princípio VIII da constituição exige testes isolados. Usar `unittest` e
`unittest.mock`, sem chave real, PostgreSQL ou custo na suíte isolada. Escrever os testes
antes do comportamento correspondente e confirmar falha pelo requisito ainda ausente.

## Formato e caminhos

Cada item segue `- [ ] Tnnn [P?] [USn?] Descrição com caminho`. `[P]` identifica trabalho
em arquivos distintos que pode ocorrer em paralelo **depois** de satisfeitas as
dependências da fase e do item. Caminhos são relativos à raiz. `[US1]`, `[US2]` e `[US3]`
correspondem às histórias da especificação. Sem rótulo de história nas fases comuns.

Antes da implementação, executar `$speckit-analyze` sobre os três artefatos. Não executar
ingestão ou chamadas ao provedor durante a geração/análise das tarefas.

## Fase 1: Preparação compartilhada

**Objetivo**: preparar o ambiente exigido e registrar suas condições reais.

- [ ] T001 Preparar CPython 3.12.12 com `python3 -m venv venv`, ativação e `pip install -r requirements.txt`; executar `python -m pip check` e conferir imports fixados; registrar versão, plataforma, comandos/resultados em `plans/validacao.md`, preservando os pins de `requirements.txt` salvo incompatibilidade demonstrada (R01/R10, FR-011, SC-004).
- [ ] T002 [P] Completar `.env.example` com chave vazia, `OPENAI_EMBEDDING_MODEL=text-embedding-3-small`, `OPENAI_EMBEDDING_DIMENSIONS=1536`, URL local psycopg, collection e `PDF_PATH=document.pdf`; conferir exclusão de `.env` e `.env.local` em `.gitignore`, preservando a credencial local existente sem imprimi-la/copiar seu valor para arquivos versionados (FR-001/011).
- [ ] T003 Após T001, executar `docker compose config --quiet` e `docker compose up -d` com `docker-compose.yml`; confirmar PostgreSQL saudável, bootstrap com saída 0 e extensão `vector`; registrar resultados ou bloqueio em `plans/validacao.md`, sem remover volume nem corrigir Compose sem defeito demonstrado (R02, FR-002, SC-004).

**Checkpoint**: ambiente reproduzido e banco pronto. Bloqueio de banco/provedor não impede
trabalho isolado: registrar o bloqueio em T003, manter seu checkbox aberto e permitir
T004–T018, T020–T026 e T028–T032 que usam dublês. Nenhum aceite integrado pode ser marcado
concluído enquanto suas pré-condições estiverem bloqueadas.

## Fase 2: Fundação — pré-requisitos das histórias

**Objetivo**: contratos comuns, configuração e acesso compatível à collection. Dependem
de T001/T002; T003 é obrigatório para integração real, não para testes isolados.

- [ ] T004 [P] Criar `tests/test_config.py` com casos de configuração comum versus ingestão, variável obrigatória ausente/vazia, dimensão inválida, URL com driver incorreto, precedência ambiente exportado > `.env.local` > `.env`, chave só em `.env.local`, ausência de chave Google/modelo de chat e ausência de `PDF_PATH` no fluxo comum; usar arquivos temporários e ambiente isolado, sem ler credencial do repositório (FR-001/008/011).
- [ ] T005 [P] Criar `tests/test_vector_store.py` com dublês de engine/PGVector para validar extensão obrigatória, opções não destrutivas, timeouts, manifesto persistido em vez do manifesto solicitado e fechamento de recursos; cobrir manifesto ausente/incompatível e provar que nenhuma chamada de embeddings/escrita ocorre nesses casos (FR-002/009/010).
- [ ] T006 Após T004, implementar `load_settings` e `create_embeddings` em `src/config.py`: configuração tipada por fluxo, leitura explícita de `.env`/`.env.local` com precedência contratada e sem mutar arquivos/estado global; modelo configurável, dimensão "`1536` no ambiente de referência; positivo.", timeout de 60 s e `max_retries=0`; nenhuma inicialização externa no import (FR-001/008/011).
- [ ] T007 Após T005/T006, implementar `open_vector_store` em `src/vector_store.py`: engine psycopg com conexão/pool de 10 s, `statement_timeout=30000`, `lock_timeout=5000`, `echo=False` e `hide_parameters=True`; conferir `vector`; criar PGVector síncrono com `use_jsonb=True`, `embedding_length=None`, `create_extension=False` e `pre_delete_collection=False`; reler manifesto por SQL parametrizado; criar somente se ausente, rejeitar identidade incompatível/legada sem atualização ou adoção automática e liberar recursos em qualquer saída (FR-002/009/010).
- [ ] T008 Após T006/T007, executar `python -m unittest discover -s tests -v` para a fundação e conferir imports de `src/config.py`/`src/vector_store.py` sem credencial, API ou conexão; registrar comandos/resultados em `plans/validacao.md` e consolidar pontos de injeção tipados de configuração, embeddings e armazenamento para as histórias (princípios III–V e VIII).

**Checkpoint**: configuração e armazenamento compatível aprovados por dublês. Nenhuma
história começa com a fundação isolada reprovada. O manifesto aplicado em T007 protege
também o MVP; US3 acrescenta regressões, reexecução e comprovação de preservação.

## Fase 3: US1 — Preparar um PDF para consulta (P1, MVP)

**Objetivo**: extrair/dividir o PDF, gerar e persistir vetores rastreáveis e informar
quantidades confirmadas. Dependência: T008; integração também exige T003.

**Teste independente**: ingerir `document.pdf` em collection exclusiva inicialmente vazia;
conferir todos os chunks, vetores, origem/página/ID e resumo, sem buscar ou iniciar chat.

### Testes da US1

- [ ] T009 [P] [US1] Criar `tests/test_ingest.py` com loader/splitter reais e amostras temporárias curta, longa, portuguesa, com página intermediária vazia e totalmente vazia; verificar `1000/150/len`, sobreposição possível sem exigir 150 em todo limite, página original, metadados, IDs determinísticos e contrato de sucesso da CLI com dublês; cobrir FR-003–006 e SC-005 antes da implementação.
- [ ] T010 [P] [US1] Ampliar `tests/test_vector_store.py` para o contrato de `persist_chunks`: listas de mesmo tamanho, vetor por texto, IDs únicos, confirmação de texto/metadados/dimensão delimitada à collection e comparação por ID mesmo com `get_by_ids` fora de ordem; provar que nenhuma quantidade é anunciada antes da confirmação (FR-005/006, SC-001).

### Implementação da US1

- [ ] T011 [US1] Após T009, implementar `load_pdf_pages` e identidade do documento em `src/ingest.py` com `Path` e `PyPDFLoader(mode="page", extract_images=False)`; aplicar "Caminho local resolvido do PDF; obrigatório, sem URL remota.", "SHA-256 dos bytes do arquivo; 64 caracteres hexadecimais.", "Todas as páginas retornadas pelo loader, incluindo vazias." e "Índice original baseado em zero; apresentação humana pode somar 1 explicitamente."; validar arquivo regular/extensão/leitura, rejeitar PDF sem texto e alteração do arquivo durante extração/hash (FR-003, SC-005).
- [ ] T012 [US1] Após T011, implementar `split_pages` em `src/ingest.py` com fonte única dos parâmetros `chunk_size=1000`, `chunk_overlap=150`, `length_function=len` e separadores padrão; aplicar "Texto extraído; somente conteúdo com `strip()` não vazio origina chunks.", "`page_content` não vazio, até 1000 caracteres.", "Origem preservada.", "Página original baseada em zero." e "Posição global baseada em zero, em ordem página/trecho após filtrar vazios."; preservar demais metadados JSON, sem concatenar páginas ou preencher texto artificialmente (FR-004/005).
- [ ] T013 [US1] Após T012, atribuir IDs e construir manifesto em `src/ingest.py`, conforme `specs/001-pdf-ingestion/data-model.md`: ID "String determinística, única em toda a tabela.", `chunk_id` "Mesmo valor do `id`, para rastreabilidade.", hash documental "Revisão do PDF." e vínculo "UUID da collection."; SHA-256 de JSON canônico com nome da collection, versão, provedor/modelo/dimensão, hash do PDF, pipeline, página/índice/hash do texto; manifesto com `schema_version` "`1`, versão do contrato.", `provider` "`openai`.", modelo "`text-embedding-3-small` no ambiente de referência.", dimensão positiva, "Revisão única de PDF aceita nesse destino." e identidade completa do pipeline fixado (FR-005/010).
- [ ] T014 [US1] Após T010/T013, implementar `persist_chunks` em `src/vector_store.py`: exigir `list[float]` "com todos os valores finitos." e "Dimensão igual ao manifesto da collection.", cardinalidades iguais e IDs únicos antes de uma chamada `PGVector.add_embeddings` com textos/vetores/metadados/IDs; conferir IDs retornados e registros/dimensões persistidos por collection, sem pressupor ordem e sem SQL na CLI (FR-005/006).
- [ ] T015 [US1] Após T014, implementar geração dos embeddings em `src/ingest.py` com cliente injetável: um vetor para cada chunk não vazio, quantidade/dimensão/valores finitos validados integralmente antes de escrever; não persistir lotes incompletos nem confundir tamanho de lote do cliente com tamanho do splitter (FR-004–006).
- [ ] T016 [US1] Após T015, compor `ingest_pdf` em `src/ingest.py` na ordem configuração/PDF → chunks/manifesto → armazenamento compatível → embeddings → persistência confirmada; retornar resultado tipado com `source: Path`, `loaded_pages: int`, `stored_chunks: int`, `collection_name: str`, sem tabela adicional; garantir cliente/engine liberados e ausência de rede no import (FR-001/005/006).
- [ ] T017 [US1] Após T016, implementar `main` e entrada `python src/ingest.py` em `src/ingest.py`: sucesso com código 0 e resumo de arquivo/páginas/chunks confirmados/collection; fronteira de falha com código não zero e mensagem sanitizada, sem anunciar sucesso; executar T009/T010 e registrar resultados em `plans/validacao.md` (FR-006/008, SC-001).
- [ ] T018 [US1] Após T017, acrescentar ao `README.md` instruções mínimas de instalação, configuração `.env`/`.env.local`, precedência, ingestão e conferência, preservando o enunciado, arquivos e comandos obrigatórios; manter exemplos de chat como enunciado, sem afirmar implementação de busca/chat (FR-011, SC-004).
- [ ] T019 [US1] Após T003/T018 e com acesso/quota válidos, executar seções 1–4 de `specs/001-pdf-ingestion/quickstart.md` com o PDF e provedor reais; antes da primeira ingestão, comprovar que a collection de validação não existe, escolhendo outro nome se já existir, sem limpar dados; manter esse nome nas consultas e reexecuções; conferir manifesto/todos os registros e amostras contra páginas; registrar estado inicial, nome escolhido, hash, modelos, comandos/códigos e evidências em `plans/validacao.md`; não tratar 34 páginas/67 chunks da pesquisa como prova da persistência atual (R02–R05, SC-001/004/005).

**Checkpoint**: MVP demonstrável após T019. Se API/banco bloquear T019, manter o item
aberto com motivo, sem impedir o avanço dos testes isolados das próximas histórias.
O MVP não encerra a spec, pois US2 e US3 são obrigatórias.

## Fase 4: US2 — Entender por que a ingestão não foi concluída (P2)

**Objetivo**: transformar falhas em diagnóstico acionável, sem segredos, contagens
inventadas ou sucesso indevido. Dependência para integração dos componentes: T017.

**Teste independente**: com amostras e dublês, provocar erros de arquivo/configuração/API/
banco e commit incerto; conferir código não zero, diagnóstico e ausência de sucesso/segredos.

### Testes da US2

- [ ] T020 [P] [US2] Ampliar `tests/test_config.py` com precedência de valor exportado vazio, variável ausente em cada fluxo, URL com senha sentinela, dimensão não positiva/não inteira e erro sem impressão de valores; comprovar ausência de inicialização externa na importação e de exigência de provedor não selecionado (FR-001/008, SC-003).
- [ ] T021 [P] [US2] Ampliar `tests/test_ingest.py` com inexistência, diretório, extensão errada, acesso negado, corrupção, arquivo alterado, PDF digitalizado/sem texto e falhas OpenAI 401/quota/timeout/conectividade; verificar que arquivo inválido não chega ao provedor, cliente é liberado, CLI retorna falha/130 em interrupção e não expõe chave/PDF/traceback bruto (FR-003/008, SC-003).
- [ ] T022 [P] [US2] Ampliar `tests/test_vector_store.py` com conexão/extensão indisponível, timeout, vetor não finito/dimensão ou cardinalidade divergente, falha antes da escrita, desconexão no commit e falha na conferência após commit; conferir ausência de retentativa automática, liberação de engine e resultado indeterminado sem afirmação falsa de rollback ou quantidade (FR-006/008/009, SC-003).

### Implementação da US2

- [ ] T023 [P] [US2] Após T020, ajustar erros específicos de configuração e composição em `src/config.py`, com nomes de variáveis e orientações `.env`/`.env.local`, sem valores de chave/URL sensível, retentativas genéricas ou rastreamento externo implícito (FR-008).
- [ ] T024 [P] [US2] Após T022, distinguir erros de conexão/extensão/manifesto/escrita/conferência em `src/vector_store.py`; manter commit incerto como falha recuperável por reexecução dos mesmos IDs, sem sucesso ou contagem não verificada, sem capturar/silenciar indiscriminadamente exceções (FR-006/008/009).
- [ ] T025 [US2] Após T021/T023/T024, tratar categorias de arquivo/API e fronteira CLI em `src/ingest.py` com exceções específicas, `logging` em stderr, mensagens acionáveis em português e captura ampla somente na fronteira final; sanitizar erros, liberar recursos em interrupção/falha e não transformar operação incompleta em sucesso (FR-006/008).
- [ ] T026 [US2] Após T025, documentar diagnóstico de PDF sem texto/OCR não suportado, credencial, quota, acesso a modelo, porta, prontidão/bootstrap e commit incerto no `README.md`, com efeitos e recuperação sem limpar dados (FR-008/011).
- [ ] T027 [US2] Após T026, executar testes da US2 e casos locais inválido/sem texto/configuração da seção 6 de `specs/001-pdf-ingestion/quickstart.md`; registrar códigos, diagnóstico sanitizado e resultados em `plans/validacao.md`, usando dublês para quota/falhas transitórias sem provocar gastos deliberados (SC-003).

**Checkpoint**: falhas previstas são distinguíveis e seguras; US1 continua aprovada.
Erros nunca são convertidos em recusa factual, cujo comportamento pertence à spec 002.

## Fase 5: US3 — Preservar o conteúdo já preparado (P2)

**Objetivo**: comprovar persistência, reexecução sem duplicatas, isolamento entre destinos
e bloqueio de mistura. Dependência de código: T017/T024/T025; integração exige T019.

**Teste independente**: reutilizar uma base previamente ingerida, reiniciar sem remover
volume e comparar conteúdo; repetir entrada e tentar configurações incompatíveis sem chat.

### Testes da US3

- [ ] T028 [P] [US3] Ampliar `tests/test_vector_store.py` com manifesto persistido ausente/incompatível em collection cheia ou vazia, modelo diferente com mesma dimensão, dimensão/revisão/pipeline/versão distintos, criação concorrente e schema legado com dimensão fixa; provar ausência de embedding/escrita/adoção/limpeza e isolamento de IDs entre collections (FR-009/010, SC-003).
- [ ] T029 [P] [US3] Ampliar `tests/test_ingest.py` com reexecução do mesmo PDF/configuração produzindo mesmos IDs/contagem, trechos textualmente iguais em posições distintas com IDs próprios, outro destino com IDs disjuntos e recuperação após resultado de commit desconhecido; não exigir embeddings bit a bit iguais entre chamadas reais (política adotada de IDs, FR-007/009).

### Implementação e comprovação da US3

- [ ] T030 [US3] Após T028, completar validação/reutilização do manifesto em `src/vector_store.py`: imutável também quando vazio, comparação estrutural do pipeline, falha segura em unicidade concorrente, rejeição de legado sem inferência por dimensão e sem `ALTER TABLE`; expor validação do espaço vetorial reutilizável pela spec 002 sem exigir `PDF_PATH` (FR-009/010).
- [ ] T031 [US3] Após T029/T030, completar recuperação idempotente em `src/ingest.py` e `src/vector_store.py`, preservando namespace da collection nos IDs e upsert sem exclusões; rejeitar PDF/modelo/dimensão/pipeline alterados no mesmo destino antes da API e orientar novo nome; executar regressões US1–US3 sem rede/banco (FR-007/009/010).
- [ ] T032 [US3] Após T031, documentar no `README.md` reingestão e eventual nova cobrança, reindexação integral em nova collection, necessidade de reindexar mesmo com dimensão igual, consumo adicional de espaço e preservação do destino anterior; explicar particularidade da dimensão global da tabela PGVector fixada sem alterar o enunciado (FR-009–011).
- [ ] T033 [US3] Após T032 e integração inicial, executar reingestão real com mesmos IDs/destino e outra collection nomeada explicitamente, além de rejeição de modelo diferente de mesma dimensão, dimensão diferente e PDF alterado na collection original; conferir contagem/IDs e preservação do destino anterior conforme `specs/001-pdf-ingestion/quickstart.md`, registrando evidências em `plans/validacao.md` (FR-009/010 e aceite adicional de IDs).
- [ ] T034 [US3] Após T033, registrar manifesto, quantidade e assinatura de texto/vetores/metadados, executar `docker compose restart postgres`, aguardar saúde e conferir igualdade dos registros em novo processo sem reingerir nem remover volume; registrar comandos/assinaturas e resultados em `plans/validacao.md` usando `specs/001-pdf-ingestion/quickstart.md` (R05, FR-007, SC-002).
- [ ] T035 [US3] Após T034, consolidar em `plans/validacao.md` a conclusão independente da US3, distinção entre assinatura após reinício e vetores recalculados na reingestão, configurações rejeitadas e qualquer bloqueio remanescente; confirmar que nenhuma collection/tabela/volume foi apagada no fluxo normal (FR-007/009/010).

**Checkpoint**: registros sobrevivem ao reinício; reexecução e reindexação respeitam o
contrato, sem misturar espaços ou sobrescrever outro destino. T033–T035 permanecem
abertas se a integração não puder ser executada, mesmo com dublês aprovados.

## Fase 6: Acabamento e verificações transversais

**Objetivo**: tornar o incremento reproduzível e registrar seu limite de entrega.

- [ ] T036 Após T027/T035 e quaisquer correções decorrentes da integração, executar a suíte completa `python -m unittest discover -s tests -v` e `python -m compileall -q src tests`, revisar tipagem pública, SRP/DRY, imports, fechamento de recursos e limites em `src/config.py`, `src/vector_store.py` e `src/ingest.py`; corrigir desvios, repetir as verificações afetadas e registrar resultados finais em `plans/validacao.md` sem acrescentar ferramentas não adotadas; execuções antecipadas são diagnósticas e não concluem este item enquanto a integração estiver pendente.
- [ ] T037 [P] Após T027/T035, revisar `README.md` e `specs/001-pdf-ingestion/quickstart.md` com configuração, comandos de testes efetivamente existentes e resultados esperados coerentes; preservar prompt/regras/exemplos do enunciado e apontar busca/chat/entrega global como trabalho das specs 002/003, sem alegar R06–R09 ou R11 integralmente concluídos.
- [ ] T038 Após T036/T037, reproduzir instalação/configuração/Compose/ingestão pelo `README.md` em ambiente novo e collection exclusiva, fornecendo credencial somente por arquivo ignorado/ambiente; conferir estrutura obrigatória e ausência de segredos no conteúdo versionado conforme `.gitignore`, registrar evidência ou bloqueio em `plans/validacao.md` (FR-011, SC-004; parcela de R11).
- [ ] T039 Após os gates executáveis, verificar convergência com `$speckit-converge` em `specs/001-pdf-ingestion/spec.md`, `specs/001-pdf-ingestion/plan.md` e `specs/001-pdf-ingestion/tasks.md`, confrontando `plans/validacao.md`; acrescentar/cumprir trabalho faltante pelo fluxo SDD, manter bloqueios pendentes e registrar matriz final FR-001–011/SC-001–005/R01–R11 com escopos e limitações reais.

**Gate final**: T036/T037 só são concluídas após US2 e US3 verificadas. A suíte pode ser
executada antes para diagnóstico, sem fechar T036. Se T038/T039 ou uma verificação posterior
exigir alteração de código, repetir T036 e os testes/validações integradas afetados antes
de concluir a funcionalidade. Integração bloqueada mantém T036 pendente, sem impedir
execuções isoladas de diagnóstico nem o levantamento de trabalho restante na convergência.

## Dependências e ordem de execução

### Grafo das fases e histórias

```text
T001 + T002 → Fundação T004–T008 → US1 isolada T009–T018
T003 + US1 isolada + acesso/quota → US1 integrada T019
US1 isolada → US2 T020–T027
US1 isolada + tratamento US2 T024/T025 → US3 isolada T028–T032
T019 + US3 isolada → US3 integrada T033–T035
US1/US2/US3 → verificações transversais T036–T039
```

US1 é o caminho P1. US2 e US3 são ambas P2, dependem do fluxo de ingestão e têm testes
independentes com dublês/amostras. A integração US3 reutiliza dados reais da US1, mas
não depende de busca/chat. Por compartilharem `src/ingest.py`, `src/vector_store.py` e
os arquivos de teste, implementar as histórias sequencialmente; não atribuir suas
alterações simultaneamente sem divisão adicional de arquivos/contratos.

### Dependências por item

| Itens | Pré-requisitos |
| --- | --- |
| T001, T002 | Nenhum; podem ocorrer em paralelo. |
| T003 | T001; não bloqueia testes isolados se houver impedimento externo registrado. |
| T004, T005 | T001 e T002; arquivos de teste distintos. |
| T006 | T004. |
| T007 | T005 e T006. |
| T008 | T006 e T007. |
| T009, T010 | T008. |
| T011 → T012 → T013 | T009, nessa ordem. |
| T014 → T015 → T016 → T017 → T018 | T010 e T013, nessa ordem. |
| T019 | T003 e T018, banco/provedor reais disponíveis e ausência da collection comprovada antes da primeira ingestão. |
| T020, T021, T022 | T017; testes por arquivo, sem dependência entre si. |
| T023 / T024 | T020 / T022, respectivamente. |
| T025 → T026 → T027 | T021, T023 e T024, nessa ordem. |
| T028, T029 | T017, T024 e T025. |
| T030 → T031 → T032 | T028; T031 exige também T029. |
| T033 → T034 → T035 | T019 e T032, nessa ordem. |
| T036 | T027 e T035, após correções da integração; execução antecipada não conclui o gate final. Repetir após alteração posterior de código. |
| T037 | T027 e T035; pode ocorrer junto a T036 em arquivos distintos. |
| T038 | T036, T037 e integração inicial disponível; registrar bloqueio se faltar pré-condição. |
| T039 | Todos os gates anteriores executáveis; não encerra itens bloqueados automaticamente. |

## Exemplos de execução paralela

Os exemplos indicam oportunidades; não autorizam automaticamente criar subagentes na
implementação. Serializar quaisquer tarefas que escrevam o mesmo arquivo, inclusive
`plans/validacao.md`.

### US1

Após T008, elaborar em paralelo T009 (`tests/test_ingest.py`) e T010
(`tests/test_vector_store.py`). Depois, seguir a cadeia T011–T018; T014 espera T010/T013.

### US2

Após T017, elaborar em paralelo T020 (`tests/test_config.py`), T021
(`tests/test_ingest.py`) e T022 (`tests/test_vector_store.py`). Depois de seus testes,
T023 (`src/config.py`) e T024 (`src/vector_store.py`) podem ocorrer em paralelo;
T025 espera ambos e T021. Não iniciar a escrita US3 no mesmo arquivo antes de integrar US2.

### US3

Após o tratamento básico de falhas, elaborar em paralelo T028 (`tests/test_vector_store.py`)
e T029 (`tests/test_ingest.py`). Implementar T030/T031 depois desses contratos, serializando
os arquivos compartilhados. Validações reais T033–T035 são sequenciais.

## Matriz de cobertura

| Requisito | Tarefas principais | Evidência de aceite |
| --- | --- | --- |
| FR-001 | T002, T004, T006, T016, T020 | Configuração por fluxo e sem editar código. |
| FR-002 | T003, T005, T007, T019 | Saúde, bootstrap, extensão e integração inicial. |
| FR-003 | T009, T011, T021, T025, T027 | PDFs reais/sintéticos e diagnósticos negativos. |
| FR-004 | T009, T012, T015 | Splitter real, limites e ausência de embeddings vazios. |
| FR-005 | T010, T012–T016, T019 | Texto/vetor/metadados/IDs associados e conferidos. |
| FR-006 | T010, T014, T017, T022, T024, T025 | Resumo só após confirmação, sem sucesso parcial. |
| FR-007 | T029, T031, T034, T035 | Conteúdo/assinatura preservados entre processos e após reinício. |
| FR-008 | T004, T017, T020–T027 | Casos de falha, códigos de saída e logs sem segredos. |
| FR-009 | T005, T007, T024, T028–T035 | Nenhuma exclusão automática; recuperação e destinos isolados. |
| FR-010 | T005, T007, T013, T028, T030–T033 | Manifesto persistido e bloqueio inclusive com dimensão igual. |
| FR-011 | T001, T002, T018, T026, T032, T037, T038 | README/configuração e ambiente novo reproduzíveis. |
| SC-001 | T010, T014–T019 | Ingestão real confirmada, sem depender do chat. |
| SC-002 | T034, T035 | Comparação exata antes/depois do reinício sem reingestão. |
| SC-003 | T020–T031, T033 | Falhas acionáveis e incompatibilidades sem sucesso indevido. |
| SC-004 | T001–T003, T018, T019, T037, T038 | Instalação e execução pelo guia. |
| SC-005 | T009, T011–T013, T019 | Amostras curtas/longas, página e origem corretas. |
| IDs adotados no plano | T009, T013, T028, T029, T031, T033 | Reingestão sem duplicar; collections com IDs disjuntos. |
| R01–R05, R10 | T001–T019, T034, T038 | Tecnologias, parâmetros, persistência e comandos exigidos. |
| R06–R09; R11 completo | Fora desta spec; delimitar em T037/T039 | Specs 002/003 e conferência pública na entrega global. |

## Estratégia de implementação

1. Antes de escrever código, analisar a consistência SDD. Resolver conflitos documentais
   sem relaxar requisitos acadêmicos ou a constituição.
2. Preparar ambiente/fundação e demonstrar o MVP US1. Sucesso do MVP não conclui a spec.
3. Acrescentar diagnósticos US2 e preservação US3, mantendo regressões anteriores aprovadas.
4. Executar verificações reais e reprodução; registrar modelo, dimensão, hash, collection,
   versões, comandos, códigos, amostras/páginas e limitações. Não incluir a chave no relatório.
5. Verificar convergência. Item só recebe `[x]` após implementação/verificação correspondente;
   se bloqueado por serviço, credencial ou quota, registrar motivo e mantê-lo pendente.

Não implementar busca, prompt, chat, OCR, outro provedor, múltiplos PDFs, limpeza destrutiva
ou publicação como parte destas tarefas. `src/search.py`/`src/chat.py` e o prompt obrigatório
permanecem preservados para as specs seguintes. Não criar commits ou branches implicitamente
durante a geração das tarefas.
