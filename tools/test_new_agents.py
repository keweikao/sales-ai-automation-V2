import os
import sys
import asyncio
import re
import logging
import json
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set GCP Location to us-central1 to test availability
os.environ["GCP_LOCATION"] = "us-central1"
os.environ["GCP_PROJECT"] = "sales-ai-automation-v2"

# Add analysis-service to python path (parent of src)
sys.path.append(os.path.join(os.getcwd(), "analysis-service"))

from src.orchestrator import MultiAgentOrchestrator  # noqa: E402

TRANSCRIPT_FILE = "202512-IC001_transcript_fixed.txt"

def parse_transcript(file_path: str) -> List[Dict[str, Any]]:
    segments = []
    current_segment = None
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            # Match [MM:SS] Speaker: Content
            match = re.match(r"\[(\d{2}):(\d{2})\] (.*?): (.*)", line)
            if match:
                minutes, seconds, speaker, text = match.groups()
                start_seconds = int(minutes) * 60 + int(seconds)
                
                if current_segment:
                    current_segment["end"] = start_seconds
                    segments.append(current_segment)
                
                current_segment = {
                    "start": start_seconds,
                    "end": start_seconds + 5, # Default duration if last
                    "speaker": speaker,
                    "text": text
                }
            elif current_segment:
                # Append continuation lines
                current_segment["text"] += " " + line
                
    if current_segment:
        segments.append(current_segment)
        
    return segments

async def main():
    print(f"Loading transcript from {TRANSCRIPT_FILE}...")
    segments = parse_transcript(TRANSCRIPT_FILE)
    print(f"Loaded {len(segments)} segments.")
    
    print("Initializing Orchestrator (3+1 Architecture)...")
    # Initialize without DB to skip persistence
    # Testing gemini-1.5-flash in us-central1
    orchestrator = MultiAgentOrchestrator(
        model_name="gemini-2.0-flash",
        db_client=None 
    )
    
    print("Starting Analysis...")
    result = await orchestrator.analyze_transcript(
        case_id="TEST_CASE_001",
        transcript_segments=segments
    )
    
    print(f"\nAnalysis Complete. Success: {result.success}")
    print(f"Total Duration: {result.total_duration:.2f}s")
    
    if not result.success:
        print(f"Error: {result.error}")
        return

    # Print Results
    print("\n" + "="*50)
    print("AGENT 1: CONTEXT (The Scene)")
    print("="*50)
    print(json.dumps(result.agent_results['agent1'].data, indent=2, ensure_ascii=False))
    
    print("\n" + "="*50)
    print("AGENT 2: BUYER (Customer & Product)")
    print("="*50)
    print(json.dumps(result.agent_results['agent2'].data, indent=2, ensure_ascii=False))
    
    print("\n" + "="*50)
    print("AGENT 3: SELLER (Sales Coach)")
    print("="*50)
    print(json.dumps(result.agent_results['agent3'].data, indent=2, ensure_ascii=False))

    print("\n" + "="*50)
    print("AGENT 4: SUMMARY (Meeting Minutes)")
    print("="*50)
    print(json.dumps(result.agent_results['agent4'].data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
