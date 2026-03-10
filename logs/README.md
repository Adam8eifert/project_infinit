# Logy

Všechny runtime logy projektu jsou soustředěné v adresáři `logs/`.

## Kde co najít

- `logs/imports/csv_import.log` — import článků z CSV do tabulky `articles`
- `logs/imports/document_import.log` — import akademických dokumentů (PDF, DOC, DOCX)
- `logs/imports/social_media_import.log` — import sociálních sítí
- `logs/pipeline/main.log` — hlavní orchestrace ETL (`main.py`)

## Poznámky

- Importéry zapisují současně i do terminálu.
- Log soubory se automaticky rotují (default: 10 MB na soubor, 5 záloh).
- Limity můžeš změnit přes proměnné prostředí `PROJECT_LOG_MAX_BYTES` a `PROJECT_LOG_BACKUP_COUNT`.
- Staré soubory jako `import_log.txt`, `document_import_log.txt`, `pdf_import_log.txt` nebo staré `pipeline*.log` jsou uložené v `logs/legacy/`.
- Nové běhy pipeline už zapisují do `logs/imports/`.
