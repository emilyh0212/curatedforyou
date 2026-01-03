#!/usr/bin/env python3
"""
Fix empty your_note fields by setting them to "-"
"""

import csv
from pathlib import Path

def main():
    data_dir = Path(__file__).parent.parent / 'data'
    master_file = data_dir / 'restaurants_master.csv'
    
    # Read the file
    rows = []
    with open(master_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        for row in reader:
            # Fix empty your_note
            if not row.get('your_note', '').strip():
                row['your_note'] = '-'
            rows.append(row)
    
    # Write back
    with open(master_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    # Count fixes
    fixed_count = sum(1 for row in rows if row.get('your_note', '').strip() == '-')
    print(f"✓ Fixed {fixed_count} empty your_note fields")
    print(f"✓ Updated {master_file}")

if __name__ == '__main__':
    main()

