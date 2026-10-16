# Plano de implementação: Chat no terminal e entrega reproduzível

**Branch Git**: `main` (existente; nenhuma branch criada) | **Data**: 2026-10-16

**Spec**: [spec.md](spec.md) | **Identificador Spec Kit**: `003-terminal-chat`

**Entrada**: spec 003, constituição v1.0.0, README, plano inicial e implementações,
contratos e evidências das specs 001/002. Cobertura principal: R09–R11; consolidação
R01–R11. Spec ativa local: `specs/003-terminal-chat` em `.specify/feature.json`.
O setup foi executado com `SPECIFY_FEATURE=main` e diretório explícito; o seletor
persistido é o diretório, independente da branch Git.

**Execução:** implementação e validação local registradas na seção 003 de
[plans/validacao.md](../../plans/validacao.md); candidato público pendente. O texto
a seguir preserva as decisões do planejamento.

## Resumo

Substituir o esqueleto de `src/chat.py` por uma CLI sequencial que inicializa uma única
`SearchChain`, lê `PERGUNTA: `, chama `invoke({"pergunta": texto})` e apresenta
`RESPOSTA: ` sem alterar a string retornada. Ignorar branco, aceitar `sair`/`exit`,
EOF e Ctrl+C como encerramento normal e liberar recursos. Falhas transitórias aceitam
nova pergunta; falhas fatais encerram com código 1 e diagnóstico seguro.

Reutilizar a busca fundamentada da 002, sem SQL, prompt, embeddings ou histórico na
CLI. Consolidar README, validação integrada, reprodução em ambiente novo e evidências
R01–R11, incluindo visibilidade pública e origem do fork. O planejamento não declara
essa entrega já validada e termina antes de gerar tarefas ou implementar código.

## Contexto técnico

| Aspecto | Decisão |
| --- | --- |
| Linguagem/versão | CPython **3.12.12**, reconfirmado no venv durante o planejamento. |
| Dependências | Manter todos os pins; LangChain 0.3.27, core 0.3.74, langchain-openai 0.3.30, langchain-postgres 0.0.15, openai 1.102.0, SQLAlchemy 2.0.43 e psycopg 3.2.9. Apenas stdlib nova na CLI. |
| Provedor/modelos | OpenAI, embeddings `text-embedding-3-small`/1536, chat `gpt-6-luna`; escolhas e fontes oficiais da 002 preservadas, com uso real registrado em 2026-10-16. Reconfirmar acesso/alias na bateria final. |
| Configuração | `search_prompt()` usa `load_settings(ingestion=False, require_chat=True)`; ambiente exportado (inclusive vazio) > `.env.local` > `.env`. Chat sem PDF_PATH/Google e sem variáveis novas. |
| Armazenamento | PostgreSQL 17/pgVector pelo Compose; consulta protegida para leitura já implementada. Nenhuma tabela, collection ou persistência de conversa nova. |
| Tipo/plataforma | CLI local síncrona, executada da raiz; macOS arm64 previamente validado. Não alegar execução Linux sem evidência. |
| Testes | `unittest`/`unittest.mock`, `io.StringIO`, leitor/cadeia dublês, subprocesso isolado para entrypoint. `tests/test_chat.py` implementado na execução da 003. |
| Verificadores | Comandos existentes: unittest discover, compileall, pip check e git diff --check; sem ferramenta/dependência adicional. |
| Desempenho | Uma cadeia por sessão; perguntas sequenciais, um invoke por pergunta válida; nenhum invoke para branco/saída. Sem meta arbitrária de latência. |
| Limites herdados | API 60 s por requisição, zero retries, geração 2048 tokens incluindo raciocínio. Banco: conexão/pool 10 s, statement 30 s, lock 5 s. Não constituem prazo global. |
| Escala/escopo | Um PDF, um provedor, um terminal; sem histórico factual, web, OCR, streaming, concorrência ou novo modelo verificador. |

## Verificação da constituição

Gate avaliado antes da pesquisa e reavaliado após o desenho: **aprovado no desenho**.
Nenhuma exceção normativa ou emenda é necessária. Aceite da implementação e da entrega
depende das verificações futuras, não deste gate documental.

| Princípio | Antes da pesquisa | Após o desenho / evidência prevista |
| --- | --- | --- |
| I — requisitos/escopo | CLI e entrega previstos na 003. | Comandos/estrutura mantidos; um PDF/provedor; matriz R01–R11 abaixo. |
| II — fundamentação | Reutilizar contrato 002. | String/recusa preservadas; sem memória, filtro ou interpretação; bateria factual/negativa real. |
| III — SOLID/DRY | Interação em chat, consulta em search. | `run_chat`/`main`, parâmetros injetáveis; config/prompt/recusa/erros nas fontes existentes. Sem classe ou camada nova. |
| IV — Python | Tipos, import sem serviços, recursos liberados. | Import dual como demais scripts; with no proprietário; capturas específicas e fronteira genérica segura. |
| V — LangChain | Contrato invoke e uma cadeia por sessão. | Instância única, clientes reutilizados; branco sem consulta; k=10 permanece na busca. |
| VI — integridade | Nenhuma escrita na CLI. | Mesmo manifesto/modelo/dimensão; reindexação em destino novo explícito; volumes preservados. |
| VII — operação | Diagnóstico e saída previsíveis. | Sem PDF/Google; zero retries; códigos 0/1; EOF/Ctrl+C normais; sanitização e tracing explícito. |
| VIII — evidência | Isolados e reais distintos. | Matriz de cenários, relatório 003, reprodução nova e acesso público; bloqueios pendentes. |

## Estrutura do projeto

### Documentação da funcionalidade

```text
specs/003-terminal-chat/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/terminal-chat.md
├── quickstart.md
└── checklists/requirements.md
```

`tasks.md` foi produzido na etapa seguinte por `$speckit-tasks`; não é saída do planejamento.
A seleção local `.specify/feature.json` é ignorada pelo Git, conforme configuração
existente: persiste neste checkout, sem tornar a seleção um artefato versionado.

### Código e documentos afetados na implementação

```text
src/
├── chat.py              # implementar laço, composição e fronteira de erros
├── search.py            # reutilizar SearchChain/search_prompt/SearchError
├── config.py            # reutilizar configuração por fluxo
├── vector_store.py      # preservar abertura protegida
└── ingest.py            # preservar ingestão
tests/
├── test_chat.py         # novo, previsto
├── test_search.py       # regressão existente
├── test_config.py
├── test_vector_store.py
└── test_ingest.py
README.md               # completar uso/diagnóstico/exemplos do chat
.env.example            # conferir suficiência, sem novas variáveis previstas
plans/validacao.md       # acrescentar seção 003 e consolidação R01–R11
```

Preservar `requirements.txt`, Compose e PDF. Não criar pacote de serviços, repositório
abstrato, nova classe de sessão ou framework de CLI. A organização atual comporta o fluxo.

## Fase 0 — Pesquisa

[research.md](research.md) resolve interação, ciclo de vida, erros, teste e reprodução.
A pesquisa delegada confirmou que `SearchError.retryable` e o contexto da cadeia já
atendem a CLI; o import absoluto e a verificação `if not chain` do stub serão substituídos.
Não restou decisão técnica aberta. Credencial, infraestrutura e acesso público são
dependências das verificações futuras.

## Fase 1 — Desenho e contratos

### Composição e ciclo de vida

`main(...) -> int` resolve dependências opcionais no momento da chamada, prepara logging
e entra em um único contexto retornado por `search_prompt()`. Somente depois do sucesso
da abertura inicia `run_chat`. Fábrica contextual, leitor e streams são injetáveis para
testes; a CLI real usa `input`, `sys.stdout` e `sys.stderr`. Um guard de módulo chama
`raise SystemExit(main())`, preservando o código. Importar `src.chat` não executa nada.

`run_chat(chain, *, read_question, output, error_output) -> int` recebe a cadeia
emprestada, lê entradas e retorna o código da sessão. `main` é o proprietário do contexto;
não há fechamento duplicado no laço. A cadeia já coordena recursos e construção parcial.
Não gerar aquecimento pago. Configuração/banco são validados ao abrir; acesso ao provedor
é comprovado pela consulta, cujas falhas seguem o contrato da 002.

### Interação

1. Ler com prompt `PERGUNTA: `; o leitor é responsável por apresentá-lo.
2. Aplicar `strip()` apenas à entrada. Se vazia, voltar à leitura sem invoke.
3. Se `casefold()` corresponder a `sair`/`exit`, terminar normalmente sem invoke.
4. Invocar uma vez `chain.invoke({"pergunta": question})`. Não enviar histórico.
5. Conferir saída string não vazia/branca; formato inválido é falha fatal de contrato.
6. Mostrar `RESPOSTA: ` com o conteúdo integral retornado e linha em branco separadora.
   A recusa vem da busca; não duplicar sua constante nem alterar a resposta.
7. Em falha transitória, mostrar erro operacional e pedir outra pergunta na mesma cadeia.
   A entrada anterior não é reenviada nem usada como contexto.

### Encerramento, erros e logs

[contracts/terminal-chat.md](contracts/terminal-chat.md) fixa mensagens, streams e códigos.
`sair`, `exit`, EOF e Ctrl+C retornam 0, inclusive interrupção na inicialização/consulta,
desde que a liberação termine sem falha. Ctrl+C não é capturado como resposta ou usado
para continuar na cadeia interrompida. Erro durante liberação retorna 1 e não anuncia
encerramento bem sucedido. Não suprimir silenciosamente falhas de recursos.

Inicialização: `ConfigurationError`/`StorageError` encerram em 1 e preservam a orientação
sanitizada; base ausente/vazia aponta para ingestão. Consulta: `SearchError.retryable=True`
permite nova pergunta; `False` encerra em 1. `QuestionError` após entrada válida e saída
inesperada são falhas fatais de contrato. Exceção imprevista recebe diagnóstico estático
na fronteira CLI, sem exceção bruta ou traceback; `except Exception` só nessa fronteira.

Erros vão para stderr, nunca para `RESPOSTA:`. Logging usa nível/categoria operacional;
não registrar perguntas, respostas, PDF, prompt, senha, URL completa ou stack com dados.
Os erros internos sanitizados da 002 podem ter sua mensagem pública exibida; não copiar
a classificação de SDK/SQLAlchemy para o chat. Não habilitar tracing implicitamente.

### Documentação e entrega

Atualizar a seção de solução implementada do README após implementação, preservando
enunciado, prompt e exemplos obrigatórios. Documentar ambiente, configuração por fluxo,
ordem de execução, códigos/saídas, custos/retries, exemplos reais com páginas, diagnóstico,
testes existentes e limitações. Manter política atual de upsert e reindexação: novo
modelo/PDF exige destino novo explícito; sem exclusão automática ou comando de limpeza.

Acrescentar seção 003 no relatório, sem sobrescrever evidências 001/002. Registrar revisão,
ambiente, pins/modelos solicitados/devolvidos, hash do PDF, collection, comandos/códigos,
sessões/erros e sustentação de cada fato nos chunks da própria consulta. Um consumidor
de validação pode observar a busca delegada sem mudar a CLI de produção ou habilitar
tracing. Não executar segunda busca para presumir quais chunks sustentaram a resposta.

Reprodução: clone separado e venv novo, somente arquivos públicos e credencial fornecida
pelos meios documentados. Confirmar Python antes da instalação. Bootstrap novo deve usar
projeto Compose/volume separado e porta livre por override de validação documentado;
não interferir no volume existente. Registrar qualquer etapa não executada. Conferir
origem do fork `devfullcycle/mba-ia-desafio-ingestao-busca`, visibilidade pública e acesso
anônimo, além de segredos em arquivos versionados/histórico, sem imprimir valores.
Problema de visibilidade/publicação deve permanecer pendente até resolução autorizada.

### Matriz de aceite da spec 003

| Requisitos | Cenários/verificação | Critérios |
| --- | --- | --- |
| FR-001/002 | Três perguntas em uma sessão; prompt, prefixos, separadores, fábrica/contexto únicos; invocações corretas. | SC-001 |
| FR-003/004 | Vazio/branco, caixa/espaços em comandos, EOF/Ctrl+C na leitura e Ctrl+C na consulta; fechamento e código 0. | SC-002 |
| FR-005 | String/Unicode/recusa preservados; sem complemento/histórico; saída inválida gera erro. | SC-001/006 |
| FR-006 | Configuração, base ausente/vazia e banco indisponível na abertura: nenhum primeiro prompt, orientação e código 1. | SC-003 |
| FR-007 | Transiente seguido de sucesso na mesma cadeia; fatal impede pergunta seguinte; liberação que falha retorna 1. | SC-003 |
| FR-008 | Sentinelas em exceção inesperada de fábrica/invoke/fechamento ausentes de stdout/stderr/log; sem traceback. | SC-003/007 |
| FR-009/010 | README executado em clone/venv novos; configuração só documentada, diagnóstico, reexecução e efeitos de reindexação. | SC-004 |
| FR-011/012 | Três fatos, três ausências, opinião/desvio pela CLI; relatório com resultados e trechos/páginas da própria recuperação. Vazio/arquivo inválido/persistência por evidência válida ou repetição. | SC-005/006 |
| FR-013 | Matriz R01–R11, arquivos, fork, acesso anônimo e inspeção de segredos. | SC-005/007 |
| FR-014 | Falta de credencial/serviço/acesso ou verificação não feita deixa critério pendente com motivo. | SC-005 |
| FR-015 | Inicialização/consulta sem PDF original e sem chave Google; configuração herdada e teste pela CLI. | SC-004 |

Testes novos protegem a fronteira da CLI sem replicar toda a suíte da busca. Dublês
comprovam transiente seguido de sucesso sem provocar falhas cobradas. Entry point em
subprocesso deve comprovar código não zero em configuração inválida usando `OPENAI_API_KEY` exportada vazia (prevalece inclusive sobre arquivos locais);
mudar somente cwd não isola .env, cuja raiz vem do módulo de configuração. Importações
devem continuar sem efeitos externos.
Nenhum teste de chat é alegado disponível antes da implementação.

### Consolidação R01–R11

| ID | Evidência existente / verificação de entrega |
| --- | --- |
| R01 | 001/002: Python/LangChain reais; confirmar runtime, instalação nova e imports do chat. |
| R02 | 001/002: Compose, bootstrap/vector e leitura; confirmar bootstrap em banco novo e saúde na reprodução. |
| R03 | 001: PDF válido e rejeições; executar ingestão conforme README em ambiente novo. |
| R04 | 001: splitter 1000/150/len e metadados; manter regressão e referência. |
| R05 | 001/002: 67 chunks, vetores/manifesto/IDs e persistência; nova ingestão e conferência na reprodução, sem limpeza. |
| R06 | 002: embedding da pergunta/k=10 e 1–9 resultados; proteger regressão e comprovar delegação do chat. |
| R07 | 002: contexto/prompt/geração; regressão e bateria pela CLI, sem montagem paralela. |
| R08 | 002: P1–P3/N1–N3/O1/A1/C1–C4; bateria final da CLI, conferir fatos e recusa exata. |
| R09 | Novo: laço/entradas/erros/saídas e sessão com três perguntas, isolado e terminal real. |
| R10 | Conferir arquivos obrigatórios e comandos da raiz, incluindo chat, em ambiente novo. |
| R11 | README completo, fork, visibilidade pública/acesso anônimo e ausência de segredos verificados no candidato. |

## Sequência e limites do planejamento

Seguir com `$speckit-tasks`, `$speckit-analyze`, implementação e convergência. A ordem
prevista é testes/CLI básica → erros/recursos → documentação → bateria/reprodução →
conferência da entrega e convergência; tarefas concretas serão geradas na próxima etapa.

Pesquisa e desenho completos; nenhuma violação constitucional ou decisão em aberto.
Não foram executados testes de comportamento do chat, chamadas reais, reprodução nova
ou verificação pública nesta etapa documental.

Verificação do planejamento executada: `check-prerequisites.sh --json --require-spec`
encontrou os quatro grupos de artefatos; `--json --paths-only`, sem override de ambiente,
resolveu a 003 persistida. Links locais, blocos Markdown e ausência de placeholders
pendentes foram conferidos nos cinco arquivos gerados; `git diff --check` passou.
Rechecado `.specify/extensions.yml` após o desenho: inexistente, assim como na checagem
anterior; nenhum hook pré/pós-plan registrado para despachar.
