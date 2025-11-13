#!/usr/bin/env python3
"""
Quick Hugging Face Token Check

Simple one-liner check for HF token validity.
Perfect for CI/CD pipelines and container startup validation.
"""

import os
import sys


def quick_check() -> bool:
    """Quick validation check."""
    token = os.getenv("HUGGINGFACE_TOKEN")

    if not token:
        print("ERROR: HUGGINGFACE_TOKEN not set", file=sys.stderr)
        return False

    print(f"Token found (masked): {token[:10]}...{token[-10:]}")

    try:
        from huggingface_hub import HfApi

        api = HfApi()
        user = api.whoami(token=token)
        print(f"✓ Token valid for user: {user.get('name', 'unknown')}")
        return True
    except Exception as e:
        print(f"ERROR: Token validation failed: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    success = quick_check()
    sys.exit(0 if success else 1)
