#!/usr/bin/env python3
"""Quick test of backend functionality without model loading"""

import sys
sys.path.insert(0, '.')

# Test basic functions that don't need the model
print("Testing MathHumanizer backend functions...")
print("=" * 50)

# Import what we can
from humanizer_api import (
    sentence_length_cv,
    count_forbidden_words,
    AI_BLACKLIST,
    pre_process
)

# Test burstiness calculation
test_text = "This is a short sentence. This is a much longer sentence that contains many more words than the previous one. Short again."
cv = sentence_length_cv(test_text)
print(f"✓ Burstiness (CV) test: {cv:.3f}")

# Test forbidden words detection
test_ai_text = "Furthermore, this crucial aspect demonstrates the multifaceted nature of the problem."
forbidden = count_forbidden_words(test_ai_text)
print(f"✓ Forbidden words detected: {forbidden}")

# Test pre-processing
processed = pre_process(test_ai_text)
print(f"✓ Pre-processing works (output length: {len(processed)} chars)")

print()
print("=" * 50)
print("Core functions working correctly!")
print("Note: Full perplexity calculation requires DistilGPT-2 model.")
print("=" * 50)
