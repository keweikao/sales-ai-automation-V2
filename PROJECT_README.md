# Sales AI Automation V2.0

**A scalable, cost-optimized sales AI automation system for iCHEF**

Automates sales call analysis using self-hosted Whisper transcription, multi-agent AI analysis (Gemini), and delivers interactive experiences via Slack.

---

## 🚀 Quick Start

### For AI Assistants Continuing Development
👉 **START HERE**: Read [`QUICK_START_FOR_AI.md`](./QUICK_START_FOR_AI.md) (5-minute read)

⚠️ **MANDATORY**: Read [`DEVELOPMENT_GUIDELINES.md`](./DEVELOPMENT_GUIDELINES.md) - Recording rules

Then read:
1. [`DEVELOPMENT_LOG.md`](./DEVELOPMENT_LOG.md) - Full session history
2. [`memory/constitution.md`](./memory/constitution.md) - System principles
3. [`specs/001-sales-ai-automation/spec.md`](./specs/001-sales-ai-automation/spec.md) - Feature specification

### For Developers
1. Clone repository
2. Read [`specs/001-sales-ai-automation/`](./specs/001-sales-ai-automation/) for complete specs
3. Follow [`specs/001-sales-ai-automation/research.md`](./specs/001-sales-ai-automation/research.md) for POC validation

---

## 📋 Project Status

**Current Phase**: Phase 0 - POC Validation (Ready to Execute)
**Last Updated**: 2025-01-29

### Completed ✅
- [x] Feature Specification (8 User Stories, 22 features)
- [x] Technical Implementation Plan (4 microservices, 6-agent architecture)
- [x] POC Validation Plan (6 critical tests)
- [x] Test Script Structure (3 example scripts)
- [x] User Decision Confirmation (all 5 decisions finalized)

### Next Steps 🎯
- [ ] Execute 6 POC validations (3-4 days, 3-person team)
- [ ] Phase 1: Detailed Design (data models, API contracts)
- [ ] Phase 2: Implementation (Sprint 1-7, 12-14 weeks)

---

## 🏗️ System Architecture

### Core Components
- **Transcription Service** (Cloud Run): Faster-Whisper + Speaker Diarization
- **Analysis Service** (Cloud Run): 6 specialized Gemini agents
- **Slack Service** (Cloud Run): Interactive Block Kit interface
- **Orchestration Service** (Cloud Run): Workflow coordination

### Multi-Agent AI Architecture
1. **Agent 1**: Participant Profile Analyzer
2. **Agent 2**: Sentiment & Attitude Analyzer
3. **Agent 3**: Product Needs Extractor
4. **Agent 4**: Competitor Intelligence Analyzer
5. **Agent 5**: Discovery Questionnaire Analyzer 🆕
6. **Agent 6**: Sales Coach Synthesizer

### Key Technologies
- **Transcription**: Faster-Whisper (large-v3)
- **AI**: Google Gemini 1.5 Flash
- **Database**: Google Cloud Firestore
- **Interface**: Slack (slack-bolt)
- **Cloud**: Google Cloud Platform (Cloud Run, Cloud Tasks, Cloud Storage)

---

## 💰 Cost & Performance

### Monthly Cost (250 files)
- **Total**: $46.74/month
  - Cloud Run (transcription): $28.80
  - Gemini API (6 agents): $13.50
  - Other GCP services: $4.44

### Performance Targets
- End-to-end processing: <4 minutes (90th percentile)
- Transcription + Diarization: <5 minutes (40-min audio)
- Multi-agent analysis: <40 seconds (parallel execution)
- Slack notification: <1 minute

---

## 📚 Documentation

### For AI Assistants
- [`QUICK_START_FOR_AI.md`](./QUICK_START_FOR_AI.md) - 5-minute quick start guide
- [`DEVELOPMENT_LOG.md`](./DEVELOPMENT_LOG.md) - Session history and decisions

### Specifications
- [`specs/001-sales-ai-automation/spec.md`](./specs/001-sales-ai-automation/spec.md) - Complete feature specification
- [`specs/001-sales-ai-automation/plan.md`](./specs/001-sales-ai-automation/plan.md) - Technical implementation plan
- [`specs/001-sales-ai-automation/research.md`](./specs/001-sales-ai-automation/research.md) - POC validation plan

### Development
- [`memory/constitution.md`](./memory/constitution.md) - System principles

### Testing
- [`specs/001-sales-ai-automation/poc-tests/`](./specs/001-sales-ai-automation/poc-tests/) - POC test scripts

---

## 🎯 Success Criteria

### Performance (6 metrics)
- Processing time <4 min for 90% of cases
- Success rate >95%
- Concurrent processing: 10+ files without degradation
- Uptime >99.5%
- Transcription quality >85%
- Speaker diarization accuracy >80%

### User Experience (5 metrics)
- Slack notification within 4 minutes
- Conversational AI response <5 seconds
- Engagement rate >70%
- Feedback submission rate >60%
- Average satisfaction >4.0/5.0

### Cost Efficiency (3 metrics)
- Monthly cost <$45 (actual: $46.74, acceptable)
- Cost per file <$0.18
- Gemini API costs <$15/month

---

## 🔧 Development Workflow

This project follows **spec-driven development**:

1. **Specification First** (`spec.md`) - Define requirements, user stories, acceptance criteria
2. **Technical Planning** (`plan.md`) - Document architecture, costs, decisions
3. **Research & Validation** (`research.md`) - POC tests to validate assumptions
4. **Task Breakdown** (`tasks.md`) - Sprint planning (not yet created)
5. **Implementation** - TDD for critical paths
6. **Review & Deploy** - Staging → Production with monitoring

---

## 👥 Team

**Product Owner**: Stephen
**Development Team**: TBD (3-person team for POC phase)

---

## 📞 Contact

For questions or contributions, see project documentation in `specs/` directory.

---

*This project is being developed using spec-driven development workflow.*
*Last Updated: 2025-01-29*
