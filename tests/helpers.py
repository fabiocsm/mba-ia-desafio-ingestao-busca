"""Amostras locais e configuração sem credenciais reais."""
from pathlib import Path
from tempfile import TemporaryDirectory

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from src.config import load_settings
from tests.test_config import ENV


def settings(**overrides):
    with TemporaryDirectory() as directory:
        return load_settings(root=Path(directory), environ={**ENV, **overrides})


def write_pdf(path: Path, texts: list[str]) -> None:
    writer = PdfWriter()
    for text in texts:
        page = writer.add_blank_page(width=600, height=800)
        if text:
            font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                                     NameObject('/Subtype'): NameObject('/Type1'),
                                     NameObject('/BaseFont'): NameObject('/Helvetica'),
                                     NameObject('/Encoding'): NameObject('/WinAnsiEncoding')})
            page[NameObject('/Resources')] = DictionaryObject({
                NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
            stream = DecodedStreamObject()
            escaped = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            stream.set_data(f'BT /F1 12 Tf 10 700 Td ({escaped}) Tj ET'.encode('latin-1'))
            page[NameObject('/Contents')] = writer._add_object(stream)
    with path.open('wb') as handle:
        writer.write(handle)
