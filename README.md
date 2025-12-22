# Curated For You

A personal restaurant recommendation chatbot that reflects Emily's taste, powered by her curated restaurant dataset.

## Setup

1. **Install dependencies** (if not already installed):
   ```bash
   pip install pandas
   ```

2. **Clean the restaurant data**:
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

Restaurant records include:
- `city`: Milan or New York
- `status`: tried or want
- `name`: Restaurant name
- `note`: Emily's personal notes
- `url`: Google Maps URL
- `place_id`: Extracted Google Place ID
- `tags`: Tags (if any)
- `comment`: Comments (if any)
