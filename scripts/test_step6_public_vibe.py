#!/usr/bin/env python3
"""
Test script for Step 6: Public vibe feature.

Validates:
1) public_signals.csv has new columns and row count unchanged (153)
2) At least 10 restaurants have non-empty public_rating and public_review_count after enrichment
3) If reviews/snippets are available:
   - public_snippets_json is valid JSON list
   - public_summary is one sentence (ends with . ! ?)
   - public_summary length <= 220 chars
4) API response includes public_summary field
5) Frontend renders "Public vibe" only when present (manual check)
"""

import csv
import json
import sys
from pathlib import Path

def test_public_signals_schema():
    """Test 1: Check public_signals.csv has new columns and correct row count."""
    data_dir = Path(__file__).parent.parent / 'data'
    public_signals_file = data_dir / 'public_signals.csv'
    
    if not public_signals_file.exists():
        print("FAIL: public_signals.csv does not exist")
        return False
    
    with open(public_signals_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    
    # Check required columns
    required_columns = [
        'restaurant_id', 'public_rating', 'public_review_count', 
        'price_tier', 'source', 'public_summary', 
        'public_snippets_json', 'public_summary_updated_at'
    ]
    
    missing_columns = [col for col in required_columns if col not in fieldnames]
    if missing_columns:
        print(f"FAIL: Missing columns: {missing_columns}")
        return False
    
    # Check row count (should be 153)
    if len(rows) != 153:
        print(f"FAIL: Expected 153 rows, found {len(rows)}")
        return False
    
    print("✓ PASS: public_signals.csv has correct schema and row count")
    return True


def test_enrichment_data():
    """Test 2: Check at least 10 restaurants have non-empty public data."""
    data_dir = Path(__file__).parent.parent / 'data'
    public_signals_file = data_dir / 'public_signals.csv'
    
    with open(public_signals_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    enriched_count = 0
    for row in rows:
        rating = row.get('public_rating', '').strip()
        review_count = row.get('public_review_count', '').strip()
        if rating and review_count:
            enriched_count += 1
    
    if enriched_count < 10:
        print(f"FAIL: Only {enriched_count} restaurants have public_rating and public_review_count (expected >= 10)")
        return False
    
    print(f"✓ PASS: {enriched_count} restaurants have public_rating and public_review_count")
    return True


def test_summary_quality():
    """Test 3: Check public_summary quality if snippets are available."""
    data_dir = Path(__file__).parent.parent / 'data'
    public_signals_file = data_dir / 'public_signals.csv'
    
    with open(public_signals_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    summaries_with_snippets = 0
    valid_summaries = 0
    
    for row in rows:
        snippets_json = row.get('public_snippets_json', '').strip()
        summary = row.get('public_summary', '').strip()
        
        if snippets_json:
            summaries_with_snippets += 1
            
            # Check snippets_json is valid JSON
            try:
                snippets = json.loads(snippets_json)
                if not isinstance(snippets, list):
                    print(f"FAIL: public_snippets_json is not a list for {row.get('restaurant_id')}")
                    return False
            except json.JSONDecodeError:
                print(f"FAIL: Invalid JSON in public_snippets_json for {row.get('restaurant_id')}")
                return False
            
            # Check summary if present
            if summary:
                # Check it's one sentence (ends with . ! ?)
                if not summary.rstrip().endswith(('.', '!', '?')):
                    print(f"FAIL: public_summary does not end with sentence punctuation for {row.get('restaurant_id')}: {summary[:50]}...")
                    return False
                
                # Check length
                if len(summary) > 220:
                    print(f"FAIL: public_summary too long ({len(summary)} chars) for {row.get('restaurant_id')}")
                    return False
                
                valid_summaries += 1
    
    if summaries_with_snippets > 0 and valid_summaries == 0:
        print("FAIL: No valid summaries found despite snippets being available")
        return False
    
    print(f"✓ PASS: {valid_summaries} valid summaries found (out of {summaries_with_snippets} with snippets)")
    return True


def test_api_response():
    """Test 4: Check that recommend() includes public_summary in response."""
    sys.path.insert(0, str(Path(__file__).parent))
    from rank_and_explain import recommend
    
    # Test with a simple query
    results = recommend("romantic dinner in NYC", top_n=3)
    
    if not results:
        print("FAIL: recommend() returned no results")
        return False
    
    # Check at least one result has public_summary field
    has_public_summary = any('public_summary' in r for r in results)
    
    if not has_public_summary:
        print("FAIL: API response does not include public_summary field")
        return False
    
    # Check public_summary is present (even if empty)
    for result in results:
        if 'public_summary' not in result:
            print(f"FAIL: Result missing public_summary field: {result.get('name')}")
            return False
    
    print("✓ PASS: API response includes public_summary field")
    return True


def main():
    print("Running Step 6 Public Vibe tests...\n")
    
    tests = [
        ("Schema and row count", test_public_signals_schema),
        ("Enrichment data", test_enrichment_data),
        ("Summary quality", test_summary_quality),
        ("API response", test_api_response),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"Test: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"FAIL: Exception in {test_name}: {e}")
            results.append((test_name, False))
        print()
    
    # Summary
    print("=" * 50)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    if passed == total:
        print(f"✓ ALL TESTS PASSED ({passed}/{total})")
        return 0
    else:
        print(f"✗ SOME TESTS FAILED ({passed}/{total})")
        for test_name, result in results:
            status = "PASS" if result else "FAIL"
            print(f"  {status}: {test_name}")
        return 1


if __name__ == '__main__':
    sys.exit(main())

