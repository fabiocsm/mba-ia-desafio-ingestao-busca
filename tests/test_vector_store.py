"""Contratos de armazenamento com banco e PGVector substituídos."""
from contextlib import contextmanager
from copy import deepcopy
import unittest
from unittest.mock import MagicMock, patch

from tests.helpers import settings
from src.vector_store import StorageError, open_vector_store


def manifest():
    from src.ingest import build_manifest
    return build_manifest(settings(), 'a' * 64)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.settings = settings()
        self.engine = MagicMock()
        self.connection = self.engine.connect.return_value.__enter__.return_value
        self.factory = MagicMock()
        self.embeddings = MagicMock()
        self.expected = manifest()

    def rows(self, *, extension=True, persisted="default", vector_type=None):
        ext, schema, collection = MagicMock(), MagicMock(), MagicMock()
        ext.scalar_one.return_value = extension
        schema.scalar_one_or_none.return_value = vector_type
        collection.mappings.return_value.one.return_value = {
            'uuid': 'collection-uuid', 'cmetadata': self.expected if persisted == 'default' else persisted}
        self.connection.execute.side_effect = [ext, schema, collection]

    @contextmanager
    def opened(self):
        with patch('src.vector_store.create_engine', return_value=self.engine) as make:
            with open_vector_store(self.settings, self.embeddings, self.expected,
                                   store_factory=self.factory) as store:
                yield store, make

    def test_options_manifest_read_and_disposal(self):
        self.rows()
        with self.opened() as (store, make):
            self.assertEqual(store.collection_id, 'collection-uuid')
            opts = make.call_args.kwargs
            self.assertEqual(opts['pool_timeout'], 10)
            self.assertTrue(opts['hide_parameters'])
            self.assertFalse(opts['echo'])
            self.assertEqual(opts['connect_args']['connect_timeout'], 10)
            self.assertIn('statement_timeout=30000', opts['connect_args']['options'])
            opts = self.factory.call_args.kwargs
            for key in ('pre_delete_collection', 'create_extension'):
                self.assertFalse(opts[key])
            self.assertIsNone(opts['embedding_length'])
            self.assertTrue(opts['use_jsonb'])
        self.engine.dispose.assert_called_once()
        self.embeddings.embed_documents.assert_not_called()

    def test_extension_missing_disposes_before_pgvector(self):
        self.rows(extension=False)
        with self.assertRaisesRegex(StorageError, 'vector'):
            with self.opened():
                pass
        self.factory.assert_not_called()
        self.engine.dispose.assert_called_once()

    def test_persisted_incompatible_manifest_rejected(self):
        wrong = deepcopy(self.expected)
        wrong['embedding_model'] = 'other-model'
        self.rows(persisted=wrong)
        with self.assertRaisesRegex(StorageError, 'collection'):
            with self.opened():
                pass
        self.embeddings.embed_documents.assert_not_called()
        self.factory.return_value.add_embeddings.assert_not_called()
        self.engine.dispose.assert_called_once()

    def test_all_incompatible_manifests_rejected_even_if_empty(self):
        variants = [None, {}, {'legacy': True}]
        for key, value in (('schema_version', 2), ('embedding_model', 'other-model'),
                           ('embedding_dimensions', 512), ('document_sha256', 'b' * 64),
                           ('pipeline', {'other': 'pipeline'})):
            variants.append({**self.expected, key: value})
        nested = deepcopy(self.expected)
        nested['pipeline']['chunk_overlap'] = 149
        variants.append(nested)
        for variant in variants:
            self.rows(persisted=variant)
            with self.subTest(manifest=variant):
                with self.assertRaises(StorageError):
                    with self.opened():
                        pass
        self.embeddings.embed_documents.assert_not_called()
        self.factory.return_value.add_embeddings.assert_not_called()

    def test_database_timeout_and_concurrent_creation_dispose(self):
        from sqlalchemy.exc import IntegrityError, OperationalError, TimeoutError
        for exception in (OperationalError('SQL secret', {}, Exception('password')),
                          TimeoutError('sentinel-secret'),
                          IntegrityError('concurrent secret', {}, Exception())):
            self.rows()
            self.factory.side_effect = exception
            with self.subTest(exception=type(exception).__name__):
                with self.assertRaises(StorageError) as error:
                    with self.opened():
                        pass
                self.assertNotIn('secret', str(error.exception))
        self.assertEqual(self.engine.dispose.call_count, 3)

    def test_connect_error_disposes_and_does_not_create_store(self):
        from sqlalchemy.exc import OperationalError
        self.engine.connect.side_effect = OperationalError('secret', {}, Exception())
        with self.assertRaises(StorageError):
            with self.opened():
                pass
        self.engine.dispose.assert_called_once()
        self.factory.assert_not_called()

    def test_legacy_fixed_dimension_incompatible_before_creation(self):
        self.rows(vector_type='vector(512)')
        with self.assertRaisesRegex(StorageError, 'legada'):
            with self.opened():
                pass
        self.factory.assert_not_called()

    def test_manifest_for_search_requires_complete_pipeline_without_pdf(self):
        from dataclasses import replace
        from src.vector_store import validate_manifest
        config = replace(self.settings, pdf_path=None)
        validate_manifest(self.expected, config)
        invalid = deepcopy(self.expected)
        invalid['pipeline'] = {'unknown': 'pipeline'}
        with self.assertRaises(StorageError):
            validate_manifest(invalid, config)


class PersistTests(unittest.TestCase):
    def setUp(self):
        from langchain_core.documents import Document
        from src.vector_store import VectorStore
        self.chunk = Document(page_content='Conteúdo', metadata={
            'chunk_id': 'id-1', 'source': '/a.pdf', 'page': 0}, id='id-1')
        self.store = MagicMock()
        self.engine = MagicMock()
        self.target = VectorStore(self.store, self.engine, 'uuid', 2)
        self.vector = [[0.1, 0.2]]
        self.store.add_embeddings.return_value = ['id-1']
        connection = self.engine.connect.return_value.__enter__.return_value
        self.result = connection.execute.return_value.mappings.return_value
        self.result.all.return_value = [{'id': 'id-1', 'document': 'Conteúdo',
                                        'cmetadata': self.chunk.metadata, 'dimensions': 2}]

    def test_write_once_and_confirm_by_id(self):
        from src.vector_store import persist_chunks
        self.assertEqual(persist_chunks(self.target, [self.chunk], self.vector), 1)
        self.store.add_embeddings.assert_called_once_with(
            texts=['Conteúdo'], embeddings=self.vector,
            metadatas=[self.chunk.metadata], ids=['id-1'])
        call = self.engine.connect.return_value.__enter__.return_value.execute.call_args
        self.assertEqual(call.args[1]['collection_id'], 'uuid')

    def test_invalid_cardinality_duplicates_and_vectors_never_write(self):
        from src.vector_store import persist_chunks
        for chunks, vectors in (([self.chunk], []), ([self.chunk] * 2, self.vector * 2),
                                ([self.chunk], [[0.1]]), ([self.chunk], [[float('nan'), 0.1]]),
                                ([self.chunk], [[float('inf'), 0.1]])):
            with self.subTest(vectors=vectors):
                with self.assertRaises(StorageError):
                    persist_chunks(self.target, chunks, vectors)
        self.store.add_embeddings.assert_not_called()

    def test_wrong_confirmation_is_failure(self):
        from src.vector_store import persist_chunks
        self.result.all.return_value[0]['document'] = 'Outro texto'
        with self.assertRaisesRegex(StorageError, 'confirm|indeterminado'):
            persist_chunks(self.target, [self.chunk], self.vector)

    def test_write_failure_and_uncertain_commit_never_retried(self):
        from sqlalchemy.exc import OperationalError
        from src.vector_store import persist_chunks
        self.store.add_embeddings.side_effect = OperationalError(
            'SQL sentinel-secret', {}, Exception('sentinel-password'))
        with self.assertRaisesRegex(StorageError, 'indeterminado') as error:
            persist_chunks(self.target, [self.chunk], self.vector)
        self.assertNotIn('sentinel', str(error.exception))
        self.store.add_embeddings.assert_called_once()

    def test_confirmation_failure_after_commit_is_indeterminate(self):
        from sqlalchemy.exc import OperationalError
        from src.vector_store import persist_chunks
        self.engine.connect.side_effect = OperationalError('SQL', {}, Exception())
        with self.assertRaisesRegex(StorageError, 'indeterminado'):
            persist_chunks(self.target, [self.chunk], self.vector)
        self.store.add_embeddings.assert_called_once()

    def test_returned_ids_missing_or_wrong_is_failure(self):
        from src.vector_store import persist_chunks
        for ids in ([], ['other'], ['id-1', 'id-1']):
            self.store.add_embeddings.return_value = ids
            with self.assertRaises(StorageError):
                persist_chunks(self.target, [self.chunk], self.vector)

    def test_out_of_order_confirmation_matches_by_id(self):
        from langchain_core.documents import Document
        from src.vector_store import persist_chunks
        other = Document(page_content='Outro', id='id-2', metadata={
            'chunk_id': 'id-2', 'source': '/a.pdf', 'page': 1})
        self.store.add_embeddings.return_value = ['id-2', 'id-1']
        self.result.all.return_value.insert(0, {'id': 'id-2', 'document': 'Outro',
                                             'cmetadata': other.metadata, 'dimensions': 2})
        self.assertEqual(persist_chunks(self.target, [self.chunk, other], self.vector * 2), 2)


class SearchStoreTests(unittest.TestCase):
    def setUp(self):
        self.settings = settings()
        self.engine = MagicMock()
        self.connection = self.engine.connect.return_value.__enter__.return_value
        self.factory = MagicMock()
        self.embeddings = MagicMock()
        self.expected = manifest()

    def rows(self, *, extension=True, schema=True, collection=True,
             persisted='default', count=3, dimensions=True, vector_type='vector'):
        values = []
        for value, method in (
            (extension, 'scalar_one'), (schema, 'scalar_one'),
            ({'uuid': 'collection-uuid', 'cmetadata': self.expected
              if persisted == 'default' else persisted} if collection else None,
             'mapping'),
            (vector_type, 'scalar_one_or_none'),
            ({'count': count, 'invalid_dimensions': 0 if dimensions else 1},
             'aggregate'),
        ):
            result = MagicMock()
            if method == 'mapping':
                result.mappings.return_value.one_or_none.return_value = value
            elif method == 'aggregate':
                result.mappings.return_value.one.return_value = value
            else:
                getattr(result, method).return_value = value
            values.append(result)
        self.connection.execute.side_effect = values

    @contextmanager
    def opened(self):
        from src.vector_store import open_search_store
        with patch('src.vector_store.create_engine', return_value=self.engine) as make:
            with open_search_store(self.settings, self.embeddings,
                                   store_factory=self.factory) as target:
                yield target, make

    def test_read_only_preflight_and_factory_options(self):
        self.rows()
        with self.opened() as (target, make):
            self.assertEqual(target.collection_id, 'collection-uuid')
            options = make.call_args.kwargs
            self.assertIn('default_transaction_read_only=on',
                          options['connect_args']['options'])
            self.assertIn('statement_timeout=30000', options['connect_args']['options'])
            self.assertIn('lock_timeout=5000', options['connect_args']['options'])
            self.assertEqual(options['pool_timeout'], 10)
            self.assertEqual(options['connect_args']['connect_timeout'], 10)
            opts = self.factory.call_args.kwargs
            self.assertIsNone(opts['embedding_length'])
            self.assertFalse(opts['create_extension'])
            self.assertFalse(opts['pre_delete_collection'])
            self.assertTrue(opts['use_jsonb'])
            self.assertNotIn('collection_metadata', opts)
            calls = self.connection.execute.call_args_list
            self.assertTrue(all(str(call.args[0]).lstrip().startswith('SELECT')
                                for call in calls))
            self.assertEqual(calls[2].args[1], {'name': self.settings.collection_name})
            self.assertEqual(calls[-1].args[1]['collection_id'], 'collection-uuid')
        self.engine.dispose.assert_called_once()
        self.embeddings.embed_query.assert_not_called()

    def test_invalid_base_before_factory(self):
        for change in ({'extension': False}, {'schema': False},
                       {'collection': False}, {'count': 0},
                       {'persisted': None}, {'dimensions': False},
                       {'vector_type': 'vector(999)'}):
            self.rows(**change)
            with self.subTest(change=change), self.assertRaises(StorageError):
                with self.opened():
                    pass
        self.factory.assert_not_called()
        self.embeddings.embed_query.assert_not_called()
        self.assertEqual(self.engine.dispose.call_count, 7)

    def test_creation_race_and_timeout_are_safe_and_dispose(self):
        from sqlalchemy.exc import OperationalError, TimeoutError
        for error in (OperationalError('SQL sentinel', {}, Exception('password')),
                      TimeoutError('sentinel')):
            self.rows()
            self.factory.side_effect = error
            with self.assertRaises(StorageError) as caught:
                with self.opened():
                    pass
            self.assertNotIn('sentinel', str(caught.exception))
            self.assertTrue(caught.exception.__suppress_context__)
        self.assertEqual(self.engine.dispose.call_count, 2)

    def test_ingestion_engine_stays_writable(self):
        with patch('src.vector_store.create_engine') as create:
            connection = create.return_value.connect.return_value.__enter__.return_value
            connection.execute.return_value.scalar_one_or_none.return_value = None
            connection.execute.return_value.mappings.return_value.one.return_value = {
                'uuid': 'id', 'cmetadata': self.expected}
            with open_vector_store(self.settings, self.embeddings, self.expected,
                                   store_factory=self.factory):
                pass
        self.assertNotIn('read_only', create.call_args.kwargs['connect_args']['options'])

    def test_manifest_matrix_rejected_before_services(self):
        variants = [None, {}, {'legacy': True}]
        for key, value in (('schema_version', True), ('provider', 'google'),
                           ('document_sha256', 'invalid'), ('pipeline', {}),
                           ('embedding_model', 'other-same-dimensions'),
                           ('embedding_dimensions', 512)):
            variants.append({**self.expected, key: value})
        for variant in variants:
            self.rows(persisted=variant)
            with self.subTest(variant=variant), self.assertRaises(StorageError):
                with self.opened():
                    pass
        self.factory.assert_not_called()
        self.embeddings.embed_query.assert_not_called()
