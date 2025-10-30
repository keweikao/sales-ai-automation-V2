# Quick Start Guide for AI Assistants

**Purpose**: Enable any AI assistant to quickly understand project context and continue development.

**Reading Time**: 5 minutes

---

## 🚀 Start Here (Essential Reading Order)

### 1️⃣ Read This First (30 seconds)
- **Current Phase**: Phase 0 - POC Validation (Ready to Execute)
- **Last Session**: 2025-01-29 (Planning & Specification completed)
- **Next Steps**: Execute 6 POC tests (3-4 days with 3-person team)

### 2️⃣ Read Context Files (5 minutes)

**Must Read** (in order):
1. `DEVELOPMENT_GUIDELINES.md` ⚠️ **MANDATORY** - Recording rules (READ FIRST!)
2. `DEVELOPMENT_LOG.md` - Full session history, decisions, and context
3. `memory/constitution.md` - System principles (cost, performance, Chinese optimization)
4. `specs/001-sales-ai-automation/spec.md` - 8 User Stories, 22 features, success criteria

**Optional** (if implementing):
4. `specs/001-sales-ai-automation/plan.md` - Technical architecture, cost breakdown
5. `specs/001-sales-ai-automation/research.md` - 6 POC test plans

### 3️⃣ Understand Key Decisions (1 minute)

All critical decisions are FINAL ✅ (do not re-discuss):

| Topic | Decision | Documented In |
|-------|----------|--------------|
| Architecture | 6-agent multi-agent, Firestore primary, Slack-first | plan.md |
| Product Catalog | iCHEF website (22 features, 6 categories) | spec.md, DEVELOPMENT_LOG.md |
| Questionnaire | Prompt-based (not Firestore templates) | plan.md, research.md |
| Disaster Recovery | Wait for recovery (no multi-region) | plan.md |
| Cost Budget | <$45/month (actual: $46.74, acceptable) | plan.md |

---

## 📋 Current State Summary

### What's Done ✅

- [x] Complete feature specification (spec.md)
- [x] Technical implementation plan (plan.md)
- [x] POC validation plan with 6 detailed tests (research.md)
- [x] Test script structure and 3 example scripts
- [x] All user decisions confirmed and documented

### What's Next 🎯

**Immediate**: Execute Phase 0 POC validations

**6 POCs to validate** (3-4 days, 3-person team):
1. Faster-Whisper + Speaker Diarization (<5 min, >80% accuracy)
2. Multi-Agent Parallel Orchestration (<40s, <5% errors)
3. Gemini Structured Output Quality (>95% compliance)
4. Slack Block Kit Interactivity (<3s response)
5. Firestore Query Performance (<$5/month)
6. Questionnaire Extraction Accuracy (>75% accuracy)

---

## 🗂️ File Structure (What to Look At)

```
sales-ai-automation-V2/
├── DEVELOPMENT_LOG.md           ⭐ FULL SESSION HISTORY - READ FIRST
├── QUICK_START_FOR_AI.md        ⭐ THIS FILE
├── README.md                    📘 Project overview
├── memory/
│   └── constitution.md          📜 Core principles (cost, performance, quality)
├── specs/001-sales-ai-automation/
│   ├── spec.md                  📋 8 User Stories, 22 features, success criteria
│   ├── plan.md                  🏗️ Architecture, microservices, cost breakdown
│   ├── research.md              🧪 6 POC test plans (NEXT TO EXECUTE)
│   └── poc-tests/
│       ├── README.md            📖 POC execution guide
│       ├── poc1_whisper/
│       │   └── test_whisper.py  🐍 Whisper performance test
│       ├── poc2_multi_agent/
│       │   └── test_parallel.py 🐍 Multi-agent orchestration test
│       └── poc6_questionnaire/
│           └── agent5_prompts/v1.md  💬 Questionnaire analyzer prompt
```

---

## 💡 Common User Requests & How to Handle

### "Continue where we left off"
→ Read `DEVELOPMENT_LOG.md` Session 1 to understand full context
→ Current task: Prepare for POC execution (or execute if ready)

### "Can you explain the architecture?"
→ Read `specs/001-sales-ai-automation/plan.md`
→ Key: 4 Cloud Run services, 6 agents (1-5 parallel, 6 synthesis), Firestore primary

### "What are the 22 features for Agent 5?"
→ See `DEVELOPMENT_LOG.md` "22 iCHEF Features" section
→ Also in `spec.md` lines 943-976

### "Why did we choose X over Y?"
→ Check `DEVELOPMENT_LOG.md` "Key Discussions & Decisions"
→ All decisions have documented rationale

### "What's the budget/cost?"
→ $46.74/month for 250 files (see `plan.md` cost breakdown)
→ Slightly over $45 target but acceptable

### "How do I run the POC tests?"
→ Read `specs/001-sales-ai-automation/research.md`
→ Test scripts in `specs/001-sales-ai-automation/poc-tests/`

---

## ⚠️ Important Notes

### DO NOT Re-Discuss These (Already Decided ✅)

- Multi-agent architecture (6 agents) - User confirmed
- Firestore as primary database - User confirmed
- Slack-first interface - User confirmed
- 22 iCHEF features for questionnaire - User confirmed
- Prompt-based questionnaire (not Firestore templates) - User confirmed

### DO Ask User About

- POC execution readiness (team availability, test data, API keys)
- New features or changes not in existing specs
- Clarification on ambiguous requirements (rare, most things are clear)

### Respect the Constitution

`memory/constitution.md` defines immutable principles:
- Cost optimization first (<$45/month target)
- Self-hosted Faster-Whisper (not OpenAI API)
- Event-driven architecture (not polling)
- Chinese language optimization

---

## 🔧 If User Wants to Execute POCs

### Prerequisites Checklist

Ask user to confirm:
- [ ] GCP project created with billing enabled
- [ ] Slack workspace with test app
- [ ] Gemini API key obtained
- [ ] Test audio files prepared (10 files, various lengths)
- [ ] Test transcripts prepared (30 files, various scenarios)
- [ ] 3-person team available for parallel execution

### Execution Steps

1. Review `specs/001-sales-ai-automation/research.md` for detailed procedures
2. Set up test environment (GCP, Slack, API keys)
3. Run POCs in parallel (Week 1 + Week 2 schedule in research.md)
4. Document results in `specs/001-sales-ai-automation/poc-tests/results/`
5. Make Go/No-Go decisions
6. Update `plan.md` with validated configurations
7. Add new session entry to `DEVELOPMENT_LOG.md`

---

## 📝 When Completing a Task

### Update DEVELOPMENT_LOG.md

1. Add new session entry using template at end of file
2. Document:
   - What was done
   - Key decisions made
   - Files created/modified
   - Technical highlights
   - Open questions
   - Next steps

### Format for Session Entry

```markdown
### Session 2: 2025-MM-DD (Title)

**Duration**: X hours
**AI Model**: [Your model name]
**User**: Stephen

#### Objectives Completed ✅
- [x] Task 1
- [x] Task 2

#### Files Created/Modified
- `path/to/file` (description)

#### Key Decisions
1. **Topic**: Decision and rationale

#### Next Session Preparation
- Action items for next AI assistant
```

---

## 🎯 Quick Decision Tree

**User says**: "Continue development"
→ Read DEVELOPMENT_LOG.md → Current phase is POC Validation → Ask if ready to execute

**User says**: "Can you implement feature X?"
→ Check if feature is in spec.md → If yes, check if POCs are done → If no, remind that POC validation comes first

**User says**: "Why did we choose X?"
→ Check DEVELOPMENT_LOG.md "Key Discussions & Decisions" → Explain rationale

**User says**: "Change decision X to Y"
→ Explain current decision and rationale → If user insists, update spec.md/plan.md → Document in DEVELOPMENT_LOG.md

**User says**: "Start POC testing"
→ Check prerequisites → Guide through research.md procedures → Document results

---

## 📞 Emergency References

**If confused about project goals**:
→ Read `README.md` or `spec.md` "Summary" section

**If confused about technical decisions**:
→ Read `plan.md` "User Decisions" section

**If confused about what to do next**:
→ Read `DEVELOPMENT_LOG.md` "Next Session Preparation"

**If user mentions something unfamiliar**:
→ Search DEVELOPMENT_LOG.md for the term
→ Ask user to clarify (may be new information)

---

## ✅ Self-Check Before Starting

Before responding to user, verify:

- [ ] I have read DEVELOPMENT_GUIDELINES.md ⚠️ **MANDATORY**
- [ ] I have read DEVELOPMENT_LOG.md
- [ ] I understand current phase (Phase 0 - POC Validation)
- [ ] I know what was done in last session
- [ ] I know what the next steps are
- [ ] I will not re-discuss finalized decisions
- [ ] **I will record this session before ending** ⚠️ **MANDATORY**

---

**Welcome to the project! You're now ready to continue development. 🚀**

*Last Updated: 2025-01-29 by Claude Sonnet 4.5*
