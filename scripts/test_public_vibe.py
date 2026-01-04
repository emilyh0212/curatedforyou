#!/usr/bin/env python3
"""
Test script for public vibe feature.

Validates:
- public_signals.csv has required columns
- At least X restaurants have review snippets
- At least X restaurants have public_vibe
- Prints 5 sample restaurants with details
"""

import csv
import json
import sys
from pathlib import Path


def main():
    data_dir = Path(__file__).parent.parent / 'data'
    public_signals_file = data_dir / 'public_signals.csv'
    
    if not public_signals_file.exists():
        print(f"ERROR: {public_signals_file} not found")
        sys.exit(1)
    
    # Load public signals
    restaurants = []
    with open(public_signals_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        restaurants = list(reader)
    
    # Check required columns
    required_columns = [
        'restaurant_id', 'public_rating', 'public_review_count', 
        'price_tier', 'source', 'public_review_snippets_json',
        'public_vibe', 'public_vibe_updated_at',
        'public_vibe_source', 'public_vibe_model'
    ]
    
    if not restaurants:
        print("ERROR: No restaurants found in public_signals.csv")
        sys.exit(1)
    
    fieldnames = list(restaurants[0].keys())
    missing_columns = [col for col in required_columns if col not in fieldnames]
    
    if missing_columns:
        print(f"FAIL: Missing columns: {missing_columns}")
        sys.exit(1)
    
    print("✓ All required columns present")
    
    # Count restaurants with snippets
    snippets_count = 0
    vibe_count = 0
    
    for restaurant in restaurants:
        snippets_json = restaurant.get('public_review_snippets_json', '').strip()
        public_vibe = restaurant.get('public_vibe', '').strip()
        
        if snippets_json:
            try:
                snippets = json.loads(snippets_json)
                if snippets:
                    snippets_count += 1
            except json.JSONDecodeError:
                pass
        
        if public_vibe:
            vibe_count += 1
    
    print(f"✓ {snippets_count} restaurants have review snippets")
    print(f"✓ {vibe_count} restaurants have public_vibe")
    
    # Verify no empty public_vibe for rows with snippets
    empty_vibes = 0
    for restaurant in restaurants:
        snippets_json = restaurant.get('public_review_snippets_json', '').strip()
        public_vibe = restaurant.get('public_vibe', '').strip()
        
        if snippets_json and not public_vibe:
            empty_vibes += 1
    
    if empty_vibes > 0:
        print(f"⚠ WARNING: {empty_vibes} restaurants have snippets but no public_vibe")
    else:
        print("✓ All restaurants with snippets have public_vibe")
    
    # Verify LLM vibes have snippets
    llm_without_snippets = 0
    for restaurant in restaurants:
        vibe_source = restaurant.get('public_vibe_source', '').strip()
        snippets_json = restaurant.get('public_review_snippets_json', '').strip()
        
        if vibe_source == 'llm' and not snippets_json:
            llm_without_snippets += 1
    
    if llm_without_snippets > 0:
        print(f"⚠ WARNING: {llm_without_snippets} restaurants have LLM vibe but no snippets")
    else:
        print("✓ All LLM vibes have review snippets")
    
    # Print 5 LLM samples and 5 fallback samples
    print("\n" + "=" * 60)
    print("Sample restaurants (LLM-generated):")
    print("=" * 60)
    
    llm_samples = []
    fallback_samples = []
    
    for restaurant in restaurants:
        snippets_json = restaurant.get('public_review_snippets_json', '').strip()
        public_vibe = restaurant.get('public_vibe', '').strip()
        
        if not snippets_json or not public_vibe:
            continue
        
        try:
            snippets = json.loads(snippets_json)
            if snippets:
                # Heuristic: LLM vibes are usually more nuanced, fallback are simpler
                # Check if it starts with common fallback patterns
                is_fallback = public_vibe.startswith(('Known for', 'Well-regarded', 'Popular spot'))
                
                sample = {
                    'id': restaurant['restaurant_id'],
                    'rating': restaurant.get('public_rating', 'N/A'),
                    'count': restaurant.get('public_review_count', 'N/A'),
                    'vibe': public_vibe,
                    'snippet': snippets[0][:100] + '...'
                }
                
                if is_fallback and len(fallback_samples) < 5:
                    fallback_samples.append(sample)
                elif not is_fallback and len(llm_samples) < 5:
                    llm_samples.append(sample)
                
                if len(llm_samples) >= 5 and len(fallback_samples) >= 5:
                    break
        except json.JSONDecodeError:
            pass
    
    # Print LLM samples
    for i, sample in enumerate(llm_samples, 1):
        print(f"\n{i}. Restaurant ID: {sample['id']}")
        print(f"   Rating: {sample['rating']} ({sample['count']} reviews)")
        print(f"   Public Vibe: {sample['vibe']}")
        print(f"   First Snippet: {sample['snippet']}")
    
    if not llm_samples:
        print("\nNo LLM-generated samples found")
    
    # Print fallback samples
    print("\n" + "=" * 60)
    print("Sample restaurants (Fallback-generated):")
    print("=" * 60)
    
    for i, sample in enumerate(fallback_samples, 1):
        print(f"\n{i}. Restaurant ID: {sample['id']}")
        print(f"   Rating: {sample['rating']} ({sample['count']} reviews)")
        print(f"   Public Vibe: {sample['vibe']}")
        print(f"   First Snippet: {sample['snippet']}")
    
    if not fallback_samples:
        print("\nNo fallback-generated samples found")
    
    print("\n" + "=" * 60)
    
    # Summary
    if snippets_count >= 10 and vibe_count >= 10:
        print("✓ PASS: Sufficient data for public vibe feature")
        return 0
    else:
        print(f"⚠ WARNING: Low data counts (snippets: {snippets_count}, vibes: {vibe_count})")
        return 1


if __name__ == '__main__':
    sys.exit(main())

