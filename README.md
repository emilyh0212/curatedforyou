# Curated For You

A personal restaurant recommendation chatbot that reflects Emily's taste, powered by her curated restaurant dataset.

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables**:
   Create a `.env` file in the project root:
   ```bash
   GOOGLE_MAPS_API_KEY=your_google_maps_api_key
   OPENAI_API_KEY=your_openai_api_key
   ```

3. **Build the master restaurant database** (Step 1):
   ```bash
   python scripts/create_master_csv.py
   ```
   
   This combines all restaurant data from source files into a single canonical table:
   - Reads from: `data/Milan Food.csv`, `data/Milan want to try.csv`, `data/NYC food.csv`, `data/NYC want to try.csv`
   - Creates: `data/restaurants_master.csv`
   - Features: Deduplicates by Google Maps URL, generates unique restaurant IDs, standardizes columns
   
   Validate the master file:
   ```bash
   python scripts/validate_master.py
   ```

4. **Generate experience signals** (Step 2):
   ```bash
   python scripts/build_experience_signals.py
   ```
   
   This infers experience signals from restaurant notes:
   - Reads from: `data/restaurants_master.csv`
   - Creates: `data/experience_signals.csv`
   - Infers: confidence, would_recommend, best_for, vibe, food_strength, dealbreakers
   - Uses controlled tag dictionaries for consistent tagging

5. **Generate public signals** (Step 3):
   ```bash
   python scripts/build_public_signals.py
   ```
   
   This extracts public data from the master file:
   - Reads from: `data/restaurants_master.csv`
   - Creates: `data/public_signals.csv`
   - Includes: public_rating, public_review_count, price_tier, source

6. **Enrich locations** (Optional):
   ```bash
   python scripts/enrich_locations_google.py
   ```
   
   Enriches restaurants with latitude, longitude, and place_id from Google Maps URLs.
   - Updates: `data/restaurants_master.csv`
   - Uses Google Places API to geocode restaurants

7. **Fetch public review snippets** (Step 6):
   ```bash
   python scripts/fetch_public_reviews.py
   ```
   
   Fetches review snippets from Google Places API (New):
   - Reads from: `data/restaurants_master.csv` and `data/public_signals.csv`
   - Updates: `data/public_signals.csv` with `public_review_snippets_json`
   - Caches API responses in `data/places_details_cache.json`
   - Extracts up to 8 review snippets (240 chars each) per restaurant

8. **Generate public vibes** (Step 6):
   ```bash
   python scripts/generate_public_vibe.py --limit 30 --sleep_seconds 2
   ```
   
   Generates one-sentence "Public vibe" summaries:
   - Uses OpenAI LLM for high-quality summaries (prioritizes tried/high confidence restaurants)
   - Falls back to deterministic summaries when LLM unavailable
   - Updates: `data/public_signals.csv` with `public_vibe`, `public_vibe_source`, `public_vibe_model`
   - Caches generated vibes in `data/public_vibe_cache.json`
   
   Options:
   - `--limit N`: Max restaurants to process with LLM (default: 30)
   - `--sleep_seconds S`: Delay between LLM requests (default: 2.0)
   - `--use_llm true/false`: Enable/disable LLM (default: true)
   - `--prioritize tried_high_conf`: Prioritize tried restaurants with high confidence

## Usage

### Backend Server

Start the FastAPI server:
```bash
python server.py
# or
uvicorn server:app --reload --port 8000
```

The server exposes:
- `POST /chat`: Main endpoint for restaurant recommendations
- `GET /health`: Health check endpoint

### Frontend

Navigate to the frontend directory:
```bash
cd ../curatedforyouChatbotv2
npm install
npm run dev
```

The frontend will be available at `http://localhost:3003/` (or another port if 3003 is in use).

## Example Queries

- "romantic dinner in NYC"
- "cheap eats near Williamsburg"
- "pasta in Milan"
- "first day near SoHo"

## Features

### Core Features

- **Personal recommendations**: Only suggests restaurants from Emily's curated list
- **Tried vs. Want-to-try**: Prioritizes places Emily has tried, clearly labels want-to-try items
- **Neighborhood-aware**: Soft filtering that prefers selected neighborhoods but suggests nearby matches when appropriate
- **Distance-based ranking**: Uses Google Maps API to calculate distances and boost nearby restaurants
- **City auto-detection**: Automatically detects city from neighborhood (e.g., Williamsburg → NYC, Brera → Milan)
- **Vibe matching**: Uses Emily's personal notes to match vibe requests
- **Multi-component scoring**: Combines match score, taste score, and public score for ranking

### Data Features

- **My take**: Shows Emily's personal notes for each restaurant
- **Public vibe**: Shows LLM-generated summaries from public review snippets (only when available)
- **Public rating & reviews**: Displays Google Maps rating and review count
- **Distance**: Shows distance from query location when available
- **Debug mode**: Optional "Show reasoning" toggle to see internal scoring components

### Ranking System

The ranking algorithm uses three components:

1. **Match Score (0-40)**: Based on city, neighborhood, vibe, best_for, and cuisine keyword matches
   - Distance bonus: +10 for 0-2km, +5 for 2-5km, +2 for 5-10km

2. **Taste Score (0-40)**: Based on Emily's experience and confidence
   - tried + high confidence: 40
   - tried + medium confidence: 28
   - tried + low confidence: 18
   - want_to_try: 12
   - Bonus: +6 for would_recommend=yes, +2 for maybe, -30 for no

3. **Public Score (0-20)**: Based on public rating and review count
   - Rating contribution (0-12): Linear scaling from 3.5 to 5.0
   - Review count contribution (0-8): Log scaling

Hard rules:
- Restaurants with `would_recommend=no` are capped at score 10 (unless explicitly queried)
- Maximum 1 `want_to_try` restaurant in top 6 results

## Testing

### Validate Master File
```bash
python scripts/validate_master.py
```

### Test Ranking System
```bash
python scripts/test_recommend.py
```

### Test Step 4 (Ranking & Explanation)
```bash
python scripts/step4_done_test.py
```

### Test Public Vibe Feature
```bash
python scripts/test_public_vibe.py
```

## Data Structure

### Master Restaurant Database (`restaurants_master.csv`)

The canonical restaurant table with one row per restaurant:
- `restaurant_id`: Unique identifier (format: `city_restaurant_name`)
- `name`: Restaurant name
- `city`: Milan or NYC
- `neighborhood`: Neighborhood (if available)
- `status`: `tried` or `want_to_try`
- `your_note`: Personal notes exactly as written
- `google_maps_url`: Google Maps URL
- `source`: Data source (currently `google_maps`)
- `latitude`, `longitude`, `place_id`: Location data (enriched via `enrich_locations_google.py`)
- Optional: `price_tier`, `public_rating`, `public_review_count`, `cuisine`

### Experience Signals (`experience_signals.csv`)

Inferred experience signals for each restaurant:
- `restaurant_id`: Links to restaurants_master.csv
- `status`: `tried` or `want_to_try`
- `your_note`: Copied from master
- `your_rating`: (currently blank)
- `would_recommend`: `yes`, `no`, or `maybe` (inferred from notes)
- `best_for`: Pipe-separated tags (date, friends, solo, parents, celebration, work_meeting, quick_bite, late_night)
- `vibe`: Pipe-separated tags (cozy, loud, trendy, romantic, casual, upscale, tiny, buzzing, classic, modern)
- `food_strength`: Pipe-separated tags (pasta, steak, sushi, pizza, seafood, bbq, dumplings, ramen, tacos, thai, indian, mediterranean, cafe, cocktails, wine, dessert, bakery)
- `dealbreakers`: Pipe-separated tags (too_loud, touristy, overpriced, long_wait, bad_service, hard_to_book)
- `confidence`: `high`, `medium`, or `low` (inferred from note strength)

### Public Signals (`public_signals.csv`)

Public data and generated summaries:
- `restaurant_id`: Links to restaurants_master.csv
- `public_rating`: Google Maps rating (if available)
- `public_review_count`: Number of reviews (if available)
- `price_tier`: Price level 1-4 (if available)
- `source`: Data source (google_maps)
- `public_review_snippets_json`: JSON array of review snippets (up to 8, 240 chars each)
- `public_vibe`: One-sentence summary (LLM or fallback generated)
- `public_vibe_source`: "llm" or "fallback"
- `public_vibe_model`: Model name if LLM-generated (e.g., "gpt-4o-mini")
- `public_vibe_updated_at`: ISO timestamp of last update

## API Integration

### Google Maps APIs

The system uses:
- **Places API (New)**: For fetching place details and review snippets
- **Geocoding API**: For resolving query locations to coordinates
- **Distance calculation**: Haversine formula for distance-based ranking

### OpenAI API

Used for generating high-quality "Public vibe" summaries from review snippets:
- Model: `gpt-4o-mini`
- Fallback: Deterministic keyword-based summaries when quota unavailable

## Exporting to Google Sheets

To export experience signals to Google Sheets:

**Simple method** (recommended):
```bash
python scripts/export_to_google_sheets_simple.py
```
Then import `data/experience_signals_for_google_sheets.csv` into Google Sheets via File > Import.

## Development Workflow

1. **Data Pipeline**:
   ```
   Source CSVs → create_master_csv.py → restaurants_master.csv
   restaurants_master.csv → build_experience_signals.py → experience_signals.csv
   restaurants_master.csv → build_public_signals.py → public_signals.csv
   restaurants_master.csv → enrich_locations_google.py → (adds lat/lng/place_id)
   restaurants_master.csv + public_signals.csv → fetch_public_reviews.py → (adds snippets)
   public_signals.csv → generate_public_vibe.py → (adds public_vibe)
   ```

2. **Ranking & Recommendations**:
   - `rank_and_explain.py`: Core ranking logic
   - `server.py`: FastAPI backend that uses ranking system
   - Frontend: React/Vite app that calls backend API

3. **Testing**:
   - Run validation scripts after each data step
   - Test ranking with sample queries
   - Verify API responses include all required fields

## Environment Variables

Required in `.env`:
- `GOOGLE_MAPS_API_KEY`: For Places API and Geocoding API
- `OPENAI_API_KEY`: For generating public vibe summaries (optional, falls back to deterministic)

## Cache Files

The following cache files are created and should be gitignored:
- `data/places_details_cache.json`: Cached Google Places API responses
- `data/public_vibe_cache.json`: Cached LLM-generated public vibes

These caches help avoid redundant API calls during development.
