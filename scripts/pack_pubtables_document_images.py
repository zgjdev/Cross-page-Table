"""Pack complete documents into image-only PDFs without consulting ground truth."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

import pymupdf as fitz


def pack_documents(images: Path, documents: list[str], output: Path) -> dict:
    if output.exists():
        raise FileExistsError(output)
    if not documents or len(set(documents)) != len(documents):
        raise ValueError('Require nonempty, unique document IDs')
    sources = {}
    pages = []
    for document in documents:
        if not re.fullmatch(r'PMC[0-9]+', document):
            raise ValueError(f'Invalid document ID: {document}')
        entries = []
        for path in images.glob(f'{document}_page_*.jpg'):
            match = re.fullmatch(re.escape(document) + r'_page_([0-9]+)\.jpg', path.name)
            if match is None:
                raise ValueError(f'Invalid page name: {path.name}')
            entries.append((int(match[1]), path))
        entries.sort()
        if not entries or [n for n, _ in entries] != list(range(len(entries))):
            raise ValueError(f'{document}: pages must be contiguous and start at zero')
        sources[document] = entries
        for number, path in entries:
            payload = path.read_bytes()
            pixmap = fitz.Pixmap(payload)
            width, height = pixmap.width, pixmap.height
            del pixmap
            if width < 1 or height < 1:
                raise ValueError(f'Invalid source image: {path}')
            pages.append({
                'document_id': document, 'image_id': path.stem,
                'relative_path': path.name, 'unit_id': document,
                'page_number': number, 'pdf_page_index': number,
                'image_sha256': hashlib.sha256(payload).hexdigest(),
                'width': width, 'height': height,
            })
    output.mkdir(parents=True, exist_ok=False)
    pdfs = []
    for document, entries in sources.items():
        target = output / f'{document}.pdf'
        mappings = [p for p in pages if p['document_id'] == document]
        with fitz.open() as pdf:
            for (_, path), mapping in zip(entries, mappings, strict=True):
                payload = path.read_bytes()
                if hashlib.sha256(payload).hexdigest() != mapping['image_sha256']:
                    raise ValueError(f'Source changed during packing: {path}')
                page = pdf.new_page(width=mapping['width'] / 2,
                                    height=mapping['height'] / 2)
                page.insert_image(page.rect, stream=payload)
            pdf.save(target)
        with fitz.open(target) as pdf:
            if len(pdf) != len(entries) or any(page.get_text() for page in pdf):
                raise ValueError(f'Image-only PDF audit failed: {target}')
            for page, mapping in zip(pdf, mappings, strict=True):
                embedded = page.get_images(full=True)
                if len(embedded) != 1:
                    raise ValueError(f'Expected one original image: {target}')
                blob = pdf.extract_image(embedded[0][0])['image']
                if hashlib.sha256(blob).hexdigest() != mapping['image_sha256']:
                    raise ValueError(f'Embedded JPEG bytes changed: {target}')
        pdfs.append({'document_id': document, 'file': target.name,
                     'pages': len(entries),
                     'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
    manifest_keys = ('image_id', 'relative_path', 'unit_id', 'document_id', 'page_number')
    with (output / 'input-manifest.jsonl').open('x', encoding='utf-8') as handle:
        for page in pages:
            handle.write(json.dumps({k: page[k] for k in manifest_keys}) + '\n')
    result = {'format': 'image-only-pdf', 'source_images': str(images.resolve()),
              'render_scale': 2.0, 'pdf_text_audit': 'empty',
              'embedded_image_audit': 'byte-identical', 'pages': pages, 'pdfs': pdfs}
    with (output / 'packing-manifest.json').open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--images', type=Path, required=True)
    parser.add_argument('--documents', nargs='+', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    result = pack_documents(args.images, args.documents, args.output_dir)
    print(json.dumps({'documents': len(result['pdfs']), 'pages': len(result['pages']),
                      'output': str(args.output_dir)}))


if __name__ == '__main__':
    main()
