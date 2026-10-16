"""Contrato observável da CLI, sem rede, banco ou credenciais reais."""
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import importlib
import io
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from src import search
from src.config import ConfigurationError, load_settings
from src.vector_store import StorageError, VectorStore


class ChatTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {
            'LANGCHAIN_TRACING_V2': 'false', 'LANGCHAIN_TRACING': 'false',
            'LANGSMITH_TRACING': 'false',
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.chain = Mock(spec=search.SearchChain)
        self.chain.invoke.return_value = 'Resposta çã.'
        self.opened = 0
        self.closed = 0
        self.close_error = None
        self.received_error = None
        self.output = io.StringIO()
        self.errors = io.StringIO()

    @contextmanager
    def factory(self):
        self.opened += 1
        try:
            yield self.chain
        except (Exception, EOFError, KeyboardInterrupt) as error:
            self.received_error = error
            raise
        finally:
            self.closed += 1
            if self.close_error is not None:
                raise self.close_error

    def execute(self, questions, **kwargs):
        from src.chat import main
        self.reader = Mock(side_effect=questions)
        return main(chain_factory=kwargs.pop('chain_factory', self.factory),
                    read_question=self.reader, output=self.output,
                    error_output=self.errors, **kwargs)

    def test_three_questions_preserve_payload_answers_and_refusal(self):
        answers = ['  Unicode: ação\nsegunda linha  ', search.REFUSAL, '2023']
        self.chain.invoke.side_effect = answers
        self.assertEqual(self.execute(['  Primeira? ', 'Segunda?', 'Terceira?',
                                       'sair']), 0)
        self.assertEqual(self.chain.invoke.call_args_list, [
            unittest.mock.call({'pergunta': question})
            for question in ['Primeira?', 'Segunda?', 'Terceira?']
        ])
        self.assertEqual(self.output.getvalue(), ''.join(
            f'RESPOSTA: {answer}\n\n' for answer in answers))
        self.assertEqual(self.errors.getvalue(), '')
        self.assertEqual((self.opened, self.closed), (1, 1))
        self.assertEqual(self.reader.call_args_list,
                         [unittest.mock.call('PERGUNTA: ')] * 4)

    def test_blank_and_exit_commands_never_invoke(self):
        for command in ['sair', 'exit', ' SAIR ', ' ExIt ']:
            with self.subTest(command=command):
                self.assertEqual(self.execute(['', '  \t ', command]), 0)
        self.chain.invoke.assert_not_called()
        self.assertEqual(self.output.getvalue(), '')
        self.assertEqual(self.errors.getvalue(), '')

    def test_eof_and_interrupt_reader_release_and_leave_streams_open(self):
        for exception in [EOFError(), KeyboardInterrupt()]:
            with self.subTest(exception=type(exception)):
                self.assertEqual(self.execute([exception]), 0)
                self.assertIs(self.received_error, exception)
        self.assertEqual(self.closed, 2)
        self.assertFalse(self.output.closed)
        self.assertFalse(self.errors.closed)
        self.assertEqual(self.errors.getvalue(), '')

    def test_interrupt_invoke_ends_session_and_reaches_owner(self):
        interruption = KeyboardInterrupt()
        self.chain.invoke.side_effect = interruption
        self.assertEqual(self.execute(['Pergunta?', 'não ler']), 0)
        self.assertIs(self.received_error, interruption)
        self.assertEqual(self.reader.call_count, 1)
        self.assertEqual(self.closed, 1)
        self.assertEqual(self.output.getvalue(), '')
        self.assertEqual(self.errors.getvalue(), '')

    def test_interrupt_during_partial_open(self):
        @contextmanager
        def opening():
            try:
                raise KeyboardInterrupt()
                yield self.chain
            finally:
                self.closed += 1
        self.assertEqual(self.execute(['sair'], chain_factory=opening), 0)
        self.reader.assert_not_called()
        self.assertEqual(self.closed, 1)

    def test_import_has_no_side_effects(self):
        with patch('src.search.search_prompt') as factory, \
                patch('src.config.load_settings') as config, \
                patch('builtins.input') as reader, \
                patch('src.config.create_embeddings') as embeddings, \
                patch('src.vector_store.create_engine') as engine:
            importlib.reload(importlib.import_module('src.chat'))
        for dependency in [factory, config, reader, embeddings, engine]:
            dependency.assert_not_called()
        importlib.reload(sys.modules['src.chat'])

    def test_defaults_are_resolved_at_call_time(self):
        from src import chat
        with patch.object(chat, 'search_prompt', self.factory), \
                patch('builtins.input', side_effect=['Pergunta?', 'exit']), \
                redirect_stdout(self.output), redirect_stderr(self.errors):
            self.assertEqual(chat.main(), 0)
        self.assertIn('RESPOSTA: Resposta çã.', self.output.getvalue())
        self.assertEqual(self.closed, 1)

    def test_run_chat_borrows_chain(self):
        from src.chat import run_chat
        self.assertEqual(run_chat(self.chain, read_question=Mock(
            side_effect=['Pergunta?', 'exit']), output=self.output,
            error_output=self.errors), 0)
        self.chain.close.assert_not_called()

    def test_open_failures_before_first_prompt_and_partial_release(self):
        for error in [ConfigurationError('OPENAI_API_KEY obrigatória.'),
                      StorageError('Collection vazia; python src/ingest.py.'),
                      StorageError('Confira Docker Compose e bootstrap.')]:
            with self.subTest(error=type(error)):
                @contextmanager
                def opening():
                    try:
                        raise error
                        yield self.chain
                    finally:
                        self.closed += 1
                self.errors.seek(0)
                self.errors.truncate()
                self.assertEqual(self.execute(['sair'],
                                              chain_factory=opening), 1)
                self.reader.assert_not_called()
                self.assertIn('Erro ao iniciar o chat: ' + str(error),
                              self.errors.getvalue())
        self.assertEqual(self.closed, 3)
        self.chain.invoke.assert_not_called()

    def test_transient_allows_next_question_without_retry(self):
        self.chain.invoke.side_effect = [search.SearchError(
            'Timeout; confira rede.', retryable=True), 'Depois']
        self.assertEqual(self.execute(['Primeira', 'Segunda', 'exit']), 0)
        self.assertEqual(self.chain.invoke.call_count, 2)
        self.assertEqual(self.chain.invoke.call_args_list, [
            unittest.mock.call({'pergunta': 'Primeira'}),
            unittest.mock.call({'pergunta': 'Segunda'})])
        self.assertEqual(self.output.getvalue(), 'RESPOSTA: Depois\n\n')
        self.assertIn('Erro na consulta: Timeout; confira rede.',
                      self.errors.getvalue())
        self.assertEqual((self.opened, self.closed), (1, 1))

    def test_fatal_stops_before_next_question(self):
        self.chain.invoke.side_effect = search.SearchError('Quota esgotada.')
        self.assertEqual(self.execute(['Primeira', 'não ler']), 1)
        self.assertEqual(self.reader.call_count, 1)
        self.assertEqual(self.output.getvalue(), '')
        self.assertIn('Erro na consulta: Quota esgotada.', self.errors.getvalue())

    def test_invalid_answer_and_question_contract_are_fatal(self):
        for answer in [None, 42, [{'text': 'bloco'}], '', ' \n ']:
            with self.subTest(answer=answer):
                self.chain.invoke.return_value = answer
                self.assertEqual(self.execute(['válida', 'não ler']), 1)
                self.assertEqual(self.reader.call_count, 1)
        self.chain.invoke.side_effect = search.QuestionError('SENTINELA')
        self.assertEqual(self.execute(['válida', 'não ler']), 1)
        self.assertEqual(self.output.getvalue(), '')
        self.assertNotIn('SENTINELA', self.errors.getvalue())

    def test_unexpected_errors_do_not_expose_secrets_or_content(self):
        from src import chat
        secret = ('sk-sentinela-segredo postgresql://u:senha@host/db '
                  'PERGUNTA_PRIVADA PDF_PRIVADO')
        for location in ['factory', 'reader', 'invoke', 'output']:
            with self.subTest(location=location):
                error = RuntimeError(secret)
                factory = self.factory
                reader = Mock(side_effect=['válida', 'exit'])
                output = self.output
                self.chain.invoke.side_effect = None
                if location == 'factory':
                    factory = Mock(side_effect=error)
                elif location == 'reader':
                    reader.side_effect = error
                elif location == 'invoke':
                    self.chain.invoke.side_effect = error
                else:
                    output = Mock(spec=io.StringIO)
                    output.write.side_effect = error
                with self.assertLogs(chat.LOGGER, level='WARNING') as logs:
                    code = chat.main(chain_factory=factory,
                                     read_question=reader, output=output,
                                     error_output=self.errors)
                self.assertEqual(code, 1)
                public = (self.output.getvalue() + self.errors.getvalue()
                          + '\n'.join(logs.output))
                for token in secret.split():
                    self.assertNotIn(token, public)
                self.assertNotIn('Traceback', public)
                self.assertIn('Erro inesperado no chat.', self.errors.getvalue())

    def test_close_interrupt_is_failure(self):
        self.close_error = KeyboardInterrupt()
        self.assertEqual(self.execute(['exit']), 1)
        self.assertIn('Erro ao encerrar o chat.', self.errors.getvalue())

    def test_real_search_composition_without_pdf_google_or_warmup(self):
        from src import chat
        settings = load_settings(root=Path('/sem-configuracao-local'),
                                 ingestion=False, require_chat=True, environ={
            'OPENAI_API_KEY': 'fake',
            'OPENAI_EMBEDDING_MODEL': 'text-embedding-3-small',
            'DATABASE_URL': 'postgresql+psycopg://u:p@localhost/db',
            'PG_VECTOR_COLLECTION_NAME': 'test',
            'OPENAI_CHAT_MODEL': 'gpt-6-luna',
        })
        store = Mock()
        store.similarity_search_with_score.return_value = [
            (Document(page_content='Fato explícito.'), 0.1)]
        model = Mock(return_value=AIMessage(content='Fato explícito.',
                                            response_metadata={'finish_reason': 'stop'}))
        @contextmanager
        def embeddings(config):
            self.assertIs(config, settings)
            yield Mock()
        @contextmanager
        def storage(config, embedding):
            yield VectorStore(store, Mock(), 'id', 1536)
        @contextmanager
        def generation(config):
            yield RunnableLambda(model)
        def factory():
            chain = search.search_prompt(settings=settings,
                                         embedding_factory=embeddings,
                                         store_factory=storage,
                                         chat_factory=generation)
            store.similarity_search_with_score.assert_not_called()
            model.assert_not_called()
            return chain
        with patch.object(chat, 'search_prompt', factory):
            self.assertEqual(chat.main(read_question=Mock(
                side_effect=['fato?', 'exit']), output=self.output,
                error_output=self.errors), 0)
        store.similarity_search_with_score.assert_called_once_with('fato?', k=10)
        self.assertEqual(model.call_count, 1)

    def test_script_fails_safely_with_empty_exported_key(self):
        root = Path(__file__).resolve().parents[1]
        environment = dict(os.environ, OPENAI_API_KEY='')
        result = subprocess.run([sys.executable, str(root / 'src/chat.py')],
                                input='não ler\n', capture_output=True,
                                text=True, env=environment, cwd=root,
                                timeout=20)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertIn('Erro ao iniciar o chat: OPENAI_API_KEY', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_close_failure_after_normal_fatal_eof_and_interrupt(self):
        from src import chat
        for scenario in ['normal', 'fatal', 'eof', 'interrupt', 'unexpected']:
            with self.subTest(scenario=scenario):
                self.close_error = RuntimeError('SEGREDO_FECHAMENTO')
                self.chain.invoke.side_effect = None
                questions = ['exit']
                if scenario == 'fatal':
                    questions = ['válida']
                    self.chain.invoke.side_effect = search.SearchError('Quota.')
                elif scenario == 'eof':
                    questions = [EOFError()]
                elif scenario == 'interrupt':
                    questions = [KeyboardInterrupt()]
                elif scenario == 'unexpected':
                    questions = [RuntimeError('SEGREDO_LEITOR')]
                self.errors.seek(0)
                self.errors.truncate()
                with self.assertLogs(chat.LOGGER, level='WARNING') as logs:
                    self.assertEqual(self.execute(questions), 1)
                self.assertIn('Erro ao encerrar o chat.', self.errors.getvalue())
                if scenario == 'fatal':
                    self.assertIn('Erro na consulta: Quota.',
                                  self.errors.getvalue())
                if scenario == 'unexpected':
                    self.assertIn('Erro inesperado no chat.',
                                  self.errors.getvalue())
                public = self.errors.getvalue() + '\n'.join(logs.output)
                self.assertNotIn('SEGREDO', public)
                self.assertNotIn('Traceback', public)


if __name__ == '__main__':
    unittest.main()
