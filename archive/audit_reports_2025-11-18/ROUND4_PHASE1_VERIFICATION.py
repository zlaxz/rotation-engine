#!/usr/bin/env python3
"""
ROUND 4 VERIFICATION - Exit Engine Phase 1 (Simple Time-Based)

Tests the simple Phase 1 implementation that just exits on fixed days.
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

from datetime import date, timedelta
from src.trading.exit_engine import ExitEngine


class MockTrade:
    """Mock trade object for testing"""
    def __init__(self, entry_date):
        self.entry_date = entry_date


def test_phase1_basic_exit():
    """Test basic Phase 1 exit on fixed day"""
    print("\n" + "="*80)
    print("TEST #1: Phase 1 Basic Time-Based Exit")
    print("="*80)

    engine = ExitEngine(phase=1)

    # Trade entered on day 0
    trade = MockTrade(entry_date=date(2024, 1, 15))

    # Day 7: Should not exit (14-day default)
    current = date(2024, 1, 22)  # 7 days later
    should_exit, reason = engine.should_exit(trade, current, 'Profile_1_LDG')
    print(f"Day 7: should_exit={should_exit}, reason={reason}")
    if not should_exit:
        print("✅ Correct: No exit before day 14")
    else:
        print("❌ FAILED: Should not exit at day 7")
        return False

    # Day 14: Should exit
    current = date(2024, 1, 29)  # 14 days later
    should_exit, reason = engine.should_exit(trade, current, 'Profile_1_LDG')
    print(f"Day 14: should_exit={should_exit}, reason={reason}")
    if should_exit:
        print("✅ Correct: Exit at day 14")
    else:
        print("❌ FAILED: Should exit at day 14")
        return False

    # Day 20: Should exit (already past exit day)
    current = date(2024, 2, 4)  # 20 days later
    should_exit, reason = engine.should_exit(trade, current, 'Profile_1_LDG')
    print(f"Day 20: should_exit={should_exit}, reason={reason}")
    if should_exit:
        print("✅ Correct: Exit after day 14")
    else:
        print("❌ FAILED: Should exit after day 14")
        return False

    return True


def test_phase1_custom_exit_days():
    """Test custom exit days override"""
    print("\n" + "="*80)
    print("TEST #2: Phase 1 Custom Exit Days")
    print("="*80)

    # Create engine with custom exit days
    custom_days = {
        'Profile_1_LDG': 7,
        'Profile_2_SDG': 3,
        'Profile_3_CHARM': 5,
    }
    engine = ExitEngine(phase=1, custom_exit_days=custom_days)

    trade = MockTrade(entry_date=date(2024, 1, 15))

    # Profile 1: Should exit at day 7
    current = date(2024, 1, 22)  # 7 days
    should_exit, reason = engine.should_exit(trade, current, 'Profile_1_LDG')
    print(f"Profile_1_LDG, day 7: should_exit={should_exit}")
    if should_exit:
        print("✅ Custom exit day respected for Profile_1_LDG")
    else:
        print("❌ FAILED: Custom exit day not respected")
        return False

    # Profile 2: Should exit at day 3
    current = date(2024, 1, 18)  # 3 days
    should_exit, reason = engine.should_exit(trade, current, 'Profile_2_SDG')
    print(f"Profile_2_SDG, day 3: should_exit={should_exit}")
    if should_exit:
        print("✅ Custom exit day respected for Profile_2_SDG")
    else:
        print("❌ FAILED: Custom exit day not respected")
        return False

    return True


def test_phase1_profile_isolation():
    """Test that different profiles have independent exit days"""
    print("\n" + "="*80)
    print("TEST #3: Phase 1 Profile Isolation")
    print("="*80)

    engine = ExitEngine(phase=1)

    trade = MockTrade(entry_date=date(2024, 1, 15))
    current = date(2024, 1, 29)  # 14 days

    # All profiles default to 14 days
    profiles = ['Profile_1_LDG', 'Profile_2_SDG', 'Profile_3_CHARM',
                'Profile_4_VANNA', 'Profile_5_SKEW', 'Profile_6_VOV']

    all_exit = True
    for profile in profiles:
        should_exit, reason = engine.should_exit(trade, current, profile)
        if not should_exit:
            print(f"❌ {profile} did not exit at day 14")
            all_exit = False

    if all_exit:
        print(f"✅ All {len(profiles)} profiles exit correctly at day 14")
    return all_exit


def test_phase1_get_exit_day():
    """Test getter methods"""
    print("\n" + "="*80)
    print("TEST #4: Phase 1 Getter Methods")
    print("="*80)

    custom_days = {'Profile_1_LDG': 10}
    engine = ExitEngine(phase=1, custom_exit_days=custom_days)

    # Test get_exit_day
    day_p1 = engine.get_exit_day('Profile_1_LDG')
    day_p2 = engine.get_exit_day('Profile_2_SDG')

    print(f"Profile_1_LDG exit day: {day_p1} (should be 10)")
    print(f"Profile_2_SDG exit day: {day_p2} (should be 14)")

    if day_p1 == 10 and day_p2 == 14:
        print("✅ Getters work correctly")
    else:
        print("❌ Getters returned wrong values")
        return False

    # Test get_all_exit_days
    all_days = engine.get_all_exit_days()
    print(f"All exit days: {all_days}")

    if all_days['Profile_1_LDG'] == 10 and all_days['Profile_2_SDG'] == 14:
        print("✅ get_all_exit_days works correctly")
    else:
        print("❌ get_all_exit_days failed")
        return False

    return True


def test_phase1_invalid_profile():
    """Test handling of unknown profile"""
    print("\n" + "="*80)
    print("TEST #5: Phase 1 Invalid Profile Handling")
    print("="*80)

    engine = ExitEngine(phase=1)
    trade = MockTrade(entry_date=date(2024, 1, 15))

    # Unknown profile should default to 14 days
    current = date(2024, 1, 29)  # 14 days
    should_exit, reason = engine.should_exit(trade, current, 'Unknown_Profile')
    print(f"Unknown profile, day 14: should_exit={should_exit}")

    if should_exit:
        print("✅ Unknown profile defaults to 14 days")
    else:
        print("❌ FAILED: Unknown profile should default to 14 days")
        return False

    return True


def test_phase1_phase_validation():
    """Test that only Phase 1 is supported"""
    print("\n" + "="*80)
    print("TEST #6: Phase 1 Validation")
    print("="*80)

    try:
        engine = ExitEngine(phase=2)
        print("❌ FAILED: Should have raised NotImplementedError for phase 2")
        return False
    except NotImplementedError as e:
        print(f"✅ Correctly raised NotImplementedError: {e}")
        return True


def test_phase1_boundary_conditions():
    """Test boundary conditions"""
    print("\n" + "="*80)
    print("TEST #7: Phase 1 Boundary Conditions")
    print("="*80)

    engine = ExitEngine(phase=1)
    trade = MockTrade(entry_date=date(2024, 1, 15))

    # Day 0 (same day): Should NOT exit
    current = date(2024, 1, 15)
    should_exit, reason = engine.should_exit(trade, current, 'Profile_1_LDG')
    if not should_exit:
        print("✅ Day 0 (entry day): No exit")
    else:
        print("❌ FAILED: Should not exit on entry day")
        return False

    # Day 1: Should NOT exit
    current = date(2024, 1, 16)
    should_exit, reason = engine.should_exit(trade, current, 'Profile_1_LDG')
    if not should_exit:
        print("✅ Day 1: No exit")
    else:
        print("❌ FAILED: Should not exit on day 1")
        return False

    # Day 13: Should NOT exit
    current = date(2024, 1, 28)
    should_exit, reason = engine.should_exit(trade, current, 'Profile_1_LDG')
    if not should_exit:
        print("✅ Day 13: No exit")
    else:
        print("❌ FAILED: Should not exit on day 13")
        return False

    return True


def run_all_tests():
    """Run all Phase 1 tests"""
    print("\n" + "#"*80)
    print("# ROUND 4 VERIFICATION - EXIT ENGINE PHASE 1")
    print("#"*80)

    tests = [
        ("Basic Time-Based Exit", test_phase1_basic_exit),
        ("Custom Exit Days", test_phase1_custom_exit_days),
        ("Profile Isolation", test_phase1_profile_isolation),
        ("Getter Methods", test_phase1_get_exit_day),
        ("Invalid Profile Handling", test_phase1_invalid_profile),
        ("Phase Validation", test_phase1_phase_validation),
        ("Boundary Conditions", test_phase1_boundary_conditions),
    ]

    results = []
    for test_name, test_fn in tests:
        try:
            result = test_fn()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ TEST CRASHED: {test_name}")
            print(f"Exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "#"*80)
    print("# PHASE 1 SUMMARY")
    print("#"*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL PHASE 1 TESTS PASSED - Exit Engine Phase 1 is CLEAN")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
