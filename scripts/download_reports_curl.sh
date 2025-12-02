#!/bin/bash
#
# Download ESG reports using curl
#
# Usage:
#   ./scripts/download_reports_curl.sh              # Download all
#   ./scripts/download_reports_curl.sh CBA          # Single company
#   ./scripts/download_reports_curl.sh --dry-run    # Preview only

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$PROJECT_ROOT/data"
REPORT_LINKS_FILE="$DATA_DIR/report_links.json"
EXCEL_DIR="$DATA_DIR/excel"
PDF_DIR="$DATA_DIR/pdfs"

# Parse arguments
DRY_RUN=false
TICKER=""

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            TICKER="$arg"
            shift
            ;;
    esac
done

# Counter variables
TOTAL=0
DOWNLOADED=0
SKIPPED=0
FAILED=0

echo "============================================================"
echo "ESG Report Downloader (curl mode)"
echo "============================================================"
echo "Mode: $([ "$DRY_RUN" = true ] && echo 'DRY RUN' || echo 'DOWNLOAD')"
echo "============================================================"
echo ""

# Function to download a file
download_file() {
    local url="$1"
    local save_path="$2"
    local filename=$(basename "$save_path")

    if [ "$DRY_RUN" = true ]; then
        echo "  🔍 Would download: $filename"
        echo "      → $save_path"
        return 0
    fi

    # Check if already exists
    if [ -f "$save_path" ]; then
        echo "  ⏭️  Already exists: $filename"
        ((SKIPPED++))
        return 0
    fi

    echo "  📥 Downloading: $filename"

    # Create directory if needed
    mkdir -p "$(dirname "$save_path")"

    # Download with curl
    if curl -L \
        -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
        -H "Accept: */*" \
        --max-time 120 \
        --retry 3 \
        --retry-delay 2 \
        --fail \
        --silent \
        --show-error \
        --output "$save_path" \
        "$url" 2>/dev/null; then

        local size=$(ls -lh "$save_path" | awk '{print $5}')
        echo "  ✅ Saved: $filename ($size)"
        ((DOWNLOADED++))
        sleep 2  # Rate limiting
        return 0
    else
        echo "  ❌ Failed to download"
        ((FAILED++))
        # Remove partial file if exists
        [ -f "$save_path" ] && rm "$save_path"
        return 1
    fi
}

# CBA
if [ -z "$TICKER" ] || [ "$TICKER" = "CBA" ]; then
    echo "📊 CBA - Commonwealth Bank of Australia"
    TOTAL=$((TOTAL + 7))

    download_file \
        "https://www.commbank.com.au/content/dam/commbank-assets/investors/docs/results/1h25/2025-Half-Year-Sustainability-Performance-Metrics-and-Disclosures.xlsx" \
        "$EXCEL_DIR/CBA/2025-Half-Year-Sustainability-Performance-Metrics-and-Disclosures.xlsx"

    download_file \
        "https://www.commbank.com.au/content/dam/commbank-assets/investors/docs/results/fy24/2024-Sustainability-Performance-Metrics-and-Disclosures.xlsx" \
        "$EXCEL_DIR/CBA/2024-Sustainability-Performance-Metrics-and-Disclosures.xlsx"

    download_file \
        "https://www.commbank.com.au/content/dam/commbank-assets/investors/docs/results/fy23/2023-Sustainability-Performance-Metrics-and-Disclosures.xlsx" \
        "$EXCEL_DIR/CBA/2023-Sustainability-Performance-Metrics-and-Disclosures.xlsx"

    download_file \
        "https://www.commbank.com.au/content/dam/commbank/about-us/shareholders/pdfs/results/fy22/cba-fy22-sustainability-performance-metrics-and-disclosures.xlsx" \
        "$EXCEL_DIR/CBA/cba-fy22-sustainability-performance-metrics-and-disclosures.xlsx"

    download_file \
        "https://www.commbank.com.au/content/dam/commbank-assets/investors/docs/results/fy24/CBA-2024-Climate-Report.pdf" \
        "$PDF_DIR/CBA/CBA-2024-Climate-Report.pdf"

    download_file \
        "https://www.commbank.com.au/content/dam/commbank-assets/investors/docs/results/fy24/CBA-2024-Sustainability-Reporting-pages-20-47-of-the-Annual-Report.pdf" \
        "$PDF_DIR/CBA/CBA-2024-Sustainability-Reporting-pages-20-47-of-the-Annual-Report.pdf"

    download_file \
        "https://www.commbank.com.au/content/dam/commbank-assets/investors/docs/results/fy23/2023-Sustainability-Reporting-pages-18-39-of-the-Annual-Report.pdf" \
        "$PDF_DIR/CBA/2023-Sustainability-Reporting-pages-18-39-of-the-Annual-Report.pdf"

    echo ""
fi

# BHP
if [ -z "$TICKER" ] || [ "$TICKER" = "BHP" ]; then
    echo "📊 BHP - BHP Group Limited"
    TOTAL=$((TOTAL + 8))

    download_file \
        "https://www.bhp.com/-/media/documents/investors/annual-reports/2025/bhp-esg-standards-and-databook-2025.xlsx" \
        "$EXCEL_DIR/BHP/bhp-esg-standards-and-databook-2025.xlsx"

    download_file \
        "https://www.bhp.com/-/media/documents/investors/annual-reports/2024/240827_esgstandardsanddatabook2024.xlsx" \
        "$EXCEL_DIR/BHP/240827_esgstandardsanddatabook2024.xlsx"

    download_file \
        "https://www.bhp.com/-/media/documents/investors/annual-reports/2023/230822_esgstandardsanddatabook2023.xlsx" \
        "$EXCEL_DIR/BHP/230822_esgstandardsanddatabook2023.xlsx"

    download_file \
        "https://www.bhp.com/-/media/documents/investors/annual-reports/2022/220906_bhpesgstandardsanddatabook2022.xlsx" \
        "$EXCEL_DIR/BHP/220906_bhpesgstandardsanddatabook2022.xlsx"

    download_file \
        "https://www.bhp.com/-/media/documents/investors/annual-reports/2024/240827_bhpannualreport2024.pdf" \
        "$PDF_DIR/BHP/240827_bhpannualreport2024.pdf"

    download_file \
        "https://www.bhp.com/-/media/documents/investors/annual-reports/2024/240827_bhpclimatetransitionactionplan2024.pdf" \
        "$PDF_DIR/BHP/240827_bhpclimatetransitionactionplan2024.pdf"

    download_file \
        "https://www.bhp.com/-/media/documents/investors/annual-reports/2023/230822_bhpannualreport2023.pdf" \
        "$PDF_DIR/BHP/230822_bhpannualreport2023.pdf"

    download_file \
        "https://www.bhp.com/-/media/documents/investors/annual-reports/2022/220906_bhpannualreport2022.pdf" \
        "$PDF_DIR/BHP/220906_bhpannualreport2022.pdf"

    echo ""
fi

# NAB
if [ -z "$TICKER" ] || [ "$TICKER" = "NAB" ]; then
    echo "📊 NAB - National Australia Bank Limited"
    TOTAL=$((TOTAL + 6))

    download_file \
        "https://www.nab.com.au/content/dam/nab/documents/reports/corporate/2025-sustainability-data-pack.xlsx" \
        "$EXCEL_DIR/NAB/2025-sustainability-data-pack.xlsx"

    download_file \
        "https://www.nab.com.au/content/dam/nab/documents/reports/corporate/2024-sustainability-data-pack.xlsx" \
        "$EXCEL_DIR/NAB/2024-sustainability-data-pack.xlsx"

    download_file \
        "https://www.nab.com.au/content/dam/nab/documents/reports/corporate/2023-sustainability-data-pack.xlsx" \
        "$EXCEL_DIR/NAB/2023-sustainability-data-pack.xlsx"

    download_file \
        "https://www.nab.com.au/content/dam/nab/documents/reports/corporate/2024-annual-report.pdf" \
        "$PDF_DIR/NAB/2024-annual-report.pdf"

    download_file \
        "https://www.nab.com.au/content/dam/nab/documents/reports/corporate/2024-climate-report.pdf" \
        "$PDF_DIR/NAB/2024-climate-report.pdf"

    download_file \
        "https://www.nab.com.au/content/dam/nab/documents/reports/corporate/2023-annual-report.pdf" \
        "$PDF_DIR/NAB/2023-annual-report.pdf"

    download_file \
        "https://www.nab.com.au/content/dam/nab/documents/reports/corporate/2022-annual-report.pdf" \
        "$PDF_DIR/NAB/2022-annual-report.pdf"

    echo ""
fi

# Add remaining companies...
# (I'll add a summary for now)

echo "============================================================"
echo "SUMMARY"
echo "============================================================"
echo "Total files:  $TOTAL"
echo "Downloaded:   $DOWNLOADED"
echo "Skipped:      $SKIPPED"
echo "Failed:       $FAILED"
echo "============================================================"
echo ""

[ "$DRY_RUN" = true ] && echo "This was a dry run. Run without --dry-run to download files."

exit 0
