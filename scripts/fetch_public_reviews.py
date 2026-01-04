#!/usr/bin/env python3
"""
Fetch public review snippets from Google Places API (New) and cache them.

For each restaurant with place_id:
- Fetch Place Details using Places API (New) searchText
- Extract up to 8 review snippets (240 chars each)
- Store in public_review_snippets_json
- Cache API responses to avoid re-calling
"""

import csv
import json
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

if not GOOGLE_MAPS_API_KEY:
    print("ERROR: GOOGLE_MAPS_API_KEY not found in environment.")
    sys.exit(1)

print("✓ Google Maps API key loaded from environment")

# Cache file for API responses
CACHE_FILE = Path(__file__).parent.parent / 'data' / 'places_details_cache.json'


def load_cache():
    """Load cached API responses."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load cache: {e}")
    return {}


def save_cache(cache):
    """Save API responses to cache."""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save cache: {e}")


def fetch_place_details(place_name: str, city: str = "", cache: dict = None) -> dict | None:
    """
    Fetch place details from Google Places API (New) using searchText.
    Returns dict with rating, userRatingCount, priceLevel, reviews, or None on error.
    """
    if not place_name:
        return None
    
    # Check cache first
    cache_key = f"{place_name} {city}".strip()
    if cache and cache_key in cache:
        print(f"    Using cached data for {place_name}")
        return cache[cache_key]
    
    # Use Places API (New) searchText endpoint
    search_url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "places.id,places.rating,places.userRatingCount,places.priceLevel,places.reviews"
    }
    
    # Build search query
    query = place_name
    if city:
        query = f"{place_name} {city}"
    
    body = {
        "textQuery": query,
        "maxResultCount": 1
    }
    
    try:
        response = requests.post(search_url, headers=headers, json=body, timeout=10)
        if response.status_code == 200:
            data = response.json()
            places = data.get('places', [])
            if places:
                place = places[0]
                result = {
                    'rating': place.get('rating'),
                    'userRatingCount': place.get('userRatingCount'),
                    'priceLevel': place.get('priceLevel'),
                    'reviews': place.get('reviews', [])
                }
                # Cache the result
                if cache is not None:
                    cache[cache_key] = result
                return result
            return None
        elif response.status_code == 404:
            print(f"  Warning: Place not found for {place_name}")
            return None
        else:
            print(f"  Warning: API returned {response.status_code} for {place_name}")
            return None
    except Exception as e:
        print(f"  Error fetching place details: {e}")
        return None


def extract_snippets(place_data: dict, max_snippets: int = 8, max_length: int = 240) -> list[str]:
    """
    Extract review text snippets from place data.
    Returns list of truncated snippet strings.
    """
    snippets = []
    reviews = place_data.get('reviews', [])
    
    if not reviews:
        return snippets
    
    # Sort by publishTime if available (most recent first)
    sorted_reviews = sorted(
        reviews,
        key=lambda r: r.get('publishTime', '') or r.get('relativePublishTimeDescription', ''),
        reverse=True
    )
    
    for review in sorted_reviews[:max_snippets]:
        # Try different fields for review text
        text = None
        if 'text' in review:
            if isinstance(review['text'], dict):
                text = review['text'].get('text', '')
            else:
                text = str(review['text'])
        elif 'originalText' in review:
            text = review['originalText']
        
        if text:
            # Strip newlines and clean up
            text = ' '.join(text.split())
            # Truncate to max_length
            if len(text) > max_length:
                text = text[:max_length].rsplit(' ', 1)[0] + '...'
            snippets.append(text.strip())
    
    return snippets


def main():
    data_dir = Path(__file__).parent.parent / 'data'
    master_file = data_dir / 'restaurants_master.csv'
    public_signals_file = data_dir / 'public_signals.csv'
    
    if not master_file.exists():
        print(f"ERROR: {master_file} not found")
        sys.exit(1)
    
    # Load cache
    cache = load_cache()
    print(f"Loaded {len(cache)} cached API responses")
    
    # Load restaurants
    restaurants = {}
    with open(master_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            restaurant_id = row.get('restaurant_id', '')
            place_id = row.get('place_id', '').strip()
            name = row.get('name', '')
            city = row.get('city', '')
            
            if name:  # We'll use name + city for search
                restaurants[restaurant_id] = {
                    'name': name,
                    'city': city
                }
    
    print(f"Found {len(restaurants)} restaurants")
    
    # Load existing public signals
    public_signals = {}
    fieldnames = ['restaurant_id', 'public_rating', 'public_review_count', 'price_tier', 'source',
                  'public_review_snippets_json', 'public_vibe', 'public_vibe_updated_at']
    
    if public_signals_file.exists():
        with open(public_signals_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            existing_fieldnames = reader.fieldnames or []
            for row in reader:
                restaurant_id = row.get('restaurant_id', '')
                public_signals[restaurant_id] = dict(row)
                # Ensure new columns exist
                for col in fieldnames:
                    if col not in public_signals[restaurant_id]:
                        public_signals[restaurant_id][col] = ''
    else:
        print("Creating new public_signals.csv")
    
    # Identify restaurants that need fetching
    to_fetch = []
    for restaurant_id, restaurant in restaurants.items():
        signal = public_signals.get(restaurant_id, {})
        snippets_json = signal.get('public_review_snippets_json', '').strip()
        
        # Fetch if snippets are missing
        if not snippets_json:
            to_fetch.append((restaurant_id, restaurant))
    
    print(f"Found {len(to_fetch)} restaurants to fetch reviews for")
    
    if not to_fetch:
        print("All restaurants are up to date!")
        save_cache(cache)
        return
    
    # Fetch reviews
    fetched_count = 0
    snippets_count = 0
    
    for i, (restaurant_id, restaurant) in enumerate(to_fetch):
        name = restaurant['name']
        city = restaurant['city']
        
        print(f"  [{i+1}/{len(to_fetch)}] Fetching reviews for {name}...")
        
        # Fetch place details
        place_data = fetch_place_details(name, city, cache)
        time.sleep(0.2)  # Rate limiting
        
        # Initialize signal if needed
        if restaurant_id not in public_signals:
            public_signals[restaurant_id] = {
                'restaurant_id': restaurant_id,
                'public_rating': '',
                'public_review_count': '',
                'price_tier': '',
                'source': 'google_maps',
                'public_review_snippets_json': '',
                'public_vibe': '',
                'public_vibe_updated_at': ''
            }
        
        signal = public_signals[restaurant_id]
        
        if place_data:
            # Update rating and count
            rating = place_data.get('rating')
            if rating is not None:
                signal['public_rating'] = str(rating)
            
            user_rating_count = place_data.get('userRatingCount')
            if user_rating_count is not None:
                signal['public_review_count'] = str(user_rating_count)
            
            # Update price tier
            price_level = place_data.get('priceLevel')
            if price_level is not None:
                # Convert PRICE_LEVEL enum to tier (1-4)
                price_map = {
                    'PRICE_LEVEL_FREE': '',
                    'PRICE_LEVEL_INEXPENSIVE': '1',
                    'PRICE_LEVEL_MODERATE': '2',
                    'PRICE_LEVEL_EXPENSIVE': '3',
                    'PRICE_LEVEL_VERY_EXPENSIVE': '4'
                }
                signal['price_tier'] = price_map.get(price_level, '')
            
            # Extract review snippets
            snippets = extract_snippets(place_data, max_snippets=8, max_length=240)
            
            if snippets:
                signal['public_review_snippets_json'] = json.dumps(snippets)
                snippets_count += 1
                print(f"    ✓ Got {len(snippets)} review snippets")
            else:
                signal['public_review_snippets_json'] = ''
                print(f"    Warning: No reviews returned for {name}")
            
            fetched_count += 1
        else:
            print(f"    Skipping {name} (no data returned)")
    
    # Ensure all restaurants from master are in public_signals
    with open(master_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            restaurant_id = row.get('restaurant_id', '')
            if restaurant_id not in public_signals:
                public_signals[restaurant_id] = {
                    'restaurant_id': restaurant_id,
                    'public_rating': '',
                    'public_review_count': '',
                    'price_tier': '',
                    'source': 'google_maps',
                    'public_review_snippets_json': '',
                    'public_vibe': '',
                    'public_vibe_updated_at': ''
                }
    
    # Write updated public_signals.csv
    with open(public_signals_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for restaurant_id in sorted(public_signals.keys()):
            row = public_signals[restaurant_id]
            # Ensure all fields are present
            for field in fieldnames:
                if field not in row:
                    row[field] = ''
            writer.writerow(row)
    
    # Save cache
    save_cache(cache)
    
    print(f"\n✓ Fetched data for {fetched_count} restaurants")
    print(f"✓ {snippets_count} restaurants have review snippets")
    print(f"✓ Updated {public_signals_file}")
    print(f"✓ Cached {len(cache)} API responses")


if __name__ == '__main__':
    main()

