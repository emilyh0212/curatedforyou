#!/usr/bin/env python3
"""
Enrich restaurant locations with lat/lng using Google Places API (New).

Reads restaurants_master.csv and enriches with:
- place_id (from Google Places API)
- latitude
- longitude

Uses GOOGLE_MAPS_API_KEY from environment.
"""

import csv
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
    print("Please create a .env file with: GOOGLE_MAPS_API_KEY=your_key_here")
    sys.exit(1)

print("✓ Google Maps API key loaded from environment")

# Google Places API (New) endpoint
PLACES_API_URL = "https://places.googleapis.com/v1/places:searchText"

def extract_place_id_from_url(url: str) -> str | None:
    """Extract place_id from Google Maps URL if present."""
    if not url:
        return None
    
    # Pattern: .../data=!4m2!3m1!1s<PLACE_ID>
    import re
    pattern = r'!1s([0-9a-fA-F:]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

def get_place_details_from_url(url: str) -> dict | None:
    """
    Get place details using place_id extracted from Google Maps URL.
    Returns: {place_id, latitude, longitude} or None
    """
    place_id = extract_place_id_from_url(url)
    if not place_id:
        return None
    
    # Use Places API (New) to get details
    # Note: The new API uses POST for place details
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "id,location"
    }
    
    # Use place_id directly with GET (simpler approach)
    # For new Places API, we might need to use the old Places API Details endpoint
    # as a fallback since the new API structure is different
    place_url = f"https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "key": GOOGLE_MAPS_API_KEY,
        "fields": "geometry"
    }
    
    try:
        response = requests.get(place_url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'OK' and data.get('result'):
                location = data['result']['geometry']['location']
                return {
                    'place_id': place_id,
                    'latitude': location.get('lat'),
                    'longitude': location.get('lng')
                }
        return None
    except Exception as e:
        print(f"  Error fetching place details: {e}")
        return None

def geocode_address(address: str) -> dict | None:
    """
    Geocode an address using Google Geocoding API.
    Returns: {latitude, longitude} or None
    """
    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": GOOGLE_MAPS_API_KEY
    }
    
    try:
        response = requests.get(geocode_url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'OK' and data.get('results'):
                location = data['results'][0]['geometry']['location']
                return {
                    'latitude': location.get('lat'),
                    'longitude': location.get('lng')
                }
        return None
    except Exception as e:
        print(f"  Error geocoding {address}: {e}")
        return None

def main():
    data_dir = Path(__file__).parent.parent / 'data'
    master_file = data_dir / 'restaurants_master.csv'
    output_file = data_dir / 'restaurants_master.csv'  # Update in place
    
    if not master_file.exists():
        print(f"ERROR: {master_file} not found")
        sys.exit(1)
    
    # Read restaurants
    restaurants = []
    with open(master_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        restaurants = list(reader)
    
    print(f"Found {len(restaurants)} restaurants")
    print("Enriching with location data...")
    
    # Check if columns exist, add if not
    has_lat = 'latitude' in restaurants[0] if restaurants else False
    has_lng = 'longitude' in restaurants[0] if restaurants else False
    has_place_id = 'place_id' in restaurants[0] if restaurants else False
    
    enriched_count = 0
    for i, restaurant in enumerate(restaurants):
        name = restaurant.get('name', '')
        url = restaurant.get('google_maps_url', '')
        city = restaurant.get('city', '')
        neighborhood = restaurant.get('neighborhood', '')
        
        # Skip if already enriched
        if has_lat and restaurant.get('latitude'):
            continue
        
        # Try to get from URL first
        place_details = None
        if url:
            place_details = get_place_details_from_url(url)
            time.sleep(0.1)  # Rate limiting
        
        # If not found, try geocoding
        if not place_details and name:
            address = f"{name}, {neighborhood}, {city}" if neighborhood else f"{name}, {city}"
            geocode_result = geocode_address(address)
            if geocode_result:
                place_details = geocode_result
            time.sleep(0.1)  # Rate limiting
        
        if place_details:
            if 'place_id' in place_details:
                restaurant['place_id'] = place_details['place_id']
            if 'latitude' in place_details:
                restaurant['latitude'] = str(place_details['latitude'])
            if 'longitude' in place_details:
                restaurant['longitude'] = str(place_details['longitude'])
            enriched_count += 1
        
        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(restaurants)}...")
    
    # Write back
    fieldnames = list(restaurants[0].keys())
    if 'latitude' not in fieldnames:
        fieldnames.append('latitude')
    if 'longitude' not in fieldnames:
        fieldnames.append('longitude')
    if 'place_id' not in fieldnames:
        fieldnames.append('place_id')
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(restaurants)
    
    print(f"\n✓ Enriched {enriched_count} restaurants with location data")
    print(f"✓ Updated {output_file}")

if __name__ == '__main__':
    main()

