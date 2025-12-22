#!/usr/bin/env python3
"""Test script to verify chatbot behavior with specific prompts."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.chatbot import RestaurantChatbot

def test_prompt(chatbot, prompt, description):
    """Test a single prompt and print results."""
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"PROMPT: {prompt}")
    print(f"{'='*60}\n")
    
    response = chatbot.process_query(prompt)
    print(response)
    print("\n")
    
    # Reset for next test
    chatbot.reset_conversation()

def main():
    """Run test prompts."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    data_path = repo_root / 'data' / 'restaurants_clean.json'
    
    try:
        chatbot = RestaurantChatbot(data_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    
    # Test 1: NYC near Soho, budget under 25, dinner
    print("TEST 1: NYC near Soho, budget under 25, dinner")
    test_prompt(chatbot, "I'm in NYC near Soho for dinner, cute but not too expensive", "Initial query")
    test_prompt(chatbot, "under 25", "Budget answer")
    test_prompt(chatbot, "dinner", "Meal time answer")
    
    # Test 2: Milan near Brera, first date, lunch
    print("\n\nTEST 2: Milan near Brera, first date, lunch")
    test_prompt(chatbot, "First date tonight in Milan near Brera", "Initial query")
    test_prompt(chatbot, "lunch", "Meal time answer")
    
    # Test 3: Quick lunch NYC SoHo, cheap and fast, budget under 25
    print("\n\nTEST 3: Quick lunch NYC SoHo, cheap and fast, budget under 25")
    test_prompt(chatbot, "Quick lunch in NYC near SoHo, cheap and fast", "Initial query")
    test_prompt(chatbot, "under 25", "Budget answer")
    test_prompt(chatbot, "lunch", "Meal time answer")
    
    # Test 4: Williamsburg - should NOT ask for city
    print("\n\nTEST 4: Williamsburg - should auto-detect NYC")
    test_prompt(chatbot, "I want to try something new in Williamsburg for dinner", "Initial query - should detect NYC automatically")
    test_prompt(chatbot, "dinner", "Meal time answer")

if __name__ == '__main__':
    main()

