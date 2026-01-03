#!/usr/bin/env python3
"""
Export experience_signals.csv to Google Sheets.

Requirements:
1. Install gspread: pip install gspread
2. Set up Google Cloud credentials:
   - Go to https://console.cloud.google.com/
   - Create a new project or select existing
   - Enable Google Sheets API
   - Create a Service Account
   - Download the JSON key file
   - Set GOOGLE_APPLICATION_CREDENTIALS environment variable or pass path to script
"""

import csv
import os
import sys
from pathlib import Path

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    print("ERROR: gspread not installed. Install it with:")
    print("  pip install gspread")
    sys.exit(1)


def load_csv_data(filepath):
    """Load CSV data into a list of dictionaries."""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        data = list(reader)
    return data, reader.fieldnames


def authenticate_google_sheets(credentials_path=None):
    """Authenticate with Google Sheets API."""
    if credentials_path:
        creds = Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
    elif os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        creds = Credentials.from_service_account_file(
            os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
    else:
        print("ERROR: No credentials found.")
        print("Please either:")
        print("  1. Set GOOGLE_APPLICATION_CREDENTIALS environment variable")
        print("  2. Pass --credentials path/to/credentials.json")
        sys.exit(1)
    
    return gspread.authorize(creds)


def create_or_update_sheet(gc, sheet_name, data, headers):
    """Create a new Google Sheet or update existing one."""
    try:
        # Try to open existing sheet
        sheet = gc.open(sheet_name)
        worksheet = sheet.sheet1
        print(f"✓ Found existing sheet: {sheet_name}")
    except gspread.exceptions.SpreadsheetNotFound:
        # Create new sheet
        sheet = gc.create(sheet_name)
        worksheet = sheet.sheet1
        print(f"✓ Created new sheet: {sheet_name}")
    
    # Clear existing data
    worksheet.clear()
    
    # Add headers
    worksheet.append_row(headers)
    
    # Add data rows
    for row in data:
        row_values = [row.get(header, '') for header in headers]
        worksheet.append_row(row_values)
    
    # Format header row
    worksheet.format('1:1', {'textFormat': {'bold': True}})
    
    # Auto-resize columns
    worksheet.columns_auto_resize(0, len(headers))
    
    return sheet


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Export experience_signals.csv to Google Sheets')
    parser.add_argument('--credentials', help='Path to Google service account credentials JSON file')
    parser.add_argument('--sheet-name', default='Restaurant Experience Signals', 
                       help='Name of the Google Sheet (default: Restaurant Experience Signals)')
    parser.add_argument('--csv-file', default='data/experience_signals.csv',
                       help='Path to CSV file to export (default: data/experience_signals.csv)')
    
    args = parser.parse_args()
    
    # Load CSV data
    data_dir = Path(__file__).parent.parent
    csv_path = data_dir / args.csv_file
    
    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}")
        sys.exit(1)
    
    print(f"Reading {csv_path}...")
    data, headers = load_csv_data(csv_path)
    print(f"✓ Loaded {len(data)} rows")
    
    # Authenticate
    print("\nAuthenticating with Google Sheets API...")
    try:
        gc = authenticate_google_sheets(args.credentials)
        print("✓ Authentication successful")
    except Exception as e:
        print(f"ERROR: Authentication failed: {e}")
        print("\nTo set up credentials:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a project and enable Google Sheets API")
        print("3. Create a Service Account and download JSON key")
        print("4. Run: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json")
        sys.exit(1)
    
    # Create or update sheet
    print(f"\nUploading to Google Sheets: {args.sheet_name}...")
    try:
        sheet = create_or_update_sheet(gc, args.sheet_name, data, headers)
        print(f"✓ Upload complete!")
        print(f"\n📊 Sheet URL: {sheet.url}")
        print(f"📋 Share this link to view the sheet")
    except Exception as e:
        print(f"ERROR: Failed to upload: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

