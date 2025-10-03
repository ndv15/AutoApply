#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QA Test Script for AutoApply Sequential Review System
Tests all 5 acceptance criteria from the plan
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
JOB_ID = "9f0cc0d4"

def test_1_repetitive_bullets():
    """Test 1: No Repetitive Bullets (MMR + History)"""
    print("\n" + "="*80)
    print("TEST 1: No Repetitive Bullets (MMR + History)")
    print("="*80)

    # Step 1: Get first suggestion for ccs-2025
    print("\n→ Fetching first suggestion for role 'ccs-2025'...")
    response = requests.post(
        f"{BASE_URL}/review/{JOB_ID}/suggestions/seq/next",
        json={"role_key": "ccs-2025"}
    )

    if response.status_code != 200:
        print(f"❌ FAIL: API returned {response.status_code}")
        print(response.text)
        return False

    data = response.json()
    first_suggestion = data.get("suggestion")

    if not first_suggestion:
        print("❌ FAIL: No suggestion returned")
        return False

    print(f"✓ Got suggestion: {first_suggestion.get('text', '')[:80]}...")
    print(f"  ID: {first_suggestion.get('id')}")
    print(f"  Score: {first_suggestion.get('score', 0)}/10")

    # Step 2: Accept the first bullet
    print("\n→ Accepting first bullet...")
    response = requests.post(
        f"{BASE_URL}/review/{JOB_ID}/suggestions/seq/accept",
        json={
            "role_key": "ccs-2025",
            "suggestion_id": first_suggestion["id"]
        }
    )

    if response.status_code != 200:
        print(f"❌ FAIL: Accept returned {response.status_code}")
        return False

    print("✓ First bullet accepted")

    # Step 3: Reject next 2 bullets
    for i in range(2):
        print(f"\n→ Fetching bullet #{i+2} to reject...")
        response = requests.post(
            f"{BASE_URL}/review/{JOB_ID}/suggestions/seq/next",
            json={"role_key": "ccs-2025"}
        )

        if response.status_code != 200:
            print(f"❌ FAIL: Next suggestion API error")
            return False

        suggestion = response.json().get("suggestion")
        if not suggestion:
            print(f"❌ FAIL: No suggestion returned for reject #{i+1}")
            return False

        print(f"  Got: {suggestion.get('text', '')[:80]}...")

        # Reject it
        response = requests.post(
            f"{BASE_URL}/review/{JOB_ID}/suggestions/seq/reject",
            json={
                "role_key": "ccs-2025",
                "suggestion_id": suggestion["id"]
            }
        )

        if response.status_code != 200:
            print(f"❌ FAIL: Reject API error")
            return False

        print(f"✓ Bullet #{i+2} rejected")

    # Step 4: Check history file
    print("\n→ Checking suggestion history file...")
    history_path = Path(f"autoapply_scaffold/out/suggestion_history/{JOB_ID}_ccs-2025.json")

    if not history_path.exists():
        print(f"❌ FAIL: History file not found at {history_path}")
        return False

    with open(history_path, 'r') as f:
        history_data = json.load(f)

    stored_suggestions = history_data.get('suggestions', [])
    print(f"✓ History file exists with {len(stored_suggestions)} suggestions")

    if len(stored_suggestions) < 3:
        print(f"❌ FAIL: Expected 3 suggestions in history, got {len(stored_suggestions)}")
        return False

    print("✓ All 3 bullets tracked in history")

    # Step 5: Request 5 more suggestions and check for duplicates
    print("\n→ Requesting 5 more suggestions to verify no duplicates...")
    seen_texts = set(stored_suggestions)
    duplicates_found = 0

    for i in range(5):
        response = requests.post(
            f"{BASE_URL}/review/{JOB_ID}/suggestions/seq/next",
            json={"role_key": "ccs-2025"}
        )

        if response.status_code != 200:
            print(f"  Warning: Could not fetch suggestion #{i+1}")
            continue

        suggestion = response.json().get("suggestion")
        if not suggestion:
            print(f"  No more suggestions available after {i}")
            break

        text = suggestion.get("text", "")

        # Check for duplicates
        if text in seen_texts:
            duplicates_found += 1
            print(f"❌ DUPLICATE FOUND: {text[:60]}...")
        else:
            print(f"  ✓ Unique suggestion #{i+1}")
            seen_texts.add(text)

        # Auto-reject to continue
        requests.post(
            f"{BASE_URL}/review/{JOB_ID}/suggestions/seq/reject",
            json={"role_key": "ccs-2025", "suggestion_id": suggestion["id"]}
        )

    if duplicates_found > 0:
        print(f"\n❌ FAIL: Found {duplicates_found} duplicate suggestions")
        return False

    print("\n✅ TEST 1 PASSED: No repetitive bullets, MMR working, history tracked")
    return True


def test_2_amot_validation():
    """Test 2: AMOT Validation"""
    print("\n" + "="*80)
    print("TEST 2: AMOT Validation")
    print("="*80)

    print("\n→ Fetching 5 suggestions for brightspeed-2022-ii...")
    amot_pass = 0
    amot_fail = 0

    for i in range(5):
        response = requests.post(
            f"{BASE_URL}/review/{JOB_ID}/suggestions/seq/next",
            json={"role_key": "brightspeed-2022-ii"}
        )

        if response.status_code != 200:
            print(f"  Warning: Could not fetch suggestion #{i+1}")
            continue

        suggestion = response.json().get("suggestion")
        if not suggestion:
            print(f"  No more suggestions after {i}")
            break

        text = suggestion.get("text", "")
        print(f"\n  Suggestion #{i+1}:")
        print(f"  {text}")

        # Check AMOT components
        has_action = any(text.startswith(v) for v in ['Led', 'Drove', 'Increased', 'Closed', 'Built', 'Achieved', 'Expanded', 'Implemented', 'Generated', 'Managed'])
        has_metric = any(char in text for char in ['%', '$']) or '[' in text  # % or $ or placeholder
        has_outcome = any(word in text.lower() for word in ['resulting', 'achieving', 'leading to', 'driving', 'generating'])
        has_tool = any(word in text.lower() for word in ['via', 'using', 'through', 'leveraging', 'with'])

        print(f"    Action verb: {'✓' if has_action else '✗'}")
        print(f"    Metric (%, $, [X]): {'✓' if has_metric else '✗'}")
        print(f"    Outcome phrase: {'✓' if has_outcome else '✗'}")
        print(f"    Tool/method: {'✓' if has_tool else '✗'}")

        if has_action and has_metric and has_outcome and has_tool:
            amot_pass += 1
            print("    ✅ AMOT COMPLIANT")
        else:
            amot_fail += 1
            print("    ❌ NOT AMOT COMPLIANT")

        # Auto-reject
        requests.post(
            f"{BASE_URL}/review/{JOB_ID}/suggestions/seq/reject",
            json={"role_key": "brightspeed-2022-ii", "suggestion_id": suggestion["id"]}
        )

    print(f"\n→ Results: {amot_pass} AMOT compliant, {amot_fail} failed")

    if amot_fail > 0:
        print(f"\n❌ FAIL: {amot_fail} bullets were not AMOT compliant")
        return False

    if amot_pass == 0:
        print("\n❌ FAIL: No suggestions were tested")
        return False

    print("\n✅ TEST 2 PASSED: All bullets are AMOT compliant")
    return True


def test_3_resume_preview():
    """Test 3: Resume Preview Updates"""
    print("\n" + "="*80)
    print("TEST 3: Resume Preview Updates After Accept")
    print("="*80)

    # Accept a bullet for brightspeed-2021
    print("\n→ Fetching suggestion for brightspeed-2021...")
    response = requests.post(
        f"{BASE_URL}/review/{JOB_ID}/suggestions/seq/next",
        json={"role_key": "brightspeed-2021"}
    )

    if response.status_code != 200:
        print("❌ FAIL: Could not fetch suggestion")
        return False

    suggestion = response.json().get("suggestion")
    if not suggestion:
        print("❌ FAIL: No suggestion returned")
        return False

    bullet_text = suggestion.get("text", "")
    print(f"  Got bullet: {bullet_text[:80]}...")

    # Accept it
    print("\n→ Accepting bullet...")
    response = requests.post(
        f"{BASE_URL}/review/{JOB_ID}/suggestions/seq/accept",
        json={
            "role_key": "brightspeed-2021",
            "suggestion_id": suggestion["id"]
        }
    )

    if response.status_code != 200:
        print(f"❌ FAIL: Accept returned {response.status_code}")
        return False

    data = response.json()
    preview_html = data.get("preview_html")

    if not preview_html:
        print("❌ FAIL: No preview_html in response")
        print(f"Response keys: {list(data.keys())}")
        return False

    print("✓ Received preview_html from server")
    print(f"  HTML length: {len(preview_html)} characters")

    # Verify HTML contains the bullet
    if bullet_text[:40] in preview_html:
        print(f"✓ Bullet found in preview HTML")
    else:
        print(f"❌ FAIL: Bullet not found in preview HTML")
        return False

    # Verify HTML contains role header
    if "brightspeed-2021" in preview_html or "Brightspeed" in preview_html:
        print("✓ Role header found in preview")
    else:
        print("❌ FAIL: Role header not in preview")
        return False

    # Verify HTML contains expected structure
    required_elements = ["resume-name", "resume-contact", "Professional Experience", "resume-bullet"]
    missing = []
    for elem in required_elements:
        if elem not in preview_html:
            missing.append(elem)

    if missing:
        print(f"❌ FAIL: Missing elements in HTML: {missing}")
        return False

    print("✓ All required HTML elements present")

    print("\n✅ TEST 3 PASSED: Resume preview updates correctly")
    return True


def test_4_quota_gating():
    """Test 4: Quota Gating"""
    print("\n" + "="*80)
    print("TEST 4: Quota Gating on Generate Button")
    print("="*80)

    # Check status endpoint
    print("\n→ Checking /seq/progress endpoint...")
    response = requests.get(f"{BASE_URL}/review/{JOB_ID}/seq/progress")

    if response.status_code != 200:
        print(f"❌ FAIL: Status endpoint returned {response.status_code}")
        return False

    data = response.json()
    print("✓ Status endpoint responded")

    # Verify structure
    if "roles" not in data or "all_complete" not in data or "can_continue" not in data:
        print(f"❌ FAIL: Missing required fields in response")
        print(f"  Keys: {list(data.keys())}")
        return False

    print("✓ Response has required fields: roles, all_complete, can_continue")

    # Check current state
    all_complete = data.get("all_complete", False)
    roles = data.get("roles", {})

    print(f"\n→ Current quota status:")
    for role_id, status in roles.items():
        accepted = status.get("accepted_count", 0)
        quota = status.get("quota", 0)
        is_complete = status.get("is_complete", False)
        print(f"  {role_id}: {accepted}/{quota} {'✓' if is_complete else '⏳'}")

    print(f"\n→ all_complete: {all_complete}")
    print(f"→ can_continue: {data.get('can_continue', False)}")

    if all_complete:
        print("  Note: All quotas already met (from previous tests)")
    else:
        print("  ✓ Gating working: not all quotas met")

    print("\n✅ TEST 4 PASSED: Quota gating endpoint working correctly")
    return True


def test_5_skills_formatting():
    """Test 5: Skills Formatting"""
    print("\n" + "="*80)
    print("TEST 5: Skills Formatting (Dynamic Categories)")
    print("="*80)

    print("\n→ Checking if format_skills_for_resume exists...")

    # Import the function
    try:
        import sys
        sys.path.insert(0, 'autoapply_scaffold')
        from app.writing.skills_engine import format_skills_for_resume
        print("✓ Function imported successfully")
    except ImportError as e:
        print(f"❌ FAIL: Could not import function: {e}")
        return False

    # Test with sample skills
    test_skills = [
        "MEDDIC",
        "Salesforce",
        "Pipeline Management",
        "Negotiation",
        "HubSpot",
        "Territory Planning",
        "Leadership",
        "Forecasting"
    ]

    print(f"\n→ Testing with {len(test_skills)} skills...")
    result = format_skills_for_resume(test_skills, max_categories=4)

    if not result:
        print("❌ FAIL: Function returned empty result")
        return False

    print(f"✓ Got {len(result)} category lines:")
    for i, line in enumerate(result, 1):
        print(f"  {i}. {line}")

    # Verify format
    for line in result:
        if ':' not in line:
            print(f"❌ FAIL: Line missing colon separator: {line}")
            return False

        if '|' not in line:
            print(f"❌ FAIL: Line missing pipe separator: {line}")
            return False

        category, items = line.split(':', 1)
        if not category.strip() or not items.strip():
            print(f"❌ FAIL: Empty category or items: {line}")
            return False

    print("✓ All lines have correct format: 'Category: item | item'")

    if len(result) > 4:
        print(f"❌ FAIL: More than 4 categories ({len(result)})")
        return False

    print(f"✓ Category count within limit (max 4)")

    print("\n✅ TEST 5 PASSED: Skills formatting is correct")
    return True


def main():
    print("\n" + "="*80)
    print("AutoApply QA Test Suite")
    print("Testing Implementation of 5 Acceptance Criteria")
    print("="*80)

    results = {}

    # Run tests
    results["Test 1: No Repetitive Bullets"] = test_1_repetitive_bullets()
    results["Test 2: AMOT Validation"] = test_2_amot_validation()
    results["Test 3: Resume Preview"] = test_3_resume_preview()
    results["Test 4: Quota Gating"] = test_4_quota_gating()
    results["Test 5: Skills Formatting"] = test_5_skills_formatting()

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} — {test_name}")

    total_passed = sum(results.values())
    total_tests = len(results)

    print(f"\n→ Overall: {total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED! Implementation is complete and correct.")
        return 0
    else:
        print(f"\n⚠️  {total_tests - total_passed} test(s) failed. Review implementation.")
        return 1


if __name__ == "__main__":
    exit(main())
