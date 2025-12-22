#!/usr/bin/env python3
"""Smoke test suite for the restaurant chatbot."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.chatbot import RestaurantChatbot

tests = [
    ("First date tonight in Milan near Brera", ["lunch or dinner"]),
    ("Quick lunch in NYC near SoHo, cheap and fast", ["Tried and loved"]),
    ("I want to try something new in Williamsburg for dinner", ["Tried and loved", "want-to-try"]),
]

def run():
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    data_path = repo_root / 'data' / 'restaurants_clean.json'
    
    bot = RestaurantChatbot(data_path)

    for i, (q, must_contain) in enumerate(tests, 1):
        # fresh state per test
        bot = RestaurantChatbot(data_path)

        print("\n" + "=" * 60)
        print(f"TEST {i}: {q}")
        print("=" * 60)

        out = bot.process_query(q)
        print(out)
        
        # If it asks for budget (check for the question pattern, not the answer)
        if "what's your budget" in out.lower() or "budget per person" in out.lower():
            out = bot.process_query("under 25")
            print("\n[Answering budget question: under 25]")
            print(out)
        
        # If it asks for meal time, answer it
        if "lunch or dinner" in out.lower() or "is this for lunch" in out.lower():
            # Extract meal time from original query if present
            meal_answer = "lunch" if "lunch" in q.lower() else "dinner" if "dinner" in q.lower() else "dinner"
            out = bot.process_query(meal_answer)
            print(f"\n[Answering meal time question: {meal_answer}]")
            print(out)

        ok = True
        lower_out = out.lower()
        for s in must_contain:
            if s.lower() not in lower_out:
                ok = False
                print(f"❌ missing expected text: {s}")

        if ok:
            print("✅ passed")

if __name__ == "__main__":
    run()

