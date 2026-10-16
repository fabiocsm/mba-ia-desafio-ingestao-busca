# Validação — ingestão de PDF (001)

Data: 2026-10-16. Escopo: spec 001; busca/chat e entrega global pendentes nas specs 002/003.

## Análise documental anterior à implementação

Aplicada `speckit-analyze`, somente leitura, a spec/plan/tasks e constituição.
11 requisitos FR e 5 critérios SC cobertos pelas 39 tarefas (100%); zero tarefas
sem vínculo, ambiguidades materiais, duplicações conflitantes ou problemas críticos.
IDs determinísticos são recomendação constitucional adotada como aceite no plano.
A dimensão global da tabela PGVector e os limites da validação estão documentados.
Checklist requirements: 16/16. Sem extensions.yml ou hooks registrados.

## Execução

Resultados serão acrescentados conforme verificados. Nenhuma integração é presumida.

### Preparação e fundação (T001–T008)

- macOS 26.6.2 arm64, CPython 3.12.12 selecionado pelo PATH do uv;
  `python3 -m venv venv`, `source venv/bin/activate`,
  `pip install -r requirements.txt`: códigos 0. Todos os 75 pins preservados.
- `python -m pip check`: código 0, nenhuma dependência inconsistente; imports de
  PyPDFLoader, splitter, OpenAIEmbeddings e PGVector aprovados. APIs inspecionadas
  no código instalado 0.0.15 (add_embeddings/upsert e create_collection).
- Documentação oficial de embeddings e text-embedding-3-small consultada novamente:
  https://developers.openai.com/api/docs/guides/embeddings e
  https://developers.openai.com/api/docs/models/text-embedding-3-small .
- `.env.example` completado e arquivos locais preservados; ignores Git/Docker verificados.
- Testes T004/T005 primeiro falharam por módulos ainda ausentes; após T006/T007,
  `python -m unittest discover -s tests -v`: 13 execuções aprovadas (5 repetidas
  por import de classe de teste, posteriormente corrigido). Suíte sem banco/API/chave.
- Defeito demonstrado no Compose original: bootstrap retornava 0 sem criar extensão;
  `docker compose config --format json` mostrava lista fragmentada, logo sh -c
  executava somente atribuição PGPASSWORD. Corrigido command para lista com uma
  única string shell; sem alterar imagem, porta ou volume.

- T003 corrigida e verificada: `docker compose config --quiet`, `up -d`,
  `wait bootstrap_vector_ext`: códigos 0; postgres healthy, bootstrap Exited(0),
  consulta real pg_extension: vector **0.8.7**. Volume preservado.
- T009/T010: falha inicial pela ingestão/persist_chunks ausentes. T011–T017:
  `python -m unittest discover -s tests -v`: **16 testes**, código 0.
  Loader/splitter reais e PDFs sintéticos com fontes, português, página vazia,
  texto de 2200 caracteres (chunks 1000/1000/500), IDs e vetores inválidos cobertos.
  Um fixture inicial sem fonte produzia texto ilegível; corrigido o PDF de teste
  com Helvetica/WinAnsi, sem modificar a extração da aplicação.
- T018: README com instalação, configuração, precedência, comandos e conferência.

### US1 integrada (T019)

- Antes da primeira ingestão: `SELECT to_regclass('langchain_pg_collection')`
  retornou NULL, código 0. Portanto ambos os nomes de validação estavam ausentes:
  `pdf_validation_20261016_001` e `pdf_validation_20261016_other_001`.
- `PG_VECTOR_COLLECTION_NAME=pdf_validation_20261016_001 python src/ingest.py`:
  código **0**, **34 páginas**, **67 chunks confirmados**, OpenAI real com
  `text-embedding-3-small`, dimensão explícita **1536**.
- Conferência SQL em outro processo: 67 IDs únicos; textos não vazios, até 1000
  caracteres; todas as dimensões 1536; índices 0–66; IDs/metadados/origem corretos.
  Todos os 67 textos comparados às respectivas páginas extraídas do PDF, aprovados.
- SHA-256 do PDF: `487adc82839c525365caa5feef4c7de01be10d3375ee43c9a2dfd24331274ca8`.
- Manifesto persistido:

```json
{
  "schema_version": 1,
  "provider": "openai",
  "embedding_model": "text-embedding-3-small",
  "embedding_dimensions": 1536,
  "document_sha256": "487adc82839c525365caa5feef4c7de01be10d3375ee43c9a2dfd24331274ca8",
  "pipeline": {
    "loader": "PyPDFLoader",
    "langchain-community": "0.3.27",
    "pypdf": "6.0.0",
    "mode": "page",
    "extract_images": false,
    "splitter": "RecursiveCharacterTextSplitter",
    "langchain-text-splitters": "0.3.9",
    "chunk_size": 1000,
    "chunk_overlap": 150,
    "length_function": "len",
    "separators": [
      "\n\n",
      "\n",
      " ",
      ""
    ]
  }
}
```

Amostras conferidas (página humana = metadado + 1):

- Página 1, chunk 0: 'Nome da empresa Faturamento Ano de fundação\nAlfa Agronegócio Indústria R$ 85.675.568,77 1931\nAlfa Ambiental Participações R$ 5.774.383,30 2021\nAlfa Energia Hold'.
- Página 1, chunk 1: 'Aliança Energia Participações R$ 440.738.519,41 1998\nAliança Esportes Comércio R$ 425.358.393,37 1945\nAliança Esportes ME R$ 4.485.320.049,16 2002\nAliança Hotel'.
- Página 2, chunk 2: 'Alta Construtora Participações R$ 82.189.431,26 1931\nAlta Construtora Serviços R$ 320.363.116,29 1937\nAlta Consultoria Comércio R$ 672.453.373,51 1989\nAlta Ener'.

### US2 (T020–T027)

- Caso real inexistente: código 1; `ERROR: PDF inexistente. Confira PDF_PATH e o diretório de execução.`.
- Caso real extensão: código 1; `ERROR: PDF_PATH deve indicar arquivo regular com extensão .pdf.`.
- Caso real configuração: código 1; `ERROR: OPENAI_API_KEY obrigatória; configure .env, .env.local ou ambiente.`.
- Caso real inválido: código 1; `ERROR: PDF inválido ou ilegível. Forneça um PDF íntegro com texto extraível.`.
- Caso real sem texto: código 1; `ERROR: PDF sem texto extraível. OCR não é suportado; forneça PDF textual.`.
- Testes antes de T025 falharam nas 5 categorias de API; após correção,
  `python -m unittest discover -s tests -v`: 26 testes aprovados, código 0.
  401, quota/429, timeout, conectividade, acesso/modelo, falha de escrita e falha
  de conferência após commit exercitados por dublês, sem provocar custos/falhas reais.
  Mensagens e código não zero, ausência de sucesso/segredos, liberação e nenhuma
  retentativa automática verificados. Recursos HTTP síncrono e assíncrono fechados.

### US3 isolada (T028–T032)

`python -m unittest discover -s tests -v`: **34 testes**, código 0.
Antes de T030, teste do manifesto para busca falhou por aceitar pipeline incompleto;
validação agora exige identidade completa do pipeline, centralizada em config.py.
Sem exigir PDF_PATH, verifica versão, provedor, modelo, dimensão, hash e pipeline.
Regressões cobrem manifesto ausente/legado, modelo com mesma dimensão, dimensão,
revisão e pipeline diferentes, destino vazio incompatível, concorrência, schema
legado, erros de conexão/timeout e liberação do engine. Dublê com commit realizado
mas resposta perdida comprova recuperação por reingestão, mesmos IDs/contagem,
textos repetidos em posições distintas e isolamento em outro destino.
T032: procedimentos e efeitos de reexecução/reindexação documentados no README.

### Incompatibilidades reais no destino já preenchido (T033)

- modelo diferente, mesma dimensão 1536: código 1, manifesto incompatível; embed_documents não chamado (spy), banco real.
- dimensão diferente: código 1, manifesto incompatível; embed_documents não chamado (spy), banco real.
- PDF alterado: código 1, manifesto incompatível; embed_documents não chamado (spy), banco real.

### Reingestão e isolamento reais (T033)

- Reexecução do mesmo comando e destino: código 0, 34 páginas e 67 chunks.
  IDs, assinatura de texto/metadados e manifesto iguais à primeira execução.
  Vetores recalculados não foram obrigados a ser bit a bit iguais.
- Ingestão em `pdf_validation_20261016_other_001`: código 0, 34 páginas, 67 chunks;
  conjuntos de IDs disjuntos. Assinatura completa do destino original antes/depois
  da criação do segundo destino permaneceu igual.
- Referência após reingestão e antes do reinício (SHA-256 da serialização JSON
  ordenada por ID de id/texto/vetor/metadados/dimensão):
  `f6161761231921ab66f3b5c9c01e160c04e0a577714f5210ab420a0c929d500d`.
- Assinatura de texto/metadados: `0e7cf74700391d91941dc3e3d3f6c87af89432a9706bc4851dc338832a86baa1`.

### Persistência e conclusão independente da US3 (T034–T035)

- `docker compose restart postgres`: código 0; aguardado healthy em `compose ps -a`.
- Novo processo de leitura, **sem reingestão após reinício**: 67 registros em cada
  destino, IDs, manifesto e assinatura completa exatamente iguais às referências
  anteriores. Assinatura do destino principal: `f6161761231921ab66f3b5c9c01e160c04e0a577714f5210ab420a0c929d500d`.
- US3 aprovada independentemente de busca/chat. Assinatura após reinício inclui
  vetores persistidos; comparação entre chamadas de reingestão exigiu apenas IDs,
  texto/metadados, dimensões e manifesto, permitindo recálculo do provedor.
- Nenhuma collection, tabela ou volume foi apagado. Sem bloqueio de integração.

### Gate de qualidade (T036)

Após integração US2/US3, revisão de contratos públicos tipados, imports, SRP/DRY e
fechamento de recursos. Pipeline centralizado em config.py, sem estado global mutável.
Diagnóstico diferencia escrita e conferência; recuperação indicada em ambos os casos.
`python -m unittest discover -s tests -v`: **34 testes**, código 0.
`python -m compileall -q src tests`: código 0. Sem ferramentas adicionais adotadas.

### Revisão documental (T037)

README e quickstart revisados contra os comandos e resultados executados; contratos
atualizados para refletir a implementação. Enunciado, exemplos e prompt preservados.
Busca, perguntas com/sem evidência, opinião, desvio de regras e collection vazia
na busca permanecem na spec 002; CLI de perguntas e entrega global na spec 003.
Sem declaração de conclusão de R06–R09 ou R11 integral.

### Reprodução em ambiente novo (T038)

- Cópia limpa dos 62 arquivos versionáveis atuais, sem venv/.env/.env.local
  originais; novo ambiente Python 3.12.12 criado com `python3 -m venv venv`.
  `pip install -r requirements.txt`, `python -m pip check`, Compose config/up/
  bootstrap: códigos 0. Chave fornecida somente em .env.local temporário modo 0600.
- Mesmo serviço Compose/volume preservado (nome do diretório/projeto igual); novo
  destino `pdf_validation_20261016_clean_001`: consulta anterior retornou contagem
  **0**, código 0. `python src/ingest.py` na cópia: código 0, 34 páginas e 67
  chunks confirmados; manifesto/IDs/registros conferidos em processo separado.
- Suíte na cópia: 34 testes aprovados, compileall código 0. Ajustes finais somente
  de quebra de linhas foram sincronizados e esses dois gates repetidos com sucesso.
- Estrutura obrigatória preservada; .env/.env.local/venv ignorados. Credencial real
  ausente dos 62 arquivos versionáveis e do índice Git, sem imprimir seu valor.
  Diretório temporário e sua credencial removidos após a reprodução.
- Versões operacionais: Docker 29.8.2; Compose 5.5.1; PostgreSQL 17.11 aarch64;
  pgVector 0.8.7; pacotes Python conforme os 75 pins originais de requirements.txt.

### Convergência e fechamento (T039)

Aplicada a skill local `speckit-converge`, após check-prerequisites --require-spec
--require-tasks --include-tasks: 11 FR, 5 SC, 11 cenários de aceite, decisões de
configuração, extração/divisão, clientes, IDs, manifesto, schema, escrita,
recuperação e preservação, e os 8 princípios constitucionais examinados.
Zero lacunas missing/partial/contradicts/unrequested no escopo 001; nenhuma fase
adicional anexada. A convergência não alterou código nem tarefas; o fechamento
deste item é registrado pelo fluxo implement após esse resultado.

Após os ajustes finais: unittest **34 testes**, compileall e git diff --check:
códigos 0. Tipos de todas as funções públicas dos três módulos implementados e
linhas até 79 caracteres conferidos por inspeção/AST. Não há meta numérica de
cobertura adotada; o aceite usa os contratos/cenários abaixo, sem afirmar 100% de
cobertura de linhas. Nenhuma credencial real encontrada em arquivos versionáveis
ou no índice. Os arquivos locais originais foram preservados.

Consulta somente leitura `gh repo view --json nameWithOwner,visibility,isFork,parent,url`:
código 0; [fabiocsm/mba-ia-desafio-ingestao-busca](https://github.com/fabiocsm/mba-ia-desafio-ingestao-busca)
é PUBLIC, fork de devfullcycle/mba-ia-desafio-ingestao-busca. Isso confirma visibilidade
e origem; as alterações desta execução são locais, sem commit ou push implícitos.

`.specify/extensions.yml` continua ausente: nenhum hook before/after implement,
analyze ou converge a executar. Checklists não foram modificados.

## Matriz final de aceite da spec 001

| Critério | Estado | Evidência |
| --- | --- | --- |
| FR-001 | Aprovado | Configuração por fluxo, precedência, variáveis e dublês. |
| FR-002 | Aprovado | Compose healthy, bootstrap 0, vector 0.8.7. |
| FR-003 | Aprovado | PDF real, PDFs sintéticos, inválido/sem texto e diagnóstico. |
| FR-004 | Aprovado | Splitter real 1000/150/len, limites e páginas preservados. |
| FR-005 | Aprovado | 67 registros, todos comparados ao PDF e metadados/dimensões. |
| FR-006 | Aprovado | Resumo somente após conferência; dublês de falha/commit incerto. |
| FR-007 | Aprovado | Igualdade exata dos dois destinos após reinício, sem reingerir. |
| FR-008 | Aprovado | Casos locais reais e falhas externas por dublês; sem segredos. |
| FR-009 | Aprovado | Nenhuma exclusão; reingestão/isolações/recuperação verificadas. |
| FR-010 | Aprovado | Manifesto; 3 incompatibilidades reais antes da API, inclusive mesma dimensão. |
| FR-011 | Aprovado | README e reprodução com Python novo, config e collection exclusiva. |
| SC-001 | Aprovado | Ingestão real 34 páginas/67 chunks e conferência completa. |
| SC-002 | Aprovado | Assinatura e manifesto iguais antes/depois do reinício. |
| SC-003 | Aprovado | Matriz negativa isolada e integrada, códigos/diagnósticos seguros. |
| SC-004 | Aprovado | Instalação e ingestão pelo README na cópia limpa. |
| SC-005 | Aprovado | Texto curto/longo, português, metadados e 67 trechos reais. |
| IDs determinísticos adotados | Aprovado | Reingestão sem duplicatas; outro destino com IDs disjuntos. |
| R01 | Parcela de ingestão aprovada | Python 3.12.12/LangChain reais; consulta nas specs seguintes. |
| R02 | Aprovado | PostgreSQL/pgVector via Compose. |
| R03 | Aprovado | PyPDFLoader e PDF fornecido. |
| R04 | Aprovado | Splitter exigido, sem preenchimento artificial. |
| R05 | Aprovado | Embeddings OpenAI reais, persistência e reinício. |
| R06 | Pendente fora desta spec | Recuperação k=10 e vetorização da pergunta na spec 002. |
| R07 | Pendente fora desta spec | Contexto/prompt/LLM na spec 002. |
| R08 | Pendente fora desta spec | Fundamentação/recusa e perguntas negativas na spec 002. |
| R09 | Pendente fora desta spec | Chat e encerramento na spec 003. |
| R10 | Parcela de ingestão aprovada | Estrutura preservada, Compose/ingestão executados; chat futuro. |
| R11 | Parcial | README de ingestão, ausência de segredos, fork público; publicação das alterações e entrega global pendentes. |

Limites reais: integração executada no macOS arm64, sem validação Linux; um PDF
textual e um provedor, sem OCR. Falhas de API/banco e concorrência são exercitadas
por dublês, não por indução deliberada de falhas cobradas. Reinício/ingestão/modelo
real foram verificados. Três collections de validação permanecem no volume, com
67 chunks cada, preservadas intencionalmente. Busca, chat e a bateria final de
perguntas/opinião/desvio/collection vazia não foram implementados ou validados aqui.
Testes aprovados não garantem ausência absoluta de falhas ou alucinações futuras.
