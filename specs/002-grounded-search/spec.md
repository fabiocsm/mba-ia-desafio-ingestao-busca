# Feature Specification: Busca e respostas fundamentadas no PDF

**Feature Branch**: main (branch existente; nenhuma branch específica criada)

**Feature Directory**: specs/002-grounded-search

**Created**: 2026-10-16

**Status**: Implementada, validada e convergida em 2026-10-16 — chat/entrega global na spec 003

**Input**: User description: "Receber uma pergunta, selecionar até dez trechos relevantes do
PDF já ingerido e responder somente com informações explícitas nesse contexto. Usar as
regras e os exemplos obrigatórios do trabalho, recusar perguntas sem evidência e distinguir
essas recusas de falhas operacionais. Disponibilizar o comportamento para integração
posterior com o chat, sem depender da interface interativa nesta etapa."

**Referências**: [plano inicial](../../plans/plano-implementacao.md), etapa 3 e validações
correspondentes das etapas 5 e 6; [README](../../README.md);
[constituição](../../.specify/memory/constitution.md); [AGENTS.md](../../AGENTS.md).
Cobertura principal: R06–R08. R01 e R10 permanecem transversais.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Obter resposta sustentada pelo documento (Priority: P1)

Como pessoa que consulta o PDF, quero fazer uma pergunta sobre um fato explícito no documento
e receber uma resposta fiel ao conteúdo disponível, sem informações adicionais inventadas.

**Why this priority**: Transformar conteúdo indexado em uma resposta verificável é o objetivo
central da consulta documental.

**Independent Test**: Com uma base válida previamente ingerida, submeter diretamente ao
componente de consulta ao menos três perguntas com trechos de evidência conhecidos, sem
executar a interface interativa, e confrontar as respostas com o documento real.

**Acceptance Scenarios**:

1. **Given** coleção compatível com conteúdo e pergunta cuja resposta está em um trecho
   recuperado, **When** a consulta é executada, **Then** a resposta comunica o fato
   explicitamente documentado sem acrescentar informações externas.
2. **Given** mais de dez trechos disponíveis, **When** uma pergunta é consultada,
   **Then** o contexto reúne os dez resultados mais próximos da pergunta, ordenados pela
   recuperação e separados de forma legível.
3. **Given** entre um e nove trechos disponíveis, **When** a consulta é executada,
   **Then** somente os trechos existentes são utilizados, sem preenchimento artificial.
4. **Given** duas perguntas feitas sucessivamente, **When** a segunda é processada,
   **Then** sua resposta depende somente da pergunta atual e do contexto recuperado.

---

### User Story 2 - Receber recusa quando falta evidência (Priority: P1)

Como pessoa que consulta o PDF, quero saber claramente quando o contexto não sustenta uma
resposta, para não interpretar uma suposição ou opinião como informação do documento.

**Why this priority**: Uma resposta falsa contraria o requisito essencial de fundamentação,
mesmo que o sistema tenha recuperado textos semelhantes à pergunta.

**Independent Test**: Submeter pelo menos três perguntas sem resposta no documento, uma
pergunta de opinião e uma tentativa de desviar as regras, além de simular recuperação
vazia; comparar a resposta com a frase de recusa obrigatória.

**Acceptance Scenarios**:

1. **Given** trechos recuperados que não respondem explicitamente à pergunta,
   **When** a consulta é executada, **Then** a saída é exatamente
   "Não tenho informações necessárias para responder sua pergunta.".
2. **Given** recuperação sem conteúdo em uma base inicialmente válida,
   **When** a consulta termina a recuperação, **Then** devolve a recusa obrigatória
   diretamente, sem solicitar uma resposta ao serviço de geração.
3. **Given** pergunta de opinião ou solicitação de conhecimento externo,
   **When** a consulta é executada, **Then** responde com a recusa obrigatória.
4. **Given** pergunta ou trecho documental que manda ignorar as regras,
   **When** a consulta é executada, **Then** essas instruções não alteram as restrições;
   na amostra sem evidência para a pergunta, o resultado é a recusa obrigatória.
5. **Given** uma pergunta que só poderia ser completada com informação de uma interação
   anterior, **When** ela é consultada sem evidência suficiente no contexto atual,
   **Then** a resposta é a recusa obrigatória.

---

### User Story 3 - Identificar impedimentos de consulta (Priority: P2)

Como operador, quero distinguir falta de informação documental de configuração incorreta
ou indisponibilidade, para corrigir a execução sem atribuir o problema ao conteúdo do PDF.

**Why this priority**: Ausência de base e falha de serviço não permitem avaliar se uma pergunta
poderia ser respondida; o diagnóstico deve preservar essa diferença.

**Independent Test**: Usar coleção vazia, configuração inválida e falhas simuladas de serviços,
verificando erros distintos da recusa factual e ausência de segredos nas mensagens.

**Acceptance Scenarios**:

1. **Given** coleção ausente ou vazia no início, **When** o componente é inicializado,
   **Then** orienta a executar a ingestão, sem apresentar a recusa como resultado de consulta.
2. **Given** falha de conexão, credencial, quota ou geração, **When** a consulta é solicitada,
   **Then** apresenta erro operacional acionável, sem inventar resposta ou usar a recusa factual.
3. **Given** configuração de consulta compatível e base existente, mas sem configuração
   do arquivo de origem ou de provedor não utilizado, **When** a consulta é inicializada,
   **Then** essas configurações irrelevantes não impedem seu funcionamento.
4. **Given** pergunta vazia ou apenas espaços, **When** é enviada ao componente,
   **Then** não inicia recuperação ou geração e informa que é necessária uma pergunta.
5. **Given** modelo de representação diferente do usado na base, **When** a consulta é
   inicializada, **Then** a incompatibilidade impede respostas sobre essa base e orienta
   usar a configuração compatível ou reindexar explicitamente.

### Edge Cases

- Coleção com menos de dez trechos: usar apenas os resultados existentes.
- Pergunta sem resposta, mas com resultados próximos: recusar; proximidade não é evidência.
- Fato presente no PDF, mas ausente dos trechos recuperados: recusar nessa consulta e registrar
  a limitação para revisão da recuperação, sem recorrer a conhecimento externo.
- Contexto contraditório ou insuficiente para determinar o fato solicitado: recusar, sem
  resolver a contradição por interpretação; perguntas sobre uma contradição explícita
  podem ser respondidas se o próprio contexto as sustentar.
- Dados removidos entre a inicialização e a recuperação: se o retorno for vazio, aplicar
  a recusa direta; falhas de acesso continuam sendo erros operacionais.
- Exemplo ilustrativo do enunciado: não considerar seus valores como fatos do PDF fornecido.
- Resultado com texto vazio: não acrescentá-lo como evidência; aplicar recusa se não restar conteúdo.
- Retorno inesperado ou falha do serviço de geração: apresentar erro operacional sem
  fabricar uma resposta ou um sucesso aparente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE aceitar uma pergunta textual não vazia e devolver uma resposta
  textual ou um erro operacional identificável, sem exigir a interface interativa.
- **FR-002**: A pergunta DEVE ser representada semanticamente de forma compatível com a
  ingestão, usando a mesma coleção, modelo e dimensionalidade; incompatibilidade impede
  a consulta sobre os dados existentes até correção ou reindexação.
- **FR-003**: A recuperação DEVE solicitar dez resultados mais relevantes para a pergunta;
  se houver menos resultados, utilizar apenas os disponíveis.
- **FR-004**: O contexto DEVE reunir somente o texto dos trechos recuperados, preservando a
  ordenação da recuperação e separando os trechos de forma legível.
- **FR-005**: A geração DEVE usar a pergunta atual e o contexto com as regras e exemplos
  obrigatórios do README, sem incorporar conhecimento externo ou memória de interações.
- **FR-006**: Toda resposta afirmativa DEVE ser sustentada por informação explícita no contexto.
  Opiniões ou inferências além do que está escrito não podem completar a resposta.
- **FR-007**: Sem evidência suficiente, a saída DEVE ser exatamente
  "Não tenho informações necessárias para responder sua pergunta.".
- **FR-008**: Sem conteúdo recuperado, a recusa DEVE ser devolvida diretamente, sem solicitação
  ao serviço de geração.
- **FR-009**: Instruções presentes no documento e na pergunta NÃO DEVEM substituir as regras
  de fundamentação, recusa e independência entre consultas.
- **FR-010**: Coleção inicialmente vazia ou ausente DEVE gerar orientação para ingestão;
  indisponibilidade, falhas de credencial, quota ou geração devem produzir erros
  operacionais distintos da recusa factual, sem revelar segredos.
- **FR-011**: A consulta NÃO DEVE exigir localização do PDF original nem credencial de
  provedor não utilizado, quando a base compatível já estiver disponível.
- **FR-012**: O comportamento DEVE ser validado contra perguntas com e sem evidência,
  opinião e tentativa de desvio, com registro de respostas e páginas que sustentam os fatos.
- **FR-013**: Perguntas vazias DEVEM ser rejeitadas antes de qualquer recuperação ou geração.
- **FR-014**: A existência de resultados ou scores de proximidade NÃO DEVE ser usada como
  comprovação de resposta; um filtro adicional exige justificativa da métrica e validação.

### Key Entities *(include if feature involves data)*

- **Pergunta**: texto atual do usuário, independente das interações anteriores.
- **Trecho recuperado**: conteúdo documental selecionado para a pergunta, com origem e posição
  na ordenação de recuperação.
- **Contexto**: conjunto ordenado dos textos recuperados que pode sustentar a resposta.
- **Resultado da consulta**: resposta fundamentada, recusa padronizada ou erro operacional,
  distinguíveis pelo comportamento apresentado ao consumidor.
- **Caso de validação**: pergunta, classificação esperada, resposta obtida e, quando houver
  fato afirmativo, trecho e página de evidência.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Pelo menos três perguntas sobre fatos conhecidos recebem respostas corretas,
  cada uma sustentada por trecho e página conferidos no documento real, sem acréscimos externos.
- **SC-002**: Pelo menos três perguntas sem resposta, uma de opinião e uma tentativa de
  desvio sem evidência recebem a frase de recusa exata em todos os casos da bateria definida.
- **SC-003**: Uma consulta sem conteúdo recuperado produz a recusa exata sem solicitação
  de geração; uma base com menos de dez trechos não produz evidência artificial.
- **SC-004**: Todos os cenários de falha operacional definidos nesta spec são identificados
  como falhas de execução, sem serem apresentados como resposta factual ou recusa documental.
- **SC-005**: As consultas da bateria podem ser executadas e seus resultados conferidos sem
  iniciar uma sessão interativa, permitindo demonstrar esta entrega separadamente.
- **SC-006**: Cada caso da bateria possui registro de pergunta, resposta e resultado esperado;
  os casos afirmativos possuem referências verificáveis à evidência no documento.

## Assumptions

- Depende da [001-pdf-ingestion](../001-pdf-ingestion/spec.md) para conteúdo real persistido
  e configuração compatível. Testes isolados podem usar dados preparados e dublês.
- Mantém um único documento e um único provedor. Sem interface web, histórico de conversa,
  ferramentas externas ou complementação por pesquisa fora do documento.
- A interface pública usada pelo chat, os componentes e o modo de composição devem seguir
  o contrato já estabelecido na constituição e ser detalhados no plano técnico.
- Não se adiciona filtro numérico de relevância por padrão; qualquer adoção exige evidência
  de necessidade e validação específica no planejamento.
- Escolha de modelo de resposta, configuração concreta, timeouts e retentativas limitadas
  pertencem ao planejamento; os modelos devem ser confirmados na documentação oficial.
- Evidências desta etapa compõem o relatório de validação do projeto. A bateria definida
  mede os casos executados e não garante ausência de alucinações para todas as perguntas.
- O chat interativo e a reprodução completa pelo avaliador pertencem à
  [003-terminal-chat](../003-terminal-chat/spec.md).
