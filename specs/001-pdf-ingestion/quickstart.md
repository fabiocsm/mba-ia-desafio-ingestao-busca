# Quickstart de validação — 001: Ingestão do PDF

Este guia será executado **após a implementação** das tarefas. Os scripts atuais ainda
são esqueleto e a suíte abaixo ainda será criada. Pesquisa já executada e seus limites:
[research.md](research.md). Contratos: [ingestão](contracts/ingestion.md) e
[dados](data-model.md). Usar uma collection exclusiva de validação, sem apagar dados existentes.

## 1. Pré-requisitos e instalação

Executar da raiz do repositório com Python **3.12.12**, Docker/Compose e acesso ao provedor.
Confirmar `python3 --version` antes de criar o ambiente; o host original usa 3.14.5.
Se necessário, instalar/selecionar 3.12.12 pelo gerenciador disponível. Com `uv`, uma
opção é `uv python install 3.12.12`, tornando o diretório do interpretador retornado por
`uv python find 3.12.12` prioritário no PATH da sessão. `uv` não é dependência da aplicação.

Preservar a preparação exigida no projeto:

```bash
python3 --version
python3 -m venv venv
source venv/bin/activate
python --version
pip install -r requirements.txt
python -m pip check
```

Esperado: Python 3.12.12 e nenhuma dependência inconsistente. Registrar plataforma,
versões e instalação real em ambiente novo; a instalação temporária por `uv` da pesquisa
não substitui esta reprodução.

Se `.env` ainda não existir, copiar `.env.example` para `.env`; preservar configuração
local preexistente. Após a implementação, o exemplo deverá conter:

```dotenv
OPENAI_API_KEY=
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1536
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/rag
PG_VECTOR_COLLECTION_NAME=pdf_ingestion_validation_v1
PDF_PATH=document.pdf
```

Preencher a chave real somente em arquivo local ignorado. Se `.env.local` já contém a
chave, preservá-lo e deixar a chave vazia no `.env`; o carregamento previsto usa precedência
ambiente exportado > `.env.local` > `.env`. Não imprimir/versionar nenhum desses arquivos
nem exigir Google ou modelo de chat para esta spec. Embeddings são enviados ao provedor e podem
ter custo; credencial válida, acesso ao modelo e quota são pré-condições da integração.

## 2. Verificar o armazenamento antes de ingerir

```bash
docker compose config --quiet
docker compose up -d
docker compose ps -a
docker compose logs bootstrap_vector_ext
docker compose exec -T postgres psql -U postgres -d rag -v ON_ERROR_STOP=1 -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

Esperado: `postgres` saudável, `bootstrap_vector_ext` encerrado com código 0 e consulta
retornando `vector`. Se ainda estiver iniciando, aguardar prontidão e repetir as verificações.
Não ingerir apenas porque o contêiner está em execução. Porta 5432 ocupada, bootstrap
malsucedido ou extensão ausente devem ser resolvidos antes de continuar.

## 3. Testes isolados e sintaxe

**Comandos planejados**, disponíveis depois da criação dos arquivos de teste:

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

Esperado: testes sem API/banco real aprovados, nenhuma requisição cobrada e sintaxe válida.
Cobertura: configuração por fluxo; leitura inválida/vazia; splitter/metadados; manifesto
real/incompatível, inclusive mesma dimensão; IDs determinísticos; dimensão/cardinalidade
de vetores; falhas de conexão/API/escrita/conferência; código de saída e logs sanitizados.
Nenhuma suíte inexistente pode ser registrada como aprovada.

Durante a implementação, esta execução pode ser antecipada para diagnóstico. O resultado
final de T036 deve ser obtido após as validações integradas de US2/US3 e suas correções.
Se reprodução ou convergência exigir alteração posterior de código, repetir a suíte,
a verificação de sintaxe e as validações afetadas. Integração pendente não permite
considerar concluído o gate final.

## 4. Ingerir e conferir registros reais

Antes da **primeira** ingestão, escolher dois nomes de validação e comprovar que ainda
não existem. Isso garante que a US1 exercita a criação, em uma base inicialmente vazia,
e reserva outro destino para conferir isolamento na seção 5. Manter as variáveis na
mesma sessão de terminal durante o guia:

```bash
validation_collection=pdf_ingestion_validation_v1
validation_other_collection=pdf_ingestion_validation_v2
docker compose exec -T postgres psql -U postgres -d rag -v ON_ERROR_STOP=1 \
  --set=collection_name="$validation_collection" \
  --set=other_collection_name="$validation_other_collection" <<'SQL'
SELECT to_regclass('langchain_pg_collection') IS NOT NULL AS collection_table_exists
\gset
\if :collection_table_exists
SELECT name
FROM langchain_pg_collection
WHERE name IN (:'collection_name', :'other_collection_name');
\else
\echo 'Tabela de collections ainda ausente; ambos os destinos inexistem.'
\endif
SQL
```

Esperado: consulta bem-sucedida com **zero linhas**, ou mensagem de tabela ausente na
primeira preparação do banco. Se algum nome aparecer, escolher outro valor para a
variável correspondente e repetir a conferência, sem apagar, esvaziar ou alterar a
collection existente. Erro de conexão/SQL não comprova ausência: interromper e corrigir
o problema antes de ingerir. Registrar os nomes escolhidos e o resultado inicial em
`plans/validacao.md`. Não executar outra ingestão nesses destinos durante essa validação.

Depois da conferência, executar:

```bash
PG_VECTOR_COLLECTION_NAME="$validation_collection" python src/ingest.py
```

Esperado: código 0 e resumo com arquivo, páginas carregadas, chunks confirmados e destino.
Na revisão de PDF/pipeline da pesquisa, foram observadas 34 páginas e 67 chunks; isso é
referência de comparação, não substitui conferir o resultado da execução real.

Inspecionar manifesto e registros, delimitando o destino:

```bash
docker compose exec -T postgres psql -U postgres -d rag -v ON_ERROR_STOP=1 \
  --set=collection_name="$validation_collection" <<'SQL'
SELECT name, cmetadata
FROM langchain_pg_collection
WHERE name = :'collection_name';

SELECT count(*) AS chunks,
       count(DISTINCT e.id) AS ids,
       min(length(e.document)) AS menor_texto,
       max(length(e.document)) AS maior_texto,
       min(vector_dims(e.embedding)) AS menor_dimensao,
       max(vector_dims(e.embedding)) AS maior_dimensao,
       count(*) FILTER (
           WHERE e.document IS NULL OR btrim(e.document) = ''
              OR e.embedding IS NULL
              OR NOT (e.cmetadata ?& ARRAY['source', 'page', 'chunk_id', 'document_sha256'])
       ) AS registros_invalidos
FROM langchain_pg_embedding e
JOIN langchain_pg_collection c ON c.uuid = e.collection_id
WHERE c.name = :'collection_name';

SELECT e.id, e.cmetadata->>'source' AS origem,
       e.cmetadata->>'page' AS pagina_base_zero, left(e.document, 160) AS amostra
FROM langchain_pg_embedding e
JOIN langchain_pg_collection c ON c.uuid = e.collection_id
WHERE c.name = :'collection_name'
ORDER BY (e.cmetadata->>'chunk_index')::integer
LIMIT 3;
SQL
```

Esperado: manifesto compatível, quantidade igual à do resumo, IDs únicos, textos até
1000 caracteres, vetores de 1536 dimensões, zero registros inválidos. Conferir amostras
com páginas reais do PDF, lembrando que `page=0` representa a primeira página.

## 5. Reingestão e persistência após reinício

Registrar a quantidade e uma assinatura de todos os registros antes de repetir/reiniciar:

```bash
docker compose exec -T postgres psql -U postgres -d rag -v ON_ERROR_STOP=1 \
  --set=collection_name="$validation_collection" <<'SQL'
SELECT count(*) AS chunks,
       md5(string_agg(md5(concat_ws('|', e.id, e.document,
           e.embedding::text, e.cmetadata::text)), '' ORDER BY e.id)) AS assinatura
FROM langchain_pg_embedding e
JOIN langchain_pg_collection c ON c.uuid = e.collection_id
WHERE c.name = :'collection_name';
SQL
```

Reexecutar somente o comando de ingestão da seção 4, mantendo `$validation_collection`,
e conferir a mesma contagem/IDs. Não repetir a exigência de inexistência para esse destino:
agora a collection preenchida é a pré-condição do teste de reingestão.
O provedor pode recalcular vetores: após reingestão, conferir também texto/metadados e
dimensões, sem impor igualdade bit a bit de embeddings entre chamadas externas.
Registrar então nova assinatura de referência e executar:

```bash
docker compose restart postgres
docker compose ps -a
```

Aguardar saúde do PostgreSQL e repetir a consulta da assinatura, **sem ingerir de novo**.
Quantidade e assinatura devem ser exatamente iguais às anteriores ao reinício. Não remover
volume. Registrar manifesto antes/depois também.

Para verificar isolamento entre destinos, ingerir com
`PG_VECTOR_COLLECTION_NAME="$validation_other_collection" python src/ingest.py`, conferir
IDs disjuntos entre as duas collections e que os registros da primeira não mudaram.
Essa verificação usa novamente o provedor e deve ter custo considerado.

## 6. Falhas e preservação

Casos locais reais, sem editar código:

```bash
PDF_PATH=arquivo-inexistente.pdf python src/ingest.py
PDF_PATH=README.md python src/ingest.py
OPENAI_API_KEY= python src/ingest.py
```

Criar amostras descartáveis de PDF inválido e PDF válido sem texto:

```bash
validation_dir=$(mktemp -d)
printf 'conteudo que nao e PDF' > "$validation_dir/invalid.pdf"
python -c 'from pypdf import PdfWriter; import sys; w = PdfWriter(); w.add_blank_page(width=200, height=200); w.write(sys.argv[1])' "$validation_dir/blank.pdf"
PDF_PATH="$validation_dir/invalid.pdf" python src/ingest.py
PDF_PATH="$validation_dir/blank.pdf" python src/ingest.py
```

Cada execução deve retornar falha com orientação, sem sucesso, embeddings vazios ou perda
dos dados existentes. Em shell, registrar `$?` imediatamente após cada comando, pois os
comandos seguintes substituem esse valor.

Na collection já preenchida, executar:

```bash
OPENAI_EMBEDDING_MODEL=text-embedding-3-large PG_VECTOR_COLLECTION_NAME="$validation_collection" python src/ingest.py
OPENAI_EMBEDDING_DIMENSIONS=512 PG_VECTOR_COLLECTION_NAME="$validation_collection" python src/ingest.py
```

Esperado: incompatibilidade detectada **antes da chamada ao provedor**, inclusive no
primeiro caso, que conserva a dimensão 1536. Mesmo resultado para PDF alterado ou manifesto
ausente, cobertos por testes/fixtures preparados na implementação. Não danificar a collection
de validação para simular esses casos; usar dublês ou destino dedicado.

Conexão recusada pode ser validada com uma porta local comprovadamente sem serviço via
`DATABASE_URL` de teste. Credencial recusada, quota, timeouts, falha parcial/commit incerto
e criação concorrente são cobertos deterministicamente por dublês; se ocorrerem na
integração real, registrar o diagnóstico. Não provocar gasto/quota esgotada para testar.

## 7. Reindexação e registro da validação

Modelo, dimensão, PDF ou pipeline diferente: escolher nova collection na configuração,
ingerir integralmente e conferir o manifesto; conservar o destino anterior. A busca futura
deverá usar o mesmo modelo/dimensão/destino. Não executar limpeza automática nem remover
volume. O enunciado alerta sobre reindexação; mesma dimensão não torna modelos compatíveis.

Registrar em `plans/validacao.md`: data, plataforma/Python/pacotes, comandos e códigos de
saída, modelo/dimensão/collection, comprovação de ausência antes da primeira ingestão,
hash do PDF, contagens, manifesto, amostras com páginas,
resultado de reingestão/reinício, casos negativos e limitações. Nunca registrar segredos.
Ausência de credencial/quota ou banco mantém integração pendente com motivo explícito.

Perguntas com/sem evidência, opinião, tentativa de desvio e collection vazia na busca ficam
na spec 002; interação e entrega global na 003. O fluxo final mantém, após esta ingestão,
`python src/chat.py`, sem declarar sua implementação ou R01–R11 completos nesta etapa.
