# Pesquisa: Chat no terminal e entrega reproduzível (003)

**Data**: 2026-10-16. Fontes normativas: [spec](spec.md),
[constituição](../../.specify/memory/constitution.md) e [README](../../README.md).
Pesquisa da CLI delegada para leitura dos contratos e documentação Python;
consolidação de reprodução/evidências feita sobre o repositório atual.
Não houve consulta paga, conexão ao banco ou alteração de dependências nesta etapa.

## 1. Continuidade da solução validada

**Decisão:** manter CPython 3.12.12, pins de `requirements.txt`, OpenAI,
`text-embedding-3-small` com 1536 dimensões e `OPENAI_CHAT_MODEL=gpt-6-luna`.
Reutilizar `search_prompt()` e sua `SearchChain`, sem alterar a busca ou a ingestão.

**Justificativa:** `venv/bin/python --version` reconfirmou 3.12.12 no planejamento.
A seção 002 de [plans/validacao.md](../../plans/validacao.md) registra uso real desses
modelos, parâmetros e versões, incluindo respostas, manifesto e fechamento. A 003
integra esse componente ao terminal; não escolhe outro modelo nem atualiza SDK.
Disponibilidade/acesso/quota devem ser reconfirmados pela execução integrada; o alias
pode mudar. Não se presume gratuidade nem suporte validado a outros ambientes.

**Alternativas consideradas:** segundo provedor, novo framework de CLI ou migração de
LangChain não resolvem uma necessidade deste escopo. Reindexação não é necessária para
acrescentar a interface de terminal.

**Fontes:** [contrato da busca](../002-grounded-search/contracts/search.md),
[pesquisa da 002 e fontes oficiais dos modelos](../002-grounded-search/research.md),
`src/config.py`, `src/search.py` e registro de validação existente.

## 2. Entrada, apresentação e encerramento

**Decisão:** usar `input("PERGUNTA: ")` em laço síncrono, normalizar somente espaços
externos da entrada e reconhecer `sair`/`exit` com `casefold()`. Ignorar branco antes
de invocar. Mostrar `RESPOSTA: ` seguido da string recebida, sem modificar seu conteúdo,
e uma linha em branco entre interações. Saídas normais retornam código 0.

**Justificativa:** atende FR-001–005 sem dependências novas. `input` retira o newline
da leitura e levanta `EOFError` no fim da entrada. `KeyboardInterrupt` deve ser tratado
explicitamente, inclusive durante inicialização/consulta, como encerramento normal do
chat. O stub atual não implementa laço, retorno de processo ou liberação e testa uma
cadeia falsa que o contrato da 002 não prevê; será substituído na implementação.

**Alternativas consideradas:** `argparse` não é necessário sem argumentos; streaming,
threads e bibliotecas de terminal ampliariam os estados sem requisito. Não armazenar
histórico de perguntas/respostas nem completar saídas com texto gerado pela CLI.

**Fontes:** `src/chat.py`, spec FR-001–005 e documentação Python 3.12 de
[input](https://docs.python.org/3.12/library/functions.html#input) e
[exceções](https://docs.python.org/3.12/library/exceptions.html).

## 3. Propriedade de recursos e injeção para testes

**Decisão:** `main` constrói uma cadeia pelo contexto `with search_prompt() as chain`,
uma vez; `run_chat` usa a cadeia emprestada e cuida só da interação. Injetar fábrica,
leitor e streams para testes; resolver defaults na execução. Usar os tipos concretos
existentes e callables, sem hierarquia nova. Permitir importação `src.chat` e execução
direta `python src/chat.py`, seguindo o padrão dos demais módulos.

**Justificativa:** a cadeia já é context manager e possui `close` idempotente. O contexto
fecha recursos em sucesso, exceção, EOF e Ctrl+C; a fábrica já libera construção parcial.
O laço não deve fechar recurso emprestado nem recriá-lo depois de cada pergunta.
Importar o módulo não deve carregar configuração, construir clientes ou abrir conexão.

**Alternativas consideradas:** `atexit`, globals e coleta de lixo não tornam a liberação
previsível. Outra classe de sessão repetiria a responsabilidade de `SearchChain`.

**Fontes:** `src/search.py`, contrato 002 e
[contextlib](https://docs.python.org/3.12/library/contextlib.html#contextlib.ExitStack),
além da semântica de [with](https://docs.python.org/3.12/reference/compound_stmts.html#the-with-statement).

## 4. Falhas operacionais e segurança

**Decisão:** consumir `SearchError.retryable` para aceitar outra pergunta ou encerrar
com código 1. Não repetir automaticamente a pergunta. Tratar `ConfigurationError` e
`StorageError` na inicialização com os diagnósticos sanitizados já contratados.
Captura ampla somente na fronteira CLI; erro inesperado produz mensagem estática,
sem `str(error)`, traceback ou `exc_info`. Erro de liberação também impede código 0.

**Justificativa:** a busca já distingue timeout/conexão/limite transitório de quota,
credencial/modelo inválido, incompatibilidade e saída inválida. Inicialização falha
mesmo se a causa for transitória: não há sessão utilizável nesse ponto. Base vazia ou
ausente orienta ingestão; recuperação vazia depois de abertura válida é recusa factual
da busca. Esses casos não podem ser confundidos pela CLI.

O preflight existente valida configuração e banco, mas não faz requisição paga para
testar credencial/modelo. A CLI não promete detectar indisponibilidade do provedor
antes da primeira consulta. Falhas detectadas na inicialização encerram sem conversa;
as detectadas no primeiro `invoke` seguem a classificação da busca. Isso atende os
cenários da spec sem introduzir chamada de aquecimento ou esconder erros.

**Alternativas consideradas:** analisar texto da exceção seria frágil; copiar a matriz
do SDK para a CLI duplicaria regras. Tratar todo erro como recusa violaria R08. Exibir
exceção inesperada bruta poderia expor chaves, conexão, pergunta ou documento.

**Fontes:** `src/search.py`, `src/config.py`, `src/vector_store.py`,
[contrato 002](../002-grounded-search/contracts/search.md) e constituição IV/V/VII.

## 5. Verificação e reprodução da entrega

**Decisão:** manter `unittest`, `unittest.mock`, `compileall`, `pip check` e
`git diff --check`. Planejar `tests/test_chat.py` com cadeia/leitor/streams dublês;
testar também o entrypoint em subprocesso sem credenciais e sem serviços. Reexecutar
a bateria factual pela CLI e registrar uma seção 003 no relatório existente.

**Justificativa:** há 61 testes aprovados no registro da 002, mas nenhum teste de chat.
Dublês provam interação e contratos, não fundamentação do modelo. A prova nova inclui
sessão com pelo menos três perguntas, branco/saídas/interrupções, continuidade após
falha transitória e execução do README em clone e ambiente virtual novos. Evidência
de persistência/PDF inválido da 001/002 pode ser referenciada se continuar aplicável.

Reprodução usará credencial fornecida por ambiente, `.env` documentado e um nome de
collection novo, explicitamente escolhido e comprovadamente ausente. Se o banco atual
for reutilizado, registrar esse limite: isso não comprova bootstrap em banco novo.
Para validar também o bootstrap, usar projeto Compose separado e porta livre, por
override local documentado, sem remover volumes nem parar a base existente.

**Alternativas consideradas:** novo test runner/scanner não é necessário. Só consultar
programaticamente repetiria a 002 sem provar R09. Só trocar o venv sem clone/isolamento
de configuração não comprova reprodução pública.

**Fontes:** `tests/test_search.py`, README (verificadores adotados),
[unittest](https://docs.python.org/3.12/library/unittest.html),
[unittest.mock](https://docs.python.org/3.12/library/unittest.mock.html#where-to-patch),
[quickstart da 001](../001-pdf-ingestion/quickstart.md) e relatório existente.

## 6. Visibilidade, fork e rastreabilidade

**Decisão:** conferir origin e metadados públicos do GitHub, origem do fork exigido,
acesso anônimo, estrutura e ausência de segredos em arquivos versionados/histórico.
Acrescentar matriz consolidada R01–R11 com status, comando, código, revisão e evidência.
Não publicar nem alterar visibilidade automaticamente como parte do planejamento.

**Justificativa:** R11 não é comprovado por testes locais nem por acesso autenticado.
O relatório da 002 deixa R09/R10 global/R11 pendentes. Falta de acesso, credencial ou
evidência futura é dependência de execução e deve manter o critério pendente.

**Alternativas consideradas:** inferir fork apenas pelo nome do remoto ou declarar
entrega aprovada porque os testes passaram não atende SC-005/007.

**Fontes:** spec FR-009–014, README (entregável), matriz R01–R11 do
[plano inicial](../../plans/plano-implementacao.md) e relatório existente.

## Resultado da pesquisa

Decisões técnicas resolvidas, sem necessidade de alterar a spec ou a constituição.
Integração da CLI, reprodução nova e conferência pública são verificações futuras,
não resultados executados neste planejamento. Hooks: `.specify/extensions.yml`
inexistente na verificação anterior ao planejamento.
