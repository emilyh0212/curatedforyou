#!/usr/bin/env python3
"""
Create restaurants_master.csv from the four source CSV files.
"""

import csv
import re
from pathlib import Path
from collections import OrderedDict

def clean_restaurant_name(name):
    """Clean restaurant name for use in restaurant_id."""
    if not name or name.strip() == '':
        return ''
    # Convert to lowercase, replace spaces and special chars with underscores
    cleaned = re.sub(r'[^\w\s-]', '', str(name))
    cleaned = re.sub(r'[\s-]+', '_', cleaned)
    return cleaned.lower().strip('_')

def generate_restaurant_id(city, name, existing_ids):
    """Generate a unique restaurant_id."""
    city_lower = city.lower()
    name_cleaned = clean_restaurant_name(name)
    
    if not name_cleaned:
        name_cleaned = 'unknown'
    
    base_id = f"{city_lower}_{name_cleaned}"
    
    # Handle duplicates
    counter = 1
    restaurant_id = base_id
    while restaurant_id in existing_ids:
        counter += 1
        restaurant_id = f"{base_id}_{counter}"
    
    existing_ids.add(restaurant_id)
    return restaurant_id

def read_csv_file(filepath, city, status):
    """Read a CSV file and return a list of dictionaries."""
    restaurants = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Skip first row if it's metadata
            first_row = next(reader, None)
            if first_row and not first_row.get('Title') and not first_row.get('title'):
                # This might be a header row, try next
                pass
            
            # Reset and read properly
            f.seek(0)
            lines = f.readlines()
            
            # Find the header row (Title, Note, URL, Tags, Comment)
            header_idx = None
            for i, line in enumerate(lines):
                if 'Title' in line and 'Note' in line and 'URL' in line:
                    header_idx = i
                    break
            
            if header_idx is None:
                print(f"  Warning: Could not find header in {filepath.name}")
                return restaurants
            
            # Read from header row
            reader = csv.DictReader(lines[header_idx:])
            
            for row in reader:
                name = row.get('Title', '').strip()
                if not name or name == '':
                    continue
                
                restaurant = {
                    'name': name,
                    'your_note': row.get('Note', '').strip(),
                    'google_maps_url': row.get('URL', '').strip(),
                    'city': city,
                    'status': status,
                    'source': 'google_maps',
                    'neighborhood': '',
                    'price_tier': '',
                    'public_rating': '',
                    'public_review_count': '',
                    'cuisine': ''
                }
                restaurants.append(restaurant)
                
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    
    return restaurants

def remove_duplicates(restaurants):
    """Remove duplicates by URL first, then by name+city."""
    seen_urls = {}
    seen_name_city = {}
    unique_restaurants = []
    
    for restaurant in restaurants:
        url = restaurant.get('google_maps_url', '').strip()
        name = restaurant.get('name', '').strip()
        city = restaurant.get('city', '').strip()
        
        # First try to dedupe by URL
        if url and url != '':
            if url not in seen_urls:
                seen_urls[url] = restaurant
                unique_restaurants.append(restaurant)
            continue
        
        # If no URL, dedupe by name + city
        key = f"{name}|||{city}"
        if key not in seen_name_city:
            seen_name_city[key] = restaurant
            unique_restaurants.append(restaurant)
    
    return unique_restaurants

def main():
    data_dir = Path(__file__).parent.parent / 'data'
    
    # Read all four files
    files = [
        (data_dir / 'Milan Food.csv', 'Milan', 'tried'),
        (data_dir / 'Milan want to try.csv', 'Milan', 'want_to_try'),
        (data_dir / 'NYC food.csv', 'NYC', 'tried'),
        (data_dir / 'NYC want to try.csv', 'NYC', 'want_to_try'),
    ]
    
    all_restaurants = []
    for filepath, city, status in files:
        print(f"Reading {filepath.name}...")
        restaurants = read_csv_file(filepath, city, status)
        all_restaurants.extend(restaurants)
        print(f"  Found {len(restaurants)} restaurants")
    
    print(f"\nTotal restaurants before deduplication: {len(all_restaurants)}")
    
    # Remove duplicates
    unique_restaurants = remove_duplicates(all_restaurants)
    print(f"Total restaurants after deduplication: {len(unique_restaurants)}")
    
    # Generate restaurant_id for each row
    existing_ids = set()
    for restaurant in unique_restaurants:
        restaurant_id = generate_restaurant_id(
            restaurant['city'],
            restaurant['name'],
            existing_ids
        )
        restaurant['restaurant_id'] = restaurant_id
    
    # Define column order
    columns = [
        'restaurant_id',
        'name',
        'city',
        'neighborhood',
        'status',
        'your_note',
        'google_maps_url',
        'source',
        'price_tier',
        'public_rating',
        'public_review_count',
        'cuisine'
    ]
    
    # Write to CSV
    output_path = data_dir / 'restaurants_master.csv'
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(unique_restaurants)
    
    print(f"\n✓ Created {output_path}")
    print(f"  Total restaurants: {len(unique_restaurants)}")
    
    # Show summary
    print("\nSummary by city and status:")
    summary = {}
    for r in unique_restaurants:
        key = (r['city'], r['status'])
        summary[key] = summary.get(key, 0) + 1
    
    for (city, status), count in sorted(summary.items()):
        print(f"  {city} - {status}: {count}")

if __name__ == '__main__':
    main()
