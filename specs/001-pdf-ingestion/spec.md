# Feature Specification: Ingestão e persistência do PDF

**Feature Branch**: main (branch existente; nenhuma branch específica criada)

**Feature Directory**: specs/001-pdf-ingestion

**Created**: 2026-10-16

**Status**: Draft — pronta para planejamento após revisão de qualidade

**Input**: User description: "Permitir que o responsável configure o ambiente e ingira um PDF,
dividindo seu texto em trechos com sobreposição, gerando representações semânticas e mantendo
os dados persistidos e rastreáveis para consulta posterior. Tratar falhas de entrada,
configuração e serviços sem declarar sucesso indevido ou apagar dados automaticamente."

**Referências**: [plano inicial](../../plans/plano-implementacao.md), etapas 1 e 2 e validações
correspondentes das etapas 5 e 6; [README](../../README.md);
[constituição](../../.specify/memory/constitution.md); [AGENTS.md](../../AGENTS.md).
Cobertura principal: R02–R05. R01 e R10 são restrições transversais do projeto.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preparar um PDF para consulta (Priority: P1)

Como responsável pelo documento, quero executar a ingestão do PDF indicado e receber uma
confirmação verificável de que seu texto foi preparado e armazenado para consultas futuras.

**Why this priority**: Sem conteúdo persistido, nenhuma pergunta posterior pode ser respondida
com evidência documental.

**Independent Test**: Ingerir o documento fornecido em uma base de validação inicialmente vazia
e conferir trechos, representações semânticas e origem, sem depender da busca ou do chat.

**Acceptance Scenarios**:

1. **Given** configuração válida, armazenamento disponível e PDF com texto extraível,
   **When** a ingestão é executada, **Then** os trechos não vazios e suas representações são
   armazenados e o resumo informa documento, páginas, trechos gravados e destino.
2. **Given** uma página longa e outra curta, **When** o texto é dividido, **Then** a divisão
   respeita o limite configurado de 1000 caracteres e a sobreposição configurada de 150,
   admitindo trechos menores e menor sobreposição efetiva nos limites de separação.
3. **Given** trechos de diferentes páginas, **When** a gravação termina, **Then** cada trecho
   mantém texto, representação, origem, página e identificador verificáveis.
4. **Given** ambiente novo, instruções e credencial válida, **When** o operador segue a
   preparação e a ingestão documentadas, **Then** conclui a execução sem editar código-fonte.

---

### User Story 2 - Entender por que a ingestão não foi concluída (Priority: P2)

Como operador, quero receber uma explicação acionável quando um arquivo, configuração ou
serviço impedir a ingestão, para corrigir o problema sem confundir falha com sucesso.

**Why this priority**: A ingestão depende de arquivo e serviços externos; confirmar sucesso
indevidamente deixaria a etapa de consulta sem uma base confiável.

**Independent Test**: Exercitar entradas inválidas e indisponibilidade de serviços com amostras
e dublês, verificando mensagem, encerramento e ausência de confirmação enganosa.

**Acceptance Scenarios**:

1. **Given** caminho inexistente, arquivo inválido ou PDF sem texto extraível,
   **When** a ingestão é solicitada, **Then** ela falha com identificação do problema e orientação.
2. **Given** configuração obrigatória ausente ou credencial recusada,
   **When** a ingestão é iniciada, **Then** a falha é apresentada sem expor segredos.
3. **Given** falha de gravação ou de geração semântica após progresso parcial,
   **When** a execução é interrompida, **Then** o resultado identifica a falha e não declara
   ingestão completa; quantidades são apresentadas somente quando confirmadas.

---

### User Story 3 - Preservar o conteúdo já preparado (Priority: P2)

Como responsável pelo documento, quero reutilizar os dados após reiniciar o armazenamento,
sem executar novamente a ingestão nem perder conteúdo por ações normais do sistema.

**Why this priority**: Persistência e preservação dos dados permitem usar ingestão e consulta
em execuções independentes.

**Independent Test**: Partir de uma base com ingestão concluída, reiniciar o serviço preservando
seus dados e conferir o conjunto armazenado sem executar qualquer função de chat.

**Acceptance Scenarios**:

1. **Given** ingestão concluída, **When** o serviço de armazenamento é reiniciado preservando
   seus dados, **Then** os mesmos trechos e metadados continuam disponíveis.
2. **Given** dados existentes, **When** uma execução normal começa ou falha,
   **Then** nenhuma limpeza automática da base, coleção ou volume é realizada.
3. **Given** intenção de trocar o modelo de representação semântica,
   **When** o operador consulta as instruções, **Then** encontra a necessidade de reindexação
   e os efeitos de qualquer limpeza explícita, inclusive quando a dimensão não muda.
4. **Given** uma coleção com dados de um modelo, **When** é solicitada gravação com outro,
   **Then** o sistema impede a mistura na mesma coleção e orienta uma reindexação explícita
   ou o uso de destino separado, sem apagar os dados existentes automaticamente.

### Edge Cases

- PDF válido com páginas vazias: ignorar conteúdo vazio e ingerir as páginas com texto;
  documento integralmente vazio ou digitalizado sem texto: falhar informando a limitação.
- Documento curto: aceitar um único trecho; não completar conteúdo artificialmente.
- Porta do armazenamento ocupada ou serviço ainda não pronto: orientar a correção ou espera,
  sem anunciar ingestão bem-sucedida.
- Credencial inválida, quota esgotada e indisponibilidade externa: distinguir falha operacional
  de problema no arquivo e encerrar sem expor informações sensíveis.
- Reexecução do mesmo documento: a política deve ser documentada no planejamento.
  Eliminar duplicatas automaticamente é recomendação, não obrigação desta especificação.
- Documento alterado ou mudança de modelo: não pressupor substituição automática de conteúdo;
  documentar reindexação delimitada, mantendo a execução normal não destrutiva.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O operador DEVE poder informar arquivo, destino e configuração de representação
  semântica sem alterar o código-fonte; somente valores necessários à ingestão são obrigatórios.
- **FR-002**: O ambiente DEVE permitir preparar e verificar o armazenamento persistente e a
  capacidade vetorial usando o fluxo de inicialização exigido no README.
- **FR-003**: A ingestão DEVE validar o arquivo e extrair o texto por página, recusando documentos
  inexistentes, inválidos ou integralmente sem texto extraível.
- **FR-004**: O texto DEVE ser dividido com tamanho configurado de 1000 caracteres e sobreposição
  configurada de 150; separadores e limites de página podem produzir trechos menores e menor
  sobreposição efetiva. Conteúdo vazio não gera representações.
- **FR-005**: Cada trecho não vazio DEVE receber sua representação semântica e ser armazenado
  com texto, origem, página e identificador na base designada.
- **FR-006**: Uma ingestão concluída DEVE emitir um resumo com arquivo, páginas carregadas,
  trechos efetivamente gravados e destino; falhas parciais não podem ser anunciadas como sucesso.
- **FR-007**: Dados de uma ingestão concluída DEVEM permanecer disponíveis entre processos e após
  reinício do armazenamento sem remoção dos dados persistentes.
- **FR-008**: Configuração inválida e falhas de arquivo, credencial, quota, conexão ou serviço
  DEVEM produzir erro acionável e encerramento em falha, sem revelar segredos.
- **FR-009**: O funcionamento normal NÃO DEVE apagar dados previamente armazenados.
  Limpeza e reindexação devem ser procedimentos explícitos com efeitos documentados.
- **FR-010**: A mesma coleção NÃO DEVE misturar representações de modelos distintos.
  A documentação deve explicar a reindexação ao trocar de modelo, mesmo com dimensões iguais.
- **FR-011**: A preparação e a ingestão DEVEM ter instruções reproduzíveis, com configuração
  de exemplo sem segredos, política de reexecução e versão do ambiente efetivamente validada.

### Key Entities *(include if feature involves data)*

- **Documento de origem**: PDF identificado por caminho e origem, composto por páginas,
  com presença ou ausência de texto extraível.
- **Trecho documental**: conteúdo não vazio de uma página, com identificador e referência à origem.
- **Representação semântica**: representação numérica associada a um trecho, produzida por um
  modelo e dimensionalidade definidos.
- **Coleção documental**: agrupamento persistente dos trechos e representações compatíveis
  que será consumido pela etapa de consulta.
- **Resultado da ingestão**: documento processado, quantidades confirmadas, destino e situação
  de conclusão ou falha, inclusive parcial.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma execução com o documento fornecido e ambiente válido termina com confirmação
  e mantém todos os trechos não vazios produzidos, cada um com representação e origem conferíveis.
- **SC-002**: Após um reinício preservando os dados, a quantidade e o conteúdo dos registros da
  ingestão validada permanecem iguais, sem nova ingestão.
- **SC-003**: Todos os casos de falha definidos nos cenários e casos de borda produzem
  diagnóstico acionável; nenhum anuncia sucesso completo indevidamente ou expõe credenciais.
- **SC-004**: Uma pessoa seguindo apenas as instruções e fornecendo credencial válida consegue
  preparar o ambiente e concluir uma ingestão sem editar código-fonte.
- **SC-005**: A conferência de amostras de texto curto e longo demonstra os limites e a
  preservação de origem definidos em FR-004 e FR-005.

## Assumptions

- O público é o autor do trabalho e seu avaliador, operando localmente com acesso aos serviços
  necessários. Credencial válida e conectividade são pré-condições para a validação real.
- A entrega cobre um PDF com texto extraível e um único provedor. Reconhecimento de imagens,
  múltiplos documentos simultâneos e resposta a perguntas estão fora desta etapa.
- A escolha do provedor, modelos disponíveis, compatibilidade, configuração concreta e
  organização do código pertencem ao planejamento, respeitando README e constituição.
- Não há dependência de outra spec. Esta entrega fornece os dados para a
  [002-grounded-search](../002-grounded-search/spec.md).
- R01, R02 e R10 devem ser detalhados como restrições obrigatórias no plano técnico;
  não representam liberdade para alterar o conjunto de tecnologias exigido no enunciado.
- A recomendação de IDs determinísticos só passa a requisito se explicitamente adotada
  no planejamento e acompanhada de verificação de reingestão.
- A validação desta etapa cobre ingestão, erros e persistência. Perguntas e interação
  completa serão verificadas nas specs seguintes; não são declaradas concluídas aqui.
