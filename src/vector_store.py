"""Manifesto imutável e persistência conferida, delimitados à collection."""
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import math
import re

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_postgres import PGVector
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

if __package__:
    from .config import CHUNK_SIZE, Settings, pipeline_identity
else:
    from config import CHUNK_SIZE, Settings, pipeline_identity

# Metadados do loader são JSON heterogêneo, tratados como object.
Manifest = dict[str, object]


class StorageError(RuntimeError):
    """Falha operacional sanitizada de preparação, escrita ou conferência."""


@dataclass(frozen=True)
class VectorStore:
    store: PGVector
    engine: Engine
    collection_id: str
    dimensions: int


def validate_manifest(
    actual: object, settings: Settings, expected: Manifest | None = None,
) -> None:
    """Valida espaço sem PDF_PATH; ingestão compara manifesto completo."""
    valid = isinstance(actual, dict)
    if valid:
        valid = (
            type(actual.get('schema_version')) is int
            and actual.get('schema_version') == 1
            and actual.get('provider') == 'openai'
            and actual.get('embedding_model') == settings.embedding_model
            and type(actual.get('embedding_dimensions')) is int
            and actual.get('embedding_dimensions')
            == settings.embedding_dimensions
            and isinstance(actual.get('document_sha256'), str)
            and re.fullmatch(r'[0-9a-f]{64}', actual['document_sha256'])
            is not None
            and isinstance(actual.get('pipeline'), dict)
            and actual['pipeline'] == pipeline_identity()
        )
    if not valid or (expected is not None and actual != expected):
        raise StorageError(
            'Manifesto da collection ausente ou incompatível. '
            'Use a configuração original ou nova collection explícita para '
            'reindexação integral; nenhum dado foi apagado.',
        )


@contextmanager
def open_vector_store(
    settings: Settings,
    embeddings: Embeddings,
    expected_manifest: Manifest,
    *,
    store_factory: Callable[..., PGVector] = PGVector,
) -> Iterator[VectorStore]:
    """Confere extensão e manifesto persistido; sempre libera o engine."""
    engine = create_engine(
        settings.database_url,
        echo=False,
        hide_parameters=True,
        pool_timeout=10,
        connect_args={
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000 -c lock_timeout=5000',
        },
    )
    try:
        try:
            with engine.connect() as connection:
                extension = connection.execute(text(
                    'SELECT EXISTS(SELECT 1 FROM pg_extension '
                    "WHERE extname='vector')",
                )).scalar_one()
                if not extension:
                    raise StorageError(
                        'Extensão vector ausente. Execute o bootstrap '
                        'do Compose e confirme sua conclusão '
                        'antes da ingestão.',
                    )
                vector_type = connection.execute(text(
                    'SELECT format_type(atttypid, atttypmod) '
                    'FROM pg_attribute '
                    "WHERE attrelid=to_regclass('langchain_pg_embedding') "
                    "AND attname='embedding' AND NOT attisdropped",
                )).scalar_one_or_none()
                fixed_type = f'vector({settings.embedding_dimensions})'
                if vector_type and vector_type not in ('vector', fixed_type):
                    raise StorageError(
                        'Tabela PGVector legada com dimensão fixa '
                        'incompatível; use banco separado ou migração '
                        'administrativa explícita.',
                    )
            store = store_factory(
                embeddings=embeddings,
                connection=engine,
                collection_name=settings.collection_name,
                collection_metadata=expected_manifest,
                embedding_length=None,
                create_extension=False,
                pre_delete_collection=False,
                use_jsonb=True,
            )
            with engine.connect() as connection:
                row = connection.execute(text(
                    'SELECT uuid, cmetadata FROM langchain_pg_collection '
                    'WHERE name=:name',
                ), {'name': settings.collection_name}).mappings().one()
            validate_manifest(row['cmetadata'], settings, expected_manifest)
        except SQLAlchemyError:
            raise StorageError(
                'Falha de conexão/preparação da collection (possível '
                'concorrência ou timeout). Confirme docker compose, porta, '
                'saúde e bootstrap; reexecute com a mesma configuração. '
                'Nenhum dado foi apagado.',
            ) from None
        yield VectorStore(
            store, engine, str(row['uuid']), settings.embedding_dimensions,
        )
    finally:
        engine.dispose()


def validate_vectors(
    chunks: list[Document], vectors: list[list[float]], dimensions: int,
) -> None:
    """Valida o lote integralmente antes de qualquer escrita."""
    ids = [chunk.id for chunk in chunks]
    if (not chunks or len(chunks) != len(vectors)
            or len(set(ids)) != len(ids) or any(not item for item in ids)):
        raise StorageError(
            'Lote inválido: quantidade de vetores ou IDs divergente.',
        )
    for chunk, vector in zip(chunks, vectors, strict=True):
        if (not chunk.page_content.strip()
                or len(chunk.page_content) > CHUNK_SIZE
                or chunk.metadata.get('chunk_id') != chunk.id
                or not isinstance(vector, list) or len(vector) != dimensions
                or any(type(value) is not float or not math.isfinite(value)
                       for value in vector)):
            raise StorageError(
                'Lote inválido: confira texto, metadados, dimensão '
                'e vetores finitos.',
            )


def _unconfirmed(stage: str) -> StorageError:
    return StorageError(
        f'{stage}; resultado indeterminado, sem quantidade confirmada. '
        'Verifique conexão e reexecute o mesmo PDF/configuração; '
        'pode haver nova cobrança de embeddings.',
    )


def persist_chunks(
    target: VectorStore, chunks: list[Document], vectors: list[list[float]],
) -> int:
    """Um upsert PGVector e conferência completa por ID e collection."""
    validate_vectors(chunks, vectors, target.dimensions)
    ids = [chunk.id for chunk in chunks]
    stage = 'Falha de escrita'
    try:
        returned = target.store.add_embeddings(
            texts=[chunk.page_content for chunk in chunks],
            embeddings=vectors,
            metadatas=[chunk.metadata for chunk in chunks],
            ids=ids,
        )
        if len(returned) != len(ids) or set(returned) != set(ids):
            raise _unconfirmed('Gravação não confirmada pelos IDs retornados')
        stage = 'Falha de conferência após escrita'
        with target.engine.connect() as connection:
            rows = connection.execute(text(
                'SELECT id, document, cmetadata, '
                'vector_dims(embedding) AS dimensions '
                'FROM langchain_pg_embedding '
                'WHERE collection_id=:collection_id',
            ), {'collection_id': target.collection_id}).mappings().all()
        records = {row['id']: row for row in rows}
        if len(rows) != len(ids) or set(records) != set(ids):
            raise _unconfirmed(
                'Conferência dos registros da collection falhou',
            )
        for chunk in chunks:
            row = records[chunk.id]
            if (row['document'] != chunk.page_content
                    or row['cmetadata'] != chunk.metadata
                    or row['dimensions'] != target.dimensions):
                raise _unconfirmed(
                    'Conferência de texto/metadados/dimensão falhou',
                )
    except SQLAlchemyError:
        raise _unconfirmed(stage) from None
    return len(records)
