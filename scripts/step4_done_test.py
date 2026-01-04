#!/usr/bin/env python3
"""
Step 4 Done-Criteria Test Runner

Validates that the ranking and explanation system meets all requirements.
"""

import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

# Track failures
failures = []
warnings = []


def check_a_files_and_functions():
    """A) Files and functions exist (import success)"""
    print("=" * 80)
    print("A) Files and Functions Exist")
    print("=" * 80)
    
    try:
        from rank_and_explain import recommend, load_data, parse_query, score_restaurant, build_explanation
        print("✓ All functions imported successfully")
        return True
    except ImportError as e:
        failures.append(("A", f"Import failed: {e}"))
        print(f"❌ FAIL: Import failed: {e}")
        return False


def check_b_data_join_integrity():
    """B) Data join integrity (row count = 153, unique restaurant_id, required columns exist)"""
    print("\n" + "=" * 80)
    print("B) Data Join Integrity")
    print("=" * 80)
    
    try:
        from rank_and_explain import load_data
        data = load_data()
        
        # Check row count
        row_count = len(data)
        if row_count != 153:
            failures.append(("B1", f"Expected 153 rows, got {row_count}"))
            print(f"❌ FAIL: Expected 153 rows, got {row_count}")
            return False
        else:
            print(f"✓ Row count: {row_count}")
        
        # Check unique restaurant_id
        restaurant_ids = [row.get('restaurant_id', '') for row in data]
        unique_ids = set(restaurant_ids)
        if len(unique_ids) != 153:
            failures.append(("B2", f"Expected 153 unique restaurant_ids, got {len(unique_ids)}"))
            print(f"❌ FAIL: Expected 153 unique restaurant_ids, got {len(unique_ids)}")
            return False
        else:
            print(f"✓ Unique restaurant_ids: {len(unique_ids)}")
        
        # Check required columns from each source
        required_master = ['restaurant_id', 'name', 'city', 'status', 'your_note', 'google_maps_url']
        required_experience = ['would_recommend', 'confidence', 'best_for', 'vibe', 'food_strength']
        required_public = ['public_rating', 'public_review_count', 'price_tier']
        
        sample_row = data[0]
        missing_master = [col for col in required_master if col not in sample_row]
        missing_experience = [col for col in required_experience if col not in sample_row]
        missing_public = [col for col in required_public if col not in sample_row]
        
        if missing_master or missing_experience or missing_public:
            failures.append(("B3", f"Missing columns: master={missing_master}, experience={missing_experience}, public={missing_public}"))
            print(f"❌ FAIL: Missing required columns")
            if missing_master:
                print(f"   Master: {missing_master}")
            if missing_experience:
                print(f"   Experience: {missing_experience}")
            if missing_public:
                print(f"   Public: {missing_public}")
            return False
        else:
            print(f"✓ All required columns present")
            print(f"   Master columns: {len(required_master)}")
            print(f"   Experience columns: {len(required_experience)}")
            print(f"   Public columns: {len(required_public)}")
        
        return True
        
    except Exception as e:
        failures.append(("B", f"Data integrity check failed: {e}"))
        print(f"❌ FAIL: Data integrity check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_c_scoring_output_validity():
    """C) Scoring output validity (sample 20 rows, score bounds and component consistency)"""
    print("\n" + "=" * 80)
    print("C) Scoring Output Validity")
    print("=" * 80)
    
    try:
        from rank_and_explain import load_data, parse_query, score_restaurant
        
        data = load_data()
        sample_size = min(20, len(data))
        sample_rows = data[:sample_size]
        
        parsed_query = parse_query("romantic dinner in NYC")
        
        issues = []
        
        for i, row in enumerate(sample_rows):
            try:
                score_result = score_restaurant(row, parsed_query)
                
                final_score = score_result.get('final_score', 0)
                components = score_result.get('components', {})
                match_score = components.get('match_score', 0)
                taste_score = components.get('taste_score', 0)
                public_score = components.get('public_score', 0)
                
                # Check score bounds
                if final_score < 0 or final_score > 100:
                    issues.append(f"Row {i+1} ({row.get('restaurant_id', 'unknown')}): final_score out of bounds: {final_score}")
                
                if match_score < 0 or match_score > 40:
                    issues.append(f"Row {i+1} ({row.get('restaurant_id', 'unknown')}): match_score out of bounds: {match_score}")
                
                if taste_score < 0 or taste_score > 40:
                    issues.append(f"Row {i+1} ({row.get('restaurant_id', 'unknown')}): taste_score out of bounds: {taste_score}")
                
                if public_score < 0 or public_score > 20:
                    issues.append(f"Row {i+1} ({row.get('restaurant_id', 'unknown')}): public_score out of bounds: {public_score}")
                
                # Check component consistency (sum should approximately equal final_score)
                component_sum = match_score + taste_score + public_score
                if abs(final_score - component_sum) > 0.1:  # Allow small floating point differences
                    issues.append(f"Row {i+1} ({row.get('restaurant_id', 'unknown')}): Score mismatch: final={final_score}, sum={component_sum}")
                
            except Exception as e:
                issues.append(f"Row {i+1} ({row.get('restaurant_id', 'unknown')}): Scoring failed: {e}")
        
        if issues:
            failures.append(("C", f"Scoring issues found: {len(issues)}"))
            print(f"❌ FAIL: Found {len(issues)} scoring issues")
            for issue in issues[:5]:  # Show first 5
                print(f"   {issue}")
            if len(issues) > 5:
                print(f"   ... and {len(issues) - 5} more")
            return False
        else:
            print(f"✓ Scored {sample_size} sample rows successfully")
            print(f"✓ All scores within bounds (0-100)")
            print(f"✓ Component scores consistent (match: 0-40, taste: 0-40, public: 0-20)")
            return True
        
    except Exception as e:
        failures.append(("C", f"Scoring validation failed: {e}"))
        print(f"❌ FAIL: Scoring validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_d_ranking_constraints():
    """D) Ranking constraints for 5 specific queries"""
    print("\n" + "=" * 80)
    print("D) Ranking Constraints")
    print("=" * 80)
    
    try:
        from rank_and_explain import recommend
        
        test_queries = [
            ("romantic dinner in SoHo", "NYC"),
            ("casual brunch with friends in Milan", "Milan"),
            ("good pasta place in NYC", None),
            ("cheap eats in Koreatown", "NYC"),
            ("date night spot in Milan Navigli", "Milan")
        ]
        
        issues = []
        
        for query, city in test_queries:
            try:
                results = recommend(query, top_n=6, city=city)
                
                # Check result count
                if len(results) == 0:
                    issues.append(f"Query '{query}': No results returned")
                    continue
                
                if len(results) > 6:
                    issues.append(f"Query '{query}': Returned {len(results)} results, expected max 6")
                
                # Check required fields
                required_fields = ['restaurant_id', 'name', 'city', 'status', 'final_score', 
                                 'why', 'price_tier', 'public_rating', 'public_review_count']
                
                for i, result in enumerate(results):
                    missing_fields = [field for field in required_fields if field not in result]
                    if missing_fields:
                        issues.append(f"Query '{query}', result {i+1}: Missing fields: {missing_fields}")
                    
                    # Check score is numeric
                    try:
                        score = float(result.get('final_score', 0))
                        if score < 0 or score > 100:
                            issues.append(f"Query '{query}', result {i+1}: Invalid score: {score}")
                    except (ValueError, TypeError):
                        issues.append(f"Query '{query}', result {i+1}: Non-numeric score: {result.get('final_score')}")
                
                # Check hard rule: max 1 want_to_try in top 6
                want_to_try_count = sum(1 for r in results if r.get('status') == 'want_to_try')
                if want_to_try_count > 1:
                    issues.append(f"Query '{query}': Found {want_to_try_count} want_to_try restaurants, max allowed is 1")
                
                # Check scores are descending
                scores = [float(r.get('final_score', 0)) for r in results]
                if scores != sorted(scores, reverse=True):
                    issues.append(f"Query '{query}': Results not sorted by score descending")
                
            except Exception as e:
                issues.append(f"Query '{query}': Failed with error: {e}")
        
        if issues:
            failures.append(("D", f"Ranking constraint issues: {len(issues)}"))
            print(f"❌ FAIL: Found {len(issues)} ranking constraint issues")
            for issue in issues[:5]:
                print(f"   {issue}")
            if len(issues) > 5:
                print(f"   ... and {len(issues) - 5} more")
            return False
        else:
            print(f"✓ All 5 test queries passed ranking constraints")
            print(f"✓ Max 1 want_to_try in top 6 (hard rule)")
            print(f"✓ Results properly sorted by score")
            print(f"✓ All required fields present")
            return True
        
    except Exception as e:
        failures.append(("D", f"Ranking constraint check failed: {e}"))
        print(f"❌ FAIL: Ranking constraint check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_e_explanation_quality():
    """E) Explanation quality constraints (length, banned phrases, non empty)"""
    print("\n" + "=" * 80)
    print("E) Explanation Quality")
    print("=" * 80)
    
    try:
        from rank_and_explain import recommend
        
        test_queries = [
            ("romantic dinner in SoHo", "NYC"),
            ("casual brunch with friends in Milan", "Milan"),
            ("good pasta place in NYC", None)
        ]
        
        banned_phrases = [
            'people say',
            'review',
            'reviews say',
            'according to',
            'users say',
            'customers say'
        ]
        
        issues = []
        all_explanations = []
        
        for query, city in test_queries:
            try:
                results = recommend(query, top_n=6, city=city)
                
                for i, result in enumerate(results):
                    why = result.get('why', '').strip()
                    all_explanations.append(why)
                    
                    # Check non-empty
                    if not why:
                        issues.append(f"Query '{query}', result {i+1} ({result.get('name', 'unknown')}): Empty explanation")
                        continue
                    
                    # Check length (should be reasonable, not too long)
                    if len(why) > 200:
                        issues.append(f"Query '{query}', result {i+1} ({result.get('name', 'unknown')}): Explanation too long ({len(why)} chars)")
                    
                    # Check for banned phrases
                    why_lower = why.lower()
                    for banned in banned_phrases:
                        if banned in why_lower:
                            issues.append(f"Query '{query}', result {i+1} ({result.get('name', 'unknown')}): Contains banned phrase '{banned}'")
                    
                    # Check it's not just generic
                    generic_phrases = ['a great match', 'a good restaurant', 'recommended']
                    if why.lower().strip() in generic_phrases and len(why.split()) < 5:
                        warnings.append(f"Query '{query}', result {i+1}: Very generic explanation: '{why}'")
                    
            except Exception as e:
                issues.append(f"Query '{query}': Failed with error: {e}")
        
        if issues:
            failures.append(("E", f"Explanation quality issues: {len(issues)}"))
            print(f"❌ FAIL: Found {len(issues)} explanation quality issues")
            for issue in issues[:5]:
                print(f"   {issue}")
            if len(issues) > 5:
                print(f"   ... and {len(issues) - 5} more")
        else:
            print(f"✓ All explanations are non-empty")
            print(f"✓ No banned phrases found")
            print(f"✓ Reasonable length (checked {len(all_explanations)} explanations)")
        
        if warnings:
            print(f"\n⚠️  Warnings ({len(warnings)}):")
            for warning in warnings[:3]:
                print(f"   {warning}")
        
        return len(issues) == 0
        
    except Exception as e:
        failures.append(("E", f"Explanation quality check failed: {e}"))
        print(f"❌ FAIL: Explanation quality check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all checks and print summary"""
    print("=" * 80)
    print("STEP 4 DONE-CRITERIA TEST RUNNER")
    print("=" * 80)
    print()
    
    # Run all checks
    results = {
        'A': check_a_files_and_functions(),
        'B': check_b_data_join_integrity(),
        'C': check_c_scoring_output_validity(),
        'D': check_d_ranking_constraints(),
        'E': check_e_explanation_quality()
    }
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✓ PASS: All checks passed!")
    else:
        print("\n❌ FAIL: Some checks failed")
        print("\nFailing rules:")
        for rule, details in failures:
            print(f"  {rule}: {details}")
    
    print(f"\nCheck Results:")
    for check, passed in results.items():
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"  {check}) {status}")
    
    print()
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

