#!/usr/bin/env python3
"""
Simple export to Google Sheets - creates a formatted CSV that's easy to import.

This script creates a Google Sheets-compatible CSV file that you can:
1. Open in Google Sheets directly (File > Import)
2. Or copy-paste into a new Google Sheet

Alternative: Use export_to_google_sheets.py for automated upload via API.
"""

import csv
from pathlib import Path


def main():
    data_dir = Path(__file__).parent.parent
    input_file = data_dir / 'data' / 'experience_signals.csv'
    output_file = data_dir / 'data' / 'experience_signals_for_google_sheets.csv'
    
    if not input_file.exists():
        print(f"ERROR: Input file not found: {input_file}")
        return
    
    # Read the CSV
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = reader.fieldnames
    
    # Write formatted CSV (Google Sheets handles this well)
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    
    print("=" * 60)
    print("CSV FILE READY FOR GOOGLE SHEETS")
    print("=" * 60)
    print(f"\n✓ Created: {output_file}")
    print(f"✓ Total rows: {len(rows)}")
    print(f"✓ Columns: {len(headers)}")
    print("\nTo import into Google Sheets:")
    print("1. Go to https://sheets.google.com")
    print("2. Click 'Blank' to create a new spreadsheet")
    print("3. Go to File > Import")
    print("4. Upload the file:")
    print(f"   {output_file}")
    print("5. Choose 'Replace spreadsheet' or 'Insert new sheet'")
    print("6. Click 'Import data'")
    print("\nAlternatively, you can:")
    print("- Open the CSV file and copy all data")
    print("- Paste into a new Google Sheet")


if __name__ == '__main__':
    main()

