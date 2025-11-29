"""
Document Text Extraction using Docling

This module uses IBM's Docling library for extracting text and tables from
ESG documents (PDF, DOCX, HTML) with high accuracy on table structures.

Docling was benchmarked at 97.9% accuracy on sustainability report tables!
https://github.com/docling-project/docling

Key benefits over pymupdf:
- AI-powered layout analysis preserves reading order
- Table structure recognition (TableFormer)
- Built-in OCR for scanned documents
- Clean Markdown output perfect for LLM analysis
"""

import logging
import time
from pathlib import Path
from typing import Dict, Optional, List
import requests
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Request headers for direct URL fetching
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}


def fetch_with_playwright(url: str) -> str:
    """
    Fetch URL content using Playwright with stealth mode to avoid bot detection.

    ListCorp blocks direct HTTP requests with 403 Forbidden, so we need
    to use a headless browser with stealth mode.

    Args:
        url: URL to fetch

    Returns:
        HTML content as string

    Raises:
        Exception if fetch fails
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            stealth_sync(page)

            logger.info(f"Fetching with Playwright: {url[:80]}...")
            page.goto(url, wait_until='networkidle', timeout=30000)
            time.sleep(2)  # Wait for JS to render

            html_content = page.content()
            browser.close()

            return html_content
    except Exception as e:
        logger.error(f"Playwright fetch failed: {e}")
        raise

# Lazy load Docling converter (downloads models on first use)
_docling_converter = None


def get_docling_converter():
    """
    Get or create the Docling DocumentConverter (singleton pattern).
    
    First call will download AI models (~1-2GB), which takes a few minutes.
    Subsequent calls reuse the same converter for efficiency.
    """
    global _docling_converter
    
    if _docling_converter is None:
        logger.info("Initializing Docling converter (first run downloads models ~1-2GB)...")
        try:
            from docling.document_converter import DocumentConverter
            _docling_converter = DocumentConverter()
            logger.info("✓ Docling converter initialized successfully")
        except ImportError:
            logger.error("Docling not installed. Run: pip install docling>=2.63.0")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Docling: {e}")
            raise
    
    return _docling_converter


def extract_with_docling(source: str) -> Dict:
    """
    Extract text and tables from a document using Docling.

    Args:
        source: URL or file path to the document

    Returns:
        Dict with:
            - text_content: Extracted text in Markdown format (preserves tables)
            - extraction_status: 'success', 'partial', or 'failed'
            - extraction_method: 'docling'
            - char_count: Length of extracted text
            - table_count: Number of tables found
            - error: Error message if failed
    """
    try:
        converter = get_docling_converter()

        logger.info(f"Extracting with Docling: {source[:80]}...")
        start_time = time.time()

        # For ListCorp URLs, fetch with Playwright first (bypasses bot detection)
        # then save to temp file for Docling to process
        if 'listcorp.com' in source and source.startswith('http'):
            try:
                html_content = fetch_with_playwright(source)
                # Save to temp file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                    f.write(html_content)
                    temp_path = f.name
                # Convert from temp file
                result = converter.convert(temp_path)
                # Clean up
                Path(temp_path).unlink(missing_ok=True)
            except Exception as e:
                logger.error(f"Failed to fetch with Playwright for Docling: {e}")
                raise
        else:
            # Convert document directly (works for PDFs, direct file paths, etc.)
            result = converter.convert(source)
        
        # Export to Markdown (preserves table structure)
        markdown_text = result.document.export_to_markdown()
        
        # Count tables
        table_count = len(result.document.tables) if hasattr(result.document, 'tables') else 0
        
        elapsed = time.time() - start_time
        char_count = len(markdown_text) if markdown_text else 0
        
        logger.info(f"  ✓ Extracted {char_count:,} chars, {table_count} tables in {elapsed:.1f}s")
        
        # Check if we got meaningful content
        if not markdown_text or char_count < 100:
            return {
                "text_content": markdown_text,
                "extraction_status": "partial",
                "extraction_method": "docling",
                "char_count": char_count,
                "table_count": table_count,
                "error": "Extracted text too short - may be image-only or empty document"
            }
        
        return {
            "text_content": markdown_text,
            "extraction_status": "success",
            "extraction_method": "docling",
            "char_count": char_count,
            "table_count": table_count,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"  ✗ Docling extraction failed: {e}")
        return {
            "text_content": None,
            "extraction_status": "failed",
            "extraction_method": "docling",
            "char_count": 0,
            "table_count": 0,
            "error": str(e)
        }


def extract_with_beautifulsoup(url: str) -> Dict:
    """
    Fallback extraction for HTML pages using BeautifulSoup.

    Useful when Docling fails or for simple HTML pages where
    the full text is already in the HTML.

    Uses Playwright to fetch content (bypasses bot detection).

    Args:
        url: URL to the HTML page

    Returns:
        Same format as extract_with_docling()
    """
    try:
        from bs4 import BeautifulSoup

        logger.info(f"Extracting with BeautifulSoup: {url[:80]}...")

        # Use Playwright to fetch page content (bypasses 403 Forbidden)
        html_content = fetch_with_playwright(url)

        soup = BeautifulSoup(html_content, 'lxml')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()
        
        # Try to find main content area (ListCorp specific)
        # ListCorp typically has announcement content in specific divs
        content = None
        
        # Try common content selectors
        for selector in ['article', '.announcement-content', '.content', 'main', '.main-content']:
            content = soup.select_one(selector)
            if content:
                break
        
        # Fallback to body if no specific content found
        if not content:
            content = soup.body
        
        if content:
            text = content.get_text(separator='\n', strip=True)
            
            # Clean up excessive whitespace
            import re
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r' {2,}', ' ', text)
            
            char_count = len(text)
            
            if char_count < 100:
                return {
                    "text_content": text,
                    "extraction_status": "partial",
                    "extraction_method": "beautifulsoup",
                    "char_count": char_count,
                    "table_count": 0,
                    "error": "Very little text content found"
                }
            
            return {
                "text_content": text,
                "extraction_status": "success",
                "extraction_method": "beautifulsoup",
                "char_count": char_count,
                "table_count": len(soup.find_all('table')),
                "error": None
            }
        
        return {
            "text_content": None,
            "extraction_status": "failed",
            "extraction_method": "beautifulsoup",
            "char_count": 0,
            "table_count": 0,
            "error": "Could not find content in HTML"
        }
        
    except Exception as e:
        logger.error(f"  ✗ BeautifulSoup extraction failed: {e}")
        return {
            "text_content": None,
            "extraction_status": "failed",
            "extraction_method": "beautifulsoup",
            "char_count": 0,
            "table_count": 0,
            "error": str(e)
        }


def extract_with_pymupdf(pdf_path: str) -> Dict:
    """
    Fallback PDF extraction using PyMuPDF (fitz).
    
    Use this when Docling fails on a specific PDF.
    Note: This won't preserve table structure as well as Docling.
    
    Args:
        pdf_path: Path to PDF file or URL
        
    Returns:
        Same format as extract_with_docling()
    """
    try:
        import fitz  # pymupdf
        
        logger.info(f"Extracting with PyMuPDF: {pdf_path}")
        
        # If URL, download first
        if pdf_path.startswith('http'):
            response = requests.get(pdf_path, headers=HEADERS, timeout=60)
            response.raise_for_status()
            doc = fitz.open(stream=response.content, filetype="pdf")
        else:
            doc = fitz.open(pdf_path)
        
        text_parts = []
        for page_num, page in enumerate(doc, 1):
            page_text = page.get_text()
            if page_text.strip():
                text_parts.append(f"--- Page {page_num} ---\n{page_text}")
        
        doc.close()
        
        text = "\n\n".join(text_parts)
        char_count = len(text)
        
        if char_count < 100:
            return {
                "text_content": text,
                "extraction_status": "partial",
                "extraction_method": "pymupdf",
                "char_count": char_count,
                "table_count": 0,
                "error": "Very little text extracted - may be scanned/image PDF"
            }
        
        return {
            "text_content": text,
            "extraction_status": "success",
            "extraction_method": "pymupdf",
            "char_count": char_count,
            "table_count": 0,  # PyMuPDF doesn't detect tables
            "error": None
        }
        
    except Exception as e:
        logger.error(f"  ✗ PyMuPDF extraction failed: {e}")
        return {
            "text_content": None,
            "extraction_status": "failed",
            "extraction_method": "pymupdf",
            "char_count": 0,
            "table_count": 0,
            "error": str(e)
        }


def extract_document_text(url: str, prefer_docling: bool = True) -> Dict:
    """
    Extract text from a document URL with automatic fallback.
    
    Strategy:
    1. Try Docling first (best for PDFs with tables)
    2. If Docling fails on HTML, try BeautifulSoup
    3. If all else fails, try PyMuPDF for PDFs
    
    Args:
        url: URL to the document
        prefer_docling: If True, try Docling first (recommended)
        
    Returns:
        Dict with extraction results (same format as individual extractors)
    """
    # Determine document type from URL
    parsed = urlparse(url)
    path_lower = parsed.path.lower()
    
    is_pdf = path_lower.endswith('.pdf')
    is_html = path_lower.endswith('.html') or path_lower.endswith('.htm') or not path_lower.split('/')[-1].count('.')
    
    # Strategy 1: Try Docling first (works great on both PDF and HTML)
    if prefer_docling:
        result = extract_with_docling(url)
        
        if result["extraction_status"] == "success":
            return result
        
        logger.info(f"  Docling returned {result['extraction_status']}, trying fallback...")
    
    # Strategy 2: For HTML pages, try BeautifulSoup
    if is_html:
        result = extract_with_beautifulsoup(url)
        if result["extraction_status"] == "success":
            return result
    
    # Strategy 3: For PDFs, try PyMuPDF as last resort
    if is_pdf:
        result = extract_with_pymupdf(url)
        if result["extraction_status"] == "success":
            return result
    
    # If we got here with a partial result from earlier, return that
    if prefer_docling:
        first_result = extract_with_docling(url)
        if first_result["text_content"]:
            return first_result
    
    # Nothing worked
    return {
        "text_content": None,
        "extraction_status": "failed",
        "extraction_method": "all_failed",
        "char_count": 0,
        "table_count": 0,
        "error": "All extraction methods failed"
    }


def extract_tables_as_dataframes(source: str) -> List[Dict]:
    """
    Extract tables from a document as pandas DataFrames.
    
    This is useful if you want to directly analyze numerical data
    without sending to an LLM.
    
    Args:
        source: URL or file path to document
        
    Returns:
        List of dicts with 'page', 'dataframe' keys
    """
    try:
        import pandas as pd
        
        converter = get_docling_converter()
        result = converter.convert(source)
        
        tables = []
        for i, table in enumerate(result.document.tables):
            try:
                df = table.export_to_dataframe()
                page_no = table.prov[0].page_no if table.prov else None
                tables.append({
                    "index": i,
                    "page": page_no,
                    "dataframe": df
                })
            except Exception as e:
                logger.warning(f"Failed to convert table {i} to DataFrame: {e}")
        
        return tables
        
    except Exception as e:
        logger.error(f"Table extraction failed: {e}")
        return []


# Test function
if __name__ == "__main__":
    print("=" * 70)
    print("Testing Document Text Extraction")
    print("=" * 70)
    
    # Test with a known ListCorp ESG report page
    test_url = "https://www.listcorp.com/asx/xro/xero-limited/news/fy25-sustainability-report-3189699.html"
    
    print(f"\nTest URL: {test_url}\n")
    
    result = extract_document_text(test_url)
    
    print(f"Status: {result['extraction_status']}")
    print(f"Method: {result['extraction_method']}")
    print(f"Characters: {result['char_count']:,}")
    print(f"Tables: {result.get('table_count', 'N/A')}")
    
    if result['error']:
        print(f"Error: {result['error']}")
    
    if result['text_content']:
        print(f"\nFirst 500 characters:")
        print("-" * 50)
        print(result['text_content'][:500])
        print("-" * 50)
        print(f"... ({result['char_count'] - 500:,} more characters)")
