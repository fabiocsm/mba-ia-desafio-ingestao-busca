"""Configuração compartilhada, sem inicialização externa na importação."""
import asyncio
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
import os
from pathlib import Path

from dotenv import dotenv_values
import httpx
from langchain_openai import OpenAIEmbeddings
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def pipeline_identity() -> dict[str, object]:
    """Retorna uma estrutura independente com o contrato do pipeline fixado."""
    return {
        'loader': 'PyPDFLoader',
        'langchain-community': '0.3.27',
        'pypdf': '6.0.0',
        'mode': 'page',
        'extract_images': False,
        'splitter': 'RecursiveCharacterTextSplitter',
        'langchain-text-splitters': '0.3.9',
        'chunk_size': CHUNK_SIZE,
        'chunk_overlap': CHUNK_OVERLAP,
        'length_function': 'len',
        'separators': ['\n\n', '\n', ' ', ''],
    }


class ConfigurationError(ValueError):
    """Configuração local incompleta ou inválida, sem valores sensíveis."""


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    embedding_model: str
    embedding_dimensions: int
    database_url: str = field(repr=False)
    collection_name: str
    pdf_path: Path | None = None


def load_settings(
    *,
    ingestion: bool = True,
    root: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Settings:
    """Lê ambiente > .env.local > .env, sem mutar arquivos ou os.environ."""
    root = root if root is not None else Path(__file__).resolve().parents[1]
    values = {}
    for filename in ('.env', '.env.local'):
        values.update(dotenv_values(
            root / filename, encoding='utf-8', interpolate=False,
        ))
    values.update(os.environ if environ is None else environ)

    def required(name: str) -> str:
        value = values.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ConfigurationError(
                f'{name} obrigatória; configure .env, .env.local ou ambiente.',
            )
        return value.strip()

    api_key = required('OPENAI_API_KEY')
    model = required('OPENAI_EMBEDDING_MODEL')
    url = required('DATABASE_URL')
    collection = required('PG_VECTOR_COLLECTION_NAME')
    try:
        parsed = make_url(url)
        if (parsed.drivername != 'postgresql+psycopg' or not parsed.host
                or not parsed.database):
            raise ValueError
        # Força a validação da porta sem imprimir a URL.
        _ = parsed.port
    except (ArgumentError, ValueError):
        raise ConfigurationError(
            'DATABASE_URL inválida; use postgresql+psycopg:// '
            'com host e banco '
            'em .env ou .env.local.',
        ) from None
    try:
        dimensions = int(values.get('OPENAI_EMBEDDING_DIMENSIONS', '1536'))
        if dimensions <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ConfigurationError(
            'OPENAI_EMBEDDING_DIMENSIONS deve ser inteiro positivo; '
            'revise .env ou .env.local.',
        ) from None
    pdf_path = Path(required('PDF_PATH')) if ingestion else None
    return Settings(api_key, model, dimensions, url, collection, pdf_path)


def create_embeddings(
    settings: Settings,
    *,
    http_client: httpx.Client | None = None,
    http_async_client: httpx.AsyncClient | None = None,
) -> OpenAIEmbeddings:
    """Constrói o cliente escolhido sem efetuar chamadas à API."""
    return OpenAIEmbeddings(
        api_key=settings.api_key,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
        request_timeout=60,
        max_retries=0,
        http_client=http_client,
        http_async_client=http_async_client,
    )


@contextmanager
def embedding_session(settings: Settings) -> Iterator[OpenAIEmbeddings]:
    """Uso síncrono da CLI; fecha ambos os transportes da integração."""
    async_http = httpx.AsyncClient(timeout=60)
    try:
        with httpx.Client(timeout=60) as sync_http:
            yield create_embeddings(
                settings, http_client=sync_http, http_async_client=async_http,
            )
    finally:
        asyncio.run(async_http.aclose())
