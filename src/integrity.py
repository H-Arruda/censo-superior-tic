"""Compare os CSVs com os checksums distribuídos pelo INEP."""
import csv
import hashlib
import re
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw'
AUDIT = ROOT / 'data/processed/audit'


def main():
    rows = []
    for year in range(2019, 2025):
        path = RAW / f'microdados_censo_da_educacao_superior_{year}.zip'
        with ZipFile(path) as z:
            manifests = [n for n in z.namelist() if 'md5' in Path(n).name.lower() and n.lower().endswith('.txt')]
            if len(manifests) != 1:
                raise ValueError(f'{year}: manifesto MD5 ausente ou ambíguo')
            entries = {}
            for line in z.read(manifests[0]).decode('utf-8-sig').splitlines():
                if not line.strip():
                    continue
                match = re.fullmatch(r'([0-9a-fA-F]{32})\s+\*?(.+)', line.strip())
                if not match:
                    raise ValueError(f'{year}: linha MD5 inválida: {line!r}')
                expected, name = match.groups()
                key = name.upper()
                if key in entries:
                    raise ValueError(f'{year}: entrada MD5 duplicada: {name}')
                entries[key] = expected.lower()
            required = {f'MICRODADOS_CADASTRO_CURSOS_{year}.CSV', f'MICRODADOS_CADASTRO_IES_{year}.CSV'}
            if set(entries) != required:
                raise ValueError(f'{year}: entradas MD5 inesperadas: {list(entries)}')
            for name, expected in entries.items():
                aliases = {name}
                if name == f'MICRODADOS_CADASTRO_IES_{year}.CSV' and year >= 2022:
                    aliases.add(f'MICRODADOS_ED_SUP_IES_{year}.CSV')
                members = [n for n in z.namelist() if Path(n).name.upper() in aliases]
                if len(members) != 1:
                    raise ValueError(f'{year}: CSV ausente ou ambíguo: {name}')
                with z.open(members[0]) as f:
                    actual = hashlib.file_digest(f, 'md5').hexdigest()
                status = 'OK' if expected == actual else 'DIVERGENTE'
                rows.append(dict(ano=year, nome_manifesto=name, arquivo_zip=members[0], md5_esperado=expected, md5_calculado=actual, status=status))
                print(f'{year} | {Path(members[0]).name} | {status}', flush=True)
    AUDIT.mkdir(parents=True, exist_ok=True)
    with (AUDIT / 'integrity.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    count = sum(r['status'] == 'OK' for r in rows)
    print(f'Checksums correspondentes: {count}/{len(rows)}')
    if count != len(rows):
        raise SystemExit('Divergências encontradas. Investigue antes da publicação.')


if __name__ == '__main__':
    main()
