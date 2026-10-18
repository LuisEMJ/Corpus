# Corpus


Python script that processes news articles saved as HTML and builds a sentence-segmented text corpus, along with an Excel database.

### What it does

- Recursively finds folders that contain `.html` files.
- Extracts the title, subtitle, category, date and paragraphs of each article.
- Splits the text into sentences and removes copyright notices.
- Sorts articles by date, from oldest to newest.
- Creates a `Noticias/` subfolder in each folder with:
  - One `.txt` file per article, in XML-like format (`<DOC>`, `<HEAD>`, `<TEXT>`, `<s>`).
  - `Noticias_Juntas.txt`: all articles from the folder in a single file.
  - `CORP-*.txt`: corpus in XML format.
  - `CORP-SEG-*.txt`: segmented corpus in `{{number,wordcount}}` format.
  - `CORP-BLANCO-*.txt`: plain-text corpus.
- Updates `Base_de_Datos_Noticias.xlsx` with new articles.

### Requirements

```bash
pip install pandas beautifulsoup4 openpyxl
```

### Usage

1. Edit the `ruta_raiz` and `ruta_excel` variables in `procesar_noticias.py` to match your paths.
2. Run:

```bash
python procesar_noticias.py
```

> Close the Excel file before running the script.
