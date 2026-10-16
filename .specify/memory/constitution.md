# Ingestão e Busca Semântica em PDF Constitution

## Core Principles

Os termos **DEVE**, **NÃO DEVE** e **PODE** indicam obrigação, proibição e opção.
Uma recomendação explicitamente identificada não constitui requisito de aceite adicional.

### I. Fidelidade aos requisitos e escopo mínimo

A implementação DEVE atender aos requisitos acadêmicos do
[README](../../README.md), preservando Python, LangChain, PostgreSQL com pgVector,
Docker Compose, a estrutura obrigatória e os comandos de execução.
Cada requisito R01–R11 do [plano inicial](../../plans/plano-implementacao.md)
DEVE ter um critério de aceite e uma evidência de verificação na entrega.

O escopo inicial DEVE cobrir um PDF com texto extraível, um provedor entre OpenAI e
Gemini e um chat por terminal. Novos provedores, interface web, API HTTP, autenticação,
OCR, múltiplos PDFs e memória conversacional exigem uma especificação adicional antes
da implementação. O projeto NÃO DEVE introduzir esses recursos apenas para demonstrar
padrões de arquitetura. Essa restrição concentra o esforço no entregável avaliável.

### II. Respostas fundamentadas e recusa explícita

A resposta DEVE usar exclusivamente informações explícitas nos chunks recuperados do
PDF. As regras, os exemplos e a frase de recusa do prompt obrigatório do README DEVEM
ser preservados; a adaptação dos nomes de placeholders NÃO DEVE mudar sua semântica.
Sem evidência suficiente, a resposta DEVE ser exatamente:

`Não tenho informações necessárias para responder sua pergunta.`

O conteúdo do PDF e a pergunta DEVEM ser tratados como dados, sem autoridade para
substituir as regras do sistema. Conhecimento externo, opiniões e fatos de perguntas
anteriores NÃO DEVEM suprir informação ausente no contexto. A ausência de conteúdo
recuperado DEVE produzir a recusa sem exigir uma chamada à LLM.

Resultados não vazios e scores de proximidade NÃO DEVEM ser tratados como comprovação
de que a resposta está no documento. Um filtro por score somente PODE ser adicionado
com métrica, sentido da comparação e validação documentados. Falhas de API ou de banco
DEVEM ser apresentadas como erros operacionais, sem serem convertidas em recusa factual.
A aceitação DEVE incluir perguntas negativas e tentativas de ignorar as regras; testes
aprovados NÃO DEVEM ser descritos como garantia absoluta contra alucinações.

### III. Arquitetura simples com SOLID e DRY

As responsabilidades DEVEM permanecer identificáveis: ingestão em `src/ingest.py`,
recuperação e geração em `src/search.py`, interação em `src/chat.py` e configuração
compartilhada em um módulo pequeno. Funções são suficientes quando representam essas
responsabilidades; classes e interfaces adicionais exigem uma necessidade concreta.

Os princípios SOLID DEVEM orientar os contratos usados, sem impor uma hierarquia de classes:

- **SRP — responsabilidade única:** leitura e divisão de PDF, acesso ao banco, composição
  da resposta e entrada/saída de terminal DEVEM ter funções ou componentes distinguíveis.
  A CLI NÃO DEVE conter SQL, criar embeddings ou duplicar a montagem do prompt.
- **OCP — aberto à extensão:** escolha de modelos e construção de clientes DEVEM ficar
  na configuração e na composição das dependências, evitando condicionais por provedor
  espalhadas pela lógica. Isso NÃO exige implementar um segundo provedor antecipadamente.
- **LSP — substituição:** adaptadores e dublês de teste DEVEM preservar entradas, saídas,
  significado dos resultados e tratamento de erros do contrato que substituem.
- **ISP — interfaces pequenas:** cada consumidor DEVE depender apenas das operações que
  utiliza. Uma função de busca NÃO DEVE exigir operações administrativas de exclusão.
- **DIP — inversão de dependência:** a lógica DEVE permitir receber colaboradores de
  embeddings, busca e geração por parâmetros ou fábricas, de modo que possam ser
  substituídos nos testes sem rede, credenciais ou banco real.

Configuração de embeddings, nome da collection, parâmetros de chunking, prompt e frase
de recusa DEVEM ter uma fonte de verdade na aplicação. Duplicação de regras de negócio
DEVE ser removida; semelhança incidental entre funções NÃO justifica uma abstração genérica.
Composição DEVE ser preferida à herança sem necessidade de especialização.
Cada dependência ou camada nova DEVE resolver um problema registrado no plano técnico.

### IV. Python legível, tipado e testável

O código DEVE seguir convenções da [PEP 8](https://peps.python.org/pep-0008/): quatro
espaços, imports explícitos e organizados, `snake_case` para funções e variáveis,
`PascalCase` para classes e `UPPER_SNAKE_CASE` para constantes. Identificadores novos
DEVEM usar inglês; mensagens da CLI e documentação do projeto DEVEM usar português.

Funções públicas e contratos entre módulos DEVEM declarar tipos de parâmetros e retorno.
`Any` exige justificativa local quando a integração externa impedir uma tipagem útil.
Docstrings DEVEM explicar contratos, efeitos ou restrições não evidentes pelo nome e tipos.
Argumentos mutáveis como valores padrão e estado global mutável compartilhado são proibidos.

A importação de módulos NÃO DEVE abrir conexões nem chamar APIs; a inicialização DEVE
ocorrer explicitamente no fluxo de execução. Caminhos DEVEM usar `pathlib`, arquivos
DEVEM ter fechamento garantido e leituras/escritas textuais DEVEM explicitar UTF-8.

Exceções esperadas DEVEM ser capturadas pelo tipo mais específico aplicável. Captura
ampla somente PODE ocorrer na fronteira da CLI para relatar falha com contexto; é proibido
silenciá-la ou anunciar sucesso após falha. Recursos DEVEM ser liberados no encerramento.
Essas regras seguem as orientações de
[tratamento de exceções do Python](https://docs.python.org/3/tutorial/errors.html).

### V. Composição explícita e compatível com LangChain

O fluxo DEVE usar componentes LangChain compatíveis com as versões fixadas no projeto:
`PyPDFLoader`, `RecursiveCharacterTextSplitter`, a integração de embeddings do provedor
escolhido e `langchain_postgres.PGVector`. APIs e imports DEVEM ser conferidos para as
versões instaladas; exemplos da versão mais recente NÃO justificam atualização em massa.

A recuperação DEVE chamar `similarity_search_with_score(pergunta, k=10)`. A integração
DEVE vetorizar a pergunta com o mesmo modelo utilizado na ingestão. Com menos de dez
chunks disponíveis, o fluxo DEVE utilizar os resultados existentes sem inventar trechos.
O contexto DEVE concatenar `page_content` dos documentos com separadores legíveis.

`search_prompt()` DEVE construir e retornar uma cadeia invocável, com contrato explícito:
`invoke({"pergunta": texto})` retorna uma string. A composição DEVE distinguir recuperação,
formatação de contexto, template, chamada ao modelo e conversão da saída. Runnables/LCEL
PODEM representar essa composição; agentes autônomos e ferramentas externas não pertencem
ao fluxo mínimo de pergunta e resposta.

A cadeia e os clientes DEVEM ser inicializados uma vez por execução do chat e reutilizados.
Entradas vazias NÃO DEVEM disparar chamadas ao provedor. Operações externas DEVEM ter
timeouts finitos; retentativas, quando usadas, DEVEM ser limitadas e restritas a falhas
transitórias, sem duplicar indiscriminadamente gravações ou chamadas cobradas.

### VI. Integridade e rastreabilidade dos dados vetoriais

A ingestão DEVE configurar `chunk_size=1000`, `chunk_overlap=150` e `length_function=len`.
Chunks menores e menor sobreposição efetiva decorrentes de separadores ou limites de página
são permitidos. Texto vazio NÃO DEVE gerar embeddings. PDF inexistente, inválido ou sem
texto extraível DEVE produzir falha clara; a presença de um arquivo NÃO comprova sua leitura.

Cada chunk persistido DEVE manter texto, vetor, origem, página e identificador. A confirmação
de ingestão DEVE apresentar somente quantidades efetivamente gravadas; falhas parciais
DEVEM ser informadas e NÃO DEVEM ser descritas como sucesso completo.

Ingestão e busca DEVEM compartilhar modelo de embeddings, dimensionalidade e collection.
A troca de modelo exige reindexação mesmo quando a dimensão é igual. Uma collection NÃO
DEVE misturar vetores de modelos distintos. A configuração/modelo utilizado DEVE constar
do registro de validação. O ciclo normal NÃO DEVE apagar collection, tabelas ou volume.
Procedimentos de limpeza DEVEM ser explícitos, delimitados e documentar a perda de dados.

**Recomendação:** usar IDs determinísticos para evitar duplicação do mesmo PDF/configuração.
Se adotada, a idempotência DEVE ter teste de reingestão; ela não substitui uma estratégia
explícita para documentos alterados. A integração e os efeitos de gravação por ID DEVEM
ser verificados na [documentação de PGVector do LangChain](https://docs.langchain.com/oss/python/integrations/vectorstores/pgvector)
e na versão instalada antes de definir essa estratégia.

### VII. Configuração segura e operação previsível

Credenciais, modelos e conexão DEVEM vir do ambiente, com `.env` local e `.env.example`
versionado sem segredos. A validação DEVE exigir apenas os valores do fluxo/provedor
executado; o chat NÃO DEVE depender de `PDF_PATH` nem da chave de um provedor não utilizado.
Credenciais reais NÃO DEVEM aparecer em código, Git, logs ou mensagens de erro.

Logs DEVEM usar `logging` com nível e contexto operacional; respostas ao usuário DEVEM
permanecer legíveis na CLI. Logs padrão NÃO DEVEM despejar o PDF, prompts completos,
strings de conexão com senha ou cabeçalhos de autenticação. Rastreamento externo somente
PODE ser ativado com configuração explícita e documentação dos dados enviados.

Configuração inválida, banco indisponível, collection vazia, quota e credencial inválida
DEVEM resultar em orientação acionável. Erros fatais DEVEM retornar código diferente de
zero. O chat DEVE aceitar várias perguntas e encerrar normalmente com `sair`, `exit`, EOF
ou `Ctrl+C`. Interrupções NÃO DEVEM ser capturadas como respostas factuais.

### VIII. Verificação por comportamento e evidência

Testes isolados DEVEM verificar contratos e resultados, usando dublês nas fronteiras de
API e banco. Eles DEVEM executar sem chave real, custo por requisição ou PostgreSQL ativo.
Testes de detalhes internos que não protegem um requisito NÃO DEVEM substituir a
verificação do comportamento observável.

A suíte DEVE cobrir parâmetros do splitter, metadados, busca com `k=10`, preenchimento do
prompt obrigatório, recusa sem contexto, configuração inválida, falhas externas e o laço
da CLI. Alterações em lógica DEVEM incluir a verificação correspondente; correções de bug
DEVEM acrescentar um caso de regressão quando reproduzível.

A validação integrada DEVE usar o PDF fornecido, PostgreSQL/pgVector real e o provedor
escolhido. Ela DEVE conter pelo menos três perguntas com evidência e três sem resposta,
além de opinião, tentativa de desviar as regras, banco vazio, PDF inválido/sem texto e
persistência após reinício sem remoção do volume. Respostas afirmativas DEVEM ser conferidas
contra trechos e páginas reais; exemplos ilustrativos do README não são evidência do PDF.

O relatório `plans/validacao.md` DEVE registrar ambiente, versões, modelos, comandos,
perguntas, respostas, evidências e limitações. Testes não executados DEVEM ser identificados
com o motivo, sem marcar os respectivos critérios como atendidos.

## Restrições técnicas e de entrega

- **Estrutura:** preservar `docker-compose.yml`, `requirements.txt`, `.env.example`,
  `src/ingest.py`, `src/search.py`, `src/chat.py`, `document.pdf` e `README.md`.
  Módulos auxiliares e testes são permitidos sem invalidar os comandos existentes.
- **Execução:** a partir da raiz, manter `docker compose up -d`, seguido de
  `python src/ingest.py` e `python src/chat.py`. A instalação DEVE usar ambiente virtual.
- **Banco:** confirmar saúde do PostgreSQL, criação da extensão e persistência em volume.
  Usar `PGVector` com o driver `psycopg` e URL `postgresql+psycopg://...` compatível.
- **Modelos:** a escolha permanece para o planejamento. Antes da integração, consultar a
  documentação oficial do provedor e registrar modelos disponíveis, dimensão de embeddings
  e compatibilidade. Priorizar custo adequado ao desafio; gratuidade não é pressuposto.
- **Dependências:** preservar versões fixas salvo necessidade demonstrada. Mudanças DEVEM
  registrar motivo e validação; a versão de Python suportada DEVE ser a efetivamente testada.
  Ferramentas de lint, formatação ou tipagem adicionais exigem configuração e comando
  reproduzível documentados no plano, sem impor uma suíte de ferramentas antecipadamente.
- **Entrega:** usar o fork exigido e disponibilizar repositório público com instruções de
  instalação, variáveis, ingestão, chat, testes, exemplos reais e diagnóstico de falhas.
  A execução em ambiente novo DEVE ser conferida antes da entrega.

## Fluxo de desenvolvimento e qualidade

O desenvolvimento DEVE seguir constituição → especificação → esclarecimentos necessários
→ plano → tarefas → análise de consistência → implementação → convergência.
Cada etapa DEVE consumir os artefatos anteriores; a implementação de uma funcionalidade
DEVE ter `spec.md`, `plan.md` e `tasks.md` em `specs/` antes da execução das tarefas.
O plano em `plans/` é contexto inicial e NÃO substitui os artefatos da funcionalidade.

A especificação DEVE distinguir requisitos obrigatórios de recomendações. O plano DEVE
registrar provedor, modelos, configuração, contratos, estratégia de testes e compatibilidade.
As tarefas DEVEM relacionar implementação e verificações aos critérios de aceite.
Descobertas que alterem requisitos ou contratos DEVEM ser refletidas nesses artefatos.

As verificações abaixo DEVEM ter resultado registrado antes de concluir a funcionalidade:

1. **Conformidade:** nenhuma divergência sem resolução entre requisitos acadêmicos,
   constituição, especificação, plano e tarefas; conferir R01–R11.
2. **Qualidade do código:** sintaxe válida, contratos tipados, responsabilidades separadas,
   regras compartilhadas sem duplicação e tratamento explícito de erros e recursos.
   Executar os verificadores automatizados adotados e documentados pelo projeto.
3. **Comportamento isolado:** suíte automatizada aprovada com verificação dos casos críticos,
   sem dependências externas reais.
4. **Integração:** ingestão e chat completos aprovados com banco e modelo reais, incluindo
   respostas negativas e persistência; registrar evidências em `plans/validacao.md`.
5. **Reprodução e entrega:** instruções do README executadas em ambiente novo, configuração
   de exemplo suficiente, ausência de segredos e visibilidade pública conferida na entrega.

Uma verificação bloqueada DEVE manter a tarefa correspondente pendente e registrar a
dependência que falta. `$speckit-converge` DEVE orientar o trabalho restante; novas tarefas
exigem nova implementação e verificação antes de declarar conclusão.

## Governance

Esta é a primeira constituição ratificada do projeto. Os requisitos acadêmicos do README
são restrições externas e NÃO PODEM ser relaxados por esta constituição. Para decisões de
engenharia, esta constituição prevalece sobre planos e tarefas. O plano inicial contribui
com decisões e recomendações; as recomendações só se tornam obrigatórias quando uma
especificação ou emenda as adota explicitamente. Inconsistências DEVEM ser resolvidas na
documentação antes de implementar comportamento conflitante.

Cada revisão de mudança DEVE verificar os princípios aplicáveis, os critérios de aceite
e as evidências. A revisão PODE ser feita pelo próprio autor neste projeto individual;
um processo obrigatório de múltiplos revisores não é imposto. Desvios propostos DEVEM
registrar motivo, impacto e alternativa. Desvio de regra obrigatória exige emenda ou
resolução do requisito externo antes de ser incorporado.

Emendas DEVEM ser feitas por `$speckit-constitution`, com justificativa, comparação dos
princípios afetados e identificação dos artefatos dependentes. Alterações em templates,
comandos ou implementação DEVEM ocorrer em trabalho separado quando necessário; esta
rotina altera somente a constituição. O relatório de sincronização no comentário inicial
é material de revisão e DEVE ser removido antes de versionar a emenda em um commit.

O versionamento DEVE seguir SemVer: **MAJOR** para remoção ou redefinição incompatível de
princípios; **MINOR** para novo princípio, seção ou expansão material; **PATCH** para
esclarecimentos sem mudança normativa. Toda emenda DEVE atualizar a versão e a data de
alteração, preservando a data da ratificação inicial. A versão `1.0.0` registra a adoção
inicial e NÃO declara os requisitos da aplicação já implementados ou verificados.

**Version**: 1.0.0 | **Ratified**: 2026-10-16 | **Last Amended**: 2026-10-16
