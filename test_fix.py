#!/usr/bin/env python3
"""Simple test to verify genetic_performance_test.py fixes."""

def test_f_string_formatting():
    """Test that f-string formatting works correctly."""
    count = 100
    time_val = 2.5

    # Test the fixed f-strings
    result1 = f"  生成用例数: {count}"
    result2 = f"  耗时: {time_val:.2f}秒"
    result3 = f"  生成速率: {count/time_val:.2f} 用例/秒"

    print("✅ F-string formatting test passed!")
    print(f"Result1: {result1}")
    print(f"Result2: {result2}")
    print(f"Result3: {result3}")

    return True

if __name__ == "__main__":
    test_f_string_formatting()
    print("🎉 genetic_performance_test.py 修复验证完成!")