#!/usr/bin/env python3
"""
Validate restaurants_master.csv against all Step 1 criteria.
"""

import csv
import re
from pathlib import Path
from collections import defaultdict, Counter

def normalize_name(name):
    """Normalize name for duplicate detection."""
    if not name:
        return ''
    # Lowercase, remove punctuation, strip whitespace
    normalized = re.sub(r'[^\w\s]', '', str(name).lower())
    return ' '.join(normalized.split())

def main():
    data_dir = Path(__file__).parent.parent / 'data'
    master_file = data_dir / 'restaurants_master.csv'
    
    violations = []
    warnings = []
    
    # A. File existence
    print("=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)
    print("\nA. File Existence")
    print("-" * 60)
    
    if not master_file.exists():
        violations.append({
            'rule': 'A1',
            'issue': 'File does not exist',
            'fix': 'Create data/restaurants_master.csv',
            'rows': []
        })
        print("❌ FAIL: File does not exist")
        return
    else:
        print("✓ PASS: File exists")
    
    # Read the master file
    restaurants = []
    with open(master_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # Start at 2 (row 1 is header)
            row['_row_num'] = i
            restaurants.append(row)
    
    total_rows = len(restaurants)
    print(f"\nTotal rows (excluding header): {total_rows}")
    
    # B. Required columns
    print("\nB. Required Columns")
    print("-" * 60)
    required_columns = [
        'restaurant_id', 'name', 'city', 'neighborhood', 
        'status', 'your_note', 'google_maps_url', 'source'
    ]
    
    if restaurants:
        actual_columns = set(restaurants[0].keys())
        actual_columns.discard('_row_num')  # Remove internal field
        
        for col in required_columns:
            if col not in actual_columns:
                violations.append({
                    'rule': f'B{required_columns.index(col) + 2}',
                    'issue': f'Missing required column: {col}',
                    'fix': f'Add column {col} to CSV',
                    'rows': []
                })
                print(f"❌ FAIL: Missing column '{col}'")
            else:
                print(f"✓ PASS: Column '{col}' exists")
    
    # C & D. Column constraints and data sanity
    print("\nC & D. Column Constraints & Data Sanity")
    print("-" * 60)
    
    restaurant_ids = []
    cities = set()
    statuses = set()
    sources = set()
    empty_names = []
    empty_notes = []
    urls = []
    url_to_rows = defaultdict(list)
    name_city_pairs = defaultdict(list)
    
    for row in restaurants:
        row_num = row['_row_num']
        
        # restaurant_id checks
        rid = row.get('restaurant_id', '').strip()
        if not rid:
            violations.append({
                'rule': 'C10',
                'issue': f'Empty restaurant_id at row {row_num}',
                'fix': f'Generate restaurant_id for row {row_num}',
                'rows': [{'row': row_num, 'name': row.get('name', 'N/A')}]
            })
        restaurant_ids.append(rid)
        
        # name checks
        name = row.get('name', '').strip()
        if not name:
            empty_names.append(row_num)
            violations.append({
                'rule': 'D14',
                'issue': f'Empty name at row {row_num}',
                'fix': f'Add name for row {row_num}',
                'rows': [{'row': row_num, 'restaurant_id': rid}]
            })
        
        # your_note checks
        note = row.get('your_note', '').strip()
        if not note:
            empty_notes.append(row_num)
            violations.append({
                'rule': 'D15',
                'issue': f'Empty your_note at row {row_num}',
                'fix': f'Add note for row {row_num} (can be short)',
                'rows': [{'row': row_num, 'name': name, 'restaurant_id': rid}]
            })
        
        # city checks
        city = row.get('city', '').strip()
        cities.add(city)
        
        # status checks
        status = row.get('status', '').strip()
        statuses.add(status)
        
        # source checks
        source = row.get('source', '').strip()
        sources.add(source)
        
        # google_maps_url checks
        url = row.get('google_maps_url', '').strip()
        if url:
            urls.append(url)
            url_to_rows[url].append(row_num)
        
        # For duplicate detection
        if name and city:
            normalized = normalize_name(name)
            key = f"{normalized}|||{city}"
            name_city_pairs[key].append({
                'row': row_num,
                'name': name,
                'city': city,
                'url': url,
                'restaurant_id': rid
            })
    
    # Check restaurant_id uniqueness
    id_counts = Counter(restaurant_ids)
    duplicates = {rid: count for rid, count in id_counts.items() if count > 1 and rid}
    if duplicates:
        dup_rows = []
        for rid, count in duplicates.items():
            for row in restaurants:
                if row.get('restaurant_id', '').strip() == rid:
                    dup_rows.append({
                        'row': row['_row_num'],
                        'restaurant_id': rid,
                        'name': row.get('name', 'N/A')
                    })
        violations.append({
            'rule': 'C10',
            'issue': f'Duplicate restaurant_id values found: {list(duplicates.keys())}',
            'fix': 'Regenerate restaurant_id for duplicates to ensure uniqueness',
            'rows': dup_rows
        })
        print(f"❌ FAIL: Duplicate restaurant_id found: {list(duplicates.keys())}")
    else:
        print("✓ PASS: All restaurant_id values are unique")
    
    # Check city format
    valid_cities = {'NYC', 'Milan'}
    invalid_cities = cities - valid_cities
    if invalid_cities:
        violations.append({
            'rule': 'C11',
            'issue': f'Invalid city values: {invalid_cities}',
            'fix': 'Normalize city values to exactly "NYC" or "Milan"',
            'rows': []
        })
        print(f"❌ FAIL: Invalid city values: {invalid_cities}")
    else:
        print(f"✓ PASS: City values are consistent: {cities}")
    
    # Check status values
    valid_statuses = {'tried', 'want_to_try'}
    invalid_statuses = statuses - valid_statuses
    if invalid_statuses:
        violations.append({
            'rule': 'C12',
            'issue': f'Invalid status values: {invalid_statuses}',
            'fix': 'Normalize status to exactly "tried" or "want_to_try"',
            'rows': []
        })
        print(f"❌ FAIL: Invalid status values: {invalid_statuses}")
    else:
        print(f"✓ PASS: Status values are valid: {statuses}")
    
    # Check source values
    if sources != {'google_maps'}:
        violations.append({
            'rule': 'C13',
            'issue': f'Invalid source values: {sources}',
            'fix': 'Set all source values to "google_maps"',
            'rows': []
        })
        print(f"❌ FAIL: Invalid source values: {sources}")
    else:
        print("✓ PASS: Source values are consistent: google_maps")
    
    # Check empty names
    if empty_names:
        print(f"❌ FAIL: Empty names at rows: {empty_names}")
    else:
        print("✓ PASS: All names are non-empty")
    
    # Check empty notes
    if empty_notes:
        print(f"❌ FAIL: Empty your_note at rows: {empty_notes}")
    else:
        print("✓ PASS: All your_note values are non-empty")
    
    # Check URL uniqueness
    url_duplicates = {url: rows for url, rows in url_to_rows.items() if len(rows) > 1}
    if url_duplicates:
        dup_info = []
        for url, rows in url_duplicates.items():
            dup_info.append({
                'url': url[:80] + '...' if len(url) > 80 else url,
                'rows': rows
            })
        violations.append({
            'rule': 'D16',
            'issue': f'Duplicate google_maps_url found: {len(url_duplicates)} URLs',
            'fix': 'Remove duplicate rows, keeping first occurrence',
            'rows': dup_info
        })
        print(f"❌ FAIL: Duplicate URLs found: {len(url_duplicates)}")
    else:
        print("✓ PASS: All URLs are unique (when present)")
    
    # E. Duplicate detection
    print("\nE. Duplicate Detection")
    print("-" * 60)
    
    duplicate_groups = []
    
    # Check by URL first
    for url, rows in url_to_rows.items():
        if len(rows) > 1:
            group = {
                'type': 'URL match',
                'match_value': url[:80] + '...' if len(url) > 80 else url,
                'rows': []
            }
            for row_num in rows:
                row_data = next(r for r in restaurants if r['_row_num'] == row_num)
                group['rows'].append({
                    'row': row_num,
                    'name': row_data.get('name', 'N/A'),
                    'city': row_data.get('city', 'N/A'),
                    'restaurant_id': row_data.get('restaurant_id', 'N/A')
                })
            duplicate_groups.append(group)
    
    # Check by normalized name + city
    for key, rows in name_city_pairs.items():
        if len(rows) > 1:
            # Check if they don't already match by URL
            urls_in_group = [r['url'] for r in rows if r['url']]
            if len(set(urls_in_group)) > 1 or not urls_in_group:
                # Different URLs or no URLs - potential duplicate
                group = {
                    'type': 'Name+City match',
                    'match_value': key,
                    'rows': rows
                }
                duplicate_groups.append(group)
    
    if duplicate_groups:
        print(f"⚠️  WARNING: Found {len(duplicate_groups)} potential duplicate groups")
        for i, group in enumerate(duplicate_groups[:5], 1):  # Show first 5
            print(f"\n  Group {i} ({group['type']}):")
            for r in group['rows']:
                print(f"    Row {r['row']}: {r['name']} ({r['city']})")
    else:
        print("✓ PASS: No duplicates detected")
    
    # F. Coverage check
    print("\nF. Coverage Check")
    print("-" * 60)
    
    source_files = [
        ('Milan Food.csv', 'Milan', 'tried'),
        ('Milan want to try.csv', 'Milan', 'want_to_try'),
        ('NYC food.csv', 'NYC', 'tried'),
        ('NYC want to try.csv', 'NYC', 'want_to_try'),
    ]
    
    all_source_restaurants = []
    missing_files = []
    
    for filename, expected_city, expected_status in source_files:
        filepath = data_dir / filename
        if not filepath.exists():
            missing_files.append(filename)
            print(f"⚠️  WARNING: Source file not found: {filename}")
            continue
        
        # Read source file
        source_count = 0
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Find header
            header_idx = None
            for i, line in enumerate(lines):
                if 'Title' in line and 'Note' in line and 'URL' in line:
                    header_idx = i
                    break
            
            if header_idx is not None:
                reader = csv.DictReader(lines[header_idx:])
                for row in reader:
                    name = row.get('Title', '').strip()
                    if name:
                        url = row.get('URL', '').strip()
                        all_source_restaurants.append({
                            'name': name,
                            'city': expected_city,
                            'status': expected_status,
                            'url': url,
                            'source_file': filename
                        })
                        source_count += 1
        
        print(f"  {filename}: {source_count} restaurants")
    
    # Check if all source restaurants are in master
    master_lookup = {}
    for row in restaurants:
        name = row.get('name', '').strip()
        city = row.get('city', '').strip()
        url = row.get('google_maps_url', '').strip()
        key = (name, city, url) if url else (name, city, None)
        master_lookup[key] = row
    
    missing_restaurants = []
    for src in all_source_restaurants:
        name = src['name']
        city = src['city']
        url = src['url']
        key = (name, city, url) if url else (name, city, None)
        
        if key not in master_lookup:
            missing_restaurants.append(src)
    
    if missing_restaurants:
        violations.append({
            'rule': 'F19',
            'issue': f'{len(missing_restaurants)} restaurants from source files are missing',
            'fix': 'Add missing restaurants to master file',
            'rows': missing_restaurants[:10]  # Show first 10
        })
        print(f"❌ FAIL: {len(missing_restaurants)} restaurants missing from master")
        print("  Examples:")
        for r in missing_restaurants[:5]:
            print(f"    - {r['name']} ({r['city']}) from {r['source_file']}")
    else:
        print("✓ PASS: All source restaurants are in master file")
    
    # G. Loadability
    print("\nG. Loadability")
    print("-" * 60)
    try:
        import pandas as pd
        df = pd.read_csv(master_file)
        print(f"✓ PASS: File loads cleanly with pandas ({len(df)} rows)")
    except ImportError:
        print("⚠️  SKIP: pandas not available, cannot test loadability")
    except Exception as e:
        violations.append({
            'rule': 'G20',
            'issue': f'File cannot be loaded with pandas: {e}',
            'fix': 'Fix CSV formatting issues',
            'rows': []
        })
        print(f"❌ FAIL: Cannot load with pandas: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    # Count by city and status
    city_status_counts = defaultdict(int)
    for row in restaurants:
        city = row.get('city', 'Unknown')
        status = row.get('status', 'Unknown')
        city_status_counts[(city, status)] += 1
    
    print(f"\nTotal rows: {total_rows}")
    print("\nCount by city and status:")
    for (city, status), count in sorted(city_status_counts.items()):
        print(f"  {city} - {status}: {count}")
    
    # Final verdict
    if violations:
        print(f"\n❌ FAIL: {len(violations)} violation(s) found")
    else:
        print("\n✓ PASS: All checks passed!")
    
    # Violations detail
    if violations:
        print("\n" + "=" * 60)
        print("VIOLATIONS")
        print("=" * 60)
        for i, v in enumerate(violations, 1):
            print(f"\n{i}. Rule {v['rule']}: {v['issue']}")
            print(f"   Fix: {v['fix']}")
            if v['rows']:
                print(f"   Affected rows:")
                for r in v['rows'][:5]:  # Show first 5
                    if isinstance(r, dict):
                        if 'row' in r:
                            print(f"     - Row {r['row']}: {r.get('name', 'N/A')} ({r.get('city', 'N/A')})")
                        elif 'name' in r:
                            print(f"     - {r['name']} ({r.get('city', 'N/A')}) from {r.get('source_file', 'N/A')}")
                    else:
                        print(f"     - {r}")
                if len(v['rows']) > 5:
                    print(f"     ... and {len(v['rows']) - 5} more")
    
    # Quick Fix Plan
    if violations:
        print("\n" + "=" * 60)
        print("QUICK FIX PLAN")
        print("=" * 60)
        fix_plan = []
        
        # Group fixes by type
        if any(v['rule'] == 'C11' for v in violations):
            fix_plan.append("1. Normalize city values to 'NYC' or 'Milan'")
        if any(v['rule'] == 'C12' for v in violations):
            fix_plan.append("2. Normalize status values to 'tried' or 'want_to_try'")
        if any(v['rule'] == 'C13' for v in violations):
            fix_plan.append("3. Set all source values to 'google_maps'")
        if any(v['rule'] == 'C10' for v in violations):
            fix_plan.append("4. Regenerate restaurant_id for duplicates")
        if any(v['rule'] == 'D14' for v in violations):
            fix_plan.append("5. Add missing names")
        if any(v['rule'] == 'D15' for v in violations):
            fix_plan.append("6. Add missing notes (can be short)")
        if any(v['rule'] == 'D16' for v in violations):
            fix_plan.append("7. Remove duplicate rows based on URL")
        if any(v['rule'] == 'F19' for v in violations):
            fix_plan.append("8. Add missing restaurants from source files")
        
        for i, fix in enumerate(fix_plan, 1):
            print(f"{i}. {fix}")
    
    return len(violations) == 0

if __name__ == '__main__':
    main()

