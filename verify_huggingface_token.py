#!/usr/bin/env python3
"""
Hugging Face Token Verification Script for Pyannote Diarization

This script verifies:
1. HF_TOKEN environment variable is set
2. Token can authenticate to Hugging Face API
3. Token has access to pyannote diarization models
4. Model can be loaded successfully
"""

import os
import sys
import logging
from typing import Optional, Dict, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_env_variable() -> Tuple[bool, str]:
    """Check if HUGGINGFACE_TOKEN environment variable is set."""
    logger.info("=" * 60)
    logger.info("Step 1: Checking HUGGINGFACE_TOKEN environment variable")
    logger.info("=" * 60)

    token = os.getenv("HUGGINGFACE_TOKEN")

    if token:
        # Show masked token for security
        masked_token = token[:10] + "*" * (len(token) - 20) + token[-10:]
        logger.info(f"✓ HUGGINGFACE_TOKEN is set: {masked_token}")
        return True, token
    else:
        logger.error("✗ HUGGINGFACE_TOKEN environment variable is not set!")
        logger.error("  Please set it with: export HUGGINGFACE_TOKEN='your-token-here'")
        return False, ""


def verify_huggingface_api(token: str) -> bool:
    """Verify token can authenticate to Hugging Face API."""
    logger.info("\n" + "=" * 60)
    logger.info("Step 2: Verifying token with Hugging Face API")
    logger.info("=" * 60)

    try:
        from huggingface_hub import HfApi

        api = HfApi()
        user_info = api.whoami(token=token)

        logger.info(f"✓ Token is valid!")
        logger.info(f"  Username: {user_info.get('name', 'N/A')}")
        logger.info(f"  Organization: {user_info.get('org_name', 'N/A')}")
        return True

    except Exception as e:
        logger.error(f"✗ Token validation failed: {e}")
        logger.error("  Ensure token has read access permissions")
        return False


def check_model_access(token: str, model_name: str) -> bool:
    """Check if token has access to the specified model."""
    logger.info("\n" + "=" * 60)
    logger.info(f"Step 3: Checking access to {model_name}")
    logger.info("=" * 60)

    try:
        from huggingface_hub import HfApi, ModelFilter

        api = HfApi()
        model_info = api.model_info(model_name, token=token)

        logger.info(f"✓ Model found: {model_name}")
        logger.info(f"  Downloads (last month): {model_info.downloads}")
        logger.info(f"  Task: {model_info.pipeline_tag}")

        # Check if it requires acceptance of terms
        if hasattr(model_info, 'gated') and model_info.gated:
            logger.warning("  Note: This model requires acceptance of terms")
            logger.warning("  Visit: https://huggingface.co/" + model_name)
            return False

        return True

    except Exception as e:
        logger.error(f"✗ Model access check failed: {e}")
        logger.error("  The token may not have access to this model")
        logger.error("  Or the model may require accepting terms of use")
        logger.error(f"  Visit: https://huggingface.co/{model_name}")
        return False


def test_model_loading(token: str, model_name: str) -> bool:
    """Test if the model can be loaded with the token."""
    logger.info("\n" + "=" * 60)
    logger.info(f"Step 4: Testing model loading from {model_name}")
    logger.info("=" * 60)

    try:
        logger.info("Importing pyannote.audio...")
        from pyannote.audio import Pipeline

        logger.info(f"Loading pipeline: {model_name}")
        logger.info("(This may take a few minutes on first run...)")

        pipeline = Pipeline.from_pretrained(model_name, use_auth_token=token)

        if pipeline is None:
            logger.error("✗ Pipeline loading returned None")
            return False

        logger.info(f"✓ Model loaded successfully!")
        logger.info(f"  Pipeline type: {type(pipeline)}")
        return True

    except Exception as e:
        logger.error(f"✗ Model loading failed: {e}")
        error_str = str(e).lower()

        if "gated" in error_str or "accept" in error_str:
            logger.error("  This model requires accepting terms of use")
            logger.error("  Visit: https://huggingface.co/" + model_name)
        elif "token" in error_str or "auth" in error_str:
            logger.error("  Token authentication failed or token has insufficient permissions")
        elif "import" in error_str or "pyannote" in error_str:
            logger.error("  pyannote.audio is not installed or has compatibility issues")
            logger.error("  Try: pip install pyannote.audio==3.1.1")

        return False


def run_full_verification(models: Optional[list] = None) -> Dict[str, bool]:
    """Run full verification suite."""
    if models is None:
        models = [
            "pyannote/speaker-diarization",
            "pyannote/speaker-diarization-3.1",
        ]

    results = {}

    # Step 1: Check environment variable
    env_ok, token = check_env_variable()
    results["env_variable"] = env_ok

    if not env_ok:
        logger.error("\nCannot proceed without HUGGINGFACE_TOKEN environment variable")
        return results

    # Step 2: Verify API access
    api_ok = verify_huggingface_api(token)
    results["huggingface_api"] = api_ok

    if not api_ok:
        logger.error("\nCannot proceed without valid Hugging Face API credentials")
        return results

    # Step 3 & 4: Check each model
    for model_name in models:
        logger.info(f"\n--- Testing model: {model_name} ---")

        access_ok = check_model_access(token, model_name)
        results[f"model_access_{model_name}"] = access_ok

        if access_ok:
            load_ok = test_model_loading(token, model_name)
            results[f"model_loading_{model_name}"] = load_ok
        else:
            logger.warning(f"Skipping loading test for {model_name} due to access issues")
            results[f"model_loading_{model_name}"] = False

    return results


def print_summary(results: Dict[str, bool]) -> None:
    """Print verification summary."""
    logger.info("\n" + "=" * 60)
    logger.info("VERIFICATION SUMMARY")
    logger.info("=" * 60)

    for check, status in results.items():
        symbol = "✓" if status else "✗"
        logger.info(f"{symbol} {check}: {'PASS' if status else 'FAIL'}")

    all_passed = all(results.values())

    logger.info("\n" + "=" * 60)
    if all_passed:
        logger.info("SUCCESS: All checks passed!")
        logger.info("Your Hugging Face token is properly configured for Pyannote diarization.")
    else:
        logger.error("FAILURE: Some checks failed.")
        logger.error("See details above for remediation steps.")
    logger.info("=" * 60)

    return all_passed


def main():
    """Main entry point."""
    logger.info("Hugging Face Token Verification for Pyannote Diarization")
    logger.info("Version: 1.0.0\n")

    results = run_full_verification()
    success = print_summary(results)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
