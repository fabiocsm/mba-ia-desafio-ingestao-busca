"""Interação pelo terminal; consulta e configuração pertencem à busca."""
from collections.abc import Callable
from contextlib import AbstractContextManager
import logging
import sys
from typing import TextIO

if __package__:
    from .config import ConfigurationError
    from .search import QuestionError, SearchChain, SearchError, search_prompt
    from .vector_store import StorageError
else:
    from config import ConfigurationError
    from search import QuestionError, SearchChain, SearchError, search_prompt
    from vector_store import StorageError

LOGGER = logging.getLogger(__name__)
UNEXPECTED_ERROR = (
    'Erro inesperado no chat. Confira a configuração e a disponibilidade '
    'dos serviços.'
)
CLOSE_ERROR = (
    'Erro ao encerrar o chat. Não foi possível liberar todos os recursos.'
)
CONTRACT_ERROR = (
    'Erro na consulta: Falha no contrato da busca. '
    'Confira a integração da aplicação.'
)


def run_chat(
    chain: SearchChain, *, read_question: Callable[[str], str],
    output: TextIO, error_output: TextIO,
) -> int:
    """Usa a cadeia emprestada; não mantém histórico nem fecha recursos."""
    while True:
        question = read_question('PERGUNTA: ').strip()
        if not question:
            continue
        if question.casefold() in {'sair', 'exit'}:
            return 0
        try:
            answer = chain.invoke({'pergunta': question})
        except SearchError as error:
            LOGGER.warning('Consulta: falha operacional.')
            print(f'Erro na consulta: {error}', file=error_output, flush=True)
            if error.retryable:
                continue
            return 1
        except QuestionError:
            LOGGER.error('Consulta: contrato de entrada inválido.')
            print(CONTRACT_ERROR, file=error_output, flush=True)
            return 1
        if not isinstance(answer, str) or not answer.strip():
            LOGGER.error('Consulta: contrato de saída inválido.')
            print(CONTRACT_ERROR, file=error_output, flush=True)
            return 1
        print(f'RESPOSTA: {answer}\n', file=output, flush=True)


def main(
    *,
    chain_factory: Callable[
        [], AbstractContextManager[SearchChain]
    ] | None = None,
    read_question: Callable[[str], str] | None = None,
    output: TextIO | None = None,
    error_output: TextIO | None = None,
) -> int:
    """Possui uma cadeia por execução; resolve colaboradores na chamada."""
    factory = search_prompt if chain_factory is None else chain_factory
    reader = input if read_question is None else read_question
    stdout = sys.stdout if output is None else output
    stderr = sys.stderr if error_output is None else error_output
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
    # A fase identifica exceções levantadas por __exit__, inclusive quando
    # substituem uma interrupção. O erro do corpo é relatado antes da liberação.
    closing = False
    interruption: EOFError | KeyboardInterrupt | None = None
    try:
        with factory() as chain:
            try:
                return run_chat(chain, read_question=reader, output=stdout,
                                error_output=stderr)
            except (EOFError, KeyboardInterrupt) as error:
                interruption = error
                raise
            except Exception:
                LOGGER.error('Sessão: falha inesperada.')
                print(UNEXPECTED_ERROR, file=stderr, flush=True)
                return 1
            finally:
                closing = True
    except (EOFError, KeyboardInterrupt) as error:
        if closing and error is not interruption:
            LOGGER.error('Liberação: interrompida.')
            print(CLOSE_ERROR, file=stderr, flush=True)
            return 1
        return 0
    except (ConfigurationError, StorageError) as error:
        if closing:
            LOGGER.error('Liberação: falha operacional.')
            print(CLOSE_ERROR, file=stderr, flush=True)
        else:
            LOGGER.error('Inicialização: configuração ou base indisponível.')
            print(f'Erro ao iniciar o chat: {error}', file=stderr, flush=True)
        return 1
    except Exception:
        LOGGER.error('Liberação: falha inesperada.' if closing
                     else 'Inicialização: falha inesperada.')
        print(CLOSE_ERROR if closing else UNEXPECTED_ERROR,
              file=stderr, flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
