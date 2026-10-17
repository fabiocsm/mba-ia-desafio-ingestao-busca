# Ingestão e Busca Semântica com LangChain e Postgres

Aplicação Python para ingerir um PDF textual no PostgreSQL/pgVector e responder
perguntas pelo terminal com LangChain e OpenAI. Cada pergunta usa até dez chunks
recuperados; sem evidência suficiente, a resposta é
`Não tenho informações necessárias para responder sua pergunta.`

## Instalação e configuração da aplicação

### 1. Pré-requisitos e código-fonte

- Git, **CPython 3.12.12** e Docker com Docker Compose disponíveis no terminal.
- Docker em execução, com a porta local **5432** e o nome de container
  `postgres_rag` livres para o Compose deste projeto.
- Chave OpenAI com acesso e quota para embeddings `text-embedding-3-small` e
  chat `gpt-6-luna`, modelos usados na validação de 2026-10-16. Chamadas podem gerar
  cobrança; disponibilidade e quota dependem da conta.
- Um PDF com texto extraível; `document.pdf` já acompanha o repositório.

O ambiente efetivamente validado foi macOS arm64 com CPython 3.12.12. Não há
validação em Linux ou Windows. Os comandos abaixo usam Bash/Zsh.

Obtenha o código-fonte e confira as ferramentas disponíveis:

```bash
git clone https://github.com/fabiocsm/mba-ia-desafio-ingestao-busca.git
cd mba-ia-desafio-ingestao-busca
python3 --version
docker compose version
```

Confirme Python 3.12.12 antes de criar o ambiente. Se já usa `uv`, pode selecionar
essa versão na sessão com:

```bash
uv python install 3.12.12
export PATH="$(dirname "$(uv python find 3.12.12)"):$PATH"
python3 --version
```

### 2. Ambiente virtual e dependências

Execute da raiz do repositório:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m pip check
```

Use o ambiente virtual também nos comandos seguintes. As dependências são fixadas
em `requirements.txt`; não é necessário instalar Spec Kit para executar a aplicação.

### 3. Variáveis de ambiente

Em um clone novo, copie o exemplo e edite `.env` localmente, preenchendo a chave
OpenAI. Se `.env` já existir, preserve-o e revise seus valores.

```bash
cp -n .env.example .env
```

| Variável | Configuração | Exigida em |
| --- | --- | --- |
| `OPENAI_API_KEY` | Sua chave OpenAI, preenchida somente localmente. | Ingestão e chat |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Ingestão e chat |
| `OPENAI_EMBEDDING_DIMENSIONS` | Inteiro positivo; exemplo e padrão: `1536`. | Ingestão e chat |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/rag` para o Compose local. | Ingestão e chat |
| `PG_VECTOR_COLLECTION_NAME` | `pdf_ingestion_validation_v1` no exemplo; use o mesmo destino nos dois fluxos. | Ingestão e chat |
| `PDF_PATH` | `document.pdf`, relativo ao diretório de execução, ou caminho absoluto de um PDF textual. | Somente ingestão |
| `OPENAI_CHAT_MODEL` | `gpt-6-luna` | Somente busca/chat |

A precedência é **ambiente exportado > `.env.local` > `.env`**, inclusive quando um
valor exportado está vazio. `.env` e `.env.local` são lidos na raiz do projeto;
o complemento `.env.local` pode conter apenas a chave. `.env.example` não é carregado
automaticamente. Os arquivos locais são ignorados pelo Git; não os versione.

Esta implementação usa somente OpenAI. A ingestão não exige modelo de chat nem
chave Google. Após ingerir a base, o chat não exige `PDF_PATH` ou o arquivo original.
A senha `postgres` acima é a configuração de exemplo do banco local.

### 4. PostgreSQL e extensão vector

Em uma primeira instalação, execute os comandos abaixo diretamente. Para repetir
a instalação no mesmo host com **um banco novo**, preservando volumes anteriores,
antes escolha um nome de projeto Compose ainda não usado:

```bash
export COMPOSE_PROJECT_NAME=rag_readme_clean_20261016
```

Mantenha essa variável na sessão durante todos os comandos `docker compose` da
instalação, inclusive reinício e parada; em outra sessão, exporte o mesmo nome para
retomar esse banco. O nome define um volume separado; reutilizá-lo também reutiliza
seus dados. A porta 5432 e o container `postgres_rag` continuam precisando estar
livres. Outro clone com o mesmo nome de diretório, sem essa variável, pode reutilizar
o volume padrão do projeto: clonar novamente não limpa o banco.

```bash
docker compose up -d
docker compose ps -a
docker compose logs bootstrap_vector_ext
docker compose exec -T postgres psql -U postgres -d rag -c "SELECT extversion FROM pg_extension WHERE extname='vector';"
```

Antes de ingerir, confirme `postgres` saudável (`healthy`),
`bootstrap_vector_ext` encerrado com código 0 e uma versão retornada pela consulta
da extensão. Se o serviço ainda estiver iniciando, aguarde e repita a conferência.
O volume `postgres_data` preserva os dados entre reinícios.

### 5. Ingestão e chat

```bash
python src/ingest.py
python src/chat.py
```

Só inicie o chat após a ingestão terminar com código 0 e informar os chunks
confirmados. Na validação do PDF fornecido foram carregadas 34 páginas e persistidos
67 chunks; outro PDF pode produzir quantidades diferentes.

Exemplo registrado na bateria real, com evidência na página 1 do PDF:

```text
PERGUNTA: Qual o faturamento da Alfa Agronegócio Indústria?
RESPOSTA: R$ 85.675.568,77

PERGUNTA: Qual é o CNPJ da Alfa Agronegócio Indústria?
RESPOSTA: Não tenho informações necessárias para responder sua pergunta.

PERGUNTA: sair
```

Use `sair`, `exit`, EOF ou Ctrl+C para encerrar normalmente. Perguntas vazias são
ignoradas; cada pergunta é independente, sem memória de conversa. Erros operacionais
aparecem em stderr e falhas fatais retornam código 1. Consulte os diagnósticos abaixo.

Para retomar em outra sessão, ative o venv e inicie o chat com o banco saudável;
não é necessário reingerir. Para parar o banco preservando o volume:

```bash
docker compose stop
deactivate
```

### 6. Testes, evidências e limites

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
python -m pip check
```

Os 78 testes isolados executam sem API, credenciais reais ou PostgreSQL ativo.
O [relatório de validação](plans/validacao.md#fechamento-público-da-entrega-003)
registra a conferência pública de T029/T034/T035, a matriz R01–R11 e as evidências
anteriores de integração, reprodução e persistência.

A [reexecução da instalação limpa](plans/validacao.md#instalação-limpa-do-readme-003-t036-e-t037)
registra a revisão avaliada, a instalação em volume novo e os resultados da
ingestão, chat, persistência e testes. As instruções de clone seguem a entrega
integrada em `main`; a validação não executou nem comprovou o merge.

O escopo é um PDF textual, um provedor e chat por terminal; não inclui OCR, web,
múltiplos PDFs ou histórico. Trocar PDF, modelo de embeddings, dimensão ou pipeline
exige nova collection explícita e ingestão integral, preservando a anterior. A bateria
aprovada não garante ausência absoluta de alucinações. Nenhum fluxo normal apaga dados.

## Enunciado do desafio

Os requisitos e exemplos originais abaixo são preservados como referência acadêmica.
Para operar a implementação, siga a instalação acima e os diagnósticos ao final.

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
O candidato publicado na revisão `ace6549` do PR #1 foi conferido anonimamente em
2026-10-16; T029/T034/T035 foram concluídas conforme o
[fechamento público](plans/validacao.md#fechamento-público-da-entrega-003).
Os exemplos do enunciado só são evidência quando conferidos na validação real.

Siga [instalação e configuração](#instalação-e-configuração-da-aplicação) para preparar
o ambiente e executar a aplicação. A conferência de texto, metadados, IDs e dimensões
é feita após a escrita.
Consulte [o quickstart](specs/001-pdf-ingestion/quickstart.md) para consultas SQL
somente de leitura, delimitadas pelo nome da collection, e amostras por página.

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
distingue resultados executados, dublês e a conferência da revisão pública. Sucesso dos
testes não garante ausência absoluta de alucinações. Custos, timeouts e tracing seguem
as configurações da busca descritas acima, sem novas variáveis da CLI.


Resultados reais da CLI em 2026-10-16: faturamento da Alfa Agronegócio Indústria
`R$ 85.675.568,77` (página 1), fundação da Atlas Biotech S.A. em `2023` (página 2) e
faturamento da SuperTechIABrazil `R$ 10.000.000,00` (página 3). Três ausências, opinião
e desvio retornaram a recusa exata. A reprodução em clone/venv/banco novos e a persistência
também passaram; o relatório registra a variação local de Compose com porta/volume
separados. A revisão pública `ace6549` contém os mesmos arquivos de execução e testes
do candidato validado; a conferência de acesso, fork, estrutura e credenciais consta
do fechamento público de T029/T034/T035 no relatório.
