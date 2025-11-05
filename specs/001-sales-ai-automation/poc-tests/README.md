# POC Test Scripts

This directory contains all test scripts for Phase 0 POC validation.

## Directory Structure

- `poc1_whisper/` - Faster-Whisper + Speaker Diarization performance tests
- `poc2_multi_agent/` - Multi-agent parallel orchestration tests
- `poc3_gemini_json/` - Gemini structured output quality tests
- `poc4_slack/` - Slack Block Kit interactivity tests
- `poc5_firestore/` - Firestore query performance and cost tests
- `poc6_questionnaire/` - Discovery questionnaire extraction accuracy tests

### Agent 6 & 7 Prompt Harness

- `analysis-service/src/agents/run_agent6_agent7.py` - CLI helper to execute Agent 6 (Sales Coach) and Agent 7 (Customer Summary) prompts using Gemini.
- `analysis-service/tests/samples/sample_agent_inputs.json` - Sample transcript metadata + Agent 1–5 outputs for quick dry-run.
- 若僅需 smoke 測試，可使用 `--mock-scenario {positive|negative|insufficient}`，腳本會讀取對應 fixture 而不呼叫 Gemini。

## Quick Start

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt  # 若僅需 Agent 6/7 測試，至少安裝 pytest

# Setup GCP credentials
gcloud auth application-default login
export GCP_PROJECT_ID="your-project-id"

# Setup Slack credentials (for POC 4)
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_SIGNING_SECRET="..."

# Setup Gemini API key (for POC 2, 3, 6, Agent 6/7 harness)
export GEMINI_API_KEY="..."
```

### Run All POCs

```bash
# Run all tests
./run_all_pocs.sh

# Run specific POC
cd poc1_whisper && python test_whisper.py

# Execute Agent 6 & 7 harness
python ../../analysis-service/src/agents/run_agent6_agent7.py \
  --inputs ../../analysis-service/tests/samples/sample_agent_inputs.json \
  --output-dir ./results/agent67

# Run Agent 6 & 7 mock regression (no API calls)
make test-agent67
```

## Test Datasets

Test audio files and transcripts are stored in `test_data/`:

- `test_data/audio/` - 10 test audio files (10min, 20min, 30min, 40min, 60min)
- `test_data/transcripts/` - 30 test transcripts for Gemini tests
- `test_data/ground_truth/` - Ground truth labels for questionnaire tests

**Note**: Test data is NOT committed to git due to size. Download from Google Drive:
[Test Data Download Link] (TODO: Upload and add link)

## Expected Timeline

- POC 1: 2-3 days
- POC 2: 1 day
- POC 3: 2 days
- POC 4: 1 day
- POC 5: 1 day
- POC 6: 2-3 days

**Total**: 7-10 days sequential, **3-4 days with 3 team members in parallel**

## Success Criteria Summary

| POC | Success Threshold |
|-----|------------------|
| POC 1 | Processing <5min, Diarization >80%, Quality >85% |
| POC 2 | Parallel <40s, Errors <5% |
| POC 3 | Schema compliance >95%, Hallucination <5% |
| POC 4 | Response <3s, No dropped events |
| POC 5 | Query <300ms, Cost <$5/month |
| POC 6 | Topic detection >85%, Accuracy >75%, Satisfaction >3.5/5 |

## Go/No-Go Decision

After completing all POCs, document results in `results/` directory and make Go/No-Go decision for each component.

See `../research.md` for detailed test procedures and decision trees.
