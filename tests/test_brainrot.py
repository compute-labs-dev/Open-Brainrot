#!/usr/bin/env python3

from brainrot_generator import transform_to_brainrot
import sys
import os

# Create test input file
test_input = """Agent Daily Digest Bot
Daily Digest (Mar 4, 2025) – AI, Compute, & Web3
Macro:
• Trump's 25% tariffs on Canada and Mexico, 20% on China took effect; all three countries announced retaliatory measures.
• Treasury Secretary Bessent confirms administration is "set on bringing interest rates down".
• IRS drafting plans to cut up to half of its 90,000-person workforce through layoffs and buyouts.
Technology & Infrastructure:
• BlackRock consortium acquires Hutchison Port Holdings for $23 billion, gaining control of 43 ports in 23 countries.
• T-Mobile's parent Deutsche Telekom announced sub-$1K AI phone with Perplexity Assistant launching later this year.
• Reddit co-founder Alexis Ohanian joins bid to acquire TikTok US and "bring it on-chain".
"""

with open("test_input.txt", "w") as f:
    f.write(test_input)

# Test with Donald Trump voice
print("Testing with Donald Trump voice...")
brainrot, paths = transform_to_brainrot(
    "test_input.txt", voice="donald_trump", model="o3mini")
print(f"Brainrot word count: {len(brainrot.split())}")
print(f"First 100 words: {' '.join(brainrot.split()[:100])}")
print(f"Last 100 words: {' '.join(brainrot.split()[-100:])}")

# Test with Ben Shapiro voice
print("\nTesting with Ben Shapiro voice...")
brainrot, paths = transform_to_brainrot(
    "test_input.txt", voice="ben_shapiro", model="o3mini")
print(f"Brainrot word count: {len(brainrot.split())}")
print(f"First 100 words: {' '.join(brainrot.split()[:100])}")
print(f"Last 100 words: {' '.join(brainrot.split()[-100:])}")

# Test with Joe Rogan voice
print("\nTesting with Joe Rogan voice...")
brainrot, paths = transform_to_brainrot(
    "test_input.txt", voice="joe_rogan", model="o3mini")
print(f"Brainrot word count: {len(brainrot.split())}")
print(f"First 100 words: {' '.join(brainrot.split()[:100])}")
print(f"Last 100 words: {' '.join(brainrot.split()[-100:])}")
