"""Contratos de configuração sem credenciais ou serviços reais."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.config import ConfigurationError, create_embeddings, load_settings

ENV = {
    'OPENAI_API_KEY': 'sentinel-secret',
    'OPENAI_EMBEDDING_MODEL': 'text-embedding-3-small',
    'DATABASE_URL': 'postgresql+psycopg://user:sentinel-password@localhost/db',
    'PG_VECTOR_COLLECTION_NAME': 'test_collection',
    'PDF_PATH': 'document.pdf',
}


class ConfigTests(unittest.TestCase):
    def load(self, values=None, *, ingestion=True):
        with TemporaryDirectory() as directory:
            return load_settings(ingestion=ingestion, root=Path(directory),
                                 environ=ENV if values is None else values)

    def test_common_does_not_require_pdf_chat_or_google(self):
        values = dict(ENV)
        del values['PDF_PATH']
        self.assertIsNone(self.load(values, ingestion=False).pdf_path)
        with self.assertRaisesRegex(ConfigurationError, 'PDF_PATH'):
            self.load(values)

    def test_required_and_dimensions(self):
        for key in ENV:
            for value in (None, '', '   '):
                values = dict(ENV)
                if value is None:
                    del values[key]
                else:
                    values[key] = value
                with self.subTest(key=key, value=value):
                    with self.assertRaisesRegex(ConfigurationError, key):
                        self.load(values)
        for value in ('0', '-1', 'no', '1.5'):
            with self.assertRaisesRegex(ConfigurationError, 'DIMENSIONS'):
                self.load({**ENV, 'OPENAI_EMBEDDING_DIMENSIONS': value})

    def test_url_driver_and_secret_repr(self):
        for url in ('postgres://u:sentinel-password@localhost/db', 'invalid',
                    'postgresql+psycopg://localhost'):
            with self.assertRaises(ConfigurationError) as error:
                self.load({**ENV, 'DATABASE_URL': url})
            self.assertNotIn('sentinel-password', str(error.exception))
        settings = self.load()
        self.assertNotIn('sentinel-secret', repr(settings))
        self.assertNotIn('sentinel-password', repr(settings))

    def test_precedence_local_key_and_empty_export(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            root.joinpath('.env').write_text('\n'.join(
                f'{k}={v}' for k, v in ENV.items() if k != 'OPENAI_API_KEY'),
                encoding='utf-8')
            root.joinpath('.env.local').write_text(
                'OPENAI_API_KEY=local-key\nPG_VECTOR_COLLECTION_NAME=local',
                encoding='utf-8')
            before = dict(os.environ)
            settings = load_settings(root=root, environ={
                'PG_VECTOR_COLLECTION_NAME': 'exported'})
            self.assertEqual(settings.api_key, 'local-key')
            self.assertEqual(settings.collection_name, 'exported')
            self.assertEqual(before, dict(os.environ))
            with self.assertRaisesRegex(ConfigurationError, 'OPENAI_API_KEY'):
                load_settings(root=root, environ={'OPENAI_API_KEY': ''})

    def test_embedding_factory_options(self):
        with patch('src.config.OpenAIEmbeddings') as factory:
            create_embeddings(self.load())
        options = factory.call_args.kwargs
        self.assertEqual(options['model'], ENV['OPENAI_EMBEDDING_MODEL'])
        self.assertEqual(options['dimensions'], 1536)
        self.assertEqual(options['request_timeout'], 60)
        self.assertEqual(options['max_retries'], 0)

    def test_import_does_not_initialize_clients_or_load_environment(self):
        import subprocess
        import sys
        code = '''
from unittest.mock import patch
with patch('sqlalchemy.create_engine', side_effect=AssertionError('database')), \\
     patch('langchain_openai.OpenAIEmbeddings', side_effect=AssertionError('api')), \\
     patch('dotenv.dotenv_values', side_effect=AssertionError('dotenv')):
    import src.config, src.vector_store, src.ingest
'''
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_owned_embedding_transports_closed_on_failure(self):
        from src.config import embedding_session
        with patch('src.config.httpx.Client') as sync, patch(
                'src.config.httpx.AsyncClient') as asynchronous, patch(
                'src.config.create_embeddings', side_effect=RuntimeError('sentinel')):
            from unittest.mock import AsyncMock
            asynchronous.return_value.aclose = AsyncMock()
            with self.assertRaises(RuntimeError):
                with embedding_session(self.load()):
                    pass
        sync.return_value.__exit__.assert_called_once()
        asynchronous.return_value.aclose.assert_awaited_once()


class ChatConfigTests(unittest.TestCase):
    def load(self, values=None, **kwargs):
        with TemporaryDirectory() as directory:
            return load_settings(root=Path(directory), environ={
                **ENV, 'OPENAI_CHAT_MODEL': 'gpt-6-luna',
                **(values or {}),
            }, **kwargs)

    def test_search_requires_chat_only_in_requested_flow(self):
        self.assertIsNone(self.load(ingestion=False).chat_model)
        config = self.load(ingestion=False, require_chat=True)
        self.assertEqual(config.chat_model, 'gpt-6-luna')
        self.assertIsNone(config.pdf_path)
        for value in ('', '   '):
            with self.assertRaisesRegex(ConfigurationError, 'OPENAI_CHAT_MODEL'):
                self.load({'OPENAI_CHAT_MODEL': value}, ingestion=False,
                          require_chat=True)
            self.assertIsNone(self.load({'OPENAI_CHAT_MODEL': value}).chat_model)

    def test_chat_precedence_without_environment_mutation(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            root.joinpath('.env').write_text('\n'.join(
                f'{k}={v}' for k, v in ENV.items()) +
                '\nOPENAI_CHAT_MODEL=base', encoding='utf-8')
            root.joinpath('.env.local').write_text(
                'OPENAI_CHAT_MODEL=local', encoding='utf-8')
            before = dict(os.environ)
            for exported, expected in (({}, 'local'),
                                       ({'OPENAI_CHAT_MODEL': 'export'}, 'export')):
                self.assertEqual(load_settings(root=root, environ=exported,
                    ingestion=False, require_chat=True).chat_model, expected)
            with self.assertRaises(ConfigurationError):
                load_settings(root=root, environ={'OPENAI_CHAT_MODEL': ''},
                              ingestion=False, require_chat=True)
            self.assertEqual(before, dict(os.environ))

    def test_chat_factory_and_owned_sessions(self):
        from src.config import chat_session, create_chat_model
        from unittest.mock import AsyncMock
        config = self.load(ingestion=False, require_chat=True)
        with patch('src.config.ChatOpenAI') as factory:
            create_chat_model(config)
        options = factory.call_args.kwargs
        for key, value in {'model': 'gpt-6-luna', 'reasoning_effort': 'low',
                           'temperature': None, 'use_responses_api': False,
                           'max_completion_tokens': 2048, 'timeout': 60,
                           'max_retries': 0}.items():
            self.assertEqual(options[key], value)
        for fails in (False, True):
            with patch('src.config.httpx.Client') as sync, patch(
                    'src.config.httpx.AsyncClient') as asynchronous, patch(
                    'src.config.create_chat_model') as create:
                asynchronous.return_value.aclose = AsyncMock()
                if fails:
                    create.side_effect = RuntimeError('sentinel')
                    with self.assertRaises(RuntimeError):
                        with chat_session(config):
                            pass
                else:
                    with chat_session(config):
                        pass
                sync.return_value.__exit__.assert_called_once()
                asynchronous.return_value.aclose.assert_awaited_once()

    def test_bad_query_config_matrix_and_safe_repr(self):
        for key in ('OPENAI_API_KEY', 'OPENAI_EMBEDDING_MODEL', 'DATABASE_URL',
                    'PG_VECTOR_COLLECTION_NAME', 'OPENAI_CHAT_MODEL'):
            for value in ('', ' \t '):
                with self.subTest(key=key), self.assertRaisesRegex(ConfigurationError, key):
                    self.load({key: value}, ingestion=False, require_chat=True)
        for url in ('postgresql+psycopg://localhost:99999/db',
                    'postgresql+psycopg://localhost:-1/db',
                    'postgresql+psycopg://localhost:bad/db'):
            with self.assertRaises(ConfigurationError) as caught:
                self.load({'DATABASE_URL': url}, ingestion=False, require_chat=True)
            self.assertNotIn(url, str(caught.exception))
        config = self.load({'PDF_PATH': '/nonexistent.pdf'}, ingestion=False, require_chat=True)
        self.assertIsNone(config.pdf_path)
        self.assertNotIn('sentinel-secret', repr(config))
        self.assertNotIn('sentinel-password', repr(config))

    def test_search_import_has_no_environment_clients_or_io(self):
        import subprocess
        import sys
        code = '''
from unittest.mock import patch
with patch('sqlalchemy.create_engine', side_effect=AssertionError('database')), \\
     patch('langchain_openai.ChatOpenAI', side_effect=AssertionError('api')), \\
     patch('langchain_openai.OpenAIEmbeddings', side_effect=AssertionError('api')), \\
     patch('dotenv.dotenv_values', side_effect=AssertionError('dotenv')):
    import src.search
'''
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


    def test_absent_chat_rejected_only_when_required(self):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ConfigurationError, 'OPENAI_CHAT_MODEL'):
                load_settings(root=Path(directory), environ=ENV,
                              ingestion=False, require_chat=True)
