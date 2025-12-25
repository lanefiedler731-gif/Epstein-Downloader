#!/usr/bin/env python3
"""
EPSTEIN FILES - COMPLETE DOWNLOADER & TEXT EXTRACTOR
=====================================================
Downloads ALL available Epstein documents and extracts readable text.
Extracts raw PDF text layers (may reveal improperly redacted content).

Sources:
1. Internet Archive - Text-searchable PDFs (Giuffre case, Black Book, Phone Book, etc.)
2. epstein-docs GitHub - 8,186 OCR'd documents with entities
3. DOJ Epstein Library - Official releases

Usage:
  python3 epstein_downloader.py --all          Download and extract everything
  python3 epstein_downloader.py --status       Show what's downloaded
  python3 epstein_downloader.py --search TERM  Search all extracted text
"""

import os
import sys
import json
import re
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional
import time
import urllib.request
import urllib.error
import importlib


def install_package(package_name: str, import_name: str = None) -> bool:
    if import_name is None:
        import_name = package_name
        
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        print(f"Installing missing dependency: {package_name}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name, "-q"])
        except subprocess.CalledProcessError:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package_name, "-q", "--break-system-packages"])
            except Exception as e:
                print(f"Failed to install {package_name}: {e}")
                return False
        
        try:
            importlib.invalidate_caches()
            importlib.import_module(import_name)
            print(f"Installed {package_name}")
            return True
        except ImportError:
            print(f"Could not import {import_name} after installation")
            return False

REQUESTS_AVAILABLE = install_package("requests")
PYMUPDF_AVAILABLE = install_package("PyMuPDF", "fitz")

if REQUESTS_AVAILABLE:
    import requests
if PYMUPDF_AVAILABLE:
    import fitz

BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / "documents"
EXTRACTED_DIR = BASE_DIR / "extracted_text"

DOCS_DIR.mkdir(exist_ok=True)
EXTRACTED_DIR.mkdir(exist_ok=True)

IA_SOURCES = {
    "giuffre_maxwell": {
        "id": "giuffre-v.-maxwell-115-cv-07433-all-documents-searchable",
        "name": "Giuffre v. Maxwell Court Case",
        "size": "1.3 GB",
        "priority": 1
    },
    "house_oversight_estate": {
        "id": "house-oversight-committe-epstein-estate-pdf",
        "name": "House Oversight - Epstein Estate (Nov 2025)",
        "size": "3+ GB",
        "priority": 2
    },
    "black_book_v2": {
        "id": "estate-production-batch-2-document-1-ocred",
        "name": "Epstein Black Book v2",
        "size": "60 MB",
        "priority": 0
    },
    "phone_book": {
        "id": "safari_202508",
        "name": "Jeffrey Epstein Phone Book (2004-2005)",
        "size": "8 MB",
        "priority": 0
    },
    "epstein_estate_alt": {
        "id": "epstein-estate-house-oversight-committee-pdf",
        "name": "Epstein Estate - House Oversight (Alt)",
        "size": "Unknown",
        "priority": 3
    }
}

GITHUB_REPO = "epstein-docs/epstein-docs.github.io"
GITHUB_FOLDERS = [f"IMAGES{str(i).zfill(3)}" for i in range(1, 13)]


def download_file(url: str, dest: Path, show_progress: bool = True) -> bool:
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        if REQUESTS_AVAILABLE:
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            total = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(dest, 'wb') as f:
                for chunk in response.iter_content(chunk_size=131072):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if show_progress and total > 0:
                            pct = downloaded / total * 100
                            mb = downloaded / 1024 / 1024
                            sys.stdout.write(f"\r    {pct:.1f}% ({mb:.1f} MB)")
                            sys.stdout.flush()
        else:
            urllib.request.urlretrieve(url, dest)
        
        if show_progress:
            print()
        return True
    except Exception as e:
        print(f"\n    Error: {e}")
        return False


def get_json(url: str) -> Optional[dict]:
    try:
        if REQUESTS_AVAILABLE:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        else:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.loads(resp.read().decode())
    except Exception as e:
        print(f"    Error fetching {url}: {e}")
        return None


def download_from_internet_archive(source_key: str) -> Dict[str, int]:
    if source_key not in IA_SOURCES:
        return {"downloaded": 0, "skipped": 0, "failed": 0}
    
    source = IA_SOURCES[source_key]
    identifier = source["id"]
    dest_dir = DOCS_DIR / "internet_archive" / source_key
    
    print(f"\n  {source['name']} ({source['size']})")
    
    metadata = get_json(f"https://archive.org/metadata/{identifier}")
    if not metadata:
        return {"downloaded": 0, "skipped": 0, "failed": 1}
    
    files = metadata.get("files", [])
    pdf_files = [f for f in files if f.get("name", "").lower().endswith(".pdf")]
    
    if not pdf_files:
        print(f"    No PDFs found")
        return {"downloaded": 0, "skipped": 0, "failed": 0}
    
    stats = {"downloaded": 0, "skipped": 0, "failed": 0}
    
    for pdf in pdf_files:
        filename = pdf["name"]
        dest_path = dest_dir / filename
        expected_size = int(pdf.get("size", 0))
        
        if dest_path.exists():
            if abs(dest_path.stat().st_size - expected_size) < 1024:
                print(f"    Exists: {filename}")
                stats["skipped"] += 1
                continue
        
        print(f"    Downloading: {filename}")
        url = f"https://archive.org/download/{identifier}/{filename}"
        
        if download_file(url, dest_path):
            stats["downloaded"] += 1
        else:
            stats["failed"] += 1
    
    return stats


def download_all_internet_archive() -> Dict[str, int]:
    print("\n" + "=" * 70)
    print("INTERNET ARCHIVE - TEXT-SEARCHABLE PDFs")
    print("=" * 70)
    
    total = {"downloaded": 0, "skipped": 0, "failed": 0}
    
    sorted_sources = sorted(IA_SOURCES.keys(), key=lambda k: IA_SOURCES[k]["priority"])
    
    for key in sorted_sources:
        stats = download_from_internet_archive(key)
        for k in total:
            total[k] += stats[k]
    
    return total


def download_github_folder(folder: str, dest_dir: Path, max_workers: int = 10) -> Dict[str, int]:
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/results/{folder}"
    
    data = get_json(api_url)
    if not data or not isinstance(data, list):
        return {"downloaded": 0, "skipped": 0, "failed": 0}
    
    json_files = [f for f in data if f["name"].endswith(".json")]
    stats = {"downloaded": 0, "skipped": 0, "failed": 0}
    
    def download_one(file_info):
        filename = file_info["name"]
        txt_filename = filename.replace(".json", ".txt")
        dest_path = dest_dir / txt_filename
        
        if dest_path.exists():
            return "skipped"
        
        try:
            json_data = get_json(file_info["download_url"])
            if not json_data:
                return "failed"
            
            full_text = json_data.get("full_text", "")
            metadata = json_data.get("document_metadata", {})
            entities = json_data.get("entities", {})
            
            lines = [
                "=" * 70,
                "DOCUMENT METADATA",
                "=" * 70,
            ]
            for k, v in metadata.items():
                lines.append(f"{k}: {v}")
            
            if entities:
                lines.append("\n" + "-" * 70)
                lines.append("ENTITIES")
                lines.append("-" * 70)
                for etype, elist in entities.items():
                    if elist:
                        if isinstance(elist, list):
                            lines.append(f"{etype}: {', '.join(str(e) for e in elist)}")
                        else:
                            lines.append(f"{etype}: {elist}")
            
            lines.append("\n" + "=" * 70)
            lines.append("FULL TEXT")
            lines.append("=" * 70)
            lines.append(full_text)
            
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            return "downloaded"
        except Exception as e:
            return "failed"
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(download_one, f) for f in json_files]
        for i, future in enumerate(as_completed(futures)):
            result = future.result()
            stats[result] += 1
            if (i + 1) % 100 == 0 or i + 1 == len(json_files):
                print(f"      {i+1}/{len(json_files)}", end="\r")
    
    print(f"      {len(json_files)} files - Downloaded: {stats['downloaded']}, Skipped: {stats['skipped']}")
    return stats


def download_all_github() -> Dict[str, int]:
    print("\n" + "=" * 70)
    print("GITHUB EPSTEIN-DOCS - 8,186 OCR'd DOCUMENTS")
    print("=" * 70)
    
    dest_dir = DOCS_DIR / "github_ocr"
    
    analyses_path = dest_dir / "analyses.json"
    if not analyses_path.exists():
        print("\n  Downloading analyses.json (AI summaries, ~10MB)...")
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/analyses.json"
        download_file(url, analyses_path)
    else:
        print("\n  analyses.json already exists")
    
    total = {"downloaded": 0, "skipped": 0, "failed": 0}
    
    for folder in GITHUB_FOLDERS:
        print(f"\n  {folder}")
        stats = download_github_folder(folder, dest_dir / folder)
        for k in total:
            total[k] += stats[k]
        time.sleep(0.5)
    
    return total


def extract_pdf_text(pdf_path: Path) -> Tuple[str, Dict]:
    if not PYMUPDF_AVAILABLE:
        try:
            result = subprocess.run(
                ["pdftotext", "-layout", str(pdf_path), "-"],
                capture_output=True, text=True, timeout=300
            )
            text = result.stdout
            pages = text.split('\f')
            return text, {
                "pages": len(pages),
                "blank_pages": sum(1 for p in pages if len(p.strip()) < 50)
            }
        except Exception as e:
            return f"Error: {e}", {"error": str(e)}
    
    doc = fitz.open(pdf_path)
    all_text = []
    page_data = []
    
    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        is_blank = len(text.strip()) < 50
        
        page_data.append({
            "page": page_num + 1,
            "chars": len(text),
            "blank": is_blank
        })
        
        all_text.append(f"--- PAGE {page_num + 1} ---\n{text}")
    
    doc.close()
    
    metadata = {
        "pages": len(page_data),
        "blank_pages": sum(1 for p in page_data if p["blank"])
    }
    
    return "\n\n".join(all_text), metadata


def extract_all_pdfs() -> Dict[str, int]:
    print("\n" + "=" * 70)
    print("EXTRACTING PDF TEXT")
    print("=" * 70)
    
    pdf_dir = DOCS_DIR / "internet_archive"
    if not pdf_dir.exists():
        print("  No PDFs to extract yet")
        return {"processed": 0, "skipped": 0, "failed": 0}
    
    pdfs = list(pdf_dir.rglob("*.pdf")) + list(pdf_dir.rglob("*.PDF"))
    stats = {"processed": 0, "skipped": 0, "failed": 0}
    
    interesting_finds = []
    
    for pdf_path in pdfs:
        rel_path = pdf_path.relative_to(pdf_dir)
        txt_path = EXTRACTED_DIR / "pdf_text" / rel_path.with_suffix(".txt")
        
        if txt_path.exists():
            print(f"  Already extracted: {rel_path.name}")
            stats["skipped"] += 1
            continue
        
        print(f"  Extracting: {rel_path.name}...")
        
        try:
            text, metadata = extract_pdf_text(pdf_path)
            
            txt_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(f"SOURCE: {pdf_path.name}\n")
                f.write(f"PAGES: {metadata.get('pages', 'unknown')}\n")
                f.write(f"BLANK PAGES: {metadata.get('blank_pages', 'unknown')}\n")
                f.write("=" * 70 + "\n\n")
                f.write(text)
            
            stats["processed"] += 1
            
            patterns = [
                (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', "phone numbers"),
                (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "emails"),
            ]
            
            for pattern, desc in patterns:
                matches = re.findall(pattern, text)
                if matches:
                    interesting_finds.append({
                        "file": str(rel_path),
                        "type": desc,
                        "samples": matches[:5]
                    })
                    break
            
            print(f"    {metadata.get('pages', '?')} pages extracted")
            
        except Exception as e:
            print(f"    Error: {e}")
            stats["failed"] += 1
    
    if interesting_finds:
        report_path = EXTRACTED_DIR / "interesting_finds.json"
        with open(report_path, 'w') as f:
            json.dump(interesting_finds, f, indent=2)
        print(f"\n  Interesting patterns saved to: {report_path}")
    
    return stats


def show_status():
    print("\n" + "=" * 70)
    print("DOWNLOAD STATUS")
    print("=" * 70)
    
    total_files = 0
    total_size = 0
    
    ia_dir = DOCS_DIR / "internet_archive"
    if ia_dir.exists():
        for source_key, source in IA_SOURCES.items():
            source_dir = ia_dir / source_key
            if source_dir.exists():
                pdfs = list(source_dir.glob("*.pdf"))
                size = sum(p.stat().st_size for p in pdfs)
                total_files += len(pdfs)
                total_size += size
                print(f"\n  {source['name']}")
                print(f"     {len(pdfs)} PDFs ({size/1024/1024:.1f} MB)")
    
    github_dir = DOCS_DIR / "github_ocr"
    if github_dir.exists():
        txts = list(github_dir.rglob("*.txt"))
        total_files += len(txts)
        print(f"\n  GitHub OCR Documents")
        print(f"     {len(txts)} text files")
    
    if EXTRACTED_DIR.exists():
        extracted = list(EXTRACTED_DIR.rglob("*.txt"))
        print(f"\n  Extracted Text")
        print(f"     {len(extracted)} files")
    
    print(f"\n  TOTAL: {total_files} files ({total_size/1024/1024:.1f} MB)")


def search_all(term: str):
    print(f"\n" + "=" * 70)
    print(f"SEARCHING FOR: {term}")
    print("=" * 70)
    
    results = []
    search_dirs = [
        DOCS_DIR / "github_ocr",
        EXTRACTED_DIR
    ]
    
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        
        for txt_file in search_dir.rglob("*.txt"):
            try:
                with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if term.lower() in content.lower():
                        matches = []
                        for i, line in enumerate(content.split('\n')):
                            if term.lower() in line.lower():
                                matches.append((i + 1, line.strip()[:100]))
                        
                        results.append({
                            "file": str(txt_file.relative_to(BASE_DIR)),
                            "matches": matches[:5]
                        })
            except Exception:
                pass
    
    if results:
        print(f"\n  Found in {len(results)} files:\n")
        for r in results[:20]:
            print(f"  {r['file']}")
            for line_num, line in r['matches'][:3]:
                print(f"     Line {line_num}: {line}")
            print()
    else:
        print(f"\n  No matches found for '{term}'")


def download_everything():
    print("\n" + "=" * 70)
    print("EPSTEIN FILES - COMPLETE DOWNLOAD")
    print("=" * 70)
    print("\nThis will download:")
    print("  Internet Archive PDFs (text-searchable, ~5GB)")
    print("  GitHub OCR documents (8,186 files)")
    print("  Extract all PDF text (may reveal hidden redactions)")
    print()
    
    total_stats = {
        "ia_downloaded": 0,
        "ia_skipped": 0,
        "github_downloaded": 0,
        "github_skipped": 0,
        "extracted": 0
    }
    
    ia_stats = download_all_internet_archive()
    total_stats["ia_downloaded"] = ia_stats["downloaded"]
    total_stats["ia_skipped"] = ia_stats["skipped"]
    
    gh_stats = download_all_github()
    total_stats["github_downloaded"] = gh_stats["downloaded"]
    total_stats["github_skipped"] = gh_stats["skipped"]
    
    ext_stats = extract_all_pdfs()
    total_stats["extracted"] = ext_stats["processed"]
    
    print("\n" + "=" * 70)
    print("COMPLETE!")
    print("=" * 70)
    print(f"\n  Internet Archive: {total_stats['ia_downloaded']} downloaded, {total_stats['ia_skipped']} skipped")
    print(f"  GitHub Documents: {total_stats['github_downloaded']} downloaded, {total_stats['github_skipped']} skipped")
    print(f"  PDFs Extracted: {total_stats['extracted']}")
    print(f"\n  Files saved to: {DOCS_DIR}")
    print(f"  Extracted text: {EXTRACTED_DIR}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Download ALL Epstein documents and extract text',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 epstein_downloader.py --all              Download everything
  python3 epstein_downloader.py --status           Show download status
  python3 epstein_downloader.py --search "trump"   Search all documents
  python3 epstein_downloader.py --ia-only          Only Internet Archive PDFs
  python3 epstein_downloader.py --github-only      Only GitHub OCR docs
  python3 epstein_downloader.py --extract          Only extract PDF text
        """
    )
    
    parser.add_argument('--all', action='store_true', help='Download and extract everything')
    parser.add_argument('--status', action='store_true', help='Show what\'s downloaded')
    parser.add_argument('--search', type=str, metavar='TERM', help='Search all documents')
    parser.add_argument('--ia-only', action='store_true', help='Only download from Internet Archive')
    parser.add_argument('--github-only', action='store_true', help='Only download from GitHub')
    parser.add_argument('--extract', action='store_true', help='Only extract PDF text')
    
    args = parser.parse_args()
    
    if args.all:
        download_everything()
    elif args.status:
        show_status()
    elif args.search:
        search_all(args.search)
    elif args.ia_only:
        download_all_internet_archive()
    elif args.github_only:
        download_all_github()
    elif args.extract:
        extract_all_pdfs()
    else:
        parser.print_help()
        print("\n" + "=" * 70)
        print("QUICK START: python3 epstein_downloader.py --all")
        print("=" * 70)


if __name__ == "__main__":
    main()
