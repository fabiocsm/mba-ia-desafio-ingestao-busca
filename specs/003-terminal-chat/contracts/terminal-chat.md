# Contrato: CLI de chat no terminal

Contrato previsto para a implementação da 003. Complementa o
[contrato de busca da 002](../../002-grounded-search/contracts/search.md).

## Execução e configuração

Comando obrigatório, da raiz e com venv ativo: `python src/chat.py`.
Também permitir importar `src.chat` em testes, sem ler configuração, abrir conexão,
construir clientes ou iniciar interação no import.

A fábrica padrão é `search.search_prompt`. Exigir apenas configuração de consulta
da 002: `OPENAI_API_KEY`, `OPENAI_EMBEDDING_MODEL`, `OPENAI_EMBEDDING_DIMENSIONS`
(padrão 1536), `DATABASE_URL`, `PG_VECTOR_COLLECTION_NAME` e `OPENAI_CHAT_MODEL`.
Não exigir/validar `PDF_PATH`, arquivo original ou credencial Google. Não criar
variáveis de ambiente próprias da CLI. Configuração válida não comprova acesso ao
provedor; sem chamada paga de aquecimento.

## Fronteiras Python

| Operação | Entrada → saída | Responsabilidade |
| --- | --- | --- |
| `main` | Dependências opcionais por nome → `int` | Resolver defaults em runtime, configurar logging, abrir contexto uma vez, executar laço, liberar e traduzir falhas/interrupções para código de processo. |
| `run_chat` | `chain: SearchChain`; `read_question: Callable[[str], str]`, `output: TextIO`, `error_output: TextIO` por nome → `int` | Ler e apresentar; usar cadeia emprestada; 0 em comando de saída, 1 em falha fatal contratada; EOF/Ctrl+C podem propagar para main. |
| Guard do script | `main()` → processo | `raise SystemExit(main())`; não engolir código de falha. |

Parâmetros opcionais de `main`: `chain_factory` com tipo
`Callable[[], AbstractContextManager[SearchChain]] | None`, leitor e streams com os
tipos acima ou `None`. `None` resolve para dependências reais no momento da chamada;
isso permite dublês sem abrir serviços nem depender de patch aplicado após um default
já vinculado. Tipos explícitos, sem `Any` ou interface administrativa nova.

O proprietário usa `with` e fecha recursos uma vez. `run_chat` não chama `close` na
cadeia emprestada; a CLI não fecha stdin/stdout/stderr nem streams de teste.
Fábrica que falha parcialmente preserva a garantia da 002 de liberar o que adquiriu.
Se a liberação falhar, o resultado é falha operacional e código 1.

## Entrada e apresentação

1. Solicitar `PERGUNTA: ` usando o leitor. O leitor real é `input`; ele apresenta o
   prompt em stdout, sem newline. Testes podem gravar o prompt no próprio dublê.
2. Fazer strip da entrada; branco repete a leitura sem invoke.
3. `sair`/`exit` após strip/casefold encerram sem invoke.
4. Invocar uma vez `chain.invoke({"pergunta": question})`; nenhuma chave adicional,
   memória, embedding, SQL ou montagem de prompt na CLI.
5. Exigir string não vazia/branca; apresentar `RESPOSTA: ` mais a string original,
   seguida de newline e linha vazia. Não remover espaços da resposta, resumir,
   reescrever a recusa ou complementar conteúdo.

A recusa `Não tenho informações necessárias para responder sua pergunta.` continua
sendo dado retornado pela busca, sem constante duplicada no chat. Logs não recebem
as perguntas/respostas. Erro operacional nunca é emitido com prefixo `RESPOSTA:`.

## Política de falhas e códigos

| Evento | Saída / continuidade | Código final |
| --- | --- | --- |
| `sair`, `exit`, EOF ou Ctrl+C, inclusive durante consulta/inicialização | Encerrar e liberar; nenhum erro factual ou traceback. Um newline de terminal é permitido; não exigir mensagem de despedida. | 0 se liberação concluir |
| `ConfigurationError` ao abrir | stderr com `Erro ao iniciar o chat: ` e orientação sanitizada existente. Nenhum primeiro prompt. | 1 |
| `StorageError` ao abrir, inclusive base ausente/vazia | Mesmo prefixo de inicialização; mensagem existente orienta Compose/bootstrap ou `python src/ingest.py`, conforme a causa. | 1 |
| `SearchError(retryable=True)` durante consulta | stderr com `Erro na consulta: ` e diagnóstico sanitizado; pedir nova pergunta usando mesma cadeia. Sem repetição automática. | Sessão continua; saída normal posterior é 0 |
| `SearchError(retryable=False)` durante consulta | stderr com mesmo prefixo e orientação; encerrar sem próxima pergunta. | 1 |
| `QuestionError` após entrada válida ou retorno inválido | Falha fatal de contrato, sem resposta parcial; diagnóstico estático seguro. | 1 |
| Exceção inesperada na fábrica, leitor, invoke ou apresentação | `Erro inesperado no chat. Confira a configuração e a disponibilidade dos serviços.` em stderr. Sem mensagem bruta da origem. | 1 |
| Falha ao liberar recursos | Diagnóstico estático `Erro ao encerrar o chat. Não foi possível liberar todos os recursos.` em stderr; não anunciar sucesso nem esconder falha anterior. | 1 |

Mensagens públicas das exceções internas da 002 são sanitizadas pelo produtor, conforme
seu contrato; não aplicar esse tratamento a uma exceção arbitrária. Logging informa
categoria e nível sem `str`/`repr` de erro inesperado, `exc_info` ou traceback. Mensagem
bruta pode conter conexão, chave, SQL, pergunta, PDF ou prompt e não deve ser impressa.
Capturas amplas ficam somente na fronteira CLI, sem capturar `BaseException` genericamente.

Inicialização não recuperável não vira sessão parcialmente funcional. Indisponibilidade
de API detectada no primeiro invoke segue `retryable`, porque não há aquecimento pago.
Quota esgotada não é igual a limite transitório: a decisão já vem de `SearchError`.

Base ausente/vazia na abertura é erro com orientação de ingestão. Recuperação sem
conteúdo após uma abertura válida é string de recusa da busca, exibida normalmente.
Nenhum desses caminhos cria/limpa collection nem modifica arquivos locais.

## Verificação do contrato

`tests/test_chat.py` é previsto, ainda inexistente neste planejamento. Dublês devem
preservar contexto/invoke/exceções e verificar fábrica única, entradas exatas, texto,
streams, códigos, fechamento e ausência de segredos sentinela. Cobrir import e script,
EOF/Ctrl+C na leitura/invoke, falha transitória seguida de sucesso, fatal e falha de
liberação, inclusive após interrupção. Regressão das specs anteriores protege k=10,
prompt, configuração e manifesto sem replicar a implementação no teste da CLI.

Validação real exige sessão de múltiplas perguntas, resultados fundamentados/recusas
e reprodução pelo README. Casos e critérios em [quickstart](../quickstart.md).
