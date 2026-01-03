# Curated For You

A personal restaurant recommendation chatbot that reflects Emily's taste, powered by her curated restaurant dataset.

## Setup

1. **Install dependencies** (if not already installed):
   ```bash
   pip install pandas
   ```

2. **Build the master restaurant database** (Step 1):
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

3. **Generate experience signals** (Step 2):
   ```bash
   python scripts/build_experience_signals.py
   ```
   
   This infers experience signals from restaurant notes:
   - Reads from: `data/restaurants_master.csv`
   - Creates: `data/experience_signals.csv`
   - Infers: confidence, would_recommend, best_for, vibe, food_strength, dealbreakers
   - Uses controlled tag dictionaries for consistent tagging

4. **Clean the restaurant data** (legacy):
   ```bash
   python scripts/clean_saved.py
   ```
   
   This will process the CSV files in `data/` and create:
   - `data/restaurants_clean.csv`
   - `data/restaurants_clean.json`
   - `data/restaurants_clean.ndjson`

## Usage

Run the chatbot:
```bash
python scripts/chatbot.py
```

The chatbot will help you find restaurants based on:
- **City**: Milan or New York City
- **Neighborhood**: Soft filtering (prefers selected neighborhood but may suggest nearby matches)
- **Vibe**: Romantic, cute, casual, cheap, vibey, quick, fancy, brunch, study
- **Meal time**: Lunch or dinner
- **Constraints**: Price, speed, no lines

## Example Queries

- "I want something romantic in SoHo for dinner"
- "Cheap lunch spots in Milan, Navigli area"
- "Cute brunch place in Williamsburg"
- "Quick dinner in NYC, Lower East Side"

## Features

- **Personal recommendations**: Only suggests restaurants from Emily's curated list
- **Tried vs. Want-to-try**: Prioritizes places Emily has tried, clearly labels want-to-try items
- **Neighborhood-aware**: Soft filtering that prefers selected neighborhoods but suggests nearby matches when appropriate
- **City auto-detection**: Automatically detects city from neighborhood (e.g., Williamsburg → NYC, Brera → Milan)
- **Budget-aware**: Filters out expensive restaurants and cocktail bars for low budgets
- **Vibe matching**: Uses Emily's personal notes to match vibe requests
- **Emily's voice**: Responses sound like Emily texting a close friend

## Testing

Run the smoke test suite:
```bash
python scripts/smoke_test.py
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

### Legacy Data Structure

Restaurant records include:
- `city`: Milan or New York
- `status`: tried or want
- `name`: Restaurant name
- `note`: Emily's personal notes
- `url`: Google Maps URL
- `place_id`: Extracted Google Place ID
- `tags`: Tags (if any)
- `comment`: Comments (if any)

## Exporting to Google Sheets

To export experience signals to Google Sheets:

**Simple method** (recommended):
```bash
python scripts/export_to_google_sheets_simple.py
```
Then import `data/experience_signals_for_google_sheets.csv` into Google Sheets via File > Import.

**Automated method** (requires Google Cloud setup):
```bash
pip install gspread google-auth
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
python scripts/export_to_google_sheets.py
```
