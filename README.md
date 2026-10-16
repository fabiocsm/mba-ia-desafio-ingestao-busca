# Ingestão e Busca Semântica com LangChain e Postgres

## Objetivo

Você deve entregar um software capaz de:

- Ingestão: Ler um arquivo PDF e salvar suas informações em um banco de dados PostgreSQL com extensão pgVector.
- Busca: Permitir que o usuário faça perguntas via linha de comando (CLI) e receba respostas baseadas apenas no conteúdo do PDF.

## Exemplo no CLI

Faça sua pergunta:

```
PERGUNTA: Qual o faturamento da Empresa SuperTechIABrazil?
RESPOSTA: O faturamento foi de 10 milhões de reais.

---

Perguntas fora do contexto:

PERGUNTA: Quantos clientes temos em 2024?
RESPOSTA: Não tenho informações necessárias para responder sua pergunta.
```

## Tecnologias obrigatórias

- Linguagem: Python
- Framework: LangChain
- Banco de dados: PostgreSQL + pgVector
- Execução do banco de dados: Docker & Docker Compose (docker-compose fornecido no repositório de exemplo)

## Pacotes recomendados

- Split: `from langchain_text_splitters import RecursiveCharacterTextSplitter`
- Embeddings (OpenAI): `from langchain_openai import OpenAIEmbeddings`
- Embeddings (Gemini): `from langchain_google_genai import GoogleGenerativeAIEmbeddings`
- PDF: `from langchain_community.document_loaders import PyPDFLoader`
- Ingestão: `from langchain_postgres import PGVector`
- Busca: `similarity_search_with_score(query, k=10)`

## OpenAI

- Crie uma API Key da OpenAI.
- Você vai precisar de um modelo de embeddings e de um modelo de LLM para responder. Consulte a documentação oficial da OpenAI para ver os modelos disponíveis.

## Gemini

- Crie uma API Key da Google.
- Você vai precisar de um modelo de embeddings e de um modelo de LLM para responder. Consulte a documentação oficial do Google para ver os modelos disponíveis.

Os limites de requisições gratuitas dos modelos podem mudar com frequência. Para informações atualizadas, consulte a documentação oficial do Google.

## Escolha dos modelos

Este desafio não fixa modelos. Nomes e versões mudam com frequência e alguns são descontinuados, então faz parte do desafio consultar a documentação oficial do provedor que você escolher, ver quais modelos estão disponíveis no momento e selecionar os que atendem ao objetivo. Para o volume deste desafio, os modelos mais leves e baratos de cada provedor são suficientes.

Atenção: modelos de embedding diferentes geram vetores com dimensões diferentes. A tabela de vetores é criada na primeira ingestão, já com a dimensão do modelo que você escolheu. Se você trocar de modelo de embeddings depois disso, a ingestão passa a falhar por incompatibilidade de dimensão. Nesse caso é responsabilidade sua apagar a collection existente (ou o volume do banco) e refazer a ingestão do zero com o novo modelo.

## Requisitos

### 1. Ingestão do PDF

- O PDF deve ser dividido em chunks de 1000 caracteres com overlap de 150.
- Cada chunk deve ser convertido em embedding.
- Os vetores devem ser armazenados no banco de dados PostgreSQL com pgVector.

### 2. Consulta via CLI

Criar um script Python para simular um chat no terminal.

Passos ao receber uma pergunta:

- Vetorizar a pergunta.
- Buscar os 10 resultados mais relevantes (k=10) no banco vetorial.
- Montar o prompt e chamar a LLM.
- Retornar a resposta ao usuário.

Prompt a ser utilizado:

```
CONTEXTO:
{resultados concatenados do banco de dados}

REGRAS:
- Responda somente com base no CONTEXTO.
- Se a informação não estiver explicitamente no CONTEXTO, responda:
  "Não tenho informações necessárias para responder sua pergunta."
- Nunca invente ou use conhecimento externo.
- Nunca produza opiniões ou interpretações além do que está escrito.

EXEMPLOS DE PERGUNTAS FORA DO CONTEXTO:
Pergunta: "Qual é a capital da França?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

Pergunta: "Quantos clientes temos em 2024?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

Pergunta: "Você acha isso bom ou ruim?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

PERGUNTA DO USUÁRIO:
{pergunta do usuário}

RESPONDA A "PERGUNTA DO USUÁRIO"
```

## Estrutura obrigatória do projeto

Faça um fork do repositório para utilizar a estrutura abaixo: https://github.com/devfullcycle/mba-ia-desafio-ingestao-busca

```
├── docker-compose.yml
├── requirements.txt      # Dependências
├── .env.example          # Template das variáveis de ambiente
├── src/
│   ├── ingest.py         # Script de ingestão do PDF
│   ├── search.py         # Script de busca
│   ├── chat.py           # CLI para interação com usuário
├── document.pdf          # PDF para ingestão
└── README.md             # Instruções de execução
```

## VirtualEnv para Python

Crie e ative um ambiente virtual antes de instalar dependências:

```
python3 -m venv venv
source venv/bin/activate
```

## Ordem de execução

1. Subir o banco de dados:

```
docker compose up -d
```

2. Executar ingestão do PDF:

```
python src/ingest.py
```

3. Rodar o chat:

```
python src/chat.py
```

## Entregável

Repositório público no GitHub contendo todo o código-fonte e README com instruções claras de execução do projeto.

## Desenvolvimento com Spec Kit (SDD)

Este repositório foi inicializado com o [GitHub Spec Kit](https://github.com/github/spec-kit), usando `specify-cli` **1.0.8**, integração **Codex** e scripts Bash. A instalação da ferramenta é independente do ambiente virtual e das dependências Python da aplicação.

Arquivos do fluxo:

- `.agents/skills/speckit-*/SKILL.md`: skills SDD para o Codex.
- `.specify/templates/`: templates de especificação, planejamento, tarefas e checklists.
- `.specify/scripts/bash/`: scripts auxiliares do fluxo.
- `.specify/memory/constitution.md`: constituição v1.0.0 com os princípios, restrições e critérios de qualidade do projeto.
- `.specify/workflows/`: definição do workflow SDD.
- `specs/`: diretório criado ao especificar uma funcionalidade, contendo seus artefatos SDD.

Para instalar a mesma versão da CLI em outra máquina com [uv](https://docs.astral.sh/uv/) e Python 3.11 ou superior:

```bash
uv tool install specify-cli==1.0.8
specify version
specify integration status --json
```

Execute a verificação da integração na raiz deste repositório. Os arquivos de inicialização já estão presentes; após clonar, não é necessário executar `specify init` novamente.

### Fluxo no chat do Codex

Abra o projeto no Codex. Se as novas skills ainda não aparecerem na sessão atual, abra uma nova sessão no repositório. Invoque cada etapa separadamente e revise os artefatos antes de avançar:

1. `$speckit-constitution`: definir os princípios a partir dos requisitos obrigatórios do README.
2. `$speckit-specify`: especificar a ingestão de PDF e as perguntas via CLI, usando este README como fonte dos requisitos e o [plano inicial](plans/plano-implementacao.md) como contexto.
3. `$speckit-clarify`: esclarecer ambiguidades relevantes antes do planejamento, quando necessário.
4. `$speckit-plan`: produzir o plano técnico da especificação.
5. `$speckit-tasks`: decompor o plano em tarefas executáveis.
6. `$speckit-analyze`: conferir a consistência entre especificação, plano e tarefas.
7. `$speckit-implement`: implementar as tarefas.
8. `$speckit-converge`: identificar lacunas; repetir implementação e convergência quando houver tarefas restantes.

Essas invocações são feitas no chat do agente, não no terminal. O plano em `plans/` é uma análise inicial; os artefatos gerados em `specs/` serão a referência do trabalho conduzido pelo fluxo SDD.

Referências: [adoção em projetos existentes](https://github.github.io/spec-kit/guides/existing-projects.html) e [integração e sintaxe dos comandos](https://github.github.io/spec-kit/reference/integrations.html).

## Solução implementada — ingestão, busca e chat (specs 001/002/003)

A ingestão, a cadeia programática de busca e o chat interativo estão implementados.
A entrega global depende das verificações registradas na seção 003 do relatório;
os exemplos do enunciado só são evidência quando conferidos na validação real. Consulte [o registro de execução](plans/validacao.md) para resultados reais.

Ambiente validado: **CPython 3.12.12**, macOS arm64, Docker e Compose.
Confirme `python3 --version` antes de criar o ambiente. Se usa `uv`, selecione
3.12.12 com `uv python install 3.12.12` e acrescente o diretório de
`uv python find 3.12.12` ao início do PATH da sessão.

Da raiz do repositório:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m pip check
# Somente se .env ainda não existir:
cp .env.example .env
```

Preencha `OPENAI_API_KEY` em `.env`, `.env.local` ou ambiente exportado.
O complemento `.env.local` pode conter só a chave. Precedência: ambiente exportado
(inclusive vazio) > `.env.local` > `.env`. Os arquivos locais são ignorados pelo Git;
não os imprima nem versione. A configuração não altera esses arquivos.

| Variável | Uso na ingestão |
| --- | --- |
| `OPENAI_API_KEY` | Chave OpenAI não vazia. |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small`, disponível à conta. |
| `OPENAI_EMBEDDING_DIMENSIONS` | Inteiro positivo, padrão 1536, enviado explicitamente. |
| `DATABASE_URL` | URL `postgresql+psycopg://` do exemplo para o Compose local. |
| `PG_VECTOR_COLLECTION_NAME` | Destino explícito, uma revisão de um PDF por collection. |
| `PDF_PATH` | PDF textual local; exemplo `document.pdf`, relativo ao diretório de execução. |

A ingestão não exige modelo de chat nem chave Google. Não há pressuposto de gratuidade:
verifique acesso e quota no provedor. A [documentação oficial de embeddings](https://developers.openai.com/api/docs/guides/embeddings)
e [do modelo](https://developers.openai.com/api/docs/models/text-embedding-3-small)
fundamentam a escolha; a integração efetiva consta do registro de validação.

```bash
docker compose up -d
docker compose ps -a
docker compose exec -T postgres psql -U postgres -d rag -c "SELECT extversion FROM pg_extension WHERE extname='vector';"
python src/ingest.py
```

Antes da ingestão, `postgres` deve estar saudável, o bootstrap deve terminar com
código 0 e a consulta deve retornar uma versão de `vector`. Sucesso da aplicação tem
código 0 e informa arquivo, páginas carregadas, chunks confirmados e collection.
A conferência completa de texto, metadados, IDs e dimensões é feita após a escrita.
Consulte [o quickstart](specs/001-pdf-ingestion/quickstart.md) para consultas SQL
somente de leitura, delimitadas pelo nome da collection, e amostras por página.

Configure também `OPENAI_CHAT_MODEL=gpt-6-luna` para executar `python src/chat.py`.
A chave Google e `PDF_PATH` não são exigidos pelo chat.

Testes isolados (não usam chave real, rede ou PostgreSQL):

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

### Diagnóstico de ingestão

Falhas retornam código 1 e orientação em stderr; Ctrl+C retorna 130, liberando recursos.
A ausência de confirmação exige verificar o problema antes de reexecutar.

| Diagnóstico | Correção |
| --- | --- |
| Variável obrigatória | Revise o nome indicado em `.env`, `.env.local` e ambiente; valor exportado vazio prevalece. |
| Arquivo inexistente/acesso negado | Confira `PDF_PATH`, extensão `.pdf` e permissões. |
| PDF inválido ou sem texto | Forneça PDF íntegro com texto extraível. OCR não é suportado. |
| Credencial/API/modelo | Revise chave e autorização para o modelo na conta OpenAI. |
| Quota/limite | Confira saldo e limites; reexecução é manual e pode gerar cobrança. |
| Conexão ou timeout | Confira rede, `docker compose ps -a`, porta 5432 e `DATABASE_URL`. |
| Extensão ausente | Verifique bootstrap com saída 0 e consulte `pg_extension`. |
| Escrita/conferência/commit incerto | Resultado pode estar persistido mesmo com erro. Reexecute o mesmo PDF/configuração para recuperar pelos mesmos IDs, sem limpar dados. |

API tem timeout de 60 s e nenhuma retentativa automática; banco tem conexão/pool de
10 s, instrução de 30 s e bloqueio de 5 s. A aplicação não imprime exceções HTTP/SQL
brutas nem habilita rastreamento externo. Não configure LangSmith/tracing nesta etapa;
essa opção requer documentação explícita dos dados enviados antes de ser utilizada.

### Reingestão, preservação e reindexação

O manifesto da collection registra provedor, modelo, dimensão, SHA-256 do PDF e
pipeline. Ele é imutável, mesmo com collection vazia. Uma collection existente sem
manifesto é rejeitada; a aplicação não adota dados legados por inferência de dimensão.
PDF, modelo, dimensão ou pipeline alterado exige **nova collection explícita** em
`PG_VECTOR_COLLECTION_NAME`, com ingestão integral. A configuração incompatível é
rejeitada antes da geração dos embeddings, inclusive com dimensão igual.

Reexecutar o mesmo PDF/configuração gera os mesmos IDs e faz upsert, sem duplicar
chunks. Textos iguais em posições distintas têm IDs próprios, e outra collection tem
IDs diferentes. A reexecução pode recalcular e cobrar embeddings; não há cache.
Após commit incerto ou falha de conferência, essa reexecução recupera os mesmos IDs.

Na integração PGVector 0.0.15, a dimensão fixa seria aplicada à tabela compartilhada.
A solução usa coluna `vector` sem dimensão global fixa e valida dimensão por collection,
sem índice ANN. Schema legado com dimensão fixa incompatível exige banco separado
ou migração administrativa planejada; não há `ALTER TABLE` automático.

Reindexação em nova collection preserva o destino anterior e consome espaço adicional.
A busca deve apontar para o mesmo modelo, dimensão e collection da ingestão.
Nenhum fluxo normal apaga collection, tabela ou volume. Este projeto não fornece comando
de limpeza; uma limpeza administrativa futura deve delimitar dados e documentar a
perda antes de ser executada. Para testar persistência sem perda de dados:

```bash
docker compose restart postgres
docker compose ps -a
```

Aguarde o estado saudável e consulte os registros antes de qualquer reingestão.
Remover volume apagaria a base persistida e não faz parte do procedimento.


### Consulta programática (spec 002)

Configure também `OPENAI_CHAT_MODEL=gpt-6-luna`. Busca exige a chave OpenAI, embeddings,
mesma dimensão/collection da ingestão e modelo de resposta. Não exige `PDF_PATH` nem
credencial Google. A ingestão continua sem exigir modelo de chat. A precedência dos
arquivos e do ambiente é a mesma para os dois fluxos.

Da raiz, com o ambiente virtual ativo e a base previamente ingerida:

```bash
python - <<'PYTHON'
from src.search import search_prompt

with search_prompt() as chain:
    print(chain.invoke({'pergunta': 'Qual o faturamento da Alfa Agronegócio Indústria?'}))
PYTHON
```

A cadeia e os clientes são construídos uma vez e podem receber várias perguntas
independentes. Use `with` ou `close()` em `finally` para liberar banco/transportes,
inclusive em interrupções. Cada pergunta válida usa um embedding e, havendo contexto,
uma geração cobrada; não há pressuposto de gratuidade. O modelo usa esforço low,
Chat Completions, sem temperatura, limite de 2048 tokens incluindo raciocínio,
timeout de 60 s por requisição e zero retentativas automáticas. Isso não representa
um prazo global de consulta. A construção não verifica acesso/quota com chamada paga.

A busca solicita k=10, mantém os resultados disponíveis e não usa score como prova de
resposta. Somente os textos recuperados entram no contexto, sem memória entre perguntas.
O laço interativo de `python src/chat.py` reutiliza essa cadeia.


Sem conteúdo recuperado, a cadeia devolve diretamente a frase obrigatória, sem geração.
Na bateria real registrada em [plans/validacao.md](plans/validacao.md), as três respostas
sobre faturamento/fundação coincidiram com o PDF; três ausências, opinião, desvio e quatro
contextos controlados retornaram a recusa exata. Acesso ao alias `gpt-6-luna` foi validado
em 2026-10-16. Esses resultados não garantem ausência de alucinações para outras perguntas.

| Diagnóstico da consulta | Ação |
| --- | --- |
| `QuestionError` | Envie somente `{'pergunta': texto}` com texto não vazio. A cadeia continua utilizável. |
| `ConfigurationError` | Revise a variável indicada e a precedência do ambiente. |
| `StorageError`, base ausente/vazia | Confira Compose/bootstrap e execute ingestão no destino correto. A busca não cria coleções. |
| Manifesto/dimensão incompatível | Use configuração original ou nova collection/reindexação explícita; a busca não repara dados. |
| `SearchError.retryable=True` | Confira rede/serviço ou aguarde o limite temporário antes de enviar outra pergunta. Não há retry automático. |
| `SearchError.retryable=False` | Corrija credencial, quota, modelo, base ou limite de geração e reabra a cadeia. Saída truncada/bloqueada não vira resposta parcial. |

Falhas operacionais são exceções, distintas da recusa factual. A CLI apresenta esses erros em stderr e encerra em código 1 quando fatais. O engine de consulta usa transações de leitura e os
mesmos timeouts de banco da ingestão. Uma collection removida durante a consulta produz
erro; retorno vazio após abertura válida produz a recusa direta.

Rastreamento externo permanece desativado por padrão. Se habilitar explicitamente
LangSmith/LangChain tracing por variáveis próprias, saiba que perguntas, chunks,
prompts, respostas e metadados da execução podem ser enviados ao serviço configurado;
revise acesso e retenção antes de ativar. Logs normais só registram categorias de falha,
sem esses conteúdos, chaves ou URL de conexão. Consulte o
[quickstart de busca](specs/002-grounded-search/quickstart.md) para validação e diagnóstico.


### Chat no terminal (spec 003)

Com o venv ativo, base ingerida e modelo de chat configurado:

```bash
python src/chat.py
```

Cada `PERGUNTA: ` recebe uma pergunta; `RESPOSTA: ` apresenta o texto integral da
busca, inclusive a recusa obrigatória. A cadeia e seus clientes são abertos uma vez,
reutilizados para várias perguntas e liberados ao encerrar. As perguntas são
independentes, sem histórico para completar fatos. Linhas vazias ou só espaços são
ignoradas sem API. `sair`/`exit` aceitam caixa e espaços externos; EOF (Ctrl+D no Unix)
e Ctrl+C também encerram normalmente, inclusive durante consulta, com código 0 se a
liberação terminar. Uma requisição já enviada pode gerar cobrança após interrupção.

Erros nunca são respostas factuais: aparecem em stderr. `Erro ao iniciar o chat:`
orienta corrigir configuração/Compose/bootstrap ou ingerir uma base ausente/vazia,
sem primeiro prompt. Configure `OPENAI_CHAT_MODEL` explicitamente: o arquivo de
exemplo não é carregado como configuração local. `Erro na consulta:` transitório
permite enviar outra pergunta na mesma cadeia; fatal (credencial/quota/modelo/base
incompatível/saída inválida) encerra com código 1. Não há retry automático. Falhas
inesperadas recebem diagnóstico estático seguro; falha de liberação também retorna 1.
Após corrigir falha fatal, execute o comando novamente. Não há aquecimento pago.

Testes do contrato da CLI, sem serviços ou credenciais reais:

```bash
python -m unittest tests.test_chat -v
```

O [guia 003](specs/003-terminal-chat/quickstart.md) contém bateria factual, interrupções,
persistência e reprodução nova. A [seção 003 de validação](plans/validacao.md#validação--chat-no-terminal-e-entrega-003)
distingue resultados executados, dublês e pendências da entrega pública. Sucesso dos
testes não garante ausência absoluta de alucinações. Custos, timeouts e tracing seguem
as configurações da busca descritas acima, sem novas variáveis da CLI.


Resultados reais da CLI em 2026-10-16: faturamento da Alfa Agronegócio Indústria
`R$ 85.675.568,77` (página 1), fundação da Atlas Biotech S.A. em `2023` (página 2) e
faturamento da SuperTechIABrazil `R$ 10.000.000,00` (página 3). Três ausências, opinião
e desvio retornaram a recusa exata. A reprodução em clone/venv/banco novos e a persistência
também passaram; o relatório registra a variação local de Compose com porta/volume
separados. **A entrega pública do candidato ainda está pendente (T029)**; o repositório
é público e o fork está correto, mas a revisão pública conferida não contém este código.
