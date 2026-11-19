
"""Auditoria dos dicionários oficiais do INEP."""

import io
import zipfile
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

VARIABLES = {
    "NU_ANO_CENSO",
    "TP_DIMENSAO",
    "TP_NIVEL_ACADEMICO",
    "TP_MODALIDADE_ENSINO",
    "TP_GRAU_ACADEMICO",
    "CO_CINE_AREA_GERAL",
    "NO_CINE_AREA_GERAL",
    "CO_CURSO",
    "CO_IES",
    "QT_MAT",
    "QT_MAT_FEM",
    "QT_MAT_MASC",
    "QT_ING",
}


def main():
    for path in sorted(RAW.glob("*.zip")):
        print(f"\n{'=' * 70}")
        print(path.name)
        print("=" * 70)

        with zipfile.ZipFile(path) as archive:
            dictionaries = [
                name for name in archive.namelist()
                if name.lower().endswith(".xlsx")
                and not Path(name).name.startswith("~$")
            ]

            for name in dictionaries:
                workbook = openpyxl.load_workbook(
                    io.BytesIO(archive.read(name)),
                    read_only=True,
                    data_only=True,
                )

                print("Abas:", workbook.sheetnames)

                for sheet in workbook.worksheets:
                    rows = list(sheet.values)
                    printed = set()

                    for index, row in enumerate(rows):
                        values = {
                            str(value).strip()
                            for value in row
                            if value is not None
                        }

                        if not VARIABLES.intersection(values):
                            continue

                        print(f"\nAba: {sheet.title}")

                        for position in range(
                            index, min(index + 16, len(rows))
                        ):
                            if position in printed:
                                continue

                            content = " | ".join(
                                str(value)
                                for value in rows[position]
                                if value is not None
                            )

                            if content:
                                print(content)

                            printed.add(position)

                workbook.close()


if __name__ == "__main__":
    main()
