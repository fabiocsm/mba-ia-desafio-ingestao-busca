# Plano de implementação — Ingestão e busca semântica em PDF

## 1. Objetivo e escopo

Implementar uma aplicação Python com LangChain que leia o `document.pdf`, armazene seus chunks e embeddings no PostgreSQL com pgVector e permita fazer perguntas pelo terminal. As respostas devem usar somente o conteúdo recuperado do PDF e seguir o prompt definido no [README](../README.md).

O entregável é um repositório público no GitHub com código funcional e instruções suficientes para outra pessoa preparar o ambiente, ingerir o PDF e executar o chat.

Este documento é um plano; a implementação e as verificações descritas abaixo ainda precisam ser executadas.

## 2. Avaliação do estado atual

| Item | Situação observada | Trabalho necessário |
| --- | --- | --- |
| Estrutura obrigatória | Os arquivos exigidos já existem. | Preservar os três scripts e seus comandos de execução. |
| `src/ingest.py` | Carrega `.env` e lê `PDF_PATH`, mas `ingest_pdf()` está vazio. | Implementar leitura, divisão, embeddings e persistência. |
| `src/search.py` | Contém o prompt solicitado; `search_prompt()` está vazio. | Implementar recuperação e geração de resposta. |
| `src/chat.py` | Chama `search_prompt()` e verifica a inicialização, mas não possui interação. | Implementar o laço de perguntas e respostas. |
| `docker-compose.yml` | Define PostgreSQL 17 com imagem pgVector, volume, healthcheck e serviço de criação da extensão. | Verificar a inicialização real do banco e da extensão. |
| `requirements.txt` | Lista versões fixas de LangChain, integrações dos provedores, drivers PostgreSQL e leitor PDF. | Validar instalação e compatibilidade antes de alterar versões. |
| `.env.example` | Tem variáveis de embeddings e conexão, mas não define o modelo de chat nem valores locais para banco, collection e PDF. | Documentar a configuração completa do provedor escolhido. |
| `.gitignore` | Já ignora `.env`, `/venv` e `__pycache__`. | Manter credenciais fora do versionamento. |
| `document.pdf` | Está presente no repositório. | Verificar se contém texto extraível e selecionar evidências para validação. |
| Testes e execução | Não foram identificados testes entre os arquivos examinados. | Validar o fluxo funcional e os casos negativos. |

O projeto está no estágio de esqueleto. O maior trabalho está na integração entre ingestão, recuperação e chat, além da comprovação de que perguntas sem resposta no documento recebem a recusa exigida.

## 3. Requisitos e critérios de aceite

| ID | Requisito do README | Critério de aceite |
| --- | --- | --- |
| R01 | Usar Python e LangChain. | Os scripts executam em ambiente virtual e utilizam LangChain no fluxo de ingestão e consulta. |
| R02 | PostgreSQL com pgVector, executado via Docker Compose. | `docker compose up -d` inicia o banco; o serviço de bootstrap termina com sucesso e a extensão `vector` está instalada. |
| R03 | Ler um PDF. | `python src/ingest.py` lê o arquivo indicado em `PDF_PATH`, com `document.pdf` como configuração de exemplo. |
| R04 | Chunks de 1000 caracteres com overlap de 150. | O splitter usa `chunk_size=1000`, `chunk_overlap=150` e contagem por caracteres. Os chunks não vazios são usados na ingestão. |
| R05 | Converter cada chunk em embedding e persistir os vetores. | A collection contém o texto, os metadados e o vetor de cada chunk ingerido; os dados permanecem após reiniciar o contêiner. |
| R06 | Vetorizar cada pergunta e buscar com `k=10`. | A busca usa o mesmo modelo de embeddings da ingestão e chama `similarity_search_with_score(query, k=10)`; se houver menos de dez chunks disponíveis, utiliza os retornados. |
| R07 | Concatenar os resultados, montar o prompt e chamar a LLM. | O contexto é composto pelo conteúdo dos chunks recuperados e o prompt mantém as regras e exemplos do README. |
| R08 | Responder somente com base no contexto. | Perguntas com evidência recebem respostas compatíveis com o PDF; perguntas sem evidência recebem exatamente a mensagem de recusa exigida. |
| R09 | Simular um chat no terminal. | `python src/chat.py` permite várias perguntas na mesma execução e imprime `PERGUNTA:` e `RESPOSTA:` de forma legível. |
| R10 | Preservar a estrutura e a ordem de execução. | Os arquivos obrigatórios continuam presentes e os comandos do README funcionam a partir da raiz do projeto. |
| R11 | Entregar repositório público e README de execução. | O README documenta instalação, configuração, ingestão, chat e limitações; a publicação e a visibilidade pública são conferidas na entrega. |

O tamanho de 1000 e o overlap de 150 são parâmetros do `RecursiveCharacterTextSplitter`. Separadores e limites de página podem produzir chunks menores e sobreposição efetiva menor; os testes devem considerar esse comportamento, sem exigir que todo chunk tenha exatamente 1000 caracteres.

## 4. Decisões de implementação

- **Provedor:** implementar inicialmente um único provedor, pois o README permite OpenAI ou Gemini e não exige suporte simultâneo aos dois. Escolher o provedor para o qual houver credencial disponível antes da integração. Suporte ao segundo fica fora do escopo mínimo.
- **Modelos:** configurar os modelos de embeddings e chat por variáveis de ambiente. Na implementação, consultar a documentação oficial do provedor escolhido para confirmar disponibilidade, dimensões e compatibilidade com a integração instalada. Os nomes já presentes no `.env.example` não constituem validação de disponibilidade atual.
- **Banco vetorial:** usar `langchain_postgres.PGVector`, com conexão SQLAlchemy para o driver `psycopg`, no formato `postgresql+psycopg://postgres:postgres@localhost:5432/rag` para o ambiente local fornecido.
- **Configuração comum:** centralizar leitura e validação de configurações em um módulo pequeno, como `src/config.py`, para evitar divergências entre ingestão e consulta. Não exigir `PDF_PATH` ao iniciar apenas o chat.
- **Contrato da busca:** manter `search_prompt()` como fábrica da cadeia utilizada por `chat.py`. A cadeia recebe `{"pergunta": texto}` em `invoke()` e devolve uma string. Ajustar a assinatura inicial incompleta para refletir esse contrato.
- **Estado do chat:** tratar cada pergunta de forma independente. Histórico conversacional não é requisito e não deve acrescentar informações ao contexto do PDF.
- **Escopo:** não criar interface web, API HTTP, autenticação, OCR ou processamento de múltiplos PDFs para cumprir esta entrega.

Fluxo de ingestão: PDF → páginas com metadados → splitter → embeddings → collection no PostgreSQL.

Fluxo de consulta: pergunta → embedding → dez chunks mais próximos → contexto concatenado → prompt obrigatório → LLM → resposta textual no terminal.

## 5. Etapas de implementação

### Etapa 1 — Preparar ambiente e confirmar o provedor

- [ ] Criar e ativar o ambiente virtual conforme o README.
- [ ] Instalar `requirements.txt` e registrar a versão de Python efetivamente validada.
- [ ] Escolher um provedor, confirmar os modelos na documentação oficial e verificar a compatibilidade com as versões instaladas.
- [ ] Alterar dependências somente se houver incompatibilidade comprovada; registrar os ajustes necessários.
- [ ] Completar `.env.example` com `DATABASE_URL`, `PG_VECTOR_COLLECTION_NAME` e `PDF_PATH=document.pdf`.
- [ ] Acrescentar a variável do modelo de chat: `OPENAI_CHAT_MODEL` ou `GOOGLE_CHAT_MODEL`, conforme a escolha. Manter as variáveis de embeddings correspondentes.
- [ ] Implementar a configuração compartilhada, com erros claros para variáveis ausentes e sem imprimir chaves de API.
- [ ] Subir o Compose e verificar a saúde do PostgreSQL, a conclusão do bootstrap e a existência da extensão `vector`.

**Aceite:** ambiente instalado, conexão funcionando e configuração suficiente para criar embeddings e chamar o modelo de chat escolhido. A chave deve existir somente no `.env` local.

### Etapa 2 — Implementar ingestão em `src/ingest.py`

- [ ] Validar a existência e a extensão do arquivo informado em `PDF_PATH`.
- [ ] Ler as páginas com `PyPDFLoader` e rejeitar documentos sem texto extraível com mensagem explicativa.
- [ ] Aplicar `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150, length_function=len)`.
- [ ] Preservar metadados de origem e página; atribuir identificador de chunk para facilitar conferência.
- [ ] Criar o cliente de embeddings e o `PGVector` com a configuração compartilhada.
- [ ] Persistir os chunks e embeddings na collection configurada.
- [ ] Exibir um resumo com arquivo, páginas carregadas, chunks gravados e collection de destino.
- [ ] Tratar falhas de arquivo, conexão, credencial e API com mensagens acionáveis e código de saída diferente de zero.

**Recomendação de robustez:** usar IDs determinísticos por documento e chunk para evitar duplicatas na reingestão do mesmo arquivo. Para substituição de um PDF ou mudança de modelo, documentar uma reinicialização explícita da collection; não apagar dados automaticamente ao executar o script.

**Aceite:** a ingestão do PDF fornecido termina com sucesso e os registros armazenam texto, metadados e vetores consultáveis. O chat posterior recupera esses dados em outro processo.

### Etapa 3 — Implementar recuperação em `src/search.py`

- [ ] Inicializar embeddings e banco usando a mesma configuração da ingestão.
- [ ] Verificar se a collection contém dados e orientar a execução da ingestão quando estiver vazia ou ausente.
- [ ] Executar `similarity_search_with_score(pergunta, k=10)` para cada pergunta válida. A integração deve produzir o embedding da consulta.
- [ ] Concatenar `page_content` dos documentos recuperados, com separadores legíveis, e preencher `{contexto}` e `{pergunta}` no template existente.
- [ ] Preservar integralmente as regras, os exemplos e a frase de recusa do prompt obrigatório.
- [ ] Chamar o modelo de chat configurado e converter sua saída em string.
- [ ] Quando a recuperação não retornar conteúdo, devolver diretamente `Não tenho informações necessárias para responder sua pergunta.`
- [ ] Propagar falhas operacionais de modo que a CLI as apresente como erros de execução, distinguindo-as da ausência de informação no PDF.

**Aceite:** a cadeia recebe uma pergunta, consulta a collection com `k=10` e retorna uma resposta baseada nos trechos recuperados usando o prompt exigido.

**Atenção:** a busca vetorial pode retornar trechos mesmo quando a pergunta não tem resposta. Resultado não vazio não comprova relevância. Não criar um limite arbitrário sobre os scores: qualquer filtro adicional exige conhecer a métrica utilizada e validar o comportamento com o PDF. Esse filtro não é requisito do trabalho.

### Etapa 4 — Implementar interação em `src/chat.py`

- [ ] Inicializar a cadeia uma vez, antes do laço de interação.
- [ ] Ler perguntas com `input("PERGUNTA: ")` e invocar a cadeia com `{"pergunta": texto}`.
- [ ] Exibir `RESPOSTA: ...` e um separador entre interações.
- [ ] Ignorar entradas vazias sem consultar a API.
- [ ] Oferecer saída com `sair` ou `exit` e encerrar corretamente em EOF e `Ctrl+C`.
- [ ] Exibir erros de inicialização com orientação para configuração ou ingestão e retornar código de falha.
- [ ] Em falhas transitórias de consulta, informar o problema sem apresentar uma resposta inventada; permitir nova pergunta quando possível.

**Aceite:** o usuário consegue fazer pelo menos três perguntas consecutivas e sair normalmente, sem reiniciar o processo entre perguntas.

### Etapa 5 — Verificar requisitos e fundamentação das respostas

Criar testes automatizados focados no comportamento, usando `unittest` e mocks, ou outra ferramenta já adotada durante a implementação. Os testes isolados não devem depender de API paga nem de banco disponível.

- [ ] Confirmar os parâmetros do splitter e a preservação de metadados com texto sintético suficientemente longo.
- [ ] Verificar que a busca envia a pergunta e `k=10` ao banco vetorial.
- [ ] Verificar que os chunks recuperados e a pergunta são inseridos no prompt obrigatório.
- [ ] Verificar a recusa exata na ausência de contexto recuperado.
- [ ] Verificar o contrato entre CLI e cadeia: várias perguntas, entrada vazia e saída.
- [ ] Verificar mensagens de configuração ausente e falhas externas, sem expor segredos.

Executar também uma validação integrada com PostgreSQL real, o PDF fornecido e o provedor escolhido:

| Cenário | Preparação | Resultado esperado |
| --- | --- | --- |
| Informação explícita | Selecionar ao menos três fatos no PDF e registrar a página e o trecho de evidência. | Respostas corretas, sem acrescentar dados externos. |
| Informação ausente | Selecionar ao menos três perguntas cuja resposta não está no PDF. | Frase de recusa exata. |
| Pergunta de opinião | Perguntar se um fato descrito é bom ou ruim. | Frase de recusa exata. |
| Tentativa de ignorar as regras | Pedir para responder com conhecimento externo ou ignorar o contexto. | As restrições são mantidas e não há resposta externa. |
| Banco vazio | Usar uma collection de teste vazia. | Orientação clara para executar a ingestão. |
| PDF inválido ou sem texto | Usar um caminho inexistente e uma amostra sem texto extraível. | Falha compreensível, sem anunciar sucesso. |
| Persistência | Reiniciar o serviço PostgreSQL sem remover seu volume. | Os chunks continuam disponíveis. |
| Reingestão, se implementada | Executar a ingestão duas vezes com o mesmo arquivo e configuração. | A contagem de chunks não duplica. |

Os exemplos de faturamento e clientes do README não devem ser usados como fatos sobre o `document.pdf` sem conferir seu conteúdo. A resposta esperada precisa derivar da evidência no arquivo real.

**Aceite:** testes isolados aprovados e resultados integrados registrados em `plans/validacao.md`, incluindo perguntas, respostas, evidências, modelos utilizados e limitações observadas.

Um prompt por si só não garante ausência absoluta de alucinações. A validação integrada deve procurar respostas indevidas e orientar ajustes antes da entrega; o relatório não deve declarar garantias que os testes não demonstram.

### Etapa 6 — Documentar e preparar a entrega

- [ ] Atualizar o README preservando os requisitos do enunciado e acrescentando as instruções da solução.
- [ ] Documentar pré-requisitos, versão de Python validada, Docker e Docker Compose.
- [ ] Incluir criação do ambiente virtual, instalação das dependências e cópia de `.env.example` para `.env`.
- [ ] Explicar cada variável de ambiente e identificar o provedor e os modelos efetivamente validados.
- [ ] Manter a sequência principal: `docker compose up -d`, `python src/ingest.py` e `python src/chat.py`.
- [ ] Documentar o comando dos testes e exemplos reais de pergunta respondida e de recusa.
- [ ] Explicar erros comuns: banco indisponível, porta 5432 ocupada, collection vazia, credencial inválida, quota da API e PDF sem texto.
- [ ] Documentar que mudar o modelo de embeddings exige reindexação e que dimensões incompatíveis podem exigir recriar a collection. Mesmo dimensões iguais não tornam modelos diferentes compatíveis semanticamente.
- [ ] Explicar os efeitos destrutivos de qualquer procedimento de limpeza de collection ou remoção do volume e mantê-lo separado da execução normal.
- [ ] Reexecutar as instruções em um ambiente novo, usando uma collection de validação, e conferir que não dependem de arquivos locais não versionados.
- [ ] Conferir o fork exigido pelo enunciado, o conteúdo versionado e a visibilidade pública do repositório de entrega. Não versionar `.env` nem credenciais.

**Aceite:** outra pessoa consegue executar o projeto seguindo apenas o README e fornecendo uma chave válida do provedor escolhido.

## 6. Arquivos previstos

| Arquivo | Alteração planejada |
| --- | --- |
| `src/ingest.py` | Implementação completa da ingestão. |
| `src/search.py` | Recuperação, montagem do prompt e chamada da LLM. |
| `src/chat.py` | Interação no terminal e tratamento de encerramento e erros. |
| `src/config.py` | Novo módulo pequeno para configuração compartilhada. |
| `.env.example` | Configuração suficiente e exemplos locais sem segredos. |
| `requirements.txt` | Ajustes somente quando necessários para compatibilidade. |
| `docker-compose.yml` | Preservar a configuração fornecida; corrigir apenas problemas demonstrados na execução. |
| `tests/` | Testes isolados dos comportamentos críticos. |
| `README.md` | Instruções da solução, validação e diagnóstico de problemas. |
| `plans/validacao.md` | Registro posterior da execução integrada e das evidências. |

## 7. Dependências, riscos e mitigação

| Risco ou dependência | Como tratar |
| --- | --- |
| Chave de API e disponibilidade de modelos | Resolver na primeira etapa e confirmar os modelos na documentação oficial do provedor. |
| Dependências fixadas incompatíveis com o ambiente ou modelo escolhido | Testar instalação e integração mínima antes de implementar todo o fluxo; ajustar apenas o necessário. |
| Dimensão ou espaço de embeddings diferente entre ingestão e busca | Compartilhar a configuração; documentar reindexação quando o modelo mudar. |
| Recuperação sem a evidência necessária | Avaliar perguntas com trechos conhecidos do PDF; conferir extração, chunks e os dez resultados antes de alterar o prompt. |
| Resposta sem suporte no contexto | Preservar as regras obrigatórias, validar perguntas negativas e corrigir os desvios identificados. |
| Limites ou indisponibilidade da API | Informar a falha com clareza e manter testes isolados independentes da API. |
| PDF digitalizado sem texto | Informar a limitação; OCR não faz parte do requisito mínimo. |

Ordem de dependências: preparação → ingestão → recuperação → CLI → validação integrada → documentação e entrega. Os testes isolados acompanham cada implementação; o relatório integrado e a revisão final do README vêm após o fluxo completo funcionar.

## 8. Definição de conclusão

- [ ] Todos os requisitos R01–R11 têm evidência de atendimento.
- [ ] O PDF é ingerido com os parâmetros exigidos e persistido no pgVector.
- [ ] O chat consulta com `k=10`, usa o prompt obrigatório e funciona por múltiplas interações.
- [ ] A bateria de perguntas com e sem evidência passa na validação integrada.
- [ ] Os testes isolados passam e o relatório de validação registra os resultados reais.
- [ ] O README permite reproduzir a execução em ambiente novo.
- [ ] O repositório de entrega está público e não contém credenciais.
