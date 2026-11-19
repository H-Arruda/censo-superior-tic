# Censo Superior TIC (2019–2024)

Análise exploratória da evolução da formação superior em Computação e Tecnologias da Informação e Comunicação no Brasil com microdados do INEP.

**Autores:** [preencher os dois nomes]  
**Instituição:** [preencher]  
**Disciplina:** Linguagem de Programação — Análise e Visualização de Dados com Python  
**Professor:** [preencher]  
**Semestre:** 2026.2

**Palavras-chave:** ensino superior; Computação e TIC; educação a distância; participação feminina; engenharia de dados; INEP.

## Perguntas de pesquisa

1. Como evoluíram as matrículas em TIC, em números absolutos e em proporção ao total da graduação?
2. Como evoluiu a participação do EaD nas matrículas e nos ingressos em TIC?
3. Como evoluiu a participação feminina nas matrículas em TIC por modalidade?

## Fonte e recorte

[Microdados do Censo da Educação Superior — INEP](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-da-educacao-superior). Período de 2019 a 2024; graduação ofertada no Brasil; área geral 06 da Cine Brasil para TIC. As dimensões 3 e 4 são excluídas das métricas estudadas conforme as regras documentadas em `data/data_dictionary.md`.

## Reprodução

Python 3.12.3 de referência. Execute na raiz do repositório, em Bash:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m src.download
```

Se a aquisição automática falhar por conectividade ou certificado TLS, baixe os seis ZIPs pela página oficial, em ambiente que valide o HTTPS, sem extrair, e coloque-os em `data/raw/` com nomes `microdados_censo_da_educacao_superior_ANO.zip`. Não desative a validação TLS. O ETL registra aquisições manuais e verifica arquivos contra o manifesto existente; arquivos divergentes não devem ser substituídos sem investigação.

```bash
mkdir -p data/processed/audit
set -o pipefail
python -m src.integrity | tee data/processed/audit/integrity.log
python -m src.inventory | tee data/processed/audit/inventory.log
python -m src.schema | tee data/processed/audit/schema.log
python -m src.profile | tee data/processed/audit/profile.log
python -m src.etl | tee data/processed/audit/etl.log
```

Execute `notebooks/analise_exploratoria.ipynb` após gerar `data/processed/agregado_anual.parquet` e `data/processed/agregado_anual.meta.json`. A publicação será servida a partir de `docs/` no GitHub Pages. [Acrescentar comando final de gráficos e link do artigo após integrar a análise.]

## Estrutura

- `src/`: módulos de aquisição, inventário, inspeção de dicionários, perfil e ETL.
- `data/raw/`: arquivos oficiais locais (não versionados) e manifesto de procedência.
- `data/processed/`: resultados gerados pelo pipeline e relatórios de auditoria.
- `data/data_dictionary.md`: metadados das variáveis originais e derivadas.
- `notebooks/`: análise exploratória.
- `docs/`: artigo e visualizações para publicação.

## Declaração FAIR

- **Localizável:** descrição, palavras-chave, autoria e fonte oficial no README.
- **Acessível:** código e instruções disponíveis no repositório público; dados originais obtidos na fonte oficial sem credenciais pagas.
- **Interoperável:** saída Parquet, relatórios CSV e metadados JSON, com dicionário de dados.
- **Reutilizável:** código autoral sob licença MIT, dependências congeladas e regras de transformação documentadas. A licença do código não se estende aos dados de terceiros; observar os termos aplicáveis do INEP.

## Validação e limitações

A execução dos seis anos gerou 24 linhas. O manifesto registra SHA-256 e a verificação CRC dos ZIPs; a aquisição manual não registrou cabeçalhos HTTP nem instante exato de download. A auditoria verificou os domínios e a identidade entre as contagens por sexo nos registros retidos. A reconciliação externa integral, a conferência de MD5 oficiais e a auditoria de chaves/reclassificações permanecem pendentes. Matrículas não equivalem a pessoas únicas; o estudo é descritivo e não identifica efeitos causais.
