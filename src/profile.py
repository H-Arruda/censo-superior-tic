
"""Auditoria quantitativa dos microdados do INEP."""

import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
AUDIT = ROOT / "data" / "processed" / "audit"

GROUPS = [
    "TP_DIMENSAO",
    "TP_NIVEL_ACADEMICO",
    "TP_MODALIDADE_ENSINO",
]

METRICS = [
    "QT_MAT",
    "QT_MAT_FEM",
    "QT_MAT_MASC",
    "QT_ING",
]

COLUMNS = GROUPS + METRICS + [
    "CO_CINE_AREA_GERAL",
    "NO_CINE_AREA_GERAL",
]


def main():
    AUDIT.mkdir(parents=True, exist_ok=True)

    reports = []

    for path in sorted(RAW.glob("*.zip")):
        year = int(path.stem[-4:])

        print(f"\n========== {year} ==========", flush=True)

        with zipfile.ZipFile(path) as archive:
            member = next(
                name for name in archive.namelist()
                if f"CADASTRO_CURSOS_{year}.CSV"
                in name.upper()
            )

            for encoding in ["utf-8-sig", "latin-1"]:
                try:
                    with archive.open(member) as file:
                        df = pd.read_csv(
                            file,
                            sep=";",
                            encoding=encoding,
                            usecols=COLUMNS,
                            dtype=str,
                            keep_default_na=False,
                        )
                    break
                except UnicodeDecodeError:
                    if encoding == "latin-1":
                        raise

        print("Encoding:", encoding)
        print("Total de registros:", len(df))

        for col in COLUMNS:
            df[col] = df[col].str.strip()

        print("Área 06:")
        print(
            df.loc[
                df["CO_CINE_AREA_GERAL"].isin(["06", "6"]),
                ["CO_CINE_AREA_GERAL", "NO_CINE_AREA_GERAL"],
            ].drop_duplicates().to_string(index=False)
        )

        for col in METRICS:
            values = pd.to_numeric(df[col], errors="coerce")

            invalid = values.isna()

            print(f"{col}: {invalid.sum()} valores não numéricos")

            if invalid.any():
                print(df.loc[invalid, col].value_counts().head())

            print("Negativos:", values.lt(0).sum())

            df[col] = values

        valid = df[METRICS[:3]].notna().all(axis=1)

        mismatch = (
            df["QT_MAT_FEM"] + df["QT_MAT_MASC"]
            != df["QT_MAT"]
        ) & valid

        print("Divergências FEM + MASC:", mismatch.sum())

        summary = df.groupby(GROUPS, dropna=False)[METRICS].sum(
            min_count=1
        )

        summary["registros"] = df.groupby(
            GROUPS, dropna=False
        ).size()

        summary = summary.reset_index()
        summary.insert(0, "ano", year)

        print(summary.to_string(index=False))

        reports.append(summary)

    if not reports:
        raise RuntimeError("Nenhum ZIP encontrado.")

    result = pd.concat(reports, ignore_index=True)

    result.to_csv(
        AUDIT / "dimension_profile.csv",
        index=False,
    )

    print("\nAuditoria concluída.")


if __name__ == "__main__":
    main()
