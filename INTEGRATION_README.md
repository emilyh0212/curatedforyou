# Restaurant Chatbot Integration Guide

This document explains how to run the integrated restaurant recommendation chatbot with the React frontend and FastAPI backend.

## Project Structure

- **Backend**: Python FastAPI server (`server.py`) that uses the chatbot logic from `scripts/chatbot.py`
- **Frontend**: React + TypeScript + Vite app in the `frontend/` folder of this repo
- **Data**: Restaurant data in `data/restaurants_clean.json`

## Setup Instructions

### 1. Backend Setup

1. **Install Python dependencies** (from the repo root):
   ```bash
   pip install -r requirements.txt
   ```

2. **Ensure restaurant data exists**:
   ```bash
   # If data/restaurants_clean.json doesn't exist, run:
   python scripts/clean_saved.py
   ```

3. **Start the FastAPI server**:
   ```bash
   uvicorn server:app --reload --port 8000
   ```

   The server will run on `http://localhost:8000`

### 2. Frontend Setup

1. **Navigate to frontend directory** (still inside this repo):
   ```bash
   cd frontend
   ```

2. **(Optional) Set the API URL**:
   ```bash
   cp .env.example .env.local   # only if your backend isn't on http://localhost:8000
   ```

3. **Install dependencies**:
   ```bash
   npm install
   ```

4. **Start the development server**:
   ```bash
   npm run dev
   ```

   The frontend will run on `http://localhost:3000` (configured in `vite.config.ts`)

## Running the Application

1. **Start the backend** (in one terminal, at the repo root):
   ```bash
   uvicorn server:app --reload --port 8000
   ```

2. **Start the frontend** (in another terminal):
   ```bash
   cd frontend
   npm run dev
   ```

3. **Open your browser** to `http://localhost:3000`

## How It Works

- The frontend sends chat messages to the backend `/chat` endpoint
- The backend processes messages using the `RestaurantChatbot` class
- Restaurant recommendations are returned as structured data
- The frontend displays chat messages and restaurant results using the Figma-designed UI components

## Features

- ✅ City selector (NYC/Milan) wired to chatbot
- ✅ Chat input sends messages to backend
- ✅ Restaurant results displayed in "Tried and loved" and "Want-to-try" sections
- ✅ Google Maps links for each restaurant
- ✅ Conversation flow with message bubbles
- ✅ Favorites section for quick queries

## API Endpoints

- `POST /chat` - Process chat message and return recommendations
- `POST /swap` - Swap one restaurant for another using the same query context
- `GET /health` - Health check endpoint

## Troubleshooting

- **CORS errors**: Make sure the backend is running on port 8000 and frontend is on port 3000 (or update CORS settings in `server.py`)
- **No restaurants returned**: Check that `data/restaurants_clean.json` exists and contains valid data
- **Frontend can't connect**: Verify backend is running and accessible at `http://localhost:8000`

