#!/usr/bin/env python3
"""
FastAPI server for restaurant recommendation chatbot.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Verify API key is available (for Google Maps APIs)
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
if not GOOGLE_MAPS_API_KEY:
    print("WARNING: GOOGLE_MAPS_API_KEY not found in environment. Distance features may not work.")

# Add scripts directory to path to import chatbot
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
from chatbot import RestaurantChatbot
from rank_and_explain import recommend

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vite default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize chatbot
script_dir = Path(__file__).parent
data_path = script_dir / 'data' / 'restaurants_clean.json'
chatbot = RestaurantChatbot(data_path)


class ChatRequest(BaseModel):
    message: str
    city: str | None = None


class SwapRequest(BaseModel):
    exclude_restaurant: str  # Name of restaurant to exclude
    city: str
    neighborhood: str | None = None
    vibes: list[str] = []
    constraints: dict = {}
    meal_time: str | None = None
    budget: int | None = None


class RestaurantData(BaseModel):
    name: str
    note: str
    url: str
    status: str
    city: str
    neighborhood: str | None = None
    why_picked: str | None = None  # Reasoning for why this restaurant was chosen
    restaurant_id: str | None = None
    final_score: float | None = None
    why: str | None = None
    price_tier: str | None = None
    public_rating: str | None = None
    public_review_count: str | None = None
    public_vibe: str | None = None
    public_vibe_source: str | None = None
    public_vibe_model: str | None = None
    distance_km: float | None = None
    # Debug fields (for internal use)
    match_score: float | None = None
    taste_score: float | None = None
    public_score: float | None = None
    confidence: str | None = None
    matched_tags: list[str] | None = None


class RestaurantResponse(BaseModel):
    tried: list[RestaurantData]
    want: list[RestaurantData]
    category: str | None = None


class ChatResponse(BaseModel):
    response: str
    restaurants: RestaurantResponse | None = None


def _generate_why_picked(restaurant: dict, vibes: list[str], constraints: dict, 
                         neighborhood: str | None, original_query: str = "") -> str:
    """Generate reasoning for why this restaurant was picked."""
    reasons = []
    note = restaurant.get('note', '').lower()
    name = restaurant['name']
    
    # Check vibes
    if 'romantic' in vibes:
        if 'romantic' in note or 'date' in note:
            reasons.append("romantic and date-friendly")
    if 'brunch' in vibes:
        if 'brunch' in note:
            reasons.append("perfect brunch spot")
    if 'casual' in vibes:
        if 'casual' in note or 'chill' in note:
            reasons.append("casual and relaxed")
    if 'fancy' in vibes:
        if 'fancy' in note or 'fine dining' in note:
            reasons.append("upscale and elegant")
    
    # Check constraints
    if constraints.get('price') == 'cheap':
        if 'cheap' in note or 'affordable' in note:
            reasons.append("very affordable")
    
    # Check neighborhood
    if neighborhood:
        if neighborhood.lower() in note or neighborhood.lower() in name.lower():
            reasons.append(f"in {neighborhood}")
    
    # Check cuisine type from original query
    if 'french' in original_query.lower():
        if 'french' in note.lower():
            reasons.append("classic French cuisine")
    if 'italian' in original_query.lower():
        if 'italian' in note.lower() or 'pasta' in note.lower() or 'pizza' in note.lower():
            reasons.append("authentic Italian")
    if 'thai' in original_query.lower():
        if 'thai' in note.lower():
            reasons.append("great Thai food")
    
    # Status-based reasoning
    if restaurant['status'] == 'tried':
        reasons.append("I've been here and loved it")
    else:
        reasons.append("on my want-to-try list")
    
    # Fallback if no specific reasons
    if not reasons:
        if note:
            # Extract key phrase from note
            if 'date' in note:
                reasons.append("great for dates")
            elif 'brunch' in note:
                reasons.append("perfect brunch spot")
            elif 'cheap' in note:
                reasons.append("very affordable")
            else:
                reasons.append("matches what you're looking for")
        else:
            reasons.append("a great fit")
    
    return "Picked because " + ", ".join(reasons[:3])  # Limit to 3 reasons


def _get_restaurants_from_chatbot(city: str, neighborhood: str | None = None,
                                  vibes: list[str] = None, constraints: dict = None,
                                  meal_time: str | None = None, budget: int | None = None,
                                  exclude_names: list[str] = None, original_query: str = ""):
    """Get structured restaurant data from chatbot."""
    vibes = vibes or []
    constraints = constraints or {}
    exclude_names = exclude_names or []
    
    tried, want = chatbot._get_recommendations(
        city, neighborhood, vibes, constraints, meal_time, budget
    )
    
    # Filter out excluded restaurants
    tried = [r for r in tried if r['name'] not in exclude_names]
    want = [r for r in want if r['name'] not in exclude_names]
    
    # Convert to structured format
    tried_data = [
        RestaurantData(
            name=r['name'],
            note=r.get('note', '').strip(),
            url=r.get('url', ''),
            status=r['status'],
            city=r['city'],
            neighborhood=neighborhood,
            why_picked=_generate_why_picked(r, vibes, constraints, neighborhood, original_query)
        )
        for r in tried[:3]  # Limit to top 3
    ]
    
    want_data = [
        RestaurantData(
            name=r['name'],
            note=r.get('note', '').strip(),
            url=r.get('url', ''),
            status=r['status'],
            city=r['city'],
            neighborhood=neighborhood,
            why_picked=_generate_why_picked(r, vibes, constraints, neighborhood, original_query)
        )
        for r in want[:max(1, 4 - len(tried[:3]))]  # Fill up to 4 total
    ]
    
    # Determine category from vibes/constraints
    category = None
    if vibes:
        vibe_map = {
            'romantic': 'Romantic dinner',
            'brunch': 'Brunch restaurants',
            'casual': 'Casual dining',
            'fancy': 'Fine dining',
            'cheap': 'Budget-friendly',
        }
        category = vibe_map.get(vibes[0], vibes[0].title())
    elif constraints.get('price') == 'cheap':
        category = 'Budget-friendly'
    
    return RestaurantResponse(
        tried=tried_data,
        want=want_data,
        category=category
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process chat message and return response."""
    user_message = request.message.strip()
    
    # If city is provided, prepend it to the message for context
    if request.city:
        user_message = f"{request.city} {user_message}"
    
    # Process query to get response text
    response_text = chatbot.process_query(user_message)
    
    # Extract restaurant data using new ranking system
    restaurants = None
    
    # Try to get city from chatbot state or request
    city = request.city or chatbot.conversation_state.get('city')
    
    if city or user_message:  # Use ranking if we have a query
        try:
            # Use new ranking system
            ranked_results = recommend(user_message, top_n=6, city=city)
            
            # Load master data to get full restaurant info
            data_dir = Path(__file__).parent / 'data'
            master_file = data_dir / 'restaurants_master.csv'
            restaurant_lookup = {}
            
            import csv
            with open(master_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    restaurant_lookup[row['restaurant_id']] = row
            
            # Convert to RestaurantData format
            tried_data = []
            want_data = []
            
            # Load experience signals for debug info
            experience_file = data_dir / 'experience_signals.csv'
            experience_lookup = {}
            import csv
            with open(experience_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    experience_lookup[row['restaurant_id']] = row
            
            # Re-score to get components for debug info
            from rank_and_explain import parse_query, score_restaurant, get_query_location
            parsed_query = parse_query(user_message)
            query_location = get_query_location(parsed_query)
            
            for result in ranked_results:
                restaurant_id = result['restaurant_id']
                master_row = restaurant_lookup.get(restaurant_id, {})
                experience_row = experience_lookup.get(restaurant_id, {})
                
                # Get scoring components for debug
                merged_row = {**master_row, **experience_row}
                score_result = score_restaurant(merged_row, parsed_query, query_location)
                
                # Extract matched tags from matched_reasons and also from tags
                matched_reasons = score_result.get('matched_reasons', [])
                matched_tags = []
                
                # Extract from matched_reasons
                for reason in matched_reasons:
                    if reason.startswith('vibe_'):
                        matched_tags.append(reason.replace('vibe_', ''))
                    elif reason.startswith('best_for_'):
                        matched_tags.append(reason.replace('best_for_', ''))
                    elif reason.startswith('cuisine_'):
                        matched_tags.append(reason.replace('cuisine_', ''))
                
                # Also include vibe and best_for tags from experience signals if they exist
                vibe_tags = experience_row.get('vibe', '').strip()
                best_for_tags = experience_row.get('best_for', '').strip()
                
                if vibe_tags:
                    vibe_list = [v.strip() for v in vibe_tags.split('|') if v.strip()]
                    # Only add vibes that match the query
                    query_vibes = parsed_query.get('vibe_keywords', [])
                    for vibe in vibe_list:
                        if vibe in query_vibes and vibe not in matched_tags:
                            matched_tags.append(vibe)
                
                if best_for_tags:
                    best_for_list = [b.strip() for b in best_for_tags.split('|') if b.strip()]
                    query_best_for = parsed_query.get('best_for_keywords', [])
                    for best_for in best_for_list:
                        if best_for in query_best_for and best_for not in matched_tags:
                            matched_tags.append(best_for)
                
                restaurant = RestaurantData(
                    name=result['name'],
                    note=master_row.get('your_note', ''),
                    url=master_row.get('google_maps_url', ''),
                    status=result['status'],
                    city=result['city'],
                    neighborhood=result.get('neighborhood') or None,
                    why_picked=result.get('why', ''),
                    restaurant_id=restaurant_id,
                    final_score=result.get('final_score'),
                    why=result.get('why'),
                    price_tier=result.get('price_tier') or None,
                    public_rating=result.get('public_rating') or None,
                    public_review_count=result.get('public_review_count') or None,
                    public_vibe=result.get('public_vibe') or None,
                    public_vibe_source=result.get('public_vibe_source') or None,
                    public_vibe_model=result.get('public_vibe_model') or None,
                    distance_km=score_result.get('distance_km') or result.get('distance_km'),
                    # Debug fields
                    match_score=round(score_result['components'].get('match_score', 0), 1),
                    taste_score=round(score_result['components'].get('taste_score', 0), 1),
                    public_score=round(score_result['components'].get('public_score', 0), 1),
                    confidence=experience_row.get('confidence'),
                    matched_tags=matched_tags if matched_tags else None
                )
                
                if result['status'] == 'tried':
                    tried_data.append(restaurant)
                else:
                    want_data.append(restaurant)
            
            restaurants = RestaurantResponse(
                tried=tried_data,
                want=want_data,
                category=None
            )
            
        except Exception as e:
            # If ranking fails, fall back to old method
            print(f"Error with ranking system: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback to old chatbot method
            if chatbot.conversation_state.get('city'):
                try:
                    city = chatbot.conversation_state['city']
                    neighborhood = chatbot.conversation_state.get('neighborhood')
                    vibes = chatbot.conversation_state.get('vibes', [])
                    constraints = chatbot.conversation_state.get('constraints', {})
                    meal_time = chatbot.conversation_state.get('meal_time')
                    budget = chatbot.conversation_state.get('budget')
                    
                    restaurants = _get_restaurants_from_chatbot(
                        city, neighborhood, vibes, constraints, meal_time, budget,
                        original_query=user_message
                    )
                except Exception as e2:
                    print(f"Error with fallback method: {e2}")
    
    # Reset conversation state after processing (as chatbot does)
    # But only if there's no pending question
    if chatbot.conversation_state.get('pending_question') is None:
        chatbot.reset_conversation()
    
    return ChatResponse(
        response=response_text,
        restaurants=restaurants
    )


class SwapRequest(BaseModel):
    exclude_restaurant: str  # Name of restaurant to exclude
    exclude_all: list[str] = []  # All current restaurant names to exclude
    city: str
    neighborhood: str | None = None
    vibes: list[str] = []
    constraints: dict = {}
    meal_time: str | None = None
    budget: int | None = None
    is_tried: bool = True  # Whether we're swapping a tried or want-to-try restaurant


@app.post("/swap", response_model=RestaurantResponse)
async def swap_restaurant(request: SwapRequest):
    """Swap out a restaurant for a new recommendation."""
    try:
        # Exclude the specific restaurant and all current ones
        exclude_list = [request.exclude_restaurant] + request.exclude_all
        restaurants = _get_restaurants_from_chatbot(
            request.city,
            request.neighborhood,
            request.vibes,
            request.constraints,
            request.meal_time,
            request.budget,
            exclude_names=exclude_list,
            original_query=f"{request.city} restaurant"
        )
        return restaurants
    except Exception as e:
        print(f"Error swapping restaurant: {e}")
        raise


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}

