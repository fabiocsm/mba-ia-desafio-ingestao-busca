# Modelo de dados: Chat no terminal (003)

Desenho previsto; não introduz tabelas, arquivos de histórico ou novas classes de domínio.
Os dados abaixo descrevem contratos em memória e registros documentais, não estruturas
que precisem virar dataclasses. Fonte: [spec](spec.md) e [contrato](contracts/terminal-chat.md).

## Sessão de terminal

| Campo conceitual | Tipo / regra |
| --- | --- |
| `chain` | `SearchChain`, criada uma vez e possuída por `main`; emprestada ao laço. |
| `read_question` | `Callable[[str], str]`; recebe o prompt e retorna entrada; pode levantar EOF/Ctrl+C. |
| `output` / `error_output` | `TextIO`; respostas em stdout, erros em stderr; streams emprestados, não fechados pela CLI. |
| `state` | Conceitual: inicializando, aguardando, consultando, encerrando, encerrada ou falha. Não exige enum/campo persistido. |
| `exit_code` | `int`: 0 para saída normal, 1 para falha fatal, inclusive liberação que falha. |

Relacionamento: uma sessão tem uma cadeia e zero ou mais interações sequenciais.
Nenhuma pergunta/resposta anterior é enviada como contexto. Referências temporárias
da interação atual não constituem memória conversacional.

### Transições

| Estado/evento | Próximo estado / ação |
| --- | --- |
| Inicializando / fábrica bem sucedida | Aguardando; recursos abertos, nenhum aquecimento pago. |
| Inicializando / configuração, base ou serviço falha | Falha; fechar recursos parcialmente adquiridos; código 1, sem prompt. |
| Aguardando / entrada branca | Aguardando; zero invocações. |
| Aguardando / `sair` ou `exit` após strip/casefold | Encerrando; zero invocações. |
| Aguardando / pergunta válida | Consultando; um invoke com chave única `pergunta`. |
| Consultando / string válida | Aguardar após apresentar resposta integral e separador. |
| Consultando / erro transitório | Aguardar após diagnóstico; não reenviar pergunta. |
| Consultando / erro fatal, QuestionError ou saída inválida | Falha; diagnóstico e liberação; código 1. |
| Inicializando, aguardando ou consultando / EOF ou Ctrl+C | Encerrando; não reutilizar cadeia interrompida. |
| Encerrando / liberação concluída | Encerrada; código 0. |
| Qualquer saída / liberação falha | Falha; diagnóstico seguro, código 1. |

Não capturar `BaseException` genericamente. EOF/Ctrl+C são casos explícitos; falhas de
liberação não podem ser convertidas em encerramento normal.

## Interação atual

| Campo | Tipo / validação |
| --- | --- |
| `raw_input` | `str` recebida do leitor; nunca registrada nos logs padrão. |
| `question` | `raw_input.strip()`; não vazia, diferente de comandos de saída sem distinguir caixa. |
| `request` | Mapping com somente `{"pergunta": question}`; sem histórico ou contexto fornecido pela CLI. |
| `answer` | `str` não vazia/branca; exibir integralmente sem novo strip, resumo ou complemento. |
| `operational_error` | Exceção, não resposta; só mensagens internas sanitizadas são públicas. |

Uma interação concluída tem resposta ou erro, nunca ambos. Resposta válida inclui a
recusa factual da busca, apresentada com o mesmo prefixo das demais. `None`, bloco,
número e string branca são falhas fatais de contrato; não converter com `str(...)`.

## Configuração documentada

Reutilizar `Settings` da 002; nenhum estado global novo. Chave OpenAI, modelo/dimensão
de embeddings, collection, conexão e modelo de chat vêm da configuração compartilhada.
`PDF_PATH` e chave Google não são requisitos do chat. A identidade de embeddings e o
manifesto permanecem os descritos nas specs 001/002. A CLI não os recalcula nem modifica.

## Evidência de entrega

Registro em `plans/validacao.md`, não banco de dados. Cada verificação contém:

| Campo | Regra |
| --- | --- |
| Identificação | ID de requisito R/FR/SC, cenário, spec produtora e revisão avaliada. |
| Ambiente | Data, plataforma, Python/pins, serviços, modelos solicitados e devolvidos. |
| Dados de execução | Collection, identidade do PDF quando aplicável, comando, código de saída e resultado observado. |
| Sustentação | Para fatos: pergunta/resposta, trecho/ID/página dos chunks da mesma consulta; página humana = índice + 1. |
| Status | Aprovado, reprovado ou pendente; pendência inclui motivo/dependência e próximo passo. |
| Origem da prova | Execução nova ou referência precisa a evidência válida da 001/002, com justificativa de aplicabilidade. |

O relatório pode incluir perguntas e excertos selecionados para avaliação, revisados
explicitamente; isso não autoriza logs automáticos de conteúdo na aplicação. Nunca
incluir credenciais ou URL com senha. Isolados não comprovam qualidade do modelo;
verificação não executada permanece pendente. Não declarar ausência absoluta de alucinações.
