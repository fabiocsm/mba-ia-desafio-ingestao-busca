# Feature Specification: Chat no terminal e entrega reproduzível

**Feature Branch**: main (branch existente; nenhuma branch específica criada)

**Feature Directory**: specs/003-terminal-chat

**Created**: 2026-10-16

**Status**: Draft — pronta para planejamento após revisão de qualidade

**Input**: User description: "Permitir que o usuário converse pelo terminal com a base do PDF,
fazendo várias perguntas na mesma execução, recebendo respostas fundamentadas ou recusas,
ignorando entradas vazias e encerrando normalmente. Apresentar falhas acionáveis e concluir
a entrega com instruções reproduzíveis, validação integrada e conferência R01–R11."

**Referências**: [plano inicial](../../plans/plano-implementacao.md), etapa 4 e consolidação
das etapas 5 e 6; [README](../../README.md); [constituição](../../.specify/memory/constitution.md);
[AGENTS.md](../../AGENTS.md). Cobertura principal: R09–R11; consolida as evidências R01–R11
sem transferir para esta etapa as verificações próprias das specs anteriores.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Conversar sobre o PDF pelo terminal (Priority: P1)

Como usuário, quero fazer várias perguntas na mesma sessão do terminal e visualizar
respostas legíveis, sem precisar reiniciar a aplicação entre as perguntas.

**Why this priority**: A interação pelo terminal é a interface exigida para uso e avaliação
da solução completa.

**Independent Test**: Com o componente de consulta disponível, iniciar uma sessão, submeter
ao menos três perguntas e encerrar normalmente. A interação também pode ser testada
isoladamente com respostas controladas, sem acesso a serviços externos.

**Acceptance Scenarios**:

1. **Given** base ingerida e configuração válida, **When** o chat é iniciado,
   **Then** apresenta PERGUNTA: e aguarda a entrada do usuário.
2. **Given** uma sessão aberta, **When** o usuário envia três perguntas consecutivas,
   **Then** recebe uma RESPOSTA: para cada uma, com separação legível, e pode continuar
   perguntando sem reiniciar a aplicação.
3. **Given** uma entrada vazia ou apenas espaços, **When** o usuário a envia,
   **Then** o chat aguarda uma pergunta válida sem consultar os serviços de resposta.
4. **Given** uma sessão aberta, **When** o usuário informa sair ou exit, ou encerra a
   entrada ou interrompe pelo teclado, **Then** a aplicação termina normalmente,
   sem apresentar o encerramento como uma falha de consulta.
5. **Given** resposta fundamentada ou recusa devolvida pela consulta,
   **When** o chat a apresenta, **Then** preserva seu conteúdo, incluindo a frase exata
   de recusa, e não complementa a resposta com conhecimento próprio.
6. **Given** informações mencionadas em uma pergunta anterior, **When** uma nova pergunta
   não possui evidência suficiente no contexto recuperado, **Then** o chat mantém a recusa
   devolvida pela consulta, sem usar o histórico da sessão para completá-la.

---

### User Story 2 - Corrigir problemas sem confundir erro com resposta (Priority: P2)

Como operador, quero entender problemas de inicialização ou consulta e saber se posso
tentar novamente, sem receber uma informação inventada ou um encerramento enganoso.

**Why this priority**: A interface deve tornar visíveis os impedimentos já identificados
na ingestão e na consulta, permitindo operar a solução com confiança.

**Independent Test**: Simular inicialização inválida, base vazia, falha fatal e uma consulta
com falha transitória seguida de sucesso; conferir mensagens e continuidade da sessão.

**Acceptance Scenarios**:

1. **Given** configuração obrigatória ausente ou serviço necessário indisponível na
   inicialização, **When** o chat é iniciado, **Then** explica o impedimento e encerra
   indicando falha, sem iniciar uma conversa aparentemente funcional.
2. **Given** base ainda não ingerida, **When** o chat tenta iniciar,
   **Then** orienta a executar a ingestão antes de fazer perguntas.
3. **Given** sessão ativa e falha transitória durante uma pergunta,
   **When** a falha é apresentada, **Then** ela é identificada como operacional,
   sem resposta factual ou recusa substituta, e a sessão aceita uma nova pergunta.
4. **Given** erro que impede a continuidade da sessão,
   **When** ele é detectado, **Then** o chat informa o motivo e encerra em falha.
5. **Given** mensagem de erro contendo informação sensível no serviço de origem,
   **When** o problema é mostrado ao usuário, **Then** credenciais e dados sensíveis
   não aparecem na saída.
6. **Given** base ingerida e configuração de consulta válida, mas sem arquivo de origem
   ou credencial de outro provedor, **When** o chat é iniciado, **Then** essas ausências
   não impedem uma sessão funcional.

---

### User Story 3 - Reproduzir e avaliar a entrega (Priority: P2)

Como avaliador, quero preparar o projeto e reproduzir os resultados usando somente
as instruções públicas e uma credencial válida, para conferir os requisitos do trabalho.

**Why this priority**: Código sem execução reproduzível e evidência não permite verificar
o atendimento ao enunciado.

**Independent Test**: Em um ambiente novo, seguir a documentação desde a preparação até
a ingestão e o chat, executar os casos de validação e conferir a evidência de cada requisito.

**Acceptance Scenarios**:

1. **Given** repositório obtido em ambiente novo e credencial válida,
   **When** o avaliador segue o README, **Then** consegue preparar o ambiente,
   ingerir o PDF e executar o chat sem editar código-fonte ou usar arquivos ocultos
   não documentados.
2. **Given** fluxo completo disponível, **When** a bateria integrada é executada,
   **Then** perguntas com evidência recebem respostas conferíveis e perguntas sem evidência,
   opinião e tentativas de desvio sem suporte recebem a recusa obrigatória.
3. **Given** resultados das três etapas, **When** a entrega é revisada,
   **Then** cada requisito R01–R11 possui evidência identificável e nenhuma verificação
   não executada é apresentada como aprovada.
4. **Given** repositório candidato à entrega, **When** seu conteúdo e acesso são conferidos,
   **Then** ele está público, deriva do fork exigido, contém os arquivos obrigatórios e
   não inclui credenciais reais.
5. **Given** necessidade de trocar modelo ou corrigir um problema comum,
   **When** o avaliador consulta as instruções, **Then** encontra configuração, diagnóstico,
   reindexação e os efeitos de qualquer procedimento destrutivo claramente delimitados.

### Edge Cases

- Espaços antes/depois de uma entrada: desconsiderá-los para detectar pergunta vazia e saída.
- Comandos de saída: aceitar sair e exit sem distinguir maiúsculas de minúsculas.
- Interrupção ou fim da entrada durante uma sessão: encerrar normalmente e liberar recursos.
- Falha transitória seguida de nova pergunta válida: manter a sessão utilizável.
- Falha fatal ou saída inesperada do componente de consulta: informar falha sem inventar resposta.
- Configuração do arquivo de origem ausente após ingestão: não impedir o chat se a base e a
  configuração de consulta estiverem válidas.
- Nenhuma credencial disponível para uma validação real: registrar a dependência e manter
  o critério pendente, sem declarar o projeto integralmente validado.
- Limpeza do armazenamento para teste: usar dados de validação e procedimento explícito;
  o funcionamento normal não apaga bases existentes.
- Exemplo de resposta do enunciado sem correspondência no PDF: não utilizá-lo como evidência.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O chat DEVE iniciar pelo comando exigido no README e permitir várias perguntas
  na mesma execução.
- **FR-002**: A interação DEVE exibir PERGUNTA: para entrada e RESPOSTA: para respostas válidas,
  com separação legível entre interações.
- **FR-003**: Entradas vazias ou compostas apenas por espaços DEVEM ser ignoradas sem iniciar
  consulta ou geração.
- **FR-004**: O usuário DEVE poder encerrar normalmente com sair, exit, fim de entrada ou
  interrupção pelo teclado; comandos de saída ignoram caixa e espaços nas extremidades.
- **FR-005**: O chat DEVE apresentar o resultado da consulta sem acrescentar conteúdo,
  preservando respostas fundamentadas e a frase de recusa obrigatória.
- **FR-006**: Falhas de inicialização DEVEM apresentar orientação acionável e encerrar em falha;
  base ausente ou vazia deve orientar a ingestão.
- **FR-007**: Falhas transitórias de consulta DEVEM ser apresentadas como erros operacionais
  e permitir nova pergunta quando a sessão continuar utilizável; falhas fatais encerram
  em falha, sem gerar respostas substitutas.
- **FR-008**: Mensagens de erro e registros de operação NÃO DEVEM revelar credenciais ou expor
  documentos e perguntas completos por padrão.
- **FR-009**: A documentação DEVE permitir preparar o ambiente, preencher configuração,
  ingerir o PDF, executar o chat e rodar as verificações adotadas, preservando a estrutura
  e a ordem de execução do enunciado.
- **FR-010**: A documentação DEVE identificar ambiente e modelos efetivamente validados,
  exemplos reais de resposta e recusa, diagnóstico de falhas, política de reexecução da
  ingestão e reindexação com efeitos destrutivos explicitados.
- **FR-011**: A entrega DEVE consolidar um relatório com comandos, ambiente, modelos,
  perguntas, respostas, trechos/páginas de evidência, falhas observadas e limitações.
- **FR-012**: A validação final DEVE conferir pelo menos três perguntas com evidência,
  três sem resposta, opinião, tentativa de desvio, base vazia, arquivo inválido/sem texto
  e persistência após reinício sem remoção dos dados; evidências anteriores válidas podem
  ser referenciadas quando a integração não alterar o comportamento verificado.
- **FR-013**: A entrega DEVE manter rastreabilidade R01–R11 e repositório público no fork
  exigido, com todos os arquivos obrigatórios e sem credenciais reais versionadas.
- **FR-014**: Verificações bloqueadas ou não executadas DEVEM permanecer explicitamente
  pendentes; conclusão de implementação não substitui comprovação de funcionamento.
- **FR-015**: Uma base previamente ingerida DEVE permitir iniciar o chat sem exigir o arquivo
  original ou a credencial de provedor não utilizado.

### Key Entities *(include if feature involves data)*

- **Sessão de terminal**: sequência de perguntas, respostas e erros operacionais até o encerramento,
  sem memória factual compartilhada entre perguntas.
- **Interação**: pergunta atual, resultado da consulta e forma de apresentação ao usuário.
- **Configuração documentada**: valores e pré-requisitos necessários para reproduzir cada fluxo,
  com exemplos públicos sem segredos.
- **Evidência de entrega**: requisito, procedimento executado, resultado e referência aos
  fatos do documento quando a verificação envolver uma resposta.
- **Relatório de validação**: registro consolidado dos resultados, ambiente e limitações reais.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma sessão demonstra pelo menos três perguntas consecutivas e uma resposta por
  pergunta, sem reinício entre interações.
- **SC-002**: Todos os casos definidos de entrada vazia, saída e interrupção terminam ou
  continuam conforme esperado, sem consultas indevidas ou falha aparente de encerramento.
- **SC-003**: Uma falha transitória seguida de pergunta válida permite continuar na mesma
  sessão; falhas fatais são identificadas sem apresentar conteúdo como resposta factual.
- **SC-004**: Uma pessoa seguindo somente a documentação e fornecendo credencial válida
  reproduz preparação, ingestão e chat em um ambiente novo sem modificar código-fonte.
- **SC-005**: Os onze requisitos R01–R11 têm resultado rastreável no relatório final;
  a entrega só é declarada validada quando todos os critérios obrigatórios são atendidos.
- **SC-006**: A bateria final registra os cenários de FR-012 e confirma o resultado esperado
  em todos os casos executados, com referência documental para cada resposta afirmativa.
- **SC-007**: O repositório de entrega pode ser acessado publicamente e sua revisão confirma
  estrutura obrigatória, origem do fork e ausência de credenciais reais versionadas.

## Assumptions

- Depende da [001-pdf-ingestion](../001-pdf-ingestion/spec.md) e da
  [002-grounded-search](../002-grounded-search/spec.md), incluindo seus contratos e evidências.
- A CLI apenas apresenta resultados e gerencia interação; a lógica de fundamentação permanece
  no componente de consulta. A sessão não introduz histórico para completar respostas.
- A suíte isolada pode usar interações e resultados controlados. A validação completa depende
  de documento, serviços e credencial válidos.
- Documentação e testes são incrementais: esta etapa consolida o material produzido nas
  anteriores, em vez de adiar para o fim todas as verificações.
- O relatório consolidado terá o local previsto no plano inicial, e a rastreabilidade
  deve identificar qual etapa produziu cada evidência sem duplicar registros desnecessariamente.
- Interface web, autenticação, OCR, múltiplos PDFs, segundo provedor e outras ampliações
  continuam fora do escopo inicial.
- Contratos internos, organização dos componentes e comandos concretos dos verificadores
  pertencem ao plano técnico e devem respeitar a constituição.
