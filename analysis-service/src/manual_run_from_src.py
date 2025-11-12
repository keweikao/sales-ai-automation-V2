import asyncio
import logging
import os
import sys
from typing import Any, Dict, Optional

# This script is designed to be run as a module from the project root
# e.g., python3 -m analysis_service.src.manual_run_from_src

# --- Relative Imports ---
from .orchestrator import MultiAgentOrchestrator
from .main import get_transcript_from_firestore, GEMINI_MODEL_DEFAULT, GEMINI_MODEL_FAST, GEMINI_MODEL_PRO
from google.cloud import firestore

# --- Configuration ---
LOGGING_LEVEL = logging.INFO
CASE_ID_TO_ANALYZE = "202511-IC004"

# --- Initialization ---
logging.basicConfig(
    level=LOGGING_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("manual_run_from_src")

async def main():
    """
    Main function to manually trigger and run the analysis pipeline for a single case.
    """
    logger.info(f"--- Starting Manual Analysis for Case ID: {CASE_ID_TO_ANALYZE} ---")

    # 1. Initialize clients
    try:
        db = firestore.Client()
        logger.info("Firestore client initialized successfully.")
        
        # Corrected relative import
        from . import main as main_module
        main_module.db = db

        orchestrator = MultiAgentOrchestrator(
            model_name=GEMINI_MODEL_DEFAULT,
            model_config={
                "agent1": GEMINI_MODEL_FAST,
                "agent2": GEMINI_MODEL_FAST,
                "agent3": GEMINI_MODEL_PRO,
                "agent4": GEMINI_MODEL_FAST,
                "agent5": GEMINI_MODEL_PRO,
            },
            min_success_threshold=3,
            db_client=db,
        )
        logger.info("Multi-Agent Orchestrator initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize clients: {e}", exc_info=True)
        return

    # 2. Fetch transcript data from Firestore
    logger.info(f"Fetching transcript data for case '{CASE_ID_TO_ANALYZE}'...")
    transcript_data = get_transcript_from_firestore(CASE_ID_TO_ANALYZE)

    if not transcript_data:
        logger.error(f"Could not fetch or process transcript data for case '{CASE_ID_TO_ANALYZE}'. Aborting.")
        return

    logger.info("Successfully fetched and processed transcript data.")

    # 3. Execute the analysis pipeline
    logger.info("Executing analysis pipeline (Agents 1-5)...")
    try:
        analysis_result = await orchestrator.analyze_transcript(
            case_id=CASE_ID_TO_ANALYZE,
            transcript_segments=transcript_data['transcript_segments'],
            speaker_statistics=transcript_data['speaker_statistics'],
            conversation_metadata=transcript_data['conversation_metadata'],
        )
        logger.info("Analysis pipeline completed.")
    except Exception as e:
        logger.error(f"An unexpected error occurred during orchestration: {e}", exc_info=True)
        return

    # 4. Generate and print the summary
    logger.info("Generating final analysis summary...")
    summary = orchestrator.get_analysis_summary(analysis_result)

    import json
    final_output = {
        "__MANUAL_RUN_RESULT__": True,
        "summary": summary
    }
    
    print(json.dumps(final_output, indent=2, default=str))
    logger.info("--- Manual Analysis Finished ---")


if __name__ == "__main__":
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        logger.error("FATAL: GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
        sys.exit(1)
    
    asyncio.run(main())
