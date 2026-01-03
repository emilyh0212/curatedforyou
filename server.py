#!/usr/bin/env python3
"""
FastAPI server for restaurant recommendation chatbot.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import sys

# Add scripts directory to path to import chatbot
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
from chatbot import RestaurantChatbot

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
    
    # Extract restaurant data if we have a city set
    # Note: We need to extract before reset, as chatbot resets after processing
    restaurants = None
    if chatbot.conversation_state.get('city'):
        city = chatbot.conversation_state['city']
        neighborhood = chatbot.conversation_state.get('neighborhood')
        vibes = chatbot.conversation_state.get('vibes', [])
        constraints = chatbot.conversation_state.get('constraints', {})
        meal_time = chatbot.conversation_state.get('meal_time')
        budget = chatbot.conversation_state.get('budget')
        
        try:
            restaurants = _get_restaurants_from_chatbot(
                city, neighborhood, vibes, constraints, meal_time, budget,
                original_query=user_message
            )
        except Exception as e:
            # If extraction fails, just return text response
            print(f"Error extracting restaurants: {e}")
    
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

