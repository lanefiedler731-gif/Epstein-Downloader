# Epstein Files – Complete Downloader & Text Extractor

A Python tool that **downloads all publicly available Jeffrey Epstein–related document collections** from multiple sources and extracts searchable text from them.

This project aggregates court records, document dumps, and OCR archives into a single local dataset, then extracts raw text layers from PDFs to enable full-text search and analysis.

---

## Features

- Downloads **all known public Epstein document collections** from:
  - Internet Archive (court filings, black books, phone books, oversight releases)
  - GitHub OCR archive (8,186 structured documents with metadata & entities)
- Extracts **raw text layers from PDFs**
  - Uses PyMuPDF when available
  - Falls back to `pdftotext` if needed
- Preserves document structure and metadata
- Generates searchable `.txt` files
- Detects potentially interesting patterns (emails, phone numbers)
- Unified search across all downloaded material
- Automatically installs missing Python dependencies

---

## Data Sources

### Internet Archive
Text-searchable PDF collections, including:
- Giuffre v. Maxwell court documents
- House Oversight Committee releases
- Epstein Black Book (multiple versions)
- Epstein phone books

---

## Requirements

- Python **3.8+**
- Internet connection
- Disk space:
  - ~5–7 GB for PDFs
  - Additional space for extracted text

### Optional (Recommended)
- PyMuPDF (auto-installed)
- `pdftotext` (system fallback)

---

## Installation

```bash
git clone https://github.com/lanefiedler731-gif/Epstein-Downloader.git
cd Epstein-Downloader
python3 epstein_downloader.py --all
```

Dependencies are installed automatically if missing.

---

## Usage

Download everything:
```bash
python3 epstein_downloader.py --all
```

Show status:
```bash
python3 epstein_downloader.py --status
```

Search all documents:
```bash
python3 epstein_downloader.py --search "keyword"
```

Only Internet Archive:
```bash
python3 epstein_downloader.py --ia-only
```

Only GitHub OCR:
```bash
python3 epstein_downloader.py --github-only
```

Extract PDF text only:
```bash
python3 epstein_downloader.py --extract
```

---

## Output Structure

```text
documents/
├── internet_archive/
├── github_ocr/
│   └── analyses.json
extracted_text/
├── pdf_text/
└── interesting_finds.json
```

---

## Text Extraction Notes

- Extracts **raw PDF text layers**
- Improper redactions may still expose underlying text
- Blank pages are flagged
- No OCR is performed on image-only PDFs

---

## Legal & Ethical Notice

- Only publicly available documents are accessed
- No private or restricted material is obtained
- Users are responsible for interpretation and use
- Intended for research, journalism, and archival transparency

---

## Disclaimer

This software makes **no claims** regarding accuracy, completeness, or interpretation of the documents.  
It is a data aggregation and text extraction utility only.

---

## License

Without a license, all rights are reserved.
