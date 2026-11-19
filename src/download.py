"""Aquisição dos microdados oficiais do Censo da Educação Superior."""
import argparse
import hashlib
import json
import logging
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
YEARS = tuple(range(2019, 2025))
BASE = 'https://download.inep.gov.br/microdados/'


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_zip(path):
    with zipfile.ZipFile(path) as archive:
        if not archive.namelist():
            raise ValueError(f'ZIP vazio: {path.name}')
        bad = archive.testzip()
        if bad is not None:
            raise ValueError(f'Membro corrompido: {bad}')


def save_manifest(path, manifest):
    temp = path.with_suffix('.json.part')
    temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2,
                               sort_keys=True) + '\n', encoding='utf-8')
    temp.replace(path)


def download(year, manifest, manifest_path):
    name = f'microdados_censo_da_educacao_superior_{year}.zip'
    url = BASE + name
    dest = RAW / name
    temp = RAW / (name + '.part')
    record = manifest.get(str(year))
    if dest.exists():
        if not record or record.get('size_bytes') != dest.stat().st_size or record.get('sha256') != sha256(dest):
            raise RuntimeError(f'{year}: ZIP sem manifesto correspondente ou hash divergente; arquivo preservado.')
        logging.info('%s: arquivo íntegro; download ignorado.', year)
        return
    if record and record.get('url') != url:
        raise RuntimeError(f'{year}: URL diferente da registrada.')
    logging.info('%s: iniciando download %s', year, url)
    try:
        with requests.get(url, stream=True, timeout=(20, 120),
                          headers={'Accept-Encoding': 'identity'}) as response:
            response.raise_for_status()
            digest = hashlib.sha256()
            size = 0
            with temp.open('wb') as out:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        out.write(chunk)
                        digest.update(chunk)
                        size += len(chunk)
            expected = response.headers.get('Content-Length')
            if expected is not None and size != int(expected):
                raise ValueError(f'Tamanho recebido {size}; esperado {expected}.')
            metadata = {'year': year, 'file': name, 'url': url,
                        'final_url': response.url, 'size_bytes': size,
                        'sha256': digest.hexdigest(),
                        'downloaded_at_utc': datetime.now(timezone.utc).isoformat(),
                        'http_headers': {key: response.headers.get(key) for key in
                                         ('Last-Modified', 'ETag', 'Content-Length', 'Content-Type')}}
        validate_zip(temp)
        if record and record.get('sha256') != metadata['sha256']:
            raise RuntimeError(f'{year}: fonte diverge do hash já registrado.')
        # Hard link cria o destino atomicamente e falha se ele já existir.
        dest.hardlink_to(temp)
        manifest[str(year)] = metadata
        save_manifest(manifest_path, manifest)
        logging.info('%s: concluído (%s bytes); SHA-256=%s', year, size, metadata['sha256'])
    finally:
        temp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--years', nargs='+', type=int, choices=YEARS, default=YEARS)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    RAW.mkdir(parents=True, exist_ok=True)
    manifest_path = RAW / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    for year in sorted(set(args.years)):
        download(year, manifest, manifest_path)


if __name__ == '__main__':
    main()
