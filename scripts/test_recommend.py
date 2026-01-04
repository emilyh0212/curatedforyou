#!/usr/bin/env python3
"""
Test script for the ranking and recommendation system.
Runs 5 sample queries and prints top results.
"""

import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from rank_and_explain import recommend


def test_query(query: str, city: str = None):
    """Test a single query and print results."""
    print("=" * 80)
    print(f"Query: {query}")
    if city:
        print(f"City: {city}")
    print("=" * 80)
    
    try:
        results = recommend(query, top_n=6, city=city)
        
        if not results:
            print("No results found.\n")
            return
        
        for i, restaurant in enumerate(results, 1):
            print(f"\n{i}. {restaurant['name']}")
            print(f"   City: {restaurant['city']}")
            if restaurant['neighborhood']:
                print(f"   Neighborhood: {restaurant['neighborhood']}")
            print(f"   Status: {restaurant['status']}")
            print(f"   Score: {restaurant['final_score']}")
            print(f"   Why: {restaurant['why']}")
            if restaurant['price_tier']:
                print(f"   Price: {restaurant['price_tier']}")
            if restaurant['public_rating']:
                print(f"   Rating: {restaurant['public_rating']}")
            if restaurant['public_review_count']:
                print(f"   Reviews: {restaurant['public_review_count']}")
        
        print("\n")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("\n")


def main():
    """Run test queries."""
    print("Testing Restaurant Recommendation System")
    print("=" * 80)
    print()
    
    # Test queries
    test_queries = [
        ("romantic dinner in SoHo", "NYC"),
        ("casual brunch with friends in Milan", "Milan"),
        ("good pasta place in NYC", None),
        ("cheap eats in Koreatown", "NYC"),
        ("date night spot in Milan Navigli", "Milan")
    ]
    
    for query, city in test_queries:
        test_query(query, city)
    
    print("=" * 80)
    print("All tests completed!")


if __name__ == '__main__':
    main()

