#!/usr/bin/env python3
"""
Step 4: Ranking and explanation system for restaurant recommendations.

Loads data from master, experience, and public signals CSVs.
Scores restaurants based on query matches and personal signals.
Generates explanations for recommendations.
Includes distance-based ranking using Google Maps APIs.
"""

import csv
import re
import math
import os
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth (in kilometers).
    Uses the Haversine formula.
    """
    # Radius of Earth in kilometers
    R = 6371.0
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


def geocode_location(location_text: str) -> Tuple[float, float] | None:
    """
    Geocode a location string (e.g., "Williamsburg Brooklyn") to lat/lng.
    Returns (latitude, longitude) or None if geocoding fails.
    """
    if not GOOGLE_MAPS_API_KEY:
        return None
    
    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": location_text,
        "key": GOOGLE_MAPS_API_KEY
    }
    
    try:
        response = requests.get(geocode_url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'OK' and data.get('results'):
                location = data['results'][0]['geometry']['location']
                return (location.get('lat'), location.get('lng'))
    except Exception as e:
        print(f"Geocoding error for '{location_text}': {e}")
    
    return None


def get_query_location(parsed_query: Dict) -> Tuple[float, float] | None:
    """
    Extract and geocode the query location from parsed_query.
    Returns (latitude, longitude) or None.
    """
    city = parsed_query.get('city')
    neighborhood = parsed_query.get('neighborhood')
    
    if not city and not neighborhood:
        return None
    
    # Build location string
    location_parts = []
    if neighborhood:
        location_parts.append(neighborhood)
    if city:
        location_parts.append(city)
    
    location_text = ', '.join(location_parts)
    return geocode_location(location_text)


def load_data() -> List[Dict]:
    """
    Load the three CSVs and join on restaurant_id.
    Returns a list of dictionaries with all columns merged.
    """
    data_dir = Path(__file__).parent.parent / 'data'
    
    # Load master
    master_file = data_dir / 'restaurants_master.csv'
    restaurants = {}
    
    with open(master_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            restaurant_id = row.get('restaurant_id', '')
            restaurants[restaurant_id] = dict(row)
    
    # Load experience signals
    experience_file = data_dir / 'experience_signals.csv'
    with open(experience_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            restaurant_id = row.get('restaurant_id', '')
            if restaurant_id in restaurants:
                # Merge experience signals (skip restaurant_id, status, your_note as they're in master)
                for key, value in row.items():
                    if key not in ['restaurant_id', 'status', 'your_note']:
                        restaurants[restaurant_id][key] = value
    
    # Load public signals
    public_file = data_dir / 'public_signals.csv'
    with open(public_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            restaurant_id = row.get('restaurant_id', '')
            if restaurant_id in restaurants:
                # Merge public signals (including new fields: public_summary, public_snippets_json, public_summary_updated_at)
                for key, value in row.items():
                    if key != 'restaurant_id':
                        restaurants[restaurant_id][key] = value
    
    return list(restaurants.values())


def parse_query(query: str) -> Dict:
    """
    Parse natural language query into structured dict.
    Returns: city, neighborhood, vibe_keywords, best_for_keywords, price_hint, cuisine_keywords
    """
    query_lower = query.lower()
    
    result = {
        'city': None,
        'neighborhood': None,
        'vibe_keywords': [],
        'best_for_keywords': [],
        'price_hint': None,
        'cuisine_keywords': []
    }
    
    # City detection
    if 'nyc' in query_lower or 'new york' in query_lower or 'new york city' in query_lower:
        result['city'] = 'NYC'
    elif 'milan' in query_lower:
        result['city'] = 'Milan'
    
    # Neighborhood detection (common ones)
    neighborhoods = {
        'nyc': ['soho', 'williamsburg', 'east village', 'west village', 'lower east side', 
                'upper east side', 'upper west side', 'chelsea', 'greenwich village', 
                'tribeca', 'chinatown', 'koreatown', 'ktown', 'lic', 'long island city',
                'flatiron', 'east village', 'west village'],
        'milan': ['navigli', 'brera', 'duomo', 'porta nuova', 'isola', 'garibaldi']
    }
    
    for city, hoods in neighborhoods.items():
        for hood in hoods:
            if hood in query_lower:
                result['neighborhood'] = hood
                if not result['city']:
                    result['city'] = city
                break
    
    # Vibe keywords
    vibe_patterns = {
        'romantic': ['romantic', 'romance', 'date', 'date night', 'intimate'],
        'cozy': ['cozy', 'cute', 'warm', 'intimate'],
        'casual': ['casual', 'chill', 'relaxed', 'laid back'],
        'trendy': ['trendy', 'vibey', 'vibe', 'hip', 'cool'],
        'upscale': ['upscale', 'fancy', 'fine dining', 'elegant', 'sophisticated'],
        'loud': ['loud', 'buzzing', 'energetic'],
        'classic': ['classic', 'traditional'],
        'modern': ['modern', 'contemporary']
    }
    
    for vibe, patterns in vibe_patterns.items():
        if any(pattern in query_lower for pattern in patterns):
            result['vibe_keywords'].append(vibe)
    
    # Best for keywords
    best_for_patterns = {
        'date': ['date', 'romantic', 'romance', 'intimate'],
        'friends': ['friends', 'group', 'with friends'],
        'solo': ['solo', 'alone', 'by myself'],
        'parents': ['parents', 'family', 'with family'],
        'celebration': ['celebration', 'birthday', 'anniversary', 'special'],
        'work_meeting': ['work', 'business', 'meeting', 'lunch meeting'],
        'quick_bite': ['quick', 'fast', 'lunch', 'grab', 'quick bite'],
        'late_night': ['late night', 'late-night', 'after hours']
    }
    
    for best_for, patterns in best_for_patterns.items():
        if any(pattern in query_lower for pattern in patterns):
            result['best_for_keywords'].append(best_for)
    
    # Price hints
    if any(word in query_lower for word in ['cheap', 'affordable', 'budget', 'inexpensive']):
        result['price_hint'] = 'cheap'
    elif any(word in query_lower for word in ['expensive', 'pricey', 'upscale', 'fancy']):
        result['price_hint'] = 'expensive'
    
    # Cuisine keywords
    cuisines = ['italian', 'pasta', 'pizza', 'chinese', 'korean', 'japanese', 'sushi', 
                'thai', 'indian', 'french', 'mexican', 'tacos', 'bbq', 'seafood', 
                'steak', 'ramen', 'dumplings', 'mediterranean']
    
    for cuisine in cuisines:
        if cuisine in query_lower:
            result['cuisine_keywords'].append(cuisine)
    
    return result


def score_restaurant(row: Dict, parsed_query: Dict, query_location: Tuple[float, float] | None = None) -> Dict:
    """
    Score a restaurant based on query and signals.
    Returns: final_score, components (match_score, taste_score, public_score), matched_reasons, distance_km
    """
    # Initialize scores
    match_score = 0.0
    taste_score = 0.0
    public_score = 0.0
    matched_reasons = []
    distance_km = None
    
    # Match score (0-40): city and keyword overlap
    city = row.get('city', '').strip()
    query_city = parsed_query.get('city')
    
    if query_city and city == query_city:
        match_score += 15
        matched_reasons.append('city_match')
    elif not query_city:
        # If no city specified, don't penalize
        match_score += 10
    
    # Neighborhood match
    neighborhood = row.get('neighborhood', '').strip().lower()
    query_neighborhood = parsed_query.get('neighborhood', '').lower() if parsed_query.get('neighborhood') else None
    
    if query_neighborhood and query_neighborhood in neighborhood:
        match_score += 10
        matched_reasons.append('neighborhood_match')
    
    # Distance-based scoring (if query location and restaurant location available)
    restaurant_lat = row.get('latitude', '').strip()
    restaurant_lng = row.get('longitude', '').strip()
    
    if query_location and restaurant_lat and restaurant_lng:
        try:
            rest_lat = float(restaurant_lat)
            rest_lng = float(restaurant_lng)
            distance_km = haversine_distance(
                query_location[0], query_location[1],
                rest_lat, rest_lng
            )
            
            # Distance scoring: closer = higher score
            # 0-2km: +10 points
            # 2-5km: +5 points
            # 5-10km: +2 points
            # >10km: 0 points
            if distance_km <= 2:
                match_score += 10
                matched_reasons.append('distance_very_close')
            elif distance_km <= 5:
                match_score += 5
                matched_reasons.append('distance_close')
            elif distance_km <= 10:
                match_score += 2
                matched_reasons.append('distance_nearby')
            # >10km gets no distance bonus
        except (ValueError, TypeError):
            pass  # Invalid coordinates, skip distance scoring
    
    # Vibe keyword matching
    vibe_tags = row.get('vibe', '').strip()
    if vibe_tags:
        vibe_list = [v.strip() for v in vibe_tags.split('|') if v.strip()]
        query_vibes = parsed_query.get('vibe_keywords', [])
        
        for query_vibe in query_vibes:
            if query_vibe in vibe_list:
                match_score += 5
                matched_reasons.append(f'vibe_{query_vibe}')
    
    # Best for keyword matching
    best_for_tags = row.get('best_for', '').strip()
    if best_for_tags:
        best_for_list = [b.strip() for b in best_for_tags.split('|') if b.strip()]
        query_best_for = parsed_query.get('best_for_keywords', [])
        
        for query_best_for_tag in query_best_for:
            if query_best_for_tag in best_for_list:
                match_score += 5
                matched_reasons.append(f'best_for_{query_best_for_tag}')
    
    # Food strength matching
    food_strength_tags = row.get('food_strength', '').strip()
    if food_strength_tags:
        food_list = [f.strip() for f in food_strength_tags.split('|') if f.strip()]
        query_cuisines = parsed_query.get('cuisine_keywords', [])
        
        for query_cuisine in query_cuisines:
            if query_cuisine in food_list:
                match_score += 3
                matched_reasons.append(f'cuisine_{query_cuisine}')
    
    # Cap match score at 40
    match_score = min(match_score, 40.0)
    
    # Taste score (0-40): status and confidence
    status = row.get('status', '').strip()
    confidence = row.get('confidence', '').strip()
    would_recommend = row.get('would_recommend', '').strip()
    
    # Base score from status and confidence
    if status == 'tried':
        if confidence == 'high':
            taste_score = 40
        elif confidence == 'medium':
            taste_score = 28
        elif confidence == 'low':
            taste_score = 18
        else:
            taste_score = 28  # Default for tried
    elif status == 'want_to_try':
        taste_score = 12
    else:
        taste_score = 10
    
    # Adjust based on would_recommend
    if would_recommend == 'yes':
        taste_score += 6
    elif would_recommend == 'maybe':
        taste_score += 2
    elif would_recommend == 'no':
        taste_score -= 30
    
    # Cap taste score
    taste_score = max(0.0, min(taste_score, 40.0))
    
    # Public score (0-20): rating and review count
    public_rating = row.get('public_rating', '').strip()
    public_review_count = row.get('public_review_count', '').strip()
    
    # Rating contribution (0-12): linear scaling from 3.5 to 5.0
    if public_rating:
        try:
            rating = float(public_rating)
            if 3.5 <= rating <= 5.0:
                # Linear scaling: 3.5 -> 0, 5.0 -> 12
                rating_contribution = ((rating - 3.5) / (5.0 - 3.5)) * 12
                public_score += rating_contribution
            elif rating > 5.0:
                public_score += 12
        except (ValueError, TypeError):
            pass
    
    # Review count contribution (0-8): log scaling
    if public_review_count:
        try:
            review_count = int(public_review_count)
            if review_count > 0:
                # Log scaling: log10(100) -> 0, log10(10000) -> 8
                # Using log base 10, scaled
                log_count = math.log10(max(100, review_count))
                review_contribution = min(8.0, (log_count - 2) * 2)  # log10(100)=2, log10(10000)=4
                public_score += max(0.0, review_contribution)
        except (ValueError, TypeError):
            pass
    
    # Cap public score at 20
    public_score = min(public_score, 20.0)
    
    # Calculate final score
    final_score = match_score + taste_score + public_score
    
    # Hard rule: if would_recommend == "no", cap at 10 unless query contains restaurant name
    restaurant_name = row.get('name', '').lower()
    query_parts = [
        parsed_query.get('city') or '',
        parsed_query.get('neighborhood') or '',
        ' '.join(parsed_query.get('vibe_keywords', [])),
        ' '.join(parsed_query.get('best_for_keywords', [])),
        ' '.join(parsed_query.get('cuisine_keywords', []))
    ]
    query_lower = ' '.join([p for p in query_parts if p]).lower()
    
    if would_recommend == 'no' and restaurant_name not in query_lower:
        final_score = min(final_score, 10.0)
    
    return {
        'final_score': final_score,
        'components': {
            'match_score': match_score,
            'taste_score': taste_score,
            'public_score': public_score
        },
        'matched_reasons': matched_reasons,
        'distance_km': round(distance_km, 1) if distance_km is not None else None
    }


def build_explanation(row: Dict, parsed_query: Dict, score_components: Dict) -> str:
    """
    Create a short explanation line using up to two reasons.
    First a query match reason, then a personal reason.
    Optionally add public proof phrase if rating exists.
    """
    reasons = []
    matched_reasons = score_components.get('matched_reasons', [])
    
    # Query match reason (first priority)
    if 'neighborhood_match' in matched_reasons:
        neighborhood = row.get('neighborhood', '').strip()
        if neighborhood:
            reasons.append(f"in {neighborhood}")
    
    vibe_tags = row.get('vibe', '').strip()
    if vibe_tags:
        vibe_list = [v.strip() for v in vibe_tags.split('|') if v.strip()]
        query_vibes = parsed_query.get('vibe_keywords', [])
        matching_vibes = [v for v in query_vibes if v in vibe_list]
        if matching_vibes:
            vibe_name = matching_vibes[0]
            if vibe_name == 'upscale':
                reasons.append("upscale and elegant")
            elif vibe_name == 'romantic':
                reasons.append("romantic and intimate")
            elif vibe_name == 'casual':
                reasons.append("casual and relaxed")
            elif vibe_name == 'cozy':
                reasons.append("cozy and warm")
            else:
                reasons.append(f"{vibe_name} vibes")
    
    best_for_tags = row.get('best_for', '').strip()
    if best_for_tags:
        best_for_list = [b.strip() for b in best_for_tags.split('|') if b.strip()]
        query_best_for = parsed_query.get('best_for_keywords', [])
        matching_best_for = [b for b in query_best_for if b in best_for_list]
        if matching_best_for:
            if matching_best_for[0] == 'date':
                reasons.append("perfect for dates")
            elif matching_best_for[0] == 'friends':
                reasons.append("great with friends")
            elif matching_best_for[0] == 'quick_bite':
                reasons.append("quick and easy")
    
    # Personal reason from your_note or tags
    your_note = row.get('your_note', '').strip()
    if your_note and your_note != '-':
        # Extract key phrases
        note_lower = your_note.lower()
        if 'favorite' in note_lower or 'fav' in note_lower:
            reasons.append("one of my favorites")
        elif 'love' in note_lower or 'loved' in note_lower:
            reasons.append("I loved it")
        elif 'really good' in note_lower or 'super good' in note_lower:
            reasons.append("really good food")
        elif 'best' in note_lower:
            reasons.append("the best")
        elif 'cute' in note_lower and 'vibe' in note_lower:
            reasons.append("super cute vibes")
        elif 'authentic' in note_lower:
            reasons.append("authentic")
        elif 'cheap' in note_lower or 'affordable' in note_lower:
            reasons.append("great value")
        else:
            # Use a short phrase from the note
            words = your_note.split()[:5]
            if len(words) >= 3:
                reasons.append(' '.join(words).lower())
    
    # If no personal reason yet, use status
    if len(reasons) < 2:
        status = row.get('status', '').strip()
        if status == 'tried':
            confidence = row.get('confidence', '').strip()
            if confidence == 'high':
                reasons.append("I highly recommend")
            else:
                reasons.append("I've tried and liked")
        elif status == 'want_to_try':
            reasons.append("on my list to try")
    
    # Limit to 2 reasons
    reasons = reasons[:2]
    
    # Build explanation
    if not reasons:
        explanation = "a great match"
    else:
        explanation = ", ".join(reasons)
    
    # Add public proof if available
    public_rating = row.get('public_rating', '').strip()
    public_review_count = row.get('public_review_count', '').strip()
    
    if public_rating and public_review_count:
        try:
            rating = float(public_rating)
            review_count = int(public_review_count)
            if rating >= 4.5 and review_count >= 100:
                explanation += f" ({rating:.1f}★, {review_count:,} reviews)"
            elif rating >= 4.0:
                explanation += f" ({rating:.1f}★)"
        except (ValueError, TypeError):
            pass
    
    return explanation


def recommend(query: str, top_n: int = 6, city: Optional[str] = None) -> List[Dict]:
    """
    Main recommendation function.
    Returns list of dicts with: restaurant_id, name, city, neighborhood, status, 
    final_score, why, price_tier, public_rating, public_review_count, distance_km
    """
    # Load data
    restaurants = load_data()
    
    # Parse query
    parsed_query = parse_query(query)
    
    # Override city if provided
    if city:
        parsed_query['city'] = city
    
    # Geocode query location for distance scoring
    query_location = get_query_location(parsed_query)
    
    # Score all restaurants
    scored_restaurants = []
    for row in restaurants:
        score_result = score_restaurant(row, parsed_query, query_location)
        
        # Build explanation
        why = build_explanation(row, parsed_query, score_result)
        
        scored_restaurants.append({
            'restaurant_id': row.get('restaurant_id', ''),
            'name': row.get('name', ''),
            'city': row.get('city', ''),
            'neighborhood': row.get('neighborhood', ''),
            'status': row.get('status', ''),
            'final_score': score_result['final_score'],
            'why': why,
            'price_tier': row.get('price_tier', ''),
            'public_rating': row.get('public_rating', ''),
            'public_review_count': row.get('public_review_count', ''),
            'distance_km': score_result.get('distance_km'),
            '_row': row  # Keep original row for sorting
        })
    
    # Sort by final_score descending
    scored_restaurants.sort(key=lambda x: x['final_score'], reverse=True)
    
    # Hard rule: at most one want_to_try in top 6
    result = []
    want_to_try_count = 0
    
    for restaurant in scored_restaurants:
        if restaurant['status'] == 'want_to_try':
            if want_to_try_count >= 1:
                continue
            want_to_try_count += 1
        
        result.append({
            'restaurant_id': restaurant['restaurant_id'],
            'name': restaurant['name'],
            'city': restaurant['city'],
            'neighborhood': restaurant['neighborhood'],
            'status': restaurant['status'],
            'final_score': round(restaurant['final_score'], 1),
            'why': restaurant['why'],
            'price_tier': restaurant['price_tier'],
            'public_rating': restaurant['public_rating'],
            'public_review_count': restaurant['public_review_count'],
            'public_vibe': restaurant.get('public_vibe', ''),
            'public_vibe_source': restaurant.get('public_vibe_source', ''),
            'public_vibe_model': restaurant.get('public_vibe_model', ''),
            'distance_km': restaurant.get('distance_km')
        })
        
        if len(result) >= top_n:
            break
    
    return result

