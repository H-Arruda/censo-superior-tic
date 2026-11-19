
"""Inventário dos microdados do Censo da Educação Superior."""

import csv
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
AUDIT = ROOT / "data" / "processed" / "audit"


def main():
    AUDIT.mkdir(parents=True, exist_ok=True)
    inventory = []

    for path in sorted(RAW.glob("*.zip")):
        print(f"\n{'=' * 70}")
        print(f"ARQUIVO: {path.name}")
        print(f"{'=' * 70}")

        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue

                inventory.append({
                    "arquivo_zip": path.name,
                    "arquivo_interno": member.filename,
                    "tamanho_bytes": member.file_size,
                })

                print(member.filename)

                if member.filename.lower().endswith(".csv"):
                    with archive.open(member) as file:
                        header = file.readline()

                    try:
                        header = header.decode("utf-8-sig")
                        encoding = "utf-8-sig"
                    except UnicodeDecodeError:
                        header = header.decode("latin-1")
                        encoding = "latin-1"

                    dialect = csv.Sniffer().sniff(
                        header, delimiters=";,\t|"
                    )
                    columns = next(csv.reader(
                        [header], dialect=dialect
                    ))

                    print(f"  Encoding preliminar: {encoding}")
                    print(f"  Separador: {repr(dialect.delimiter)}")
                    print(f"  Total de colunas: {len(columns)}")
                    print(f"  Colunas: {columns}")

    output = AUDIT / "inventory.csv"

    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "arquivo_zip",
                "arquivo_interno",
                "tamanho_bytes",
            ],
        )
        writer.writeheader()
        writer.writerows(inventory)

    print(f"\nInventário salvo em: {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
