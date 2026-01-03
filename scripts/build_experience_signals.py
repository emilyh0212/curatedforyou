#!/usr/bin/env python3
"""
Build experience_signals.csv from restaurants_master.csv
"""

import csv
import re
from pathlib import Path
from collections import Counter

# Controlled tag dictionaries
BEST_FOR_TAGS = {
    'date', 'friends', 'solo', 'parents', 'celebration', 
    'work_meeting', 'quick_bite', 'late_night'
}

VIBE_TAGS = {
    'cozy', 'loud', 'trendy', 'romantic', 'casual', 'upscale', 
    'tiny', 'buzzing', 'classic', 'modern'
}

FOOD_STRENGTH_TAGS = {
    'pasta', 'steak', 'sushi', 'pizza', 'seafood', 'bbq', 'dumplings', 
    'ramen', 'tacos', 'thai', 'indian', 'mediterranean', 'cafe', 
    'cocktails', 'wine', 'dessert', 'bakery'
}

DEALBREAKERS_TAGS = {
    'too_loud', 'touristy', 'overpriced', 'long_wait', 
    'bad_service', 'hard_to_book'
}

# Strong sentiment words for confidence inference
STRONG_POSITIVE = [
    'amazing', 'love', 'loved', 'best', 'favorite', 'fav', 'must', 
    'perfect', 'incredible', 'excellent', 'superb', 'fantastic', 
    'immaculate', 'really really good', 'really good'
]

STRONG_NEGATIVE = [
    'terrible', 'never', 'worst', 'bad', 'awful', 'hate', 'disappointing',
    'bland', 'overrated'
]

# Positive indicators for would_recommend
POSITIVE_INDICATORS = [
    'good', 'great', 'love', 'loved', 'favorite', 'fav', 'best', 
    'amazing', 'perfect', 'excellent', 'really good', 'super', 
    'cute', 'nice', 'solid', 'authentic'
]

# Negative indicators for would_recommend
NEGATIVE_INDICATORS = [
    'bad', 'terrible', 'worst', 'never', 'hate', 'disappointing',
    'bland', 'overrated', 'nothing stood out', 'slightly bland'
]

def normalize_text(text):
    """Normalize text for matching."""
    if not text:
        return ''
    return text.lower().strip()

def infer_confidence(note, status):
    """Infer confidence level from note."""
    if status == 'want_to_try':
        return 'low'
    
    if not note or note == '-':
        return 'medium'
    
    note_lower = normalize_text(note)
    
    # Check for strong positive or negative language
    for word in STRONG_POSITIVE + STRONG_NEGATIVE:
        if word in note_lower:
            return 'high'
    
    return 'medium'

def infer_would_recommend(note, status):
    """Infer would_recommend from note."""
    if status == 'want_to_try':
        return 'maybe'
    
    if not note or note == '-':
        return 'maybe'
    
    note_lower = normalize_text(note)
    
    # Count positive vs negative indicators
    positive_count = sum(1 for word in POSITIVE_INDICATORS if word in note_lower)
    negative_count = sum(1 for word in NEGATIVE_INDICATORS if word in note_lower)
    
    if negative_count > positive_count:
        return 'no'
    elif positive_count > negative_count:
        return 'yes'
    else:
        return 'maybe'

def infer_best_for(note):
    """Infer best_for tags from note."""
    if not note or note == '-':
        return ''
    
    note_lower = normalize_text(note)
    tags = []
    
    # Direct mentions
    if 'date' in note_lower or 'dates' in note_lower:
        tags.append('date')
    if 'friend' in note_lower or 'friends' in note_lower:
        tags.append('friends')
    if 'solo' in note_lower:
        tags.append('solo')
    if 'parent' in note_lower:
        tags.append('parents')
    if 'celebration' in note_lower or 'birthday' in note_lower:
        tags.append('celebration')
    if 'work' in note_lower or 'meeting' in note_lower:
        tags.append('work_meeting')
    if 'quick' in note_lower or 'fast' in note_lower or 'takeout' in note_lower:
        tags.append('quick_bite')
    if 'late night' in note_lower or 'late-night' in note_lower:
        tags.append('late_night')
    
    # Context clues
    if 'brunch' in note_lower and 'friend' in note_lower:
        tags.append('friends')
    if 'lunch' in note_lower and ('casual' in note_lower or 'quick' in note_lower):
        tags.append('quick_bite')
    
    # Remove duplicates and return pipe-separated
    return '|'.join(sorted(set(tags)))

def infer_vibe(note):
    """Infer vibe tags from note."""
    if not note or note == '-':
        return ''
    
    note_lower = normalize_text(note)
    tags = []
    
    # Direct mentions
    if 'cozy' in note_lower:
        tags.append('cozy')
    if 'loud' in note_lower:
        tags.append('loud')
    if 'trendy' in note_lower or 'vibey' in note_lower or 'vibe' in note_lower:
        tags.append('trendy')
    if 'romantic' in note_lower:
        tags.append('romantic')
    if 'casual' in note_lower:
        tags.append('casual')
    if 'upscale' in note_lower or 'fancy' in note_lower or 'fine dining' in note_lower:
        tags.append('upscale')
    if 'tiny' in note_lower or 'small' in note_lower:
        tags.append('tiny')
    if 'buzzing' in note_lower or 'busy' in note_lower:
        tags.append('buzzing')
    if 'classic' in note_lower:
        tags.append('classic')
    if 'modern' in note_lower:
        tags.append('modern')
    
    # Context clues
    if 'cute' in note_lower and 'vibe' in note_lower:
        tags.append('cozy')
    if 'chill' in note_lower:
        tags.append('casual')
    if 'roof top' in note_lower or 'rooftop' in note_lower:
        tags.append('trendy')
    
    # Remove duplicates and return pipe-separated
    return '|'.join(sorted(set(tags)))

def infer_food_strength(note, name, cuisine):
    """Infer food_strength tags from note, name, and cuisine."""
    tags = []
    
    # Combine all text sources
    text = ' '.join([note or '', name or '', cuisine or '']).lower()
    
    if not text or text.strip() == '-':
        return ''
    
    # Direct mentions in note
    if 'pasta' in text:
        tags.append('pasta')
    if 'steak' in text:
        tags.append('steak')
    if 'sushi' in text:
        tags.append('sushi')
    if 'pizza' in text:
        tags.append('pizza')
    if 'seafood' in text or 'fish' in text:
        tags.append('seafood')
    if 'bbq' in text or 'barbecue' in text or 'kbbq' in text:
        tags.append('bbq')
    if 'dumpling' in text:
        tags.append('dumplings')
    if 'ramen' in text:
        tags.append('ramen')
    if 'taco' in text:
        tags.append('tacos')
    if 'thai' in text:
        tags.append('thai')
    if 'indian' in text:
        tags.append('indian')
    if 'mediterranean' in text:
        tags.append('mediterranean')
    if 'cafe' in text or 'coffee' in text:
        tags.append('cafe')
    if 'cocktail' in text:
        tags.append('cocktails')
    if 'wine' in text:
        tags.append('wine')
    if 'dessert' in text or 'tiramisu' in text or 'sweet' in text:
        tags.append('dessert')
    if 'bakery' in text or 'bagel' in text:
        tags.append('bakery')
    
    # Cuisine-based inference
    cuisine_lower = (cuisine or '').lower()
    if 'chinese' in cuisine_lower or 'chinese' in text:
        if 'dumpling' not in text:
            tags.append('dumplings')  # Common Chinese food
    if 'korean' in cuisine_lower or 'korean' in text:
        if 'bbq' not in text:
            tags.append('bbq')  # Common Korean food
    if 'japanese' in cuisine_lower or 'japanese' in text:
        if 'sushi' not in text and 'ramen' not in text:
            tags.append('sushi')  # Common Japanese food
    if 'italian' in cuisine_lower or 'italian' in text:
        if 'pasta' not in text and 'pizza' not in text:
            tags.append('pasta')  # Common Italian food
    
    # Remove duplicates and return pipe-separated
    return '|'.join(sorted(set(tags)))

def infer_dealbreakers(note):
    """Infer dealbreakers from note."""
    if not note or note == '-':
        return ''
    
    note_lower = normalize_text(note)
    tags = []
    
    # Direct mentions
    if 'too loud' in note_lower or 'very loud' in note_lower:
        tags.append('too_loud')
    if 'touristy' in note_lower or 'tourist' in note_lower:
        tags.append('touristy')
    if 'overpriced' in note_lower or 'expensive' in note_lower:
        tags.append('overpriced')
    if 'long wait' in note_lower or 'wait' in note_lower:
        tags.append('long_wait')
    if 'bad service' in note_lower or 'service' in note_lower and 'bad' in note_lower:
        tags.append('bad_service')
    if 'hard to book' in note_lower or 'reservation' in note_lower:
        tags.append('hard_to_book')
    
    # Remove duplicates and return pipe-separated
    return '|'.join(sorted(set(tags)))

def main():
    data_dir = Path(__file__).parent.parent / 'data'
    master_file = data_dir / 'restaurants_master.csv'
    output_file = data_dir / 'experience_signals.csv'
    
    # Read master file
    restaurants = []
    with open(master_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        restaurants = list(reader)
    
    # Build experience signals
    signals = []
    for restaurant in restaurants:
        restaurant_id = restaurant.get('restaurant_id', '')
        status = restaurant.get('status', '')
        your_note = restaurant.get('your_note', '')
        name = restaurant.get('name', '')
        cuisine = restaurant.get('cuisine', '')
        
        # Copy basic fields
        signal = {
            'restaurant_id': restaurant_id,
            'status': status,
            'your_note': your_note,
            'your_rating': '',  # Always blank for now
            'would_recommend': infer_would_recommend(your_note, status),
            'best_for': infer_best_for(your_note),
            'vibe': infer_vibe(your_note),
            'food_strength': infer_food_strength(your_note, name, cuisine),
            'dealbreakers': infer_dealbreakers(your_note),
            'confidence': infer_confidence(your_note, status)
        }
        
        signals.append(signal)
    
    # Write output file
    fieldnames = [
        'restaurant_id', 'status', 'your_note', 'your_rating', 
        'would_recommend', 'best_for', 'vibe', 'food_strength', 
        'dealbreakers', 'confidence'
    ]
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(signals)
    
    # Summary statistics
    total_rows = len(signals)
    confidence_counts = Counter(s['confidence'] for s in signals)
    status_counts = Counter(s['status'] for s in signals)
    
    print("=" * 60)
    print("EXPERIENCE SIGNALS GENERATED")
    print("=" * 60)
    print(f"\nTotal rows: {total_rows}")
    print(f"\nCounts by confidence:")
    for conf, count in sorted(confidence_counts.items()):
        print(f"  {conf}: {count}")
    print(f"\nCounts by status:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")
    print(f"\n✓ Created {output_file}")

if __name__ == '__main__':
    main()

