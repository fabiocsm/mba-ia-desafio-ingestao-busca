"""Extração, divisão e ingestão de um PDF, sem I/O na importação."""
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
import hashlib
import json
import logging
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
import openai
from pypdf.errors import PyPdfError

if __package__:
    from .config import (
        CHUNK_OVERLAP, CHUNK_SIZE, ConfigurationError, Settings,
        embedding_session, load_settings, pipeline_identity,
    )
    from .vector_store import (
        Manifest, StorageError, VectorStore, open_vector_store,
        persist_chunks, validate_vectors,
    )
else:
    from config import (
        CHUNK_OVERLAP, CHUNK_SIZE, ConfigurationError, Settings,
        embedding_session, load_settings, pipeline_identity,
    )
    from vector_store import (
        Manifest, StorageError, VectorStore, open_vector_store,
        persist_chunks, validate_vectors,
    )

LOGGER = logging.getLogger(__name__)
EmbeddingFactory = Callable[[Settings], AbstractContextManager[Embeddings]]
StoreFactory = Callable[..., AbstractContextManager[VectorStore]]


class IngestionError(RuntimeError):
    """Falha de entrada ou processamento com diagnóstico sanitizado."""


@dataclass(frozen=True)
class IngestionResult:
    source: Path
    loaded_pages: int
    stored_chunks: int
    collection_name: str


def document_hash(path: Path) -> str:
    """Hash dos bytes, com leitura e fechamento garantidos."""
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def load_pdf_pages(path: Path) -> list[Document]:
    """Carrega todas as páginas de arquivo estável; não aplica OCR."""
    try:
        path = path.resolve(strict=True)
        if not path.is_file() or path.suffix.lower() != '.pdf':
            raise IngestionError(
                'PDF_PATH deve indicar arquivo regular com extensão .pdf.',
            )
        before = document_hash(path)
        pages = PyPDFLoader(
            str(path), mode='page', extract_images=False,
        ).load()
        if document_hash(path) != before:
            raise IngestionError(
                'PDF alterado durante leitura. '
                'Estabilize o arquivo e reexecute.',
            )
    except FileNotFoundError:
        raise IngestionError(
            'PDF inexistente. Confira PDF_PATH e o diretório de execução.',
        ) from None
    except PermissionError:
        raise IngestionError(
            'Acesso ao PDF negado. Confira permissões de leitura.',
        ) from None
    except (PyPdfError, ValueError, OSError):
        raise IngestionError(
            'PDF inválido ou ilegível. '
            'Forneça um PDF íntegro com texto extraível.',
        ) from None
    if not any(page.page_content.strip() for page in pages):
        raise IngestionError(
            'PDF sem texto extraível. '
            'OCR não é suportado; forneça PDF textual.',
        )
    for page in pages:
        page.metadata['document_sha256'] = before
    return pages


def build_manifest(settings: Settings, sha256: str) -> Manifest:
    """Identidade completa do espaço vetorial, revisão e pipeline fixado."""
    return {
        'schema_version': 1,
        'provider': 'openai',
        'embedding_model': settings.embedding_model,
        'embedding_dimensions': settings.embedding_dimensions,
        'document_sha256': sha256,
        'pipeline': pipeline_identity(),
    }


def split_pages(
    pages: list[Document], settings: Settings, manifest: Manifest,
) -> list[Document]:
    """Divide por página; ID inclui namespace, posição e hash do texto."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )
    nonempty_pages = [page for page in pages if page.page_content.strip()]
    chunks = [chunk for chunk in splitter.split_documents(nonempty_pages)
              if chunk.page_content.strip()]
    for index, chunk in enumerate(chunks):
        text_hash = hashlib.sha256(
            chunk.page_content.encode('utf-8'),
        ).hexdigest()
        identity = {
            **manifest,
            'collection_name': settings.collection_name,
            'page': chunk.metadata['page'],
            'chunk_index': index,
            'text_sha256': text_hash,
        }
        chunk_id = hashlib.sha256(json.dumps(
            identity, sort_keys=True, ensure_ascii=False,
            separators=(',', ':'),
        ).encode('utf-8')).hexdigest()
        chunk.id = chunk_id
        chunk.metadata.update(
            chunk_id=chunk_id, chunk_index=index,
            document_sha256=manifest['document_sha256'],
        )
    return chunks


def generate_embeddings(
    embeddings: Embeddings, chunks: list[Document],
) -> list[list[float]]:
    """Gera o lote; erros do provedor não incluem corpo HTTP ou chaves."""
    try:
        return embeddings.embed_documents(
            [chunk.page_content for chunk in chunks],
        )
    except openai.AuthenticationError:
        raise IngestionError(
            'API: credencial recusada; revise OPENAI_API_KEY em .env.local.',
        ) from None
    except openai.RateLimitError:
        raise IngestionError(
            'API: quota ou limite de requisições; '
            'confira saldo/limites antes de reexecutar.',
        ) from None
    except openai.APITimeoutError:
        raise IngestionError(
            'API: tempo limite excedido; '
            'confira conectividade e reexecute manualmente.',
        ) from None
    except openai.APIConnectionError:
        raise IngestionError(
            'API: falha de conexão; confira rede e acesso ao provedor.',
        ) from None
    except (
        openai.PermissionDeniedError, openai.NotFoundError,
        openai.BadRequestError,
    ):
        raise IngestionError(
            'API: confira acesso ao modelo, seu nome '
            'e a dimensão configurada.',
        ) from None
    except openai.APIStatusError:
        raise IngestionError(
            'API: serviço recusou a operação; '
            'confira disponibilidade e acesso ao modelo.',
        ) from None


def ingest_pdf(
    settings: Settings | None = None,
    *,
    embeddings_factory: EmbeddingFactory = embedding_session,
    store_factory: StoreFactory = open_vector_store,
) -> IngestionResult:
    """Valida antes da API; retorna sucesso somente após conferência."""
    settings = settings if settings is not None else load_settings()
    if settings.pdf_path is None:
        raise IngestionError('PDF_PATH obrigatório para ingestão.')
    pages = load_pdf_pages(settings.pdf_path)
    source = Path(pages[0].metadata['source'])
    sha256 = document_hash(source)
    # Detecta alteração também entre extração e construção da identidade.
    if pages[0].metadata['document_sha256'] != sha256:
        raise IngestionError(
            'PDF alterado após extração. Estabilize o arquivo e reexecute.',
        )
    manifest = build_manifest(settings, sha256)
    chunks = split_pages(pages, settings, manifest)
    if not chunks:
        raise IngestionError('PDF sem chunks textuais; OCR não é suportado.')
    with embeddings_factory(settings) as embeddings:
        with store_factory(settings, embeddings, manifest) as target:
            vectors = generate_embeddings(embeddings, chunks)
            validate_vectors(chunks, vectors, settings.embedding_dimensions)
            stored = persist_chunks(target, chunks, vectors)
    return IngestionResult(
        source, len(pages), stored, settings.collection_name,
    )


def main() -> int:
    """Fronteira CLI: não imprime exceções externas brutas ou segredos."""
    logging.basicConfig(
        level=logging.WARNING, format='%(levelname)s: %(message)s',
    )
    # O parser pode incluir bytes do PDF em avisos; a CLI sanitiza o erro.
    logging.getLogger('pypdf').setLevel(logging.CRITICAL)
    try:
        result = ingest_pdf(load_settings())
    except KeyboardInterrupt:
        LOGGER.error(
            'Ingestão interrompida; conclusão não confirmada. '
            'Reexecute a mesma entrada.',
        )
        return 130
    except (ConfigurationError, IngestionError, StorageError) as error:
        LOGGER.error('%s', error)
        return 1
    except Exception:
        LOGGER.error(
            'Falha operacional na ingestão. '
            'Revise configuração, conexão e acesso ao provedor.',
        )
        return 1
    print(
        f'Ingestão concluída: arquivo={result.source}; '
        f'páginas={result.loaded_pages}; '
        f'chunks confirmados={result.stored_chunks}; '
        f'collection={result.collection_name}',
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
