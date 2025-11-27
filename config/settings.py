"""
Configuration settings for ESG Intelligence Platform
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "esg_intel.db"
PDF_DIR = DATA_DIR / "pdfs"
COMPANIES_CSV = DATA_DIR / "companies.csv"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
PDF_DIR.mkdir(exist_ok=True)

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Scraping Configuration
REQUEST_DELAY = 2  # seconds between requests to be polite to ListCorp
LISTCORP_BASE = "https://www.listcorp.com"

# Target financial years for ESG reports (most recent first)
TARGET_YEARS = ["FY2025", "FY2024", "FY2023", "FY2022", "FY2021"]

# User agent for requests (appears as a normal browser)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}
