#!/usr/bin/env python3
"""
Generate "Public vibe" summaries from review snippets using OpenAI LLM.

For each restaurant with review snippets:
- Call OpenAI to generate ONE sentence summary
- Must be grounded only in snippets
- Max 170 characters
- Neutral tone, no hype
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY not found in environment.")
    print("Please create a .env file with: OPENAI_API_KEY=your_key_here")
    sys.exit(1)

# Initialize OpenAI client
openai.api_key = OPENAI_API_KEY

# Cache file for generated vibes
CACHE_FILE = Path(__file__).parent.parent / 'data' / 'public_vibe_cache.json'


def load_cache():
    """Load cached generated vibes."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load cache: {e}")
    return {}


def save_cache(cache):
    """Save generated vibes to cache."""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save cache: {e}")


def is_stale(updated_at_str: str | None, days: int = 30) -> bool:
    """Check if a timestamp is older than N days."""
    if not updated_at_str or updated_at_str.strip() == '':
        return True
    
    try:
        updated_at = datetime.fromisoformat(updated_at_str)
        return datetime.now() - updated_at > timedelta(days=days)
    except (ValueError, TypeError):
        return True


def generate_public_vibe_llm(snippets: list[str], cache: dict = None, restaurant_id: str = "", max_retries: int = 2) -> str:
    """
    Generate a one-sentence "Public vibe" summary using OpenAI.
    Returns the generated summary or empty string on error.
    """
    if not snippets:
        return ""
    
    # Check cache first
    cache_key = restaurant_id or json.dumps(snippets, sort_keys=True)
    if cache and cache_key in cache:
        return cache[cache_key]
    
    # Combine snippets into context
    combined_snippets = '\n'.join([f"- {s}" for s in snippets[:8]])
    
    prompt = f"""Generate a ONE sentence summary (max 170 characters) about this restaurant based ONLY on these review snippets.

Requirements:
- Must be grounded only in the snippets provided
- Include 1 strong positive aspect
- Optionally include 1 caution only if it appears frequently in snippets
- Do NOT say "reviews", "people say", "reviewers mention", or "highly recommend"
- Use neutral, factual tone (e.g., "Known for...", "Expect...", "Often praised for...")
- No hype words like "best ever", "must try", "insanely"
- End with a period

Review snippets:
{combined_snippets}

One sentence summary:"""

    # Retry logic with exponential backoff
    for attempt in range(max_retries):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates concise, factual restaurant summaries based on review snippets."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Ensure it ends with punctuation
            if summary and not summary[-1] in '.!?':
                summary += '.'
            
            # Truncate if too long
            if len(summary) > 170:
                summary = summary[:167].rsplit(' ', 1)[0] + '...'
            
            # Cache the result
            if cache is not None and restaurant_id:
                cache[restaurant_id] = summary
            
            return summary
        
        except (openai.RateLimitError, openai.APIError) as e:
            error_code = getattr(e, 'status_code', None) if hasattr(e, 'status_code') else None
            if error_code == 429 or 'quota' in str(e).lower() or 'rate limit' in str(e).lower():
                # Quota/rate limit - return empty to trigger fallback
                return ""
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 2
                time.sleep(wait_time)
            else:
                return ""
        
        except Exception as e:
            return ""
    
    return ""


def generate_deterministic_vibe(snippets: list[str]) -> str:
    """
    Fallback: Generate a simple deterministic summary when OpenAI is unavailable.
    """
    if not snippets:
        return ""
    
    # Combine all snippets for analysis
    combined_text = ' '.join(snippets).lower()
    
    # Extract key themes
    themes = []
    
    # Food quality
    if any(word in combined_text for word in ['amazing', 'delicious', 'incredible', 'best', 'excellent', 'fantastic', 'great', 'wonderful']):
        if 'pasta' in combined_text:
            themes.append("Known for excellent pasta")
        elif 'pizza' in combined_text:
            themes.append("Known for great pizza")
        elif 'sushi' in combined_text:
            themes.append("Known for quality sushi")
        elif 'steak' in combined_text:
            themes.append("Known for excellent steaks")
        elif 'ramen' in combined_text:
            themes.append("Known for quality ramen")
        else:
            themes.append("Known for quality food")
    
    # Service
    if any(word in combined_text for word in ['service', 'staff', 'friendly', 'attentive', 'helpful', 'welcoming']):
        if 'attentive' in combined_text or 'helpful' in combined_text:
            themes.append("with attentive service")
        elif 'friendly' in combined_text:
            themes.append("with friendly service")
    
    # Atmosphere
    if 'cozy' in combined_text:
        themes.append("cozy atmosphere")
    elif 'romantic' in combined_text:
        themes.append("romantic setting")
    elif 'busy' in combined_text or 'crowded' in combined_text:
        if not themes:
            themes.append("Popular spot")
        themes.append("can get busy")
    
    # Build summary
    if themes:
        summary = themes[0]
        if len(themes) > 1:
            summary += f" {themes[1]}"
        summary += "."
    else:
        summary = "Well-regarded by diners."
    
    # Ensure length
    if len(summary) > 170:
        summary = summary[:167].rsplit(' ', 1)[0] + '...'
    
    return summary


def load_experience_signals():
    """Load experience signals to get status and confidence for prioritization."""
    data_dir = Path(__file__).parent.parent / 'data'
    experience_file = data_dir / 'experience_signals.csv'
    
    experience_lookup = {}
    if experience_file.exists():
        with open(experience_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                restaurant_id = row.get('restaurant_id', '')
                experience_lookup[restaurant_id] = {
                    'status': row.get('status', ''),
                    'confidence': row.get('confidence', '')
                }
    
    return experience_lookup


def prioritize_restaurants(restaurants, experience_lookup, prioritize_tried_high_conf=True):
    """
    Prioritize restaurants based on status and confidence.
    Returns sorted list: (restaurant_id, snippets, priority_score)
    """
    prioritized = []
    
    for restaurant_id, snippets in restaurants:
        status = experience_lookup.get(restaurant_id, {}).get('status', '')
        confidence = experience_lookup.get(restaurant_id, {}).get('confidence', '')
        
        # Calculate priority score
        priority = 0
        if prioritize_tried_high_conf:
            if status == 'tried' and confidence == 'high':
                priority = 100
            elif status == 'tried' and confidence == 'medium':
                priority = 50
            elif status == 'tried' and confidence == 'low':
                priority = 30
            elif status == 'want_to_try':
                priority = 10
        else:
            # Simple: tried > want_to_try
            priority = 50 if status == 'tried' else 10
        
        prioritized.append((priority, restaurant_id, snippets))
    
    # Sort by priority (descending), then by restaurant_id for stability
    prioritized.sort(key=lambda x: (-x[0], x[1]))
    
    return [(rid, snippets) for _, rid, snippets in prioritized]


def main():
    parser = argparse.ArgumentParser(description='Generate public vibes from review snippets')
    parser.add_argument('--limit', type=int, default=30, help='Max number of restaurants to process with LLM (default: 30)')
    parser.add_argument('--prioritize', type=str, default='tried_high_conf', help='Prioritization strategy (default: tried_high_conf)')
    parser.add_argument('--sleep_seconds', type=float, default=2.0, help='Sleep between LLM requests in seconds (default: 2.0)')
    parser.add_argument('--use_llm', type=str, default='true', help='Use LLM for generation (true/false, default: true)')
    
    args = parser.parse_args()
    
    use_llm = args.use_llm.lower() in ('true', '1', 'yes', 'on')
    prioritize_tried_high_conf = args.prioritize == 'tried_high_conf'
    
    print(f"Configuration:")
    print(f"  LLM limit: {args.limit}")
    print(f"  Prioritization: {args.prioritize}")
    print(f"  Sleep between requests: {args.sleep_seconds}s")
    print(f"  Use LLM: {use_llm}")
    print()
    
    if use_llm:
        print("✓ OpenAI API key loaded from environment")
    
    data_dir = Path(__file__).parent.parent / 'data'
    public_signals_file = data_dir / 'public_signals.csv'
    
    if not public_signals_file.exists():
        print(f"ERROR: {public_signals_file} not found")
        sys.exit(1)
    
    # Load cache
    cache = load_cache()
    print(f"Loaded {len(cache)} cached vibes")
    
    # Load experience signals for prioritization
    experience_lookup = load_experience_signals()
    print(f"Loaded experience signals for {len(experience_lookup)} restaurants")
    
    # Load public signals
    public_signals = {}
    fieldnames = ['restaurant_id', 'public_rating', 'public_review_count', 'price_tier', 'source',
                  'public_review_snippets_json', 'public_vibe', 'public_vibe_updated_at',
                  'public_vibe_source', 'public_vibe_model']
    
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
    
    # Identify restaurants that need vibe generation
    to_generate_llm = []
    to_generate_fallback = []
    skipped_fresh = 0
    missing_snippets = 0
    
    for restaurant_id, signal in public_signals.items():
        snippets_json = signal.get('public_review_snippets_json', '').strip()
        public_vibe = signal.get('public_vibe', '').strip()
        updated_at = signal.get('public_vibe_updated_at', '').strip()
        
        if not snippets_json:
            missing_snippets += 1
            continue
        
        try:
            snippets = json.loads(snippets_json)
            if not snippets:
                missing_snippets += 1
                continue
        except json.JSONDecodeError:
            missing_snippets += 1
            continue
        
        # Check if needs backfill (has vibe but missing source)
        vibe_source = signal.get('public_vibe_source', '').strip()
        if public_vibe:
            if not vibe_source:
                # Backfill: add source for existing vibes without source
                to_generate_fallback.append((restaurant_id, snippets))
                continue
            elif vibe_source == 'llm' and not is_stale(updated_at, days=30):
                # Skip fresh LLM vibes
                skipped_fresh += 1
                continue
            elif vibe_source == 'fallback' and not is_stale(updated_at, days=30):
                # Skip fresh fallback vibes
                skipped_fresh += 1
                continue
        
        # Needs generation (no vibe or stale)
        if use_llm and len(to_generate_llm) < args.limit:
            to_generate_llm.append((restaurant_id, snippets))
        else:
            # Will use fallback
            to_generate_fallback.append((restaurant_id, snippets))
    
    # Prioritize LLM candidates
    if to_generate_llm:
        to_generate_llm = prioritize_restaurants(to_generate_llm, experience_lookup, prioritize_tried_high_conf)
    
    print(f"\nRestaurants to process:")
    print(f"  LLM generation: {len(to_generate_llm)}")
    print(f"  Fallback generation: {len(to_generate_fallback)}")
    print(f"  Skipped (fresh): {skipped_fresh}")
    print(f"  Missing snippets: {missing_snippets}")
    print()
    
    # Generate vibes with LLM
    llm_generated = 0
    fallback_generated = 0
    
    for i, (restaurant_id, snippets) in enumerate(to_generate_llm):
        print(f"  [{i+1}/{len(to_generate_llm)}] LLM: {restaurant_id}...")
        
        vibe = ""
        if use_llm:
            vibe = generate_public_vibe_llm(snippets, cache, restaurant_id)
        
        # Use fallback if LLM failed or not using LLM
        if not vibe:
            vibe = generate_deterministic_vibe(snippets)
            if vibe:
                fallback_generated += 1
                print(f"    ✓ Fallback: {vibe[:60]}...")
                public_signals[restaurant_id]['public_vibe'] = vibe
                public_signals[restaurant_id]['public_vibe_source'] = 'fallback'
                public_signals[restaurant_id]['public_vibe_model'] = ''
                public_signals[restaurant_id]['public_vibe_updated_at'] = datetime.now().isoformat()
        else:
            llm_generated += 1
            print(f"    ✓ LLM: {vibe[:60]}...")
            public_signals[restaurant_id]['public_vibe'] = vibe
            public_signals[restaurant_id]['public_vibe_source'] = 'llm'
            public_signals[restaurant_id]['public_vibe_model'] = 'gpt-4o-mini'
            public_signals[restaurant_id]['public_vibe_updated_at'] = datetime.now().isoformat()
        
        # Rate limiting
        if i < len(to_generate_llm) - 1:
            time.sleep(args.sleep_seconds)
        
        # Save progress every 10 restaurants
        if (i + 1) % 10 == 0:
            with open(public_signals_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for rid in sorted(public_signals.keys()):
                    row = public_signals[rid]
                    for field in fieldnames:
                        if field not in row:
                            row[field] = ''
                    writer.writerow(row)
            save_cache(cache)
            print(f"    💾 Progress saved")
    
    # Generate fallback vibes for remaining (or backfill source for existing vibes)
    for i, (restaurant_id, snippets) in enumerate(to_generate_fallback):
        existing_vibe = public_signals[restaurant_id].get('public_vibe', '').strip()
        existing_source = public_signals[restaurant_id].get('public_vibe_source', '').strip()
        
        if not existing_vibe:
            # Generate new fallback vibe
            vibe = generate_deterministic_vibe(snippets)
            if vibe:
                public_signals[restaurant_id]['public_vibe'] = vibe
                public_signals[restaurant_id]['public_vibe_source'] = 'fallback'
                public_signals[restaurant_id]['public_vibe_model'] = ''
                public_signals[restaurant_id]['public_vibe_updated_at'] = datetime.now().isoformat()
                fallback_generated += 1
        elif not existing_source:
            # Backfill: existing vibe but missing source - mark as fallback
            public_signals[restaurant_id]['public_vibe_source'] = 'fallback'
            public_signals[restaurant_id]['public_vibe_model'] = ''
            # Don't update timestamp for backfill
            fallback_generated += 1
    
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
    
    # Final report
    print(f"\n{'='*60}")
    print(f"Final Report:")
    print(f"{'='*60}")
    print(f"  LLM generated: {llm_generated}")
    print(f"  Fallback generated: {fallback_generated}")
    print(f"  Skipped (fresh): {skipped_fresh}")
    print(f"  Missing snippets: {missing_snippets}")
    print(f"  Total with vibes: {llm_generated + fallback_generated + skipped_fresh}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
