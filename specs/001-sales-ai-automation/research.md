# Phase 0 Research: Technical Validation & Proof-of-Concepts

**Feature**: Sales AI Automation System V2.0
**Phase**: 0 - Research & POC Validation
**Date**: 2025-01-29
**Status**: Ready for Execution
**Related Docs**: [spec.md](./spec.md) | [plan.md](./plan.md)

---

## Objective

Validate 6 critical technical assumptions before committing to full implementation. Each POC tests a key uncertainty that could block or significantly impact the architecture.

**Success Criteria**: All POCs must meet their defined thresholds OR provide clear fallback paths.

**Timeline**: 1-2 weeks (can run POCs in parallel)

---

## POC Overview

| POC | Question | Risk if Wrong | Time |
|-----|----------|--------------|------|
| 1 | Can Faster-Whisper + diarization process 40-min audio in <5 min on CPU? | Architecture requires GPU (+$10-15/month) | 2-3 days |
| 2 | Can 5 Gemini agents execute in <40s parallel? | Sequential execution → 2x slower | 1 day |
| 3 | Can Gemini produce consistent structured JSON? | Need fallback parsing → complexity | 2 days |
| 4 | Can Slack Block Kit handle interactivity within 3s timeout? | Need Socket Mode → architecture change | 1 day |
| 5 | Can Firestore handle queries within budget? | Need BigQuery → cost increase | 1 day |
| 6 | Can Agent 5 extract questionnaires at >75% accuracy? | Manual questionnaire needed → UX degradation | 2-3 days |

**Total Estimated Time**: 7-10 days (with parallel execution: 3-4 days)

---

## POC 1: Faster-Whisper Performance with Speaker Diarization

### Question
Can Faster-Whisper with speaker diarization process 40-minute Chinese audio in <5 minutes on Cloud Run (CPU-only)?

### Why This Matters
- **Cost Impact**: GPU adds $10-15/month
- **Architecture Impact**: CPU-only keeps system simple
- **Performance**: <5 min target enables <4 min end-to-end processing

### Success Criteria
| Metric | Target | Fallback Threshold |
|--------|--------|-------------------|
| Processing Time (40-min audio) | <5 min (0.125x real-time) | <7 min acceptable |
| Speaker Diarization Accuracy | >80% (2-3 speakers) | >70% acceptable |
| Chinese Transcription Quality | >85% WER | >80% acceptable |
| Memory Usage | <3GB | <4GB max (Cloud Run limit) |
| Cost per File | <$0.10 compute | <$0.15 acceptable |

### Test Setup

#### Environment
```yaml
Platform: Cloud Run
CPU: 2 vCPU
Memory: 4 GB
Region: asia-east1 (Taiwan)
Container: Python 3.11 + faster-whisper
```

#### Test Dataset
- **Quantity**: 10 diverse audio files
- **Formats**: m4a (primary), mp3, wav
- **Durations**: 10min, 20min, 30min, 40min, 60min
- **Languages**: Traditional Chinese (primary), Simplified Chinese, Mixed Chinese-English
- **Speaker Counts**: 1 speaker, 2 speakers, 3 speakers
- **Audio Quality**: Good (studio), Medium (phone recording), Poor (noisy environment)

#### Models to Test
1. **faster-whisper large-v3** (recommended - best Chinese accuracy)
2. **faster-whisper medium** (fallback - faster but less accurate)

#### Diarization Methods to Test
1. **pyannote.audio** (deep learning-based, higher accuracy)
2. **simple VAD + clustering** (faster, lower accuracy)

### Test Procedure

#### Step 1: Baseline Test (No Diarization)
```bash
# Deploy minimal Cloud Run service
cd poc/whisper-test
docker build -t whisper-test .
gcloud run deploy whisper-test --image whisper-test --region asia-east1

# Test transcription only
curl -X POST https://whisper-test-xxx.run.app/transcribe \
  -F "audio=@test-40min-chinese.m4a" \
  -F "enable_diarization=false"

# Measure: processing_time, quality_score, memory_peak
```

#### Step 2: Diarization Test (pyannote.audio)
```bash
# Enable diarization
curl -X POST https://whisper-test-xxx.run.app/transcribe \
  -F "audio=@test-40min-2speakers.m4a" \
  -F "enable_diarization=true" \
  -F "diarization_method=pyannote"

# Measure: processing_time, speaker_separation_accuracy, quality_score
```

#### Step 3: Manual Validation
- Randomly sample 5 files
- Sales rep manually reviews speaker boundaries
- Calculate accuracy: `correct_boundaries / total_boundaries`

#### Step 4: Cost Analysis
```python
# Calculate cost per file
cpu_time_seconds = 240  # Example: 4 minutes
vcpu_count = 2
cost_per_vcpu_second = 0.00002400

compute_cost = cpu_time_seconds * vcpu_count * cost_per_vcpu_second
print(f"Cost per file: ${compute_cost:.4f}")

# Target: <$0.10 per file
# 250 files/month = $25/month compute
```

### Expected Results

#### Hypothesis
- **large-v3 + pyannote**: 4-5 minutes, >85% quality, >80% diarization accuracy
- **medium + simple VAD**: 2-3 minutes, >80% quality, >70% diarization accuracy

#### Decision Tree
```
IF processing_time <5 min AND quality >85% AND diarization >80%:
    → Use large-v3 + pyannote (recommended path)

ELIF processing_time <7 min AND quality >80% AND diarization >70%:
    → Use medium + simple VAD (acceptable fallback)

ELSE:
    → Consider GPU acceleration (adds $10-15/month)
    → OR disable diarization (use text-based speaker inference)
```

### Risks & Mitigations

| Risk | Probability | Mitigation |
|------|------------|------------|
| Processing >7 min | Medium | Use GPU-enabled Cloud Run (n1-standard-1 with T4) |
| Memory >4GB | Low | Reduce batch size, process in chunks |
| Diarization accuracy <70% | Medium | Fallback to text-based speaker inference (Agent 1 infers from content) |
| Chinese accuracy <80% | Low | Fine-tune Whisper on Chinese sales call data (Phase 3) |

---

## POC 2: Multi-Agent Orchestration Performance

### Question
Can 5 Gemini agents execute in parallel within 40 seconds total?

### Why This Matters
- **Performance**: 40s target keeps total processing <4 min
- **Cost**: Parallel execution is critical to avoid 5x latency
- **Rate Limits**: Need to verify Gemini API can handle 5 concurrent requests

### Success Criteria
| Metric | Target | Fallback Threshold |
|--------|--------|-------------------|
| Parallel Execution Time (Agents 1-5) | <40s | <60s acceptable |
| Individual Agent Time | <30s each | <45s acceptable |
| Agent 6 Synthesis Time | <20s | <30s acceptable |
| Total Analysis Time | <60s | <90s acceptable |
| Gemini API Rate Limit Errors | 0 errors | <5% error rate acceptable |

### Test Setup

#### Environment
```yaml
Platform: Local development (then Cloud Run)
Python: 3.11
Libraries: google-generativeai, asyncio
Model: gemini-1.5-flash
API Key: Test quota (15 RPM free tier)
```

#### Test Transcript
- **Source**: Real 40-minute sales call (anonymized)
- **Length**: ~10,000 Chinese characters
- **Speakers**: 3 (sales rep, owner, manager)
- **Content**: Discussion of POS system, pricing, competitors

#### Agent Configurations
```python
agents = {
    "agent1_participant": {
        "prompt": "participant_analyzer.md",
        "expected_output": "participants[]",
        "expected_tokens": 500,
        "expected_time": 30
    },
    "agent2_sentiment": {
        "prompt": "sentiment_analyzer.md",
        "expected_output": "sentiment{}",
        "expected_tokens": 400,
        "expected_time": 20
    },
    "agent3_needs": {
        "prompt": "needs_extractor.md",
        "expected_output": "productNeeds{}",
        "expected_tokens": 600,
        "expected_time": 25
    },
    "agent4_competitor": {
        "prompt": "competitor_analyzer.md",
        "expected_output": "competitors[]",
        "expected_tokens": 300,
        "expected_time": 20
    },
    "agent5_questionnaire": {
        "prompt": "questionnaire_analyzer.md",
        "expected_output": "discoveryQuestionnaires[]",
        "expected_tokens": 500,
        "expected_time": 25
    }
}
```

### Test Procedure

#### Step 1: Sequential Baseline
```python
# Test agents sequentially to get individual times
import time
from google import generativeai as genai

genai.configure(api_key="YOUR_API_KEY")
model = genai.GenerativeModel('gemini-1.5-flash')

transcript = open("test_transcript.txt").read()

results = {}
for agent_id, config in agents.items():
    prompt = open(config["prompt"]).read() + f"\n\nTranscript:\n{transcript}"

    start = time.time()
    response = model.generate_content(prompt)
    duration = time.time() - start

    results[agent_id] = {
        "duration": duration,
        "tokens": response.usage_metadata.total_token_count,
        "output": response.text
    }

    print(f"{agent_id}: {duration:.2f}s, {results[agent_id]['tokens']} tokens")

total_sequential = sum(r["duration"] for r in results.values())
print(f"Total sequential: {total_sequential:.2f}s")
```

#### Step 2: Parallel Execution
```python
import asyncio

async def run_agent(agent_id, config, transcript):
    prompt = open(config["prompt"]).read() + f"\n\nTranscript:\n{transcript}"

    start = time.time()
    response = await model.generate_content_async(prompt)
    duration = time.time() - start

    return {
        "agent_id": agent_id,
        "duration": duration,
        "tokens": response.usage_metadata.total_token_count,
        "output": response.text
    }

async def run_all_agents():
    tasks = [run_agent(aid, cfg, transcript) for aid, cfg in agents.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

# Execute
start = time.time()
results = asyncio.run(run_all_agents())
parallel_duration = time.time() - start

print(f"Parallel execution: {parallel_duration:.2f}s")
print(f"Speedup: {total_sequential / parallel_duration:.2f}x")

# Check for rate limit errors
errors = [r for r in results if isinstance(r, Exception)]
print(f"Errors: {len(errors)}/{len(results)}")
```

#### Step 3: Load Test (Concurrent Cases)
```python
# Simulate 10 concurrent cases (50 parallel Gemini calls)
async def process_case(case_id, transcript):
    results = await run_all_agents(transcript)
    return case_id, results

async def load_test():
    transcripts = [load_transcript(i) for i in range(10)]
    tasks = [process_case(i, t) for i, t in enumerate(transcripts)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

# Measure: total time, error rate, rate limit hits
start = time.time()
results = asyncio.run(load_test())
duration = time.time() - start

print(f"10 cases (50 parallel calls): {duration:.2f}s")
print(f"Average per case: {duration/10:.2f}s")
```

#### Step 4: Agent 6 Synthesis Test
```python
# Agent 6 receives outputs from Agents 1-5
agent6_input = {
    "participants": results["agent1_participant"]["output"],
    "sentiment": results["agent2_sentiment"]["output"],
    "productNeeds": results["agent3_needs"]["output"],
    "competitors": results["agent4_competitor"]["output"],
    "questionnaires": results["agent5_questionnaire"]["output"]
}

prompt = open("sales_coach_synthesizer.md").read()
prompt += f"\n\nAgent Outputs:\n{json.dumps(agent6_input, ensure_ascii=False)}"

start = time.time()
response = model.generate_content(prompt)
agent6_duration = time.time() - start

print(f"Agent 6 synthesis: {agent6_duration:.2f}s")
print(f"Subtotal analysis time: {parallel_duration + agent6_duration:.2f}s")

# Agent 7: Customer Summary Test
agent7_input = {
    "transcript": transcript_text,
    "structured": response.text,
    "participants": results["agent1_participant"],
    "sentiment": results["agent2_sentiment"],
    "productNeeds": results["agent3_needs"],
    "competitors": results["agent4_competitor"],
    "questionnaires": results["agent5_questionnaire"],
}

summary_prompt = open("customer_summary.md").read()
summary_prompt += f"\n\nAgent Outputs:\n{json.dumps(agent7_input, ensure_ascii=False)}"

start = time.time()
summary_response = model.generate_content(summary_prompt)
agent7_duration = time.time() - start

print(f"Agent 7 summary: {agent7_duration:.2f}s")
print(f"Total analysis time: {parallel_duration + agent6_duration + agent7_duration:.2f}s")
```

### Expected Results

#### Hypothesis
- **Parallel Execution (Agents 1-5)**: 30-40s (dominated by slowest agent)
- **Agent 6 Synthesis**: 15-20s
- **Agent 7 Summary**: 10-15s
- **Total Analysis**: 55-75s

#### Decision Tree
```
IF parallel_time <40s AND agent6_time <20s AND errors == 0:
    → Proceed with parallel architecture (recommended)

ELIF parallel_time <60s AND rate_limit_errors <5%:
    → Acceptable, monitor in production

ELSE IF rate_limit_errors >5%:
    → Implement token bucket queue (adds 10-20s latency)
    → OR upgrade to Gemini API paid tier (higher rate limits)

ELSE IF parallel_time >60s:
    → Reduce prompt lengths
    → OR use faster model (gemini-1.5-flash-8b)
```

### Risks & Mitigations

| Risk | Probability | Mitigation |
|------|------------|------------|
| Rate limit errors (>5%) | Medium | Implement exponential backoff + retry queue |
| Parallel time >60s | Low | Optimize prompts (reduce examples, shorten context) |
| Gemini API downtime | Low | Implement circuit breaker, retry with backoff |
| Cost exceeds budget | Low | Monitor token usage, optimize prompts |

---

## POC 3: Gemini Structured Output Quality

### Question
Can Gemini 1.5 Flash produce consistent structured outputs (JSON) with >95% schema compliance?

### Why This Matters
- **Automation**: Structured outputs enable direct database storage
- **Reliability**: High compliance rate = less error handling code
- **User Experience**: Poor JSON = failed analyses = user frustration

### Success Criteria
| Metric | Target | Fallback Threshold |
|--------|--------|-------------------|
| JSON Schema Compliance | >95% | >90% acceptable |
| Hallucination Rate | <5% | <10% acceptable |
| Field Completeness | >90% | >80% acceptable |
| Parsing Errors | <2% | <5% acceptable |

### Test Setup

#### Test Dataset (30 Transcripts)
- **Variety**:
  - Short calls (10 min): 10 transcripts
  - Medium calls (30 min): 10 transcripts
  - Long calls (60 min): 10 transcripts
- **Speaker Counts**: 1, 2, 3, 4+ speakers
- **Scenarios**: Cold call, demo, negotiation, objection handling

#### JSON Schemas (Pydantic Models)
```python
from pydantic import BaseModel, Field
from typing import List, Literal

class Participant(BaseModel):
    speakerId: str
    role: str
    roleConfidence: int = Field(ge=0, le=100)
    personalityType: Literal["analytical", "driver", "amiable", "expressive"]
    decisionPower: int = Field(ge=0, le=100)
    influenceLevel: Literal["primary", "secondary", "observer"]
    concerns: List[dict]
    interests: List[str]

class Agent1Output(BaseModel):
    participants: List[Participant]

# (Similar schemas for Agents 2-6)
```

### Test Procedure

#### Step 1: Schema Compliance Test
```python
import json
from pydantic import ValidationError

def test_schema_compliance(agent_id, schema_class, test_transcripts):
    results = {
        "total": len(test_transcripts),
        "valid": 0,
        "invalid": 0,
        "errors": []
    }

    for i, transcript in enumerate(test_transcripts):
        prompt = load_prompt(f"{agent_id}.md") + f"\n\nTranscript:\n{transcript}"
        response = model.generate_content(prompt)

        try:
            # Extract JSON from response (may have markdown code blocks)
            json_text = extract_json(response.text)
            data = json.loads(json_text)

            # Validate against Pydantic schema
            validated = schema_class(**data)
            results["valid"] += 1

        except (json.JSONDecodeError, ValidationError) as e:
            results["invalid"] += 1
            results["errors"].append({
                "transcript_id": i,
                "error": str(e),
                "response": response.text[:200]
            })

    compliance_rate = results["valid"] / results["total"] * 100
    print(f"{agent_id} compliance: {compliance_rate:.1f}%")

    return results

# Test all agents
for agent_id, schema in agent_schemas.items():
    test_schema_compliance(agent_id, schema, test_transcripts)
```

#### Step 2: Hallucination Detection Test
```python
# Test if agents invent information not in transcript
def test_hallucinations():
    # Use transcripts with known ground truth
    test_cases = [
        {
            "transcript": "只有業務員和老闆兩個人對話...",
            "ground_truth": {
                "participant_count": 2,
                "competitors_mentioned": [],
                "products_discussed": ["POS系統"]
            }
        },
        # ... more test cases
    ]

    hallucinations = []

    for case in test_cases:
        # Run Agent 1 (Participant)
        result = run_agent("agent1", case["transcript"])
        if len(result.participants) != case["ground_truth"]["participant_count"]:
            hallucinations.append({
                "agent": "agent1",
                "type": "phantom_participant",
                "expected": case["ground_truth"]["participant_count"],
                "actual": len(result.participants)
            })

        # Run Agent 4 (Competitor)
        result = run_agent("agent4", case["transcript"])
        mentioned = [c.name for c in result.competitors]
        phantom = set(mentioned) - set(case["ground_truth"]["competitors_mentioned"])
        if phantom:
            hallucinations.append({
                "agent": "agent4",
                "type": "phantom_competitor",
                "invented": list(phantom)
            })

    hallucination_rate = len(hallucinations) / len(test_cases) * 100
    print(f"Hallucination rate: {hallucination_rate:.1f}%")

    return hallucinations
```

#### Step 3: Field Completeness Test
```python
def test_field_completeness(agent_id, required_fields):
    """Test if agent fills all required fields"""

    completeness_scores = []

    for transcript in test_transcripts:
        result = run_agent(agent_id, transcript)
        result_dict = result.dict()

        filled_fields = sum(1 for f in required_fields if result_dict.get(f) is not None)
        completeness = filled_fields / len(required_fields) * 100
        completeness_scores.append(completeness)

    avg_completeness = sum(completeness_scores) / len(completeness_scores)
    print(f"{agent_id} field completeness: {avg_completeness:.1f}%")

    return completeness_scores

# Example: Agent 3 should fill all product need fields
agent3_required = [
    "explicitNeeds",
    "implicitNeeds",
    "recommendedProducts",
    "budget.estimatedMin",
    "budget.estimatedMax",
    "decisionTimeline.urgency"
]
test_field_completeness("agent3", agent3_required)
```

#### Step 4: Prompt Engineering Iteration
```python
# If compliance <95%, iterate on prompts:
improvements = {
    "add_json_schema": "Provide JSON schema in prompt",
    "add_examples": "Add 2-3 example outputs",
    "structured_generation": "Use Gemini function calling",
    "output_constraints": "Add strict output format rules"
}

for improvement_name, description in improvements.items():
    print(f"Testing: {description}")
    # Modify prompt
    # Re-run compliance test
    # Compare results
```

### Expected Results

#### Hypothesis
- **Initial Compliance**: 85-90% (without optimization)
- **After Prompt Engineering**: >95%
- **Hallucination Rate**: <5%
- **Field Completeness**: >90%

#### Decision Tree
```
IF compliance >95% AND hallucination <5%:
    → Proceed with JSON output parsing (recommended)

ELIF compliance 90-95%:
    → Use Gemini function calling (higher compliance, slight latency increase)

ELIF compliance <90%:
    → Implement retry with error feedback
    → OR fallback to regex-based extraction (less reliable)

IF hallucination >10%:
    → Add stricter prompt instructions
    → OR implement hallucination detection filters
```

### Risks & Mitigations

| Risk | Probability | Mitigation |
|------|------------|------------|
| Compliance <95% | Medium | Use Gemini function calling API |
| High hallucination (>10%) | Low | Add ground truth validation, stricter prompts |
| Parsing errors | Medium | Implement robust JSON extraction (handle markdown blocks) |
| Field incompleteness | Low | Make fields optional in schema, handle missing data gracefully |

---

## POC 4: Slack Block Kit Interactivity

### Question
Can Slack Block Kit + FastAPI handle interactive buttons, modals, and threaded conversations within 3s timeout?

### Why This Matters
- **User Experience**: Slack has 3s timeout for interactions
- **Architecture**: If timeout exceeded, need Socket Mode (WebSocket)
- **Complexity**: Socket Mode adds deployment complexity

### Success Criteria
| Metric | Target | Fallback Threshold |
|--------|--------|-------------------|
| Button Click Response Time | <1s | <2s acceptable |
| Modal Submission Processing | <2s | <3s acceptable |
| Thread Context Retrieval | <500ms | <1s acceptable |
| Concurrent Interactions (10 users) | No dropped events | <5% drop acceptable |

### Test Setup

#### Environment
```yaml
Platform: Local FastAPI → Cloud Run
Framework: FastAPI + slack-bolt
Slack App: Test workspace
Tools: ngrok (for local testing), pytest-asyncio
```

#### Test Slack App Features
1. Slash command: `/test-upload`
2. Interactive message with 5 buttons
3. Modal form with 3 fields
4. Threaded message detection
5. Conversational AI (simple echo bot)

### Test Procedure

#### Step 1: Basic Slack App Setup
```python
# slack_service.py
from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler
from fastapi import FastAPI, Request

app = FastAPI()
slack_app = App(token="xoxb-...", signing_secret="...")
handler = SlackRequestHandler(slack_app)

@slack_app.command("/test-upload")
def handle_upload_command(ack, command, client):
    start = time.time()
    ack()  # Acknowledge within 3s

    # Open modal
    client.views_open(
        trigger_id=command["trigger_id"],
        view={
            "type": "modal",
            "title": {"type": "plain_text", "text": "Upload Audio"},
            "submit": {"type": "plain_text", "text": "Submit"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "customer_name",
                    "label": {"type": "plain_text", "text": "Customer Name"},
                    "element": {"type": "plain_text_input", "action_id": "customer_name_input"}
                }
            ]
        }
    )

    duration = time.time() - start
    print(f"Slash command processed in {duration:.3f}s")

@app.post("/slack/events")
async def endpoint(req: Request):
    return await handler.handle(req)

# Run: uvicorn slack_service:app --reload
# Expose: ngrok http 8000
```

#### Step 2: Interactive Message Test
```python
@slack_app.action("view_transcript")
def handle_view_transcript(ack, action, client):
    start = time.time()
    ack()

    # Simulate Firestore fetch
    case_id = action["value"]
    transcript = fetch_from_firestore(case_id)  # Should be <500ms

    # Send ephemeral message with transcript
    client.chat_postEphemeral(
        channel=action["channel"]["id"],
        user=action["user"]["id"],
        text=f"Transcript:\n{transcript}"
    )

    duration = time.time() - start
    print(f"Button click processed in {duration:.3f}s")
    assert duration < 2.0, "Exceeds 2s threshold"

# Send test interactive message
def send_test_message():
    client.chat_postMessage(
        channel="#test-channel",
        blocks=[
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Test Case: 202501-IC001*"}
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Transcript"},
                        "action_id": "view_transcript",
                        "value": "202501-IC001"
                    }
                ]
            }
        ]
    )
```

#### Step 3: Modal Submission Test
```python
@slack_app.view("upload_modal_submission")
def handle_modal_submission(ack, view, client):
    start = time.time()
    ack()

    # Extract form data
    values = view["state"]["values"]
    customer_name = values["customer_name"]["customer_name_input"]["value"]

    # Simulate saving to Firestore
    case_id = create_case(customer_name)  # Should be <1s

    # Send confirmation
    client.chat_postMessage(
        channel=view["user"]["id"],
        text=f"Case {case_id} created for {customer_name}"
    )

    duration = time.time() - start
    print(f"Modal submission processed in {duration:.3f}s")
    assert duration < 2.0, "Exceeds 2s threshold"
```

#### Step 4: Thread Context Retrieval Test
```python
@slack_app.event("message")
def handle_message(event, client):
    start = time.time()

    # Check if message is in a thread
    if "thread_ts" in event:
        thread_ts = event["thread_ts"]

        # Retrieve case context from Firestore
        case = get_case_by_slack_ts(thread_ts)  # Should be <500ms

        if case:
            # Conversational AI
            question = event["text"]
            answer = generate_answer(case, question)  # Gemini API, <5s

            client.chat_postMessage(
                channel=event["channel"],
                thread_ts=thread_ts,
                text=answer
            )

    duration = time.time() - start
    print(f"Thread message processed in {duration:.3f}s")
```

#### Step 5: Load Test (10 Concurrent Users)
```python
import asyncio
from slack_sdk.web.async_client import AsyncWebClient

async def simulate_button_click(user_id):
    # Simulate user clicking button
    response = await client.actions_click(
        action_id="view_transcript",
        value="202501-IC001"
    )
    return response

async def load_test():
    tasks = [simulate_button_click(f"U{i:04d}") for i in range(10)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    errors = [r for r in results if isinstance(r, Exception)]
    print(f"Errors: {len(errors)}/10")

    return results

# Run load test
asyncio.run(load_test())
```

### Expected Results

#### Hypothesis
- **Button clicks**: <1s (Firestore fetch is fast)
- **Modal submissions**: <2s (Firestore write is fast)
- **Thread retrieval**: <500ms (indexed Firestore query)
- **Concurrent load**: 0 dropped events

#### Decision Tree
```
IF all_response_times <3s AND dropped_events == 0:
    → Proceed with HTTP mode (recommended - simpler)

ELIF dropped_events <5%:
    → Acceptable for MVP, monitor in production

ELSE IF response_times >3s OR dropped_events >5%:
    → Switch to Socket Mode (WebSocket)
    → Requires persistent connection, more complex deployment
```

### Risks & Mitigations

| Risk | Probability | Mitigation |
|------|------------|------------|
| Firestore query >1s | Low | Add caching layer (Redis) |
| Slack timeout (>3s) | Low | Optimize Firestore indexes, use Socket Mode |
| Concurrent events dropped | Low | Increase Cloud Run max instances |
| WebSocket needed | Low | Socket Mode supported by slack-bolt, but adds complexity |

---

## POC 5: Firestore Query Performance

### Question
Can Firestore handle real-time queries for 200-250 cases/month within budget (<$5/month)?

### Why This Matters
- **Cost**: Firestore charges per read/write operation
- **Performance**: Need <300ms query latency for good UX
- **Scalability**: 2+ years of data = 5000+ documents

### Success Criteria
| Metric | Target | Fallback Threshold |
|--------|--------|-------------------|
| Query Latency (by ID) | <100ms | <200ms acceptable |
| Query Latency (complex filters) | <300ms | <500ms acceptable |
| Monthly Read Cost | <$3 | <$5 acceptable |
| Monthly Write Cost | <$2 | <$3 acceptable |
| Storage Cost | <$1 | <$2 acceptable |

### Test Setup

#### Environment
```yaml
Platform: Firestore (Native mode)
Region: asia-east1
Dataset: 1000 test cases (simulated 4 years)
```

#### Pricing Model
```python
FIRESTORE_PRICING = {
    "reads": 0.06 / 100_000,      # $0.06 per 100K reads
    "writes": 0.18 / 100_000,     # $0.18 per 100K writes
    "deletes": 0.02 / 100_000,    # $0.02 per 100K deletes
    "storage_gb": 0.18            # $0.18 per GB/month
}
```

### Test Procedure

#### Step 1: Seed Test Data
```python
from google.cloud import firestore
import random
from datetime import datetime, timedelta

db = firestore.Client()

def seed_test_cases(count=1000):
    """Create 1000 test cases spanning 4 years"""

    sales_reps = [f"rep{i}@ichef.com" for i in range(20)]

    for i in range(count):
        case_id = f"202101-IC{i:03d}"
        created_at = datetime(2021, 1, 1) + timedelta(days=random.randint(0, 1460))

        case_data = {
            "caseId": case_id,
            "createdAt": created_at,
            "salesRepEmail": random.choice(sales_reps),
            "customerName": f"Customer {i}",
            "status": random.choice(["completed", "failed", "pending"]),
            "transcription": {
                "text": "..." * 1000,  # ~3KB
                "qualityScore": random.randint(60, 100)
            },
            "analysis": {
                "participants": [...],  # ~2KB
                "sentiment": {...},      # ~1KB
                "productNeeds": {...},   # ~2KB
                "competitors": [...],    # ~1KB
                "structured": {...}      # ~3KB
            },
            # Total document size: ~12KB
        }

        db.collection("cases").document(case_id).set(case_data)

        if i % 100 == 0:
            print(f"Seeded {i}/{count} cases")

seed_test_cases()
```

#### Step 2: Query Performance Test
```python
import time

def test_query_performance():
    results = {}

    # Query 1: Fetch by ID (most common)
    start = time.time()
    doc = db.collection("cases").document("202101-IC001").get()
    results["fetch_by_id"] = time.time() - start

    # Query 2: Fetch all cases for sales rep (common)
    start = time.time()
    cases = db.collection("cases") \
        .where("salesRepEmail", "==", "rep0@ichef.com") \
        .limit(50) \
        .stream()
    list(cases)  # Consume iterator
    results["fetch_by_rep"] = time.time() - start

    # Query 3: Fetch recent completed cases (dashboard)
    start = time.time()
    cases = db.collection("cases") \
        .where("status", "==", "completed") \
        .order_by("createdAt", direction=firestore.Query.DESCENDING) \
        .limit(20) \
        .stream()
    list(cases)
    results["fetch_recent_completed"] = time.time() - start

    # Query 4: Aggregate count (admin dashboard)
    start = time.time()
    count_query = db.collection("cases") \
        .where("status", "==", "completed") \
        .count()
    count = count_query.get()
    results["aggregate_count"] = time.time() - start

    # Print results
    for query, latency in results.items():
        status = "✅" if latency < 0.3 else "⚠️"
        print(f"{status} {query}: {latency*1000:.1f}ms")

    return results

test_query_performance()
```

#### Step 3: Cost Estimation
```python
def estimate_monthly_cost():
    # Assumptions for 250 files/month
    operations = {
        "case_creation": 250,                    # Write new case
        "transcription_update": 250,             # Update with transcript
        "analysis_update": 250 * 6,              # 6 agent updates (could batch)
        "notification_update": 250,              # Update with Slack thread_ts
        "feedback_update": 250 * 0.6,            # 60% feedback rate
        "conversation_writes": 250 * 1.5,        # 1.5 Q&A per case

        "slack_notification_read": 250,          # Fetch for notification
        "conversational_ai_read": 250 * 1.5,     # Fetch for Q&A
        "dashboard_queries": 30 * 20,            # 30 sales reps × 20 queries/month
        "admin_queries": 100,                    # Admin monitoring
    }

    total_writes = (
        operations["case_creation"] +
        operations["transcription_update"] +
        operations["analysis_update"] +
        operations["notification_update"] +
        operations["feedback_update"] +
        operations["conversation_writes"]
    )

    total_reads = (
        operations["slack_notification_read"] +
        operations["conversational_ai_read"] +
        operations["dashboard_queries"] +
        operations["admin_queries"]
    )

    # Calculate costs
    write_cost = total_writes * FIRESTORE_PRICING["writes"]
    read_cost = total_reads * FIRESTORE_PRICING["reads"]

    # Storage cost (assuming 12KB per case, 2 years retention)
    total_cases = 250 * 12 * 2  # 6000 cases
    storage_gb = (total_cases * 12_000) / 1_000_000_000  # ~0.072 GB
    storage_cost = storage_gb * FIRESTORE_PRICING["storage_gb"]

    total_cost = write_cost + read_cost + storage_cost

    print(f"Total writes: {total_writes}")
    print(f"Total reads: {total_reads}")
    print(f"Write cost: ${write_cost:.2f}")
    print(f"Read cost: ${read_cost:.2f}")
    print(f"Storage cost: ${storage_cost:.2f}")
    print(f"Total monthly cost: ${total_cost:.2f}")

    return total_cost

estimate_monthly_cost()
```

#### Step 4: Index Optimization
```python
# Identify needed indexes
indexes_needed = [
    {
        "collection": "cases",
        "fields": [
            {"field": "salesRepEmail", "order": "ASCENDING"},
            {"field": "createdAt", "order": "DESCENDING"}
        ]
    },
    {
        "collection": "cases",
        "fields": [
            {"field": "status", "order": "ASCENDING"},
            {"field": "createdAt", "order": "DESCENDING"}
        ]
    }
]

# Create indexes (via Firebase Console or gcloud)
# gcloud firestore indexes composite create \
#   --collection-group=cases \
#   --field-config field-path=salesRepEmail,order=ascending \
#   --field-config field-path=createdAt,order=descending
```

### Expected Results

#### Hypothesis
- **Fetch by ID**: <100ms (single document read)
- **Fetch by rep**: <200ms (indexed query, 50 results)
- **Aggregate count**: <300ms (count aggregation)
- **Monthly cost**: $3-5

#### Decision Tree
```
IF latency <300ms AND cost <$5:
    → Proceed with Firestore (recommended)

ELIF cost >$5 BUT latency OK:
    → Optimize write operations (batch agent updates)
    → Reduce query frequency (add caching)

ELIF latency >500ms:
    → Add indexes for slow queries
    → Consider read replicas for dashboard queries

ELSE IF cost >$10:
    → Use BigQuery for historical analytics (not real-time)
    → Keep Firestore for operational data only
```

### Risks & Mitigations

| Risk | Probability | Mitigation |
|------|------------|------------|
| Cost >$5/month | Medium | Batch agent writes (6 writes → 1 write) |
| Query latency >500ms | Low | Add composite indexes |
| Storage >1GB (cost increase) | Low | Auto-delete old analysis data (keep transcripts only) |
| Read quota exceeded | Very Low | Implement rate limiting on dashboard |

---

## POC 6: Discovery Questionnaire Extraction Accuracy

### Question
Can Agent 5 accurately extract questionnaire responses from conversation without explicit Q&A structure at >75% accuracy?

### Why This Matters
- **User Experience**: High accuracy = no manual questionnaire filling
- **Data Quality**: Poor extraction = incomplete questionnaires = poor insights
- **Feature Viability**: If <75% accurate, manual questionnaire needed (UX regression)

### Success Criteria
| Metric | Target | Fallback Threshold |
|--------|--------|-------------------|
| Topic Detection Recall | >85% | >75% acceptable |
| Response Extraction Accuracy | >75% | >65% acceptable |
| Confidence Calibration | High conf (>80) → >90% accurate | >80% |
| Sales Rep Satisfaction | >3.5/5.0 | >3.0/5.0 acceptable |

### Test Setup

#### Test Dataset (15 Transcripts)
- **Explicit conversations** (5 transcripts): Clear Q&A structure
  - "你們有用掃碼點餐嗎？" → "有，已經用了半年"

- **Implicit conversations** (5 transcripts): Needs inference
  - "客人都是老人家，不會用手機點餐" → barriers: customer_adoption

- **Mixed signals** (5 transcripts): Contradictory statements
  - "想要省人力但擔心成本太高" → perceived_value (positive) + barriers (budget)

#### Ground Truth Labels
```yaml
# Example ground truth for transcript #1
transcript_id: 001
features_discussed:
  - feature: 掃碼點餐
    current_status: "使用中"
    has_need: true
    need_reasons:
      - "尖峰時段人手不足"
    perceived_value:
      score: 75
      aspects:
        - aspect: "省人力"
          sentiment: positive
    implementation_willingness: "high"
    barriers:
      - type: "customer_adoption"
        severity: "low"
        detail: "有些老客人不習慣"

  - feature: 會員管理
    current_status: "未使用"
    has_need: true
    need_reasons:
      - "想要累積回頭客"
    # ...
```

#### Agent 5 Prompt (Initial Version)
```markdown
# Agent 5: Discovery Questionnaire Analyzer

## Role
You are a sales analyst extracting structured questionnaire responses from sales conversations.

## iCHEF Feature Catalog (22 features, 6 categories)

### 1️⃣ 點餐與訂單管理
1. 掃碼點餐（QR Code 掃碼點餐）
2. 多人掃碼點餐
3. 套餐加價購
4. 智慧菜單推薦
5. POS 點餐系統
6. 線上點餐接單

### 2️⃣ 線上整合服務
7. 線上訂位管理
8. 線上外帶自取
9. 雲端餐廳（Online Store）
10. Google 整合
11. LINE 整合
12. 外送平台整合
13. 聯絡式外帶服務

### 3️⃣ 成本與庫存管理
14. 成本控管
15. 庫存管理
16. 帳款管理

### 4️⃣ 業績與銷售分析
17. 銷售分析
18. 報表生成功能

### 5️⃣ 客戶關係管理
19. 零秒集點（忠誠點數系統 2.0）
20. 會員管理

### 6️⃣ 企業級功能
21. 總部系統
22. 連鎖品牌管理

## Task
For EACH feature mentioned in the conversation (explicitly or implicitly), extract structured questionnaire:

{
  "discoveryQuestionnaires": [
    {
      "topic": "掃碼點餐",
      "featureCategory": "點餐與訂單管理",
      "currentStatus": "使用中" | "未使用" | "考慮中" | "曾使用過",
      "hasNeed": true | false | null,
      "needReasons": [
        {
          "reason": "...",
          "quote": "...",
          "confidence": 85
        }
      ],
      "noNeedReasons": [...],
      "perceivedValue": {
        "score": 75,
        "aspects": [...]
      },
      "implementationWillingness": "high" | "medium" | "low" | "none",
      "barriers": [...],
      "timeline": {...},
      "completenessScore": 80,
      "additionalContext": "..."
    }
  ]
}

## Instructions
1. **Topic Detection**: Identify ALL features discussed (even if just mentioned)
2. **Implicit Inference**: Infer status/needs from context (e.g., "客人不會用" → barrier: customer_adoption)
3. **Confidence Scoring**: Assign 0-100 confidence to each extracted reason
4. **Handle Ambiguity**: If unclear, set hasNeed=null and explain in additionalContext
5. **Completeness**: Calculate % of questionnaire answered

Return ONLY valid JSON.
```

### Test Procedure

#### Step 1: Topic Detection Test
```python
def test_topic_detection(test_transcripts, ground_truth):
    """Test if Agent 5 finds all discussed features"""

    results = {
        "total_features": 0,
        "detected_features": 0,
        "missed_features": [],
        "false_positives": []
    }

    for transcript, gt in zip(test_transcripts, ground_truth):
        response = run_agent5(transcript)

        detected_topics = {q["topic"] for q in response["discoveryQuestionnaires"]}
        expected_topics = {f["feature"] for f in gt["features_discussed"]}

        results["total_features"] += len(expected_topics)
        results["detected_features"] += len(detected_topics & expected_topics)

        missed = expected_topics - detected_topics
        if missed:
            results["missed_features"].append({
                "transcript_id": gt["transcript_id"],
                "missed": list(missed)
            })

        false_pos = detected_topics - expected_topics
        if false_pos:
            results["false_positives"].append({
                "transcript_id": gt["transcript_id"],
                "false_positives": list(false_pos)
            })

    recall = results["detected_features"] / results["total_features"] * 100
    print(f"Topic Detection Recall: {recall:.1f}%")

    return results
```

#### Step 2: Response Extraction Accuracy Test
```python
def test_extraction_accuracy(test_transcripts, ground_truth):
    """Test if extracted responses match ground truth"""

    accuracy_scores = []

    for transcript, gt in zip(test_transcripts, ground_truth):
        response = run_agent5(transcript)

        for gt_feature in gt["features_discussed"]:
            topic = gt_feature["feature"]
            agent_response = next((q for q in response["discoveryQuestionnaires"] if q["topic"] == topic), None)

            if not agent_response:
                accuracy_scores.append(0)
                continue

            # Calculate field-level accuracy
            correct_fields = 0
            total_fields = 0

            # Check currentStatus
            if gt_feature.get("current_status"):
                total_fields += 1
                if agent_response["currentStatus"] == gt_feature["current_status"]:
                    correct_fields += 1

            # Check hasNeed
            if gt_feature.get("has_need") is not None:
                total_fields += 1
                if agent_response["hasNeed"] == gt_feature["has_need"]:
                    correct_fields += 1

            # Check needReasons (fuzzy match on content)
            if gt_feature.get("need_reasons"):
                total_fields += 1
                agent_reasons = [r["reason"] for r in agent_response["needReasons"]]
                overlap = len(set(gt_feature["need_reasons"]) & set(agent_reasons))
                correct_fields += overlap / len(gt_feature["need_reasons"])

            # ... similar checks for other fields

            field_accuracy = correct_fields / total_fields * 100 if total_fields > 0 else 0
            accuracy_scores.append(field_accuracy)

    avg_accuracy = sum(accuracy_scores) / len(accuracy_scores)
    print(f"Response Extraction Accuracy: {avg_accuracy:.1f}%")

    return accuracy_scores
```

#### Step 3: Confidence Calibration Test
```python
def test_confidence_calibration():
    """Test if high confidence → high accuracy"""

    calibration_data = {
        "high_confidence": [],  # >80 confidence
        "medium_confidence": [],  # 50-80
        "low_confidence": []  # <50
    }

    for transcript, gt in zip(test_transcripts, ground_truth):
        response = run_agent5(transcript)

        for questionnaire in response["discoveryQuestionnaires"]:
            for reason in questionnaire["needReasons"]:
                confidence = reason["confidence"]

                # Manual validation: Is this reason correct?
                is_correct = validate_reason(reason, gt)

                if confidence > 80:
                    calibration_data["high_confidence"].append(is_correct)
                elif confidence > 50:
                    calibration_data["medium_confidence"].append(is_correct)
                else:
                    calibration_data["low_confidence"].append(is_correct)

    # Calculate accuracy per confidence band
    for band, results in calibration_data.items():
        accuracy = sum(results) / len(results) * 100 if results else 0
        print(f"{band}: {accuracy:.1f}% accurate")
```

#### Step 4: Sales Rep Validation
```python
def sales_rep_validation():
    """Have sales reps review 30 auto-completed questionnaires"""

    # Select 30 random cases
    validation_cases = random.sample(completed_cases, 30)

    # Create Google Form for sales rep review
    form_questions = [
        "Overall questionnaire accuracy (1-5 stars)",
        "Which fields are incorrect? (checkboxes)",
        "Missing important information? (text)",
        "Would you use this feature? (yes/no/needs_improvement)"
    ]

    # Send to sales reps
    send_validation_forms(validation_cases)

    # Collect responses
    responses = collect_form_responses()

    # Calculate satisfaction score
    avg_rating = sum(r["accuracy_rating"] for r in responses) / len(responses)
    print(f"Sales Rep Satisfaction: {avg_rating:.2f}/5.0")

    return responses
```

#### Step 5: Prompt Iteration (if <75% accurate)
```python
# Iterate on prompt to improve accuracy
improvements = {
    "v1": "Initial prompt",
    "v2": "Add 3 examples of implicit reasoning",
    "v3": "Add stricter confidence scoring guidelines",
    "v4": "Add feature-specific extraction hints"
}

for version, description in improvements.items():
    print(f"\nTesting {version}: {description}")

    # Load improved prompt
    prompt = load_prompt(f"agent5_{version}.md")

    # Re-run accuracy tests
    recall = test_topic_detection()
    accuracy = test_extraction_accuracy()

    print(f"Recall: {recall:.1f}%, Accuracy: {accuracy:.1f}%")

    if recall > 85 and accuracy > 75:
        print(f"✅ {version} meets success criteria")
        break
```

### Expected Results

#### Hypothesis
- **Topic Detection Recall**: 80-85% (may miss subtle mentions)
- **Extraction Accuracy**: 70-75% (implicit inference is hard)
- **Confidence Calibration**: High conf (>80) → 85-90% accurate
- **Sales Rep Satisfaction**: 3.5-4.0/5.0

#### Decision Tree
```
IF recall >85% AND accuracy >75% AND satisfaction >3.5:
    → Proceed with Agent 5 (recommended)

ELIF recall >75% AND accuracy >65%:
    → Acceptable for MVP, add "Review Questionnaire" button in Slack
    → Sales rep can correct/complete missing fields

ELIF accuracy <65%:
    → Show questionnaire summary in Slack, sales rep fills manually
    → Agent 5 provides "draft" to speed up manual entry

ELSE IF satisfaction <3.0:
    → Feature not ready, defer to Phase 2
    → Focus on other agents first
```

### Risks & Mitigations

| Risk | Probability | Mitigation |
|------|------------|------------|
| Accuracy <75% | Medium | Add "Review Questionnaire" UI, sales rep corrects |
| High false positive rate | Medium | Increase confidence threshold, filter low-confidence extractions |
| Sales rep doesn't trust AI | Medium | Show confidence scores, allow manual override |
| Feature-specific accuracy varies | High | Create feature-specific extraction prompts (Phase 2) |

---

## POC Execution Plan

### Parallel Execution Strategy

**Week 1** (Parallel):
- **POC 1** (Whisper): Team member A (2-3 days)
- **POC 2** (Multi-Agent): Team member B (1 day)
- **POC 3** (Gemini JSON): Team member B (2 days, after POC 2)
- **POC 4** (Slack): Team member C (1 day)
- **POC 5** (Firestore): Team member C (1 day, after POC 4)

**Week 2** (Parallel):
- **POC 6** (Questionnaire): Team member A (2-3 days, after POC 1)
- **POC 1 optimization** (if needed): Team member A
- **POC 3 prompt iteration** (if needed): Team member B
- **Documentation**: All team members

**Total Time**: 7-10 days sequential, **3-4 days with 3 team members in parallel**

---

## Success Summary

At the end of Phase 0, we should have:

### Deliverables
1. ✅ POC test results for all 6 experiments
2. ✅ Performance benchmarks (latency, cost, accuracy)
3. ✅ Recommended configurations (models, prompts, infrastructure)
4. ✅ Identified risks and mitigation strategies
5. ✅ Go/No-Go decision for each component

### Go/No-Go Decision Criteria

| Component | Go Criteria | No-Go → Fallback |
|-----------|------------|------------------|
| Faster-Whisper + Diarization | <5min, >80% diarization, >85% quality | GPU-enabled Cloud Run OR disable diarization |
| Multi-Agent Parallel | <40s parallel, <5% errors | Sequential execution (slower) OR reduce agent count |
| Gemini Structured Output | >95% compliance, <5% hallucination | Function calling OR regex-based extraction |
| Slack Block Kit | <3s response, 0% drops | Socket Mode (WebSocket) |
| Firestore | <300ms queries, <$5/month | Batch writes, add caching, BigQuery for analytics |
| Questionnaire Extraction | >75% accuracy, >3.5/5 satisfaction | Manual questionnaire with AI-draft assistance |

### Next Steps After Phase 0

**If all POCs pass**:
→ Proceed to Phase 1 (Detailed Design)

**If 1-2 POCs fail**:
→ Implement fallback strategies, re-validate, then proceed to Phase 1

**If 3+ POCs fail**:
→ Re-evaluate architecture, consider alternative approaches, delay Phase 1

---

## Appendix: Test Scripts Repository

All POC test scripts will be stored in:
```
specs/001-sales-ai-automation/poc-tests/
├── poc1_whisper/
│   ├── Dockerfile
│   ├── test_whisper.py
│   ├── test_diarization.py
│   └── README.md
├── poc2_multi_agent/
│   ├── test_parallel.py
│   ├── test_agents.py
│   └── README.md
├── poc3_gemini_json/
│   ├── test_schema_compliance.py
│   ├── test_hallucinations.py
│   └── agent_schemas.py
├── poc4_slack/
│   ├── slack_app.py
│   ├── test_interactions.py
│   └── README.md
├── poc5_firestore/
│   ├── seed_data.py
│   ├── test_queries.py
│   ├── test_cost.py
│   └── README.md
└── poc6_questionnaire/
    ├── test_extraction.py
    ├── ground_truth.yaml
    ├── agent5_prompts/
    │   ├── v1.md
    │   ├── v2.md
    │   └── v3.md
    └── README.md
```

**End of Research Plan**
