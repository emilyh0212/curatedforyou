#!/usr/bin/env python3
"""
Enrich public signals with review snippets and generate "Public vibe" summaries.

Uses Google Places API (New) to fetch:
- rating
- userRatingCount
- priceLevel
- reviews (if available)

Generates deterministic one-sentence summaries from review snippets.
Caches results in public_signals.csv.
"""

import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import requests
import re

# Load environment variables
load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

if not GOOGLE_MAPS_API_KEY:
    print("ERROR: GOOGLE_MAPS_API_KEY not found in environment.")
    print("Please create a .env file with: GOOGLE_MAPS_API_KEY=your_key_here")
    sys.exit(1)

print("✓ Google Maps API key loaded from environment")

# Google Places API (New) endpoint
PLACES_API_URL = "https://places.googleapis.com/v1/places"


def is_stale(updated_at_str: str | None, days: int = 30) -> bool:
    """Check if a timestamp is older than N days."""
    if not updated_at_str or updated_at_str.strip() == '':
        return True
    
    try:
        updated_at = datetime.fromisoformat(updated_at_str)
        return datetime.now() - updated_at > timedelta(days=days)
    except (ValueError, TypeError):
        return True


def fetch_place_details(place_id: str, place_name: str = "", city: str = "") -> dict | None:
    """
    Fetch place details from Google Places API (New) using searchText.
    Returns dict with rating, userRatingCount, priceLevel, reviews, or None on error.
    """
    if not place_name:
        return None
    
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
                return {
                    'rating': place.get('rating'),
                    'userRatingCount': place.get('userRatingCount'),
                    'priceLevel': place.get('priceLevel'),
                    'reviews': place.get('reviews', [])
                }
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


def _fetch_old_places_api(place_id: str) -> dict | None:
    """Fallback to old Places API Details endpoint."""
    old_api_url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "key": GOOGLE_MAPS_API_KEY,
        "fields": "rating,user_ratings_total,price_level,reviews"
    }
    
    try:
        response = requests.get(old_api_url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'OK' and data.get('result'):
                result = data['result']
                # Convert to new API format
                return {
                    'rating': result.get('rating'),
                    'userRatingCount': result.get('user_ratings_total'),
                    'priceLevel': _convert_price_level(result.get('price_level')),
                    'reviews': _convert_reviews(result.get('reviews', []))
                }
            elif data.get('status') == 'REQUEST_DENIED':
                error_message = data.get('error_message', 'Unknown error')
                print(f"  Warning: API request denied: {error_message}")
                return None
            else:
                return None
        return None
    except Exception:
        return None


def _convert_price_level(price_level: int | None) -> str | None:
    """Convert old API price_level (0-4) to new API format."""
    if price_level is None:
        return None
    price_map = {
        0: 'PRICE_LEVEL_FREE',
        1: 'PRICE_LEVEL_INEXPENSIVE',
        2: 'PRICE_LEVEL_MODERATE',
        3: 'PRICE_LEVEL_EXPENSIVE',
        4: 'PRICE_LEVEL_VERY_EXPENSIVE'
    }
    return price_map.get(price_level)


def _convert_reviews(old_reviews: list) -> list:
    """Convert old API reviews format to new API format."""
    new_reviews = []
    for review in old_reviews[:8]:  # Limit to 8
        new_review = {
            'text': {
                'text': review.get('text', '')
            },
            'publishTime': review.get('time', 0)
        }
        new_reviews.append(new_review)
    return new_reviews


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
        key=lambda r: r.get('publishTime', ''),
        reverse=True
    )
    
    for review in sorted_reviews[:max_snippets]:
        text = review.get('text', {}).get('text', '')
        if text:
            # Truncate to max_length
            if len(text) > max_length:
                text = text[:max_length].rsplit(' ', 1)[0] + '...'
            snippets.append(text.strip())
    
    return snippets


def build_public_summary(snippets: list[str]) -> str:
    """
    Generate a one-sentence "Public vibe" summary from review snippets.
    Deterministic, no LLM.
    
    Rules:
    - Exactly ONE sentence, <= 160 chars if possible (max 220)
    - Grounded only in snippets
    - Structure: 1 strong positive + 1 specific detail + optional caution
    - Avoid hype words, avoid "people say" phrasing
    - Use neutral phrasing: "Known for...", "Expect...", "Often praised for..."
    """
    if not snippets:
        return ""
    
    # Combine all snippets into one text for analysis
    combined_text = ' '.join(snippets).lower()
    
    # Extract keywords/phrases (simple frequency-based)
    keywords = {
        'wait': ['wait', 'line', 'queue', 'busy'],
        'loud': ['loud', 'noisy', 'noise'],
        'pricey': ['pricey', 'expensive', 'overpriced', 'cost'],
        'small': ['small', 'tiny', 'cramped', 'tight'],
        'service': ['service', 'staff', 'server', 'attentive', 'friendly'],
        'ambiance': ['ambiance', 'atmosphere', 'vibe', 'decor', 'cozy', 'romantic'],
        'fresh': ['fresh', 'quality', 'ingredients'],
        'spicy': ['spicy', 'heat', 'flavorful'],
        'portions': ['portions', 'generous', 'large', 'small'],
        'value': ['value', 'worth', 'affordable', 'reasonable']
    }
    
    # Count keyword mentions
    keyword_counts = {}
    for category, terms in keywords.items():
        count = sum(combined_text.count(term) for term in terms)
        if count > 0:
            keyword_counts[category] = count
    
    # Extract positive phrases
    positive_patterns = [
        r'amazing\s+\w+',
        r'best\s+\w+',
        r'love\s+\w+',
        r'perfect\s+\w+',
        r'great\s+\w+',
        r'excellent\s+\w+',
        r'incredible\s+\w+',
        r'fantastic\s+\w+',
    ]
    
    positive_phrases = []
    for pattern in positive_patterns:
        matches = re.findall(pattern, combined_text)
        positive_phrases.extend(matches[:2])  # Limit to avoid too many
    
    # Build summary
    summary_parts = []
    
    # Start with a positive descriptor
    if positive_phrases:
        # Extract the noun/adjective from first positive phrase
        first_positive = positive_phrases[0].split()[-1] if positive_phrases else None
        if first_positive:
            summary_parts.append(f"Known for {first_positive}")
    else:
        # Fallback: look for common food/service descriptors
        if 'pasta' in combined_text:
            summary_parts.append("Known for pasta")
        elif 'pizza' in combined_text:
            summary_parts.append("Known for pizza")
        elif 'sushi' in combined_text:
            summary_parts.append("Known for sushi")
        elif 'steak' in combined_text:
            summary_parts.append("Known for steak")
        else:
            summary_parts.append("Often praised")
    
    # Add specific detail
    if keyword_counts.get('service', 0) >= 2:
        summary_parts.append("attentive service")
    elif keyword_counts.get('fresh', 0) >= 2:
        summary_parts.append("fresh ingredients")
    elif keyword_counts.get('portions', 0) >= 2:
        if 'generous' in combined_text or 'large' in combined_text:
            summary_parts.append("generous portions")
    elif keyword_counts.get('ambiance', 0) >= 2:
        if 'cozy' in combined_text:
            summary_parts.append("cozy atmosphere")
        elif 'romantic' in combined_text:
            summary_parts.append("romantic setting")
    
    # Add caution if frequently mentioned
    cautions = []
    if keyword_counts.get('wait', 0) >= 3:
        cautions.append("can get busy")
    elif keyword_counts.get('loud', 0) >= 2:
        cautions.append("can be loud")
    elif keyword_counts.get('pricey', 0) >= 2:
        cautions.append("on the pricier side")
    elif keyword_counts.get('small', 0) >= 2:
        cautions.append("intimate space")
    
    # Combine into one sentence
    if summary_parts:
        sentence = summary_parts[0]
        if len(summary_parts) > 1:
            sentence += f" with {summary_parts[1]}"
        if cautions:
            sentence += f", though {cautions[0]}"
        sentence += "."
    else:
        # Fallback: generic positive summary
        sentence = "Well-regarded by diners."
    
    # Ensure length constraint
    if len(sentence) > 220:
        # Truncate at last complete word before 220
        sentence = sentence[:220].rsplit(' ', 1)[0] + "..."
    
    return sentence


def extract_place_id_from_url(url: str) -> str | None:
    """Extract place_id from Google Maps URL if present."""
    if not url:
        return None
    
    # Pattern: .../data=!4m2!3m1!1s<PLACE_ID>
    # Place ID format: hexadecimal with colons, e.g., 0x4786c7912565cdf7:0x3a14ed6389b46858
    # Match everything after !1s until the next ! or end of string
    pattern = r'!1s([^!&?]+)'
    match = re.search(pattern, url)
    if match:
        place_id = match.group(1)
        # Clean up any trailing characters
        place_id = place_id.rstrip('&?')
        return place_id if place_id and len(place_id) > 1 else None
    return None


def main():
    data_dir = Path(__file__).parent.parent / 'data'
    master_file = data_dir / 'restaurants_master.csv'
    public_signals_file = data_dir / 'public_signals.csv'
    
    if not master_file.exists():
        print(f"ERROR: {master_file} not found")
        sys.exit(1)
    
    # Load restaurants with place_id (extract from URL if missing)
    restaurants = {}
    with open(master_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            restaurant_id = row.get('restaurant_id', '')
            place_id = row.get('place_id', '').strip()
            
            # If place_id is missing, try to extract from URL
            if not place_id:
                url = row.get('google_maps_url', '').strip()
                place_id = extract_place_id_from_url(url)
            
            if place_id:
                restaurants[restaurant_id] = {
                    'place_id': place_id,
                    'name': row.get('name', ''),
                    'city': row.get('city', '')
                }
    
    print(f"Found {len(restaurants)} restaurants with place_id")
    
    # Load existing public signals
    public_signals = {}
    fieldnames = ['restaurant_id', 'public_rating', 'public_review_count', 'price_tier', 'source',
                  'public_summary', 'public_snippets_json', 'public_summary_updated_at']
    
    if public_signals_file.exists():
        with open(public_signals_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Handle missing columns gracefully
            existing_fieldnames = reader.fieldnames or []
            for row in reader:
                restaurant_id = row.get('restaurant_id', '')
                public_signals[restaurant_id] = dict(row)
                # Ensure new columns exist
                if 'public_summary' not in public_signals[restaurant_id]:
                    public_signals[restaurant_id]['public_summary'] = ''
                if 'public_snippets_json' not in public_signals[restaurant_id]:
                    public_signals[restaurant_id]['public_snippets_json'] = ''
                if 'public_summary_updated_at' not in public_signals[restaurant_id]:
                    public_signals[restaurant_id]['public_summary_updated_at'] = ''
    else:
        # Create new file structure
        print("Creating new public_signals.csv")
    
    # Identify restaurants that need enrichment
    to_enrich = []
    for restaurant_id, restaurant in restaurants.items():
        signal = public_signals.get(restaurant_id, {})
        public_summary = signal.get('public_summary', '').strip()
        updated_at = signal.get('public_summary_updated_at', '').strip()
        snippets_json = signal.get('public_snippets_json', '').strip()
        
        if (not public_summary or 
            not snippets_json or 
            is_stale(updated_at, days=30)):
            to_enrich.append((restaurant_id, restaurant))
    
    print(f"Found {len(to_enrich)} restaurants to enrich")
    
    if not to_enrich:
        print("All restaurants are up to date!")
        return
    
    # Enrich restaurants
    enriched_count = 0
    for i, (restaurant_id, restaurant) in enumerate(to_enrich):
        place_id = restaurant['place_id']
        name = restaurant['name']
        city = restaurant.get('city', '')
        
        print(f"  [{i+1}/{len(to_enrich)}] Enriching {name}...")
        
        # Fetch place details using searchText
        place_data = fetch_place_details(place_id, name, city)
        time.sleep(0.2)  # Rate limiting (more conservative for searchText)
        
        if not place_data:
            print(f"    Skipping {name} (no data returned)")
            continue
        
        # Initialize signal if needed
        if restaurant_id not in public_signals:
            public_signals[restaurant_id] = {
                'restaurant_id': restaurant_id,
                'public_rating': '',
                'public_review_count': '',
                'price_tier': '',
                'source': 'google_maps',
                'public_summary': '',
                'public_snippets_json': '',
                'public_summary_updated_at': ''
            }
        
        signal = public_signals[restaurant_id]
        
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
            # Store snippets as JSON
            signal['public_snippets_json'] = json.dumps(snippets)
            
            # Generate summary
            summary = build_public_summary(snippets)
            signal['public_summary'] = summary
            signal['public_summary_updated_at'] = datetime.now().isoformat()
            
            enriched_count += 1
            print(f"    ✓ Added summary: {summary[:60]}...")
        else:
            print(f"    Warning: No reviews returned for place_id={place_id}, skipping summary")
            signal['public_snippets_json'] = ''
            signal['public_summary'] = ''
            signal['public_summary_updated_at'] = datetime.now().isoformat()
    
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
                    'public_summary': '',
                    'public_snippets_json': '',
                    'public_summary_updated_at': ''
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
    
    print(f"\n✓ Enriched {enriched_count} restaurants with public summaries")
    print(f"✓ Updated {public_signals_file}")


if __name__ == '__main__':
    main()

