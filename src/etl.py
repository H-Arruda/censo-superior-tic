"""ETL nacional (oferta no Brasil), Censo Superior 2019–2024."""
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw'
OUT = ROOT / 'data/processed'
AUDIT = OUT / 'audit'
YEARS = range(2019, 2025)
METRICS = ['QT_MAT', 'QT_MAT_FEM', 'QT_MAT_MASC', 'QT_ING']
COLS = ['NU_ANO_CENSO', 'TP_DIMENSAO', 'TP_NIVEL_ACADEMICO',
        'TP_MODALIDADE_ENSINO', 'CO_CINE_AREA_GERAL', 'NO_CINE_AREA_GERAL', *METRICS]
BASE = 'https://download.inep.gov.br/microdados/'


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write_json(path, obj):
    temp = path.with_suffix(path.suffix + '.part')
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def process(df, year):
    for col in COLS:
        df[col] = df[col].str.strip()
    if not df.NU_ANO_CENSO.eq(str(year)).all():
        raise ValueError(f'{year}: ano divergente')
    for col, domain in [('TP_NIVEL_ACADEMICO', ['1', '2']),
                        ('TP_DIMENSAO', ['1', '2', '3', '4']),
                        ('TP_MODALIDADE_ENSINO', ['1', '2'])]:
        if not df[col].isin(domain).all():
            raise ValueError(f'{year}: código desconhecido em {col}')
    expected = df.TP_DIMENSAO.map({'1': '1', '2': '2', '3': '2', '4': '2'})
    if not expected.eq(df.TP_MODALIDADE_ENSINO).all():
        raise ValueError(f'{year}: dimensão/modalidade incompatível')
    dim3 = df.loc[df.TP_DIMENSAO.eq('3'), METRICS]
    if not dim3.isin(['', '0']).all().all():
        raise ValueError(f'{year}: dimensão 3 contém valores inesperados')
    grad = df.loc[df.TP_NIVEL_ACADEMICO.eq('1')]
    kept = grad.loc[grad.TP_DIMENSAO.isin(['1', '2'])].copy()
    for col in METRICS:
        if not kept[col].str.fullmatch(r'[0-9]+').all():
            raise ValueError(f'{year}: valor inválido em {col} nos registros retidos')
        kept[col] = kept[col].astype('int64')
    if not (kept.QT_MAT_FEM + kept.QT_MAT_MASC).eq(kept.QT_MAT).all():
        raise ValueError(f'{year}: divergência por sexo')
    tic = kept.loc[kept.CO_CINE_AREA_GERAL.eq('06')]
    if tic.empty or not tic.NO_CINE_AREA_GERAL.str.contains('Computação', regex=False).all():
        raise ValueError(f'{year}: classificação 06 inesperada')
    counts = {'ano': year, 'registros_brutos': len(df), 'apos_graduacao': len(grad),
              'excluidos_sequenciais': len(df)-len(grad),
              'excluidos_dimensao_3': int(grad.TP_DIMENSAO.eq('3').sum()),
              'excluidos_dimensao_4': int(grad.TP_DIMENSAO.eq('4').sum()),
              'apos_dimensao': len(kept), 'registros_tic': len(tic),
              'area_ausente_ou_invalida': int((~kept.CO_CINE_AREA_GERAL.str.fullmatch(r'[0-9]{2}')).sum())}
    rows = []
    for scope, part in [('total_graduacao', kept), ('computacao_tic', tic)]:
        for code, label in [('1', 'presencial'), ('2', 'ead')]:
            subset = part.loc[part.TP_MODALIDADE_ENSINO.eq(code)]
            if subset.empty:
                raise ValueError(f'{year}: grupo ausente {scope}/{label}')
            rows.append({'ano': year, 'escopo': scope, 'modalidade': label,
                         **{m.lower(): int(subset[m].sum()) for m in METRICS}})
    return rows, counts


def main():
    AUDIT.mkdir(parents=True, exist_ok=True)
    manifest_path = RAW / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    rows, filters = [], []
    for year in YEARS:
        name = f'microdados_censo_da_educacao_superior_{year}.zip'
        path = RAW / name
        sha = digest(path)
        record = manifest.get(str(year))
        if record and (record['sha256'] != sha or record['size_bytes'] != path.stat().st_size):
            raise ValueError(f'{year}: hash/tamanho divergente')
        print(f'{year}: validando ZIP e lendo CSV', flush=True)
        with zipfile.ZipFile(path) as z:
            bad = z.testzip()
            if bad is not None:
                raise ValueError(f'{year}: ZIP corrompido: {bad}')
            members = [n for n in z.namelist() if n.upper().endswith(f'CADASTRO_CURSOS_{year}.CSV')]
            if len(members) != 1:
                raise ValueError(f'{year}: CSV de cursos ambíguo ou ausente')
            with z.open(members[0]) as f:
                df = pd.read_csv(f, sep=';', encoding='latin-1', usecols=COLS,
                                 dtype=str, keep_default_na=False)
        if not record:
            manifest[str(year)] = {'year': year, 'file': name, 'url': BASE + name,
                'size_bytes': path.stat().st_size, 'sha256': sha,
                'registered_at_utc': datetime.now(timezone.utc).isoformat(),
                'acquisition_method': 'manual_browser_upload_reported_by_user',
                'downloaded_at_utc': None, 'http_headers': None, 'zip_crc_verified': True}
            write_json(manifest_path, manifest)
        result, counts = process(df, year)
        rows.extend(result)
        filters.append(counts)
        print(counts, flush=True)
        del df
    result = pd.DataFrame(rows)
    if len(result) != 24 or result.duplicated(['ano','escopo','modalidade']).any():
        raise ValueError('Grade de saída inválida')
    for m in [x.lower() for x in METRICS]:
        wide = result.pivot(index=['ano','modalidade'], columns='escopo', values=m)
        if (wide.computacao_tic > wide.total_graduacao).any():
            raise ValueError(f'{m}: TIC maior que total')
    meta = {'origem': 'INEP', 'fonte_manifest': {'path': 'data/raw/manifest.json', 'sha256': digest(manifest_path)},
        'gerado_em_utc': datetime.now(timezone.utc).isoformat(),
        'regra_agregacao': 'Graduação (1), dimensões 1 e 2 (oferta no Brasil). Dimensão 3 sem métricas de matrícula/ingresso na auditoria; dimensão 4 excluída pelo recorte geográfico. Soma por ano e modalidade; TIC = área geral 06. Não deduplicamos por código de curso.',
        'filtros': filters, 'validacao_externa': 'pendente', 'encoding': 'latin-1'}
    pd.DataFrame(filters).to_csv(AUDIT / 'etl_filters.csv', index=False)
    target = OUT / 'agregado_anual.parquet'
    temp = target.with_suffix('.parquet.part')
    result.to_parquet(temp, index=False)
    temp.replace(target)
    write_json(OUT / 'agregado_anual.meta.json', meta)
    print(result.to_string(index=False))
    print('ETL concluído: 24 linhas; reconciliação externa pendente.')


if __name__ == '__main__':
    main()
