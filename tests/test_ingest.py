"""Ingestão com loader e splitter reais, API e banco substituídos."""
from contextlib import contextmanager
from dataclasses import replace
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from src.ingest import (IngestionError, build_manifest, ingest_pdf, load_pdf_pages,
                        main, split_pages)
from tests.helpers import settings, write_pdf


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.config = settings()
        self.manifest = build_manifest(self.config, 'a' * 64)

    def test_real_loader_short_portuguese_and_blank_page(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'sample.PDF'
            write_pdf(path, ['Informação útil sobre ingestão.', '', 'Página final.'])
            pages = load_pdf_pages(path)
            chunks = split_pages(pages, self.config, self.manifest)
        self.assertEqual(len(pages), 3)
        self.assertEqual([d.metadata['page'] for d in chunks], [0, 2])
        self.assertTrue(all(d.metadata['source'] == str(path.resolve()) for d in chunks))
        self.assertIn('Informação', chunks[0].page_content)
        self.assertEqual(chunks[0].metadata['chunk_index'], 0)

    def test_real_splitter_limits_overlap_and_metadata(self):
        page = Document(page_content='a' * 2200,
                        metadata={'page': 4, 'source': '/file.pdf', 'extra': 'preserved'})
        chunks = split_pages([page], self.config, self.manifest)
        self.assertEqual([len(d.page_content) for d in chunks], [1000, 1000, 500])
        self.assertEqual(chunks[0].page_content[-150:], chunks[1].page_content[:150])
        self.assertTrue(all(d.metadata['page'] == 4 for d in chunks))
        self.assertTrue(all(d.metadata['extra'] == 'preserved' for d in chunks))
        self.assertEqual(self.manifest['pipeline']['chunk_overlap'], 150)
        self.assertEqual(self.manifest['pipeline']['length_function'], 'len')
        paragraphs = Document(page_content=('Ação e coração.\n\n' * 250),
                              metadata=page.metadata)
        self.assertTrue(all(0 < len(d.page_content) <= 1000 for d in
                            split_pages([paragraphs], self.config, self.manifest)))

    def test_ids_deterministic_and_distinct_per_position(self):
        pages = [Document(page_content='repetido', metadata={'page': i, 'source': '/a'})
                 for i in range(2)]
        chunks = split_pages(pages, self.config, self.manifest)
        again = split_pages(pages, self.config, self.manifest)
        self.assertEqual(chunks, again)
        self.assertNotEqual(chunks[0].id, chunks[1].id)
        other = split_pages(pages, replace(self.config, collection_name='other'), self.manifest)
        self.assertTrue(set(d.id for d in chunks).isdisjoint(d.id for d in other))

    def test_blank_pdf_rejected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'blank.pdf'
            write_pdf(path, ['', ''])
            with self.assertRaisesRegex(IngestionError, 'texto|OCR'):
                load_pdf_pages(path)

    def test_orchestration_and_cli_confirmed_success(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'test.pdf'
            write_pdf(path, ['Texto para ingestão.'])
            config = replace(self.config, pdf_path=path)
            embeddings = MagicMock()
            embeddings.embed_documents.return_value = [[0.1] * 1536]
            @contextmanager
            def session(_):
                try:
                    yield embeddings
                finally:
                    embeddings.close()
            @contextmanager
            def store(*args):
                yield MagicMock()
            with patch('src.ingest.persist_chunks', return_value=1) as persist:
                result = ingest_pdf(config, embeddings_factory=session, store_factory=store)
            self.assertEqual(result.stored_chunks, 1)
            self.assertEqual(result.loaded_pages, 1)
            persist.assert_called_once()
            embeddings.close.assert_called_once()
            with patch('src.ingest.load_settings', return_value=config), patch(
                    'src.ingest.ingest_pdf', return_value=result), patch(
                    'sys.stdout', new_callable=io.StringIO) as output:
                self.assertEqual(main(), 0)
                self.assertIn('chunks confirmados=1', output.getvalue())

    def test_invalid_files_never_open_embeddings(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            invalid = root / 'invalid.pdf'
            invalid.write_text('sentinel-PDF-secret', encoding='utf-8')
            blank = root / 'blank.pdf'
            write_pdf(blank, [''])
            for path in (root / 'missing.pdf', root, root / 'file.txt', invalid, blank):
                factory = MagicMock()
                with self.subTest(path=path):
                    with self.assertRaises(IngestionError):
                        ingest_pdf(replace(self.config, pdf_path=path), embeddings_factory=factory)
                    factory.assert_not_called()

    def test_permission_and_changing_pdf(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'test.pdf'
            write_pdf(path, ['texto'])
            with patch('src.ingest.document_hash', side_effect=PermissionError):
                with self.assertRaisesRegex(IngestionError, 'Acesso'):
                    load_pdf_pages(path)
            with patch('src.ingest.document_hash', side_effect=['a', 'b']):
                with self.assertRaisesRegex(IngestionError, 'alterado'):
                    load_pdf_pages(path)

    def test_external_api_categories_release_resources(self):
        import httpx
        import openai
        request = httpx.Request('POST', 'https://api.openai.com/v1/embeddings')
        cases = [
            (openai.AuthenticationError('sentinel-secret', response=httpx.Response(
                401, request=request), body=None), 'credencial'),
            (openai.RateLimitError('sentinel-secret', response=httpx.Response(
                429, request=request), body=None), 'quota'),
            (openai.APITimeoutError(request=request), 'tempo'),
            (openai.APIConnectionError(request=request), 'conexão'),
            (openai.PermissionDeniedError('secret', response=httpx.Response(
                403, request=request), body=None), 'modelo'),
        ]
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'test.pdf'
            write_pdf(path, ['texto'])
            for exception, category in cases:
                client = MagicMock()
                client.embed_documents.side_effect = exception
                closed = MagicMock()
                @contextmanager
                def embedding_context(_):
                    try:
                        yield client
                    finally:
                        closed()
                @contextmanager
                def target(*args):
                    yield MagicMock()
                with self.subTest(category=category):
                    with self.assertRaisesRegex(IngestionError, category) as error:
                        ingest_pdf(replace(self.config, pdf_path=path),
                                   embeddings_factory=embedding_context, store_factory=target)
                    self.assertNotIn('sentinel-secret', str(error.exception))
                    closed.assert_called_once()

    def test_cli_fails_without_success_or_secrets(self):
        from src.config import ConfigurationError
        for exception, code in ((ConfigurationError('OPENAI_API_KEY ausente'), 1),
                                (IngestionError('PDF inválido'), 1),
                                (RuntimeError('sentinel-password'), 1),
                                (KeyboardInterrupt(), 130)):
            with self.subTest(code=code), patch('src.ingest.load_settings', side_effect=exception), \
                    patch('sys.stdout', new_callable=io.StringIO) as output:
                with self.assertLogs('src.ingest', level='ERROR') as logs:
                    self.assertEqual(main(), code)
                self.assertEqual(output.getvalue(), '')
                self.assertNotIn('sentinel-password', ' '.join(logs.output))
                self.assertNotIn('Traceback', ' '.join(logs.output))

    def test_reingestion_recovers_uncertain_commit_and_isolates_destinations(self):
        from sqlalchemy.exc import OperationalError
        from src.vector_store import StorageError, VectorStore
        database = {}
        fail_commit = [True]
        @contextmanager
        def embeddings_factory(_):
            embeddings = MagicMock()
            embeddings.embed_documents.side_effect = lambda texts: [[0.1] * 1536 for _ in texts]
            yield embeddings
        @contextmanager
        def store_factory(config, embeddings, manifest):
            records = database.setdefault(config.collection_name, {})
            store, engine = MagicMock(), MagicMock()
            def upsert(*, texts, embeddings, metadatas, ids):
                for identifier, content, metadata in zip(ids, texts, metadatas, strict=True):
                    records[identifier] = {'id': identifier, 'document': content,
                                           'cmetadata': dict(metadata), 'dimensions': 1536}
                if fail_commit[0]:
                    fail_commit[0] = False
                    raise OperationalError('commit unknown', {}, Exception())
                return ids
            store.add_embeddings.side_effect = upsert
            engine.connect.return_value.__enter__.return_value.execute.return_value.mappings.return_value.all.side_effect = lambda: list(reversed(list(records.values())))
            yield VectorStore(store, engine, config.collection_name, 1536)
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'test.pdf'
            write_pdf(path, ['Mesmo texto.', '', 'Mesmo texto.'])
            config = replace(self.config, pdf_path=path)
            def run(target=config):
                return ingest_pdf(target, embeddings_factory=embeddings_factory,
                                  store_factory=store_factory)
            with self.assertRaisesRegex(StorageError, 'indeterminado'):
                run()
            snapshot = dict(database[config.collection_name])
            self.assertEqual(run().stored_chunks, 2)
            self.assertEqual(database[config.collection_name], snapshot)
            self.assertEqual(run().stored_chunks, 2)
            run(replace(config, collection_name='other'))
            self.assertTrue(set(database['other']).isdisjoint(snapshot))
            self.assertEqual(database[config.collection_name], snapshot)

    def test_invalid_embedding_batch_does_not_persist(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'test.pdf'
            write_pdf(path, ['texto'])
            client = MagicMock()
            client.embed_documents.return_value = []
            @contextmanager
            def session(_):
                try:
                    yield client
                finally:
                    client.close()
            @contextmanager
            def target(*args):
                yield MagicMock()
            with patch('src.ingest.persist_chunks') as persist:
                from src.vector_store import StorageError
                with self.assertRaises(StorageError):
                    ingest_pdf(replace(self.config, pdf_path=path),
                               embeddings_factory=session, store_factory=target)
                persist.assert_not_called()
            client.close.assert_called_once()

    def test_store_incompatibility_prevents_embedding_and_releases_client(self):
        from src.vector_store import StorageError
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'test.pdf'
            write_pdf(path, ['texto'])
            client = MagicMock()
            @contextmanager
            def session(_):
                try:
                    yield client
                finally:
                    client.close()
            @contextmanager
            def incompatible(*args):
                raise StorageError('collection incompatível')
                yield
            with self.assertRaises(StorageError):
                ingest_pdf(replace(self.config, pdf_path=path),
                           embeddings_factory=session, store_factory=incompatible)
            client.embed_documents.assert_not_called()
            client.close.assert_called_once()
