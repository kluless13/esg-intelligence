#!/usr/bin/env python3
"""Temporary script to collect documents for the first 10 major companies."""
import subprocess

companies = ["ANZ", "BHP", "CBA", "CSL", "FMG", "GMG", "MQG", "NAB", "ORG"]

for i, ticker in enumerate(companies, 1):
    print(f"\n{'='*80}")
    print(f"[{i}/{len(companies)}] Processing {ticker}...")
    print('='*80)

    result = subprocess.run(
        ["python", "scripts/02b_find_via_website.py", "--ticker", ticker],
        capture_output=False,
        text=True
    )

    if result.returncode != 0:
        print(f"  ⚠ Error processing {ticker}")
    else:
        print(f"  ✓ {ticker} complete")

print("\n" + "="*80)
print("All companies processed!")
print("="*80)
