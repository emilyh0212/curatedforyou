#!/usr/bin/env python3
"""
Build public_signals.csv from restaurants_master.csv (Step 3).

Extracts public data signals: ratings, review counts, price tiers.
"""

import csv
from pathlib import Path
from statistics import mean


def main():
    data_dir = Path(__file__).parent.parent / 'data'
    master_file = data_dir / 'restaurants_master.csv'
    output_file = data_dir / 'public_signals.csv'
    
    # Read master file
    restaurants = []
    with open(master_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        restaurants = list(reader)
    
    # Build public signals
    public_signals = []
    ratings = []
    
    for restaurant in restaurants:
        restaurant_id = restaurant.get('restaurant_id', '')
        public_rating = restaurant.get('public_rating', '').strip()
        public_review_count = restaurant.get('public_review_count', '').strip()
        price_tier = restaurant.get('price_tier', '').strip()
        
        # Collect ratings for average calculation
        if public_rating:
            try:
                rating_float = float(public_rating)
                ratings.append(rating_float)
            except (ValueError, TypeError):
                pass
        
        signal = {
            'restaurant_id': restaurant_id,
            'public_rating': public_rating if public_rating else '',
            'public_review_count': public_review_count if public_review_count else '',
            'price_tier': price_tier if price_tier else '',
            'source': 'google_maps'
        }
        
        public_signals.append(signal)
    
    # Write output file
    fieldnames = [
        'restaurant_id',
        'public_rating',
        'public_review_count',
        'price_tier',
        'source'
    ]
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(public_signals)
    
    # Calculate statistics
    total_rows = len(public_signals)
    rating_count = sum(1 for s in public_signals if s['public_rating'])
    review_count_count = sum(1 for s in public_signals if s['public_review_count'])
    price_tier_count = sum(1 for s in public_signals if s['price_tier'])
    
    avg_rating = None
    if ratings:
        avg_rating = mean(ratings)
    
    # Print summary
    print("=" * 60)
    print("PUBLIC SIGNALS GENERATED")
    print("=" * 60)
    print(f"\nTotal rows: {total_rows}")
    print(f"Rows with public_rating: {rating_count} ({rating_count/total_rows*100:.1f}%)")
    print(f"Rows with public_review_count: {review_count_count} ({review_count_count/total_rows*100:.1f}%)")
    print(f"Rows with price_tier: {price_tier_count} ({price_tier_count/total_rows*100:.1f}%)")
    
    if avg_rating is not None:
        print(f"Average rating: {avg_rating:.2f}")
    else:
        print("Average rating: N/A (no ratings available)")
    
    print(f"\n✓ Created {output_file}")
    
    # Verify file loads cleanly
    print("\nVerifying file...")
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            verify_rows = list(reader)
            if len(verify_rows) == total_rows:
                print(f"✓ File verified: {len(verify_rows)} rows loaded successfully")
            else:
                print(f"⚠️  Warning: Expected {total_rows} rows, found {len(verify_rows)}")
    except Exception as e:
        print(f"⚠️  Error verifying file: {e}")


if __name__ == '__main__':
    main()

