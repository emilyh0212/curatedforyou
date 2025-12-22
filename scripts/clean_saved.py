#!/usr/bin/env python3
"""
Clean Google Takeout "Saved" CSV exports for restaurant recommendation chatbot.

This script processes CSV files from Google Takeout, extracts restaurant data,
adds metadata columns, cleans and deduplicates the data, and outputs in
multiple formats (CSV, JSON, NDJSON).
"""

import csv
import json
import re
from pathlib import Path
from urllib.parse import unquote

import pandas as pd


def extract_place_id(url: str) -> str:
    """
    Extract Google Place ID from a Google Maps URL.
    
    URLs typically have format:
    https://www.google.com/maps/place/.../data=!4m2!3m1!1s<PLACE_ID>
    
    Args:
        url: Google Maps URL string
        
    Returns:
        Place ID string, or empty string if not found
    """
    if not url or pd.isna(url):
        return ""
    
    # Pattern to match place ID after !1s in the URL
    # Place ID format: hexadecimal string, often with colon separator
    pattern = r'!1s([0-9a-fA-F:]+)'
    match = re.search(pattern, url)
    
    if match:
        return match.group(1)
    
    return ""


def load_csv_robust(filepath: Path) -> pd.DataFrame:
    """
    Load CSV file, handling the Google Takeout format.
    
    Format can be:
    - Line 1: Human description (optional)
    - Line 2: Blank
    - Line 3: Header row (Title,Note,URL,Tags,Comment)
    - Line 4+: Data rows
    
    Or:
    - Line 1: Header row
    - Line 2: Blank/empty row
    - Line 3+: Data rows
    
    Args:
        filepath: Path to CSV file
        
    Returns:
        DataFrame with restaurant data
    """
    # Read first few lines to detect format
    with open(filepath, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
        second_line = f.readline().strip()
        third_line = f.readline().strip()
    
    # Determine skiprows: if first line is header, skip 0; otherwise skip 2
    if first_line.startswith('Title'):
        skiprows = 0
    else:
        skiprows = 2
    
    # Read CSV with appropriate skiprows
    df = pd.read_csv(
        filepath,
        skiprows=skiprows,
        encoding='utf-8',
        dtype=str,  # Read all as strings to preserve data
        keep_default_na=False,  # Don't convert empty strings to NaN
    )
    
    return df


def determine_city_and_status(filename: str) -> tuple[str, str]:
    """
    Determine city and status from filename.
    
    Args:
        filename: CSV filename
        
    Returns:
        Tuple of (city, status)
    """
    filename_lower = filename.lower()
    
    # Determine city
    if 'milan' in filename_lower:
        city = 'Milan'
    elif 'nyc' in filename_lower or 'new york' in filename_lower:
        city = 'New York'
    else:
        city = 'Unknown'
    
    # Determine status
    if 'want to try' in filename_lower or 'want' in filename_lower:
        status = 'want'
    elif 'food' in filename_lower:
        status = 'tried'
    else:
        status = 'unknown'
    
    return city, status


def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Clean the dataframe: strip whitespace, drop empty names.
    
    Args:
        df: Input dataframe
        
    Returns:
        Tuple of (cleaned dataframe, number of rows dropped due to empty names)
    """
    # Strip whitespace from all string columns
    for col in df.columns:
        if df[col].dtype == 'object':  # String columns
            df[col] = df[col].str.strip()
    
    # Drop rows where name is empty
    initial_count = len(df)
    df = df[df['name'].astype(str).str.strip() != '']
    dropped_empty = initial_count - len(df)
    
    return df, dropped_empty


def deduplicate_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Deduplicate by (city, status, name), keeping row with non-empty note if available.
    
    Args:
        df: Input dataframe
        
    Returns:
        Tuple of (deduplicated dataframe, number of duplicates removed)
    """
    initial_count = len(df)
    
    # Sort by note length (descending) so rows with notes come first
    df['_note_length'] = df['note'].astype(str).str.len()
    df = df.sort_values('_note_length', ascending=False)
    
    # Drop duplicates, keeping first (which will be the one with longest note)
    df = df.drop_duplicates(subset=['city', 'status', 'name'], keep='first')
    
    # Remove helper column
    df = df.drop(columns=['_note_length'])
    
    duplicates_removed = initial_count - len(df)
    
    return df, duplicates_removed


def main():
    """Main execution function."""
    # Define paths
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    data_dir = repo_root / 'data'
    output_dir = repo_root / 'data'
    
    # Define input files
    input_files = [
        'Milan Food.csv',
        'Milan want to try.csv',
        'NYC food.csv',
        'NYC want to try.csv',
    ]
    
    # Load and process each CSV file
    all_dfs = []
    total_dropped_empty = 0
    
    for filename in input_files:
        filepath = data_dir / filename
        
        if not filepath.exists():
            print(f"Warning: {filepath} not found, skipping...")
            continue
        
        print(f"Processing {filename}...")
        
        # Load CSV
        df = load_csv_robust(filepath)
        
        # Determine city and status from filename
        city, status = determine_city_and_status(filename)
        
        # Add city and status columns
        df['city'] = city
        df['status'] = status
        
        # Rename columns
        df = df.rename(columns={
            'Title': 'name',
            'Note': 'note',
            'URL': 'url',
            'Tags': 'tags',
            'Comment': 'comment',
        })
        
        # Extract place_id from URL
        df['place_id'] = df['url'].apply(extract_place_id)
        
        # Clean data
        df, dropped_empty = clean_dataframe(df)
        total_dropped_empty += dropped_empty
        
        all_dfs.append(df)
    
    # Combine all dataframes
    if not all_dfs:
        print("Error: No data loaded!")
        return
    
    combined_df = pd.concat(all_dfs, ignore_index=True)
    
    # Deduplicate
    combined_df, duplicates_removed = deduplicate_dataframe(combined_df)
    
    # Reorder columns for output
    column_order = ['city', 'status', 'name', 'note', 'url', 'place_id', 'tags', 'comment']
    combined_df = combined_df[column_order]
    
    # Output CSV
    csv_output = output_dir / 'restaurants_clean.csv'
    combined_df.to_csv(csv_output, index=False, encoding='utf-8')
    print(f"\n✓ Saved CSV: {csv_output}")
    
    # Output JSON (array of objects)
    json_output = output_dir / 'restaurants_clean.json'
    records = combined_df.to_dict('records')
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved JSON: {json_output}")
    
    # Output NDJSON (one JSON object per line)
    ndjson_output = output_dir / 'restaurants_clean.ndjson'
    with open(ndjson_output, 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    print(f"✓ Saved NDJSON: {ndjson_output}")
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    # Total rows per city/status
    print("\nTotal rows by city/status:")
    summary = combined_df.groupby(['city', 'status']).size().reset_index(name='count')
    for _, row in summary.iterrows():
        print(f"  {row['city']} / {row['status']}: {row['count']}")
    
    print(f"\nDuplicates removed: {duplicates_removed}")
    
    # Count rows with missing notes
    missing_notes = combined_df['note'].astype(str).str.strip().isin(['', 'nan']).sum()
    print(f"Rows with missing notes: {missing_notes}")
    
    print(f"\nTotal restaurants: {len(combined_df)}")
    print("="*60)


if __name__ == '__main__':
    main()

