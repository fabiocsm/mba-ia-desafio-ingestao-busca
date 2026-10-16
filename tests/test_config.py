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
