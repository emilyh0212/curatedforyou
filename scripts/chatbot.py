#!/usr/bin/env python3
"""
Personal food recommendation chatbot that reflects Emily's taste.

This chatbot uses Emily's curated restaurant dataset to provide personalized
recommendations based on her actual experiences and notes.
"""

import json
import re
from pathlib import Path
from typing import Optional


# Neighborhood mappings for soft filtering
NYC_NEIGHBORHOODS = {
    'soho': ['soho', 'west village'],
    'west village': ['soho', 'west village'],
    'lower east side': ['lower east side', 'east village'],
    'east village': ['lower east side', 'east village'],
    'williamsburg': ['williamsburg'],
    'brooklyn heights': ['brooklyn heights', 'dumbo'],
    'dumbo': ['brooklyn heights', 'dumbo'],
    'long island city': ['long island city', 'lic'],
    'lic': ['long island city', 'lic'],
    'flushing': ['flushing'],
    'midtown': ['midtown', 'chelsea'],
    'chelsea': ['midtown', 'chelsea'],
}

MILAN_NEIGHBORHOODS = {
    'brera': ['brera'],
    'duomo': ['duomo', 'centro'],
    'centro': ['duomo', 'centro'],
    'navigli': ['navigli'],
    'bocconi': ['bocconi', 'porta romana'],
    'porta romana': ['bocconi', 'porta romana'],
}

# Neighborhood overrides for common restaurants (bootstrap layer)
NEIGHBORHOOD_OVERRIDES = {
    "L'industrie Pizzeria West Village": "SoHo / West Village",
    "Raku": "SoHo / West Village",
    "Little Ruby's West Village": "SoHo / West Village",
    "Misi": "Williamsburg (Brooklyn)",
    "Win Son Bakery": "Williamsburg (Brooklyn)",
}

# Vibe keywords from Emily's notes
VIBE_KEYWORDS = {
    'romantic': ['romantic', 'date', 'date night', 'date vibes', 'intimate'],
    'cute': ['cute', 'cute vibes', 'super cute', 'chill', 'chill vibes'],
    'casual': ['casual', 'casual lunch', 'casual dinner', 'chill'],
    'cheap': ['cheap', 'low prices', 'very cheap', 'cheap eats', 'decently priced'],
    'vibey': ['vibey', 'vibes', 'vibe', 'good vibes', 'cute vibes', 'chill vibes'],
    'quick': ['quick', 'takeout', 'fast'],
    'fancy': ['fancy', 'fine dining', 'fancy dinner', 'fancy bar'],
    'brunch': ['brunch', 'brunch place', 'perfect brunch'],
    'study': ['study', 'study place', 'wifi'],
}


class RestaurantChatbot:
    """Chatbot that recommends restaurants from Emily's curated dataset."""
    
    def __init__(self, data_path: Path):
        """Initialize chatbot with restaurant data."""
        self.data_path = data_path
        self.restaurants = self._load_data()
        self.conversation_state = {
            'city': None,
            'neighborhood': None,
            'meal_time': None,
            'pending_question': None,
            'vibes': [],
            'constraints': {},
            'budget': None,
        }
    
    def _load_data(self) -> list[dict]:
        """Load restaurant data from JSON file."""
        if not self.data_path.exists():
            raise FileNotFoundError(
                f"Restaurant data not found at {self.data_path}. "
                "Please run scripts/clean_saved.py first."
            )
        
        with open(self.data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _normalize_city(self, text: str) -> Optional[str]:
        """Extract city from user input."""
        text_lower = text.lower()
        if 'milan' in text_lower:
            return 'Milan'
        elif 'nyc' in text_lower or 'new york' in text_lower or 'new york city' in text_lower:
            return 'New York'
        return None
    
    def _normalize_neighborhood(self, text: str, city: str) -> Optional[str]:
        """Extract neighborhood from user input."""
        text_lower = text.lower()
        
        if city == 'Milan':
            for key, aliases in MILAN_NEIGHBORHOODS.items():
                if key in text_lower or any(alias in text_lower for alias in aliases):
                    return key.title()
        elif city == 'New York':
            for key, aliases in NYC_NEIGHBORHOODS.items():
                if key in text_lower or any(alias in text_lower for alias in aliases):
                    return key.title()
        
        return None
    
    def _extract_budget(self, text: str) -> Optional[int]:
        """
        Extract budget from user input.
        
        Looks for phrases like "under 25", "under 50", "under 80" or
        budget-related keywords. Returns integer budget or None.
        """
        text_lower = text.lower()
        
        # Check for explicit numeric budget
        # Look for "under 25", "under 50", "under 80", "$25", etc.
        under_match = re.search(r'under\s*\$?\s*(\d+)', text_lower)
        if under_match:
            amount = int(under_match.group(1))
            # Normalize to tiers: 25, 50, or 80
            if amount <= 25:
                return 25
            elif amount <= 50:
                return 50
            elif amount <= 80:
                return 80
            else:
                return None  # Over 80, treat as no limit
        
        # Check for budget keywords without numbers
        budget_keywords = ['not too expensive', 'cheap', 'budget', 'affordable']
        if any(kw in text_lower for kw in budget_keywords):
            # Return None to indicate budget mentioned but no number - will ask
            return None
        
        return None
    
    def _parse_budget_answer(self, text: str) -> Optional[int]:
        """Parse budget answer from user response to budget question."""
        text_lower = text.lower()
        
        if 'no limit' in text_lower or 'no budget' in text_lower or 'any' in text_lower:
            return None
        
        # Look for numbers
        numbers = re.findall(r'\d+', text_lower)
        if numbers:
            amount = int(numbers[0])
            if amount <= 25:
                return 25
            elif amount <= 50:
                return 50
            elif amount <= 80:
                return 80
        
        # Check for tier mentions
        if '25' in text_lower or 'twenty-five' in text_lower:
            return 25
        elif '50' in text_lower or 'fifty' in text_lower:
            return 50
        elif '80' in text_lower or 'eighty' in text_lower:
            return 80
        
        return None
    
    def _extract_meal_time(self, text: str) -> Optional[str]:
        """Extract meal time (lunch/dinner) from user input."""
        text_lower = text.lower()
        if 'lunch' in text_lower:
            return 'lunch'
        elif 'dinner' in text_lower:
            return 'dinner'
        return None
    
    def _extract_vibes(self, text: str) -> list[str]:
        """Extract vibe keywords from user input."""
        text_lower = text.lower()
        matched_vibes = []
        
        for vibe, keywords in VIBE_KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                matched_vibes.append(vibe)
        
        return matched_vibes
    
    def _extract_constraints(self, text: str) -> dict:
        """Extract hard constraints (price, speed, no lines)."""
        text_lower = text.lower()
        constraints = {}
        
        # Price constraints
        if 'cheap' in text_lower or 'budget' in text_lower or 'affordable' in text_lower:
            constraints['price'] = 'cheap'
        elif 'expensive' in text_lower or 'splurge' in text_lower:
            constraints['price'] = 'expensive'
        
        # Speed constraints
        if 'quick' in text_lower or 'fast' in text_lower or 'quickly' in text_lower:
            constraints['speed'] = 'quick'
        
        # No lines constraint
        if 'no line' in text_lower or 'no wait' in text_lower or 'no reservation' in text_lower:
            constraints['no_lines'] = True
        
        return constraints
    
    def _score_restaurant(self, restaurant: dict, vibes: list[str], 
                         constraints: dict, neighborhood: Optional[str],
                         city: str, budget: Optional[int] = None) -> float:
        """Score a restaurant based on how well it matches the request."""
        score = 0.0
        
        # Base score: tried restaurants get higher priority
        if restaurant['status'] == 'tried':
            score += 100.0
        else:
            score += 10.0
        
        # Neighborhood matching (soft constraint)
        if neighborhood:
            # Check if neighborhood appears in name or note
            note_lower = (restaurant.get('note', '') + ' ' + restaurant.get('name', '')).lower()
            neighborhood_lower = neighborhood.lower()
            
            # Exact neighborhood match gets bonus
            if neighborhood_lower in note_lower:
                score += 20.0
            # Related neighborhoods get smaller bonus
            elif city == 'New York' and neighborhood_lower in NYC_NEIGHBORHOODS:
                related = NYC_NEIGHBORHOODS[neighborhood_lower]
                if any(n in note_lower for n in related):
                    score += 10.0
            elif city == 'Milan' and neighborhood_lower in MILAN_NEIGHBORHOODS:
                related = MILAN_NEIGHBORHOODS[neighborhood_lower]
                if any(n in note_lower for n in related):
                    score += 10.0
        
        # Vibe matching from Emily's notes
        note = restaurant.get('note', '').lower()
        for vibe in vibes:
            if vibe in VIBE_KEYWORDS:
                keywords = VIBE_KEYWORDS[vibe]
                if any(keyword in note for keyword in keywords):
                    score += 30.0
        
        # Constraint matching
        if constraints.get('price') == 'cheap':
            cheap_keywords = ['cheap', 'low prices', 'very cheap', 'cheap eats', 'decently priced']
            if any(kw in note for kw in cheap_keywords):
                score += 25.0
            else:
                score -= 50.0  # Penalize if doesn't match constraint
        
        if constraints.get('speed') == 'quick':
            quick_keywords = ['quick', 'takeout', 'fast', 'casual']
            if any(kw in note for kw in quick_keywords):
                score += 25.0
        
        # Boost restaurants with notes (Emily's personal insights)
        if restaurant.get('note') and restaurant['note'].strip():
            score += 15.0
        
        # Budget-based scoring adjustments (soft nudge, not hard filter)
        if budget is not None:
            note = restaurant.get('note', '').lower()
            
            # Expensive keywords to penalize for budget constraints
            expensive_keywords = ['tasting', 'prix fixe', 'omakase', 'fine dining', 
                                 'upscale', 'michelin', '$$$$', 'expensive']
            # Cheap/affordable keywords to boost
            affordable_keywords = ['cheap', 'affordable', 'casual', 'quick', 
                                  'no-frills', 'lunch', 'under']
            
            # For budgets 25 or 50, apply adjustments
            if budget in [25, 50]:
                # Penalize expensive-sounding restaurants
                if any(kw in note for kw in expensive_keywords):
                    score -= 15.0  # Small penalty
                # Boost affordable-sounding restaurants
                if any(kw in note for kw in affordable_keywords):
                    score += 10.0  # Small boost
            
            # If budget is low, avoid drinks-only / cocktail bar suggestions
            if budget in [25, 50]:
                drink_keywords = ["cocktail", "bar", "drinks", "lounge", "speakeasy"]
                if any(k in note for k in drink_keywords):
                    # Stronger penalty for budget 25, lighter for 50
                    penalty = -30 if budget == 25 else -20
                    score += penalty
        
        # Neighborhood proximity boost
        restaurant_name = restaurant["name"]
        restaurant_neighborhood = NEIGHBORHOOD_OVERRIDES.get(restaurant_name, "")
        
        # soft neighborhood preference using name / note heuristics
        note = restaurant.get("note", "").lower()
        if neighborhood:
            # Check override first
            if restaurant_neighborhood:
                selected_neighborhood_lower = neighborhood.lower()
                restaurant_neighborhood_lower = restaurant_neighborhood.lower()
                # Extract key neighborhood names (handle formats like "SoHo / West Village" or "Williamsburg (Brooklyn)")
                # Split by common separators and remove parentheticals
                restaurant_parts = re.sub(r'\([^)]*\)', '', restaurant_neighborhood_lower).replace('/', ' ').split()
                selected_parts = re.sub(r'\([^)]*\)', '', selected_neighborhood_lower).replace('/', ' ').split()
                # Check if any parts match
                if any(part in restaurant_neighborhood_lower for part in selected_parts) or \
                   any(part in selected_neighborhood_lower for part in restaurant_parts):
                    score += 6
            # Fallback to note-based matching
            elif neighborhood.lower() in note:
                score += 6
        
        return score
    
    def _filter_by_constraints(self, restaurants: list[dict], constraints: dict) -> list[dict]:
        """Filter restaurants by hard constraints."""
        filtered = []
        
        for restaurant in restaurants:
            note = restaurant.get('note', '').lower()
            name = restaurant.get('name', '').lower()
            text = note + ' ' + name
            
            # Check price constraint
            if constraints.get('price') == 'cheap':
                cheap_keywords = ['cheap', 'low prices', 'very cheap', 'cheap eats', 'decently priced']
                if not any(kw in text for kw in cheap_keywords):
                    continue
            
            # Check speed constraint
            if constraints.get('speed') == 'quick':
                quick_keywords = ['quick', 'takeout', 'fast', 'casual']
                if not any(kw in text for kw in quick_keywords):
                    continue
            
            filtered.append(restaurant)
        
        return filtered
    
    def _get_recommendations(self, city: str, neighborhood: Optional[str],
                            vibes: list[str], constraints: dict,
                            meal_time: Optional[str], budget: Optional[int] = None) -> tuple[list[dict], list[dict]]:
        """Get restaurant recommendations based on criteria."""
        # Filter by city
        city_restaurants = [r for r in self.restaurants if r['city'] == city]
        
        # Apply hard constraints first
        if constraints:
            city_restaurants = self._filter_by_constraints(city_restaurants, constraints)
        
        # Score and sort restaurants
        scored = []
        for restaurant in city_restaurants:
            score = self._score_restaurant(restaurant, vibes, constraints, neighborhood, city, budget)
            scored.append((score, restaurant))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Separate tried and want-to-try
        tried = [r for score, r in scored if r['status'] == 'tried']
        
        # Pick highest-scoring want-to-try restaurant after budget penalties, exclude ones with score <= 0
        want_candidates = [
            (score, r) for score, r in scored
            if r['status'] == 'want' and score > 0
        ]
        selected_want = max(want_candidates, key=lambda x: x[0])[1] if want_candidates else None
        
        # Return tried list and single want-to-try (or empty list)
        want = [selected_want] if selected_want else []
        
        return tried, want
    
    def _format_recommendation(self, restaurant: dict, index: int, 
                               is_tried: bool = True) -> str:
        """Format a single restaurant recommendation in Emily's voice."""
        name = restaurant['name']
        note = restaurant.get('note', '').strip()
        url = restaurant.get('url', '')
        status = restaurant['status']
        
        lines = [f"{index}. **{name}**"]
        
        # Add status and note with personal voice
        if is_tried:
            lines.append("   ✓ I've been here")
            if note:
                lines.append(f"   {note}")
            else:
                lines.append("   I liked it!")
        else:
            lines.append("   ⭐ On my want-to-try list")
            if note:
                lines.append(f"   {note}")
            else:
                lines.append("   I haven't been yet, but it's on my list—go try it for me.")
        
        # Add concrete expectation
        expectation = self._get_concrete_expectation(restaurant)
        lines.append(f"   → {expectation}")
        
        # Add URL if available
        if url:
            lines.append(f"   {url}")
        
        return '\n'.join(lines)
    
    def _is_restaurant_in_neighborhood(self, restaurant: dict, neighborhood: Optional[str]) -> bool:
        """Check if restaurant is in the selected neighborhood."""
        if not neighborhood:
            return True  # No neighborhood filter, so all restaurants are "in"
        
        restaurant_name = restaurant["name"]
        restaurant_neighborhood = NEIGHBORHOOD_OVERRIDES.get(restaurant_name, "")
        
        if restaurant_neighborhood:
            # Check if selected neighborhood matches restaurant neighborhood
            selected_neighborhood_lower = neighborhood.lower()
            restaurant_neighborhood_lower = restaurant_neighborhood.lower()
            # Extract key neighborhood names (handle formats like "SoHo / West Village")
            restaurant_parts = re.sub(r'\([^)]*\)', '', restaurant_neighborhood_lower).replace('/', ' ').split()
            selected_parts = re.sub(r'\([^)]*\)', '', selected_neighborhood_lower).replace('/', ' ').split()
            # Check if any parts match
            if any(part in restaurant_neighborhood_lower for part in selected_parts) or \
               any(part in selected_neighborhood_lower for part in restaurant_parts):
                return True
        
        # Fallback to note-based matching
        note = restaurant.get('note', '').lower()
        name = restaurant.get('name', '').lower()
        text = note + ' ' + name
        neighborhood_lower = neighborhood.lower()
        
        return neighborhood_lower in text
    
    def _get_concrete_expectation(self, restaurant: dict) -> str:
        """Extract one concrete expectation from Emily's notes."""
        note = restaurant.get('note', '').lower()
        
        # Look for specific mentions
        if 'date' in note or 'romantic' in note:
            return "Great for dates"
        elif 'brunch' in note:
            return "Perfect brunch spot"
        elif 'cheap' in note or 'low prices' in note:
            return "Very affordable"
        elif 'fancy' in note or 'fine dining' in note:
            return "Upscale/fancy"
        elif 'takeout' in note:
            return "Good for takeout"
        elif 'study' in note or 'wifi' in note:
            return "Good for studying"
        elif 'vibes' in note or 'vibey' in note:
            return "Great vibes"
        elif 'pizza' in note:
            return "Known for pizza"
        elif 'pasta' in note:
            return "Known for pasta"
        elif 'sushi' in note:
            return "Known for sushi"
        elif 'steak' in note:
            return "Known for steak"
        else:
            return "Worth checking out"
    
    def process_query(self, user_input: str) -> str:
        """Process user query and return response."""
        user_input_lower = user_input.lower().strip()
        
        # Check for exit commands
        if user_input_lower in ['exit', 'quit', 'bye', 'goodbye']:
            return "Bye! Hope you find something good to eat! 🍽️"
        
        # Handle pending budget question
        budget = None
        budget_extracted = False
        if self.conversation_state['pending_question'] == 'budget':
            budget = self._parse_budget_answer(user_input)
            if budget is not None or 'no limit' in user_input_lower or 'no budget' in user_input_lower or 'any' in user_input_lower:
                self.conversation_state['budget'] = budget
                self.conversation_state['pending_question'] = None
                # Continue processing with budget set (don't re-extract budget from this answer)
                budget_extracted = True
            else:
                return "Sorry, I didn't catch that. What's your budget per person: under 25, under 50, under 80, or no limit?"
        
        # Handle pending meal time question
        if self.conversation_state['pending_question'] == 'meal_time':
            meal_time = self._extract_meal_time(user_input)
            if meal_time:
                self.conversation_state['meal_time'] = meal_time
                self.conversation_state['pending_question'] = None
                # Reprocess with meal time and saved context
                return self._generate_recommendations(
                    city=self.conversation_state['city'],
                    neighborhood=self.conversation_state.get('neighborhood'),
                    vibes=self.conversation_state.get('vibes', []),
                    constraints=self.conversation_state.get('constraints', {}),
                    meal_time=meal_time,
                    budget=self.conversation_state.get('budget')
                )
            else:
                return "Sorry, I didn't catch that. Is this for lunch or dinner?"
        
        # Extract city
        city = self._normalize_city(user_input)
        
        # Extract neighborhood (try with current city, or without city to detect it)
        neighborhood = None
        if city:
            neighborhood = self._normalize_neighborhood(user_input, city)
        else:
            # Try to detect neighborhood without city to infer city
            # Check NYC neighborhoods first
            for key, aliases in NYC_NEIGHBORHOODS.items():
                if key in user_input_lower or any(alias in user_input_lower for alias in aliases):
                    neighborhood = key.title()
                    city = 'New York'  # Infer city from neighborhood
                    break
            # If not NYC, check Milan neighborhoods
            if not neighborhood:
                for key, aliases in MILAN_NEIGHBORHOODS.items():
                    if key in user_input_lower or any(alias in user_input_lower for alias in aliases):
                        neighborhood = key.title()
                        city = 'Milan'  # Infer city from neighborhood
                        break
        
        # If still no city and no neighborhood detected, ask for city
        if not city and not self.conversation_state['city']:
            return "Which city are you looking for recommendations in? (Milan or New York City)"
        
        # Set city if detected
        if city:
            self.conversation_state['city'] = city
        
        city = self.conversation_state['city']
        
        # Set neighborhood if detected
        if neighborhood:
            self.conversation_state['neighborhood'] = neighborhood
        
        neighborhood = self.conversation_state.get('neighborhood')
        
        # Extract budget (skip if we just handled budget question)
        if not budget_extracted:
            budget = self._extract_budget(user_input)
            if budget is None:
                # Check if budget-related keywords were mentioned but no number
                budget_keywords = ['not too expensive', 'cheap', 'budget', 'affordable', 'under $', 'under 25', 'under 50', 'under 80']
                if any(kw in user_input_lower for kw in budget_keywords) and self.conversation_state['budget'] is None:
                    # Budget mentioned but no number and no budget stored - ask
                    if self.conversation_state['pending_question'] is None:
                        self.conversation_state['pending_question'] = 'budget'
                        return "Quick check, what's your budget per person: under 25, under 50, under 80, or no limit?"
            else:
                # Budget number extracted
                self.conversation_state['budget'] = budget
        
        # Use stored budget if no new one extracted
        if budget is None:
            budget = self.conversation_state.get('budget')
        
        # Extract meal time
        meal_time = self._extract_meal_time(user_input)
        if not meal_time and not self.conversation_state['meal_time']:
            # Only ask meal time if no pending budget question
            if self.conversation_state['pending_question'] != 'budget':
                self.conversation_state['pending_question'] = 'meal_time'
                return "Quick question: is this for lunch or dinner?"
        
        if meal_time:
            self.conversation_state['meal_time'] = meal_time
        
        # Extract vibes and constraints
        vibes = self._extract_vibes(user_input)
        constraints = self._extract_constraints(user_input)
        
        # Save vibes and constraints to conversation state
        if vibes:
            self.conversation_state['vibes'] = vibes
        if constraints:
            self.conversation_state['constraints'] = constraints
        
        # Use saved vibes/constraints if none extracted from current input
        vibes = vibes or self.conversation_state.get('vibes', [])
        constraints = constraints or self.conversation_state.get('constraints', {})
        
        # Default budget to 50 if not set (but don't store in conversation_state so note shows)
        if budget is None:
            budget = 50
        
        # Generate recommendations
        return self._generate_recommendations(city, neighborhood, vibes, constraints, meal_time, budget)
    
    def _generate_recommendations(self, city: Optional[str] = None,
                                  neighborhood: Optional[str] = None,
                                  vibes: Optional[list[str]] = None,
                                  constraints: Optional[dict] = None,
                                  meal_time: Optional[str] = None,
                                  budget: Optional[int] = None) -> str:
        """Generate formatted recommendations."""
        city = city or self.conversation_state['city']
        neighborhood = neighborhood or self.conversation_state.get('neighborhood')
        vibes = vibes or []
        constraints = constraints or {}
        meal_time = meal_time or self.conversation_state.get('meal_time')
        budget = budget if budget is not None else self.conversation_state.get('budget')
        
        if not city:
            return "Which city are you looking for recommendations in? (Milan or New York City)"
        
        # Default budget to 50 if not set
        if budget is None:
            budget = 50
        
        # Get recommendations
        tried, want = self._get_recommendations(city, neighborhood, vibes, constraints, meal_time, budget)
        
        # Add budget note to response if defaulted
        budget_note = ""
        if budget == 50 and self.conversation_state.get('budget') is None:
            budget_note = "\n*Assuming budget under $50 per person.*\n"
        
        # Build response
        response_parts = []
        
        # Add budget note if defaulted
        if budget_note:
            response_parts.append(budget_note)
        
        # Check if any restaurants are outside the selected neighborhood
        all_recommended = tried[:3] + want[:max(1, 4 - len(tried[:3]))]
        has_outside_neighborhood = False
        if neighborhood:
            for restaurant in all_recommended:
                if not self._is_restaurant_in_neighborhood(restaurant, neighborhood):
                    has_outside_neighborhood = True
                    break
        
        # Add single neighborhood note at top if needed
        if has_outside_neighborhood:
            neighborhood_display = neighborhood.title() if neighborhood else ""
            response_parts.append(f"A couple of these are a short walk from {neighborhood_display}, but they're great fits for what you want.\n")
        
        # Tried restaurants (prioritize 3)
        if tried:
            response_parts.append("**Tried and loved:**\n")
            for i, restaurant in enumerate(tried[:3], 1):
                rec = self._format_recommendation(restaurant, i, is_tried=True)
                response_parts.append(rec)
                response_parts.append("")
        else:
            response_parts.append("**Tried and loved:**\n")
            response_parts.append("Hmm, I don't have any tried restaurants that match exactly. "
                                "But here are some from my want-to-try list that might work!")
            response_parts.append("")
        
        # Want-to-try restaurants (always include at least 1)
        if want:
            response_parts.append("**On my want-to-try list:**\n")
            # Include more want-to-try if we don't have 3 tried
            num_want = max(1, 4 - len(tried[:3]))
            for i, restaurant in enumerate(want[:num_want], len(tried[:3]) + 1):
                rec = self._format_recommendation(restaurant, i, is_tried=False)
                response_parts.append(rec)
                response_parts.append("")
        elif len(tried) < 3:
            response_parts.append("**On my want-to-try list:**\n")
            response_parts.append("Sorry, I don't have anything on my list that matches. "
                                "Maybe try adjusting your criteria?")
            response_parts.append("")
        
        # Add explanation if we have fewer than 3 tried
        if len(tried) < 3 and len(tried) > 0:
            response_parts.append(f"*Only found {len(tried)} tried restaurants matching your criteria, "
                                 f"so I added more from my want-to-try list.*")
        
        return '\n'.join(response_parts)
    
    def reset_conversation(self):
        """Reset conversation state."""
        self.conversation_state = {
            'city': None,
            'neighborhood': None,
            'meal_time': None,
            'pending_question': None,
            'vibes': [],
            'constraints': {},
            'budget': None,
        }


def main():
    """Main interactive loop."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    data_path = repo_root / 'data' / 'restaurants_clean.json'
    
    try:
        chatbot = RestaurantChatbot(data_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    
    print("=" * 60)
    print("🍽️  Emily's Restaurant Recommendations")
    print("=" * 60)
    print("\nHey! I'll help you find restaurants based on places I've actually tried")
    print("and loved, plus some spots on my want-to-try list.")
    print("\nJust tell me what you're looking for—city, neighborhood, vibe, etc.")
    print("Type 'exit' to quit.\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            response = chatbot.process_query(user_input)
            print(f"\n{response}\n")
            
            # Reset conversation after each full recommendation
            if chatbot.conversation_state['pending_question'] is None:
                chatbot.reset_conversation()
        
        except KeyboardInterrupt:
            print("\n\nBye! Hope you find something good to eat! 🍽️")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Let's try again!\n")


if __name__ == '__main__':
    main()

