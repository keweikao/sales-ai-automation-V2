# Development Guidelines - Sales AI Automation V2.0

**Purpose**: Define mandatory practices for all development activities to ensure continuity across different AI assistants.

**Status**: Enforced from 2025-01-29
**Applies to**: All AI assistants, developers, and contributors

---

## 🚨 Core Principle

**Every development activity MUST be recorded before the session ends.**

This is not optional. Failure to record development activities breaks continuity and wastes time for future AI assistants.

---

## 📋 Mandatory Recording Rules

### Rule 1: Record Every Session ✅ REQUIRED

**WHEN**: At the end of every development session, before saying goodbye to the user

**WHERE**: `DEVELOPMENT_LOG.md`

**HOW**: Add a new session entry using the provided template

**Template Location**: See bottom of `DEVELOPMENT_LOG.md`

**What to Record**:
- [ ] Session duration and AI model used
- [ ] Objectives completed (checked/unchecked)
- [ ] Files created or modified (with line counts if significant)
- [ ] Key discussions and decisions (with user quotes)
- [ ] Technical highlights (architecture, performance, costs)
- [ ] Known issues and risks (with mitigation strategies)
- [ ] Open questions (with status)
- [ ] Next session preparation (action items for next AI)

**Example**:
```markdown
### Session 2: 2025-02-01 (POC 1-3 Execution)

**Duration**: 4 hours
**AI Model**: Claude Sonnet 4.5
**User**: Stephen

#### Objectives Completed ✅
- [x] Execute POC 1: Whisper performance test
- [x] Execute POC 2: Multi-agent parallel test
- [x] Execute POC 3: Gemini structured output test
- [ ] Execute POC 4-6 (deferred to next session)

#### Files Created/Modified
**Created**:
- `specs/001-sales-ai-automation/poc-tests/results/poc1_results.json`
- `specs/001-sales-ai-automation/poc-tests/results/poc2_results.json`

**Modified**:
- `specs/001-sales-ai-automation/plan.md` (Updated with validated Whisper config)

#### Key Discussions & Decisions
##### 1. Whisper Model Selection
**User Request**: "POC 1 結果顯示 large-v3 太慢，我們應該用 medium 嗎？"
**Decision**: Continue with large-v3, enable GPU acceleration
**Rationale**: large-v3 quality (92%) significantly better than medium (78%). GPU adds only $12/month.

...
```

---

### Rule 2: Update Quick Reference When Needed ✅ REQUIRED

**WHEN**: When a new critical decision is made OR project status changes

**WHERE**: `DEVELOPMENT_LOG.md` → "Quick Reference for New AI Assistants" section

**WHAT**: Update the decision table, feature list, or current status

**Example Updates**:
- New technology choice (e.g., switched from Firestore to PostgreSQL)
- New feature added (e.g., added Agent 7 for email analysis)
- Budget change (e.g., budget increased to $60/month)
- Current phase change (e.g., from Phase 0 to Phase 1)

---

### Rule 3: Create Session Summary for User ✅ REQUIRED

**WHEN**: At the end of every session, after updating DEVELOPMENT_LOG.md

**WHERE**: As a message to the user (not a file)

**FORMAT**:
```markdown
## 📋 Session Summary

**Today's Work** (X hours):
- ✅ Completed objective 1
- ✅ Completed objective 2
- ⏸️ Partially completed objective 3 (reason)

**Key Decisions**:
1. Decision 1 (rationale)
2. Decision 2 (rationale)

**Files Changed**:
- Created: file1.md, file2.py
- Modified: file3.md (reason)

**Next Steps**:
- [ ] Action item 1
- [ ] Action item 2

**For Next AI Assistant**:
- Must read: DEVELOPMENT_LOG.md Session X
- Current status: [phase/milestone]
- Blockers: [any blockers or dependencies]

✅ All work has been recorded in DEVELOPMENT_LOG.md Session X
```

---

### Rule 4: Update Project Status ✅ REQUIRED

**WHEN**: When phase or major milestone changes

**WHERE**:
1. `DEVELOPMENT_LOG.md` → "Current Status" section
2. `PROJECT_README.md` → "Project Status" section
3. `QUICK_START_FOR_AI.md` → "Start Here" section

**WHAT**: Update current phase, last updated date, next steps

---

### Rule 5: Document New Files ✅ REQUIRED

**WHEN**: Every time you create a new file

**WHERE**: `DEVELOPMENT_LOG.md` → Current session → "Files Created/Modified"

**FORMAT**:
```markdown
**Created**:
- `path/to/file.ext` (description, line count if >100 lines)
```

**Example**:
```markdown
**Created**:
- `services/transcription-service/src/main.py` (FastAPI app, 234 lines)
- `services/transcription-service/Dockerfile` (Container config)
```

---

### Rule 6: Document All Decisions ✅ REQUIRED

**WHEN**: Every time you make a technical or design decision

**WHERE**: `DEVELOPMENT_LOG.md` → Current session → "Key Discussions & Decisions"

**FORMAT**:
```markdown
##### [Number]. [Decision Topic]
**User Request**: "[Original user quote if applicable]"
**Decision**: [What was decided]
**Rationale**: [Why this decision was made]
**Alternatives Considered**: [Other options considered]
**Trade-offs**: [What was gained/lost]
```

**Example**:
```markdown
##### 3. Database Choice for POC
**User Request**: "Firestore 太慢了，可以用 PostgreSQL 嗎？"
**Decision**: Switch to PostgreSQL for POC phase only
**Rationale**:
- POC needs faster queries for testing (Firestore: 300ms, PostgreSQL: 50ms)
- Easier to seed test data
- Can still use Firestore for production if POC validates performance
**Alternatives Considered**:
- Redis (too volatile for POC)
- MySQL (team less familiar)
**Trade-offs**:
- Gained: Faster development, easier testing
- Lost: One more migration step if we keep PostgreSQL for production
```

---

## 🎯 Development Workflow with Recording

### Standard Development Cycle

```
1. Read Context
   ├─ Read QUICK_START_FOR_AI.md (5 min)
   ├─ Read DEVELOPMENT_LOG.md (last session)
   └─ Read relevant spec/plan files

2. Understand Request
   ├─ Clarify ambiguities with user
   ├─ Check if decision was already made (DEVELOPMENT_LOG.md)
   └─ Confirm scope with user

3. Execute Work
   ├─ Write code / create files
   ├─ Test functionality
   └─ Fix issues

4. Record Work ⚠️ MANDATORY
   ├─ Update DEVELOPMENT_LOG.md (new session entry)
   ├─ Update QUICK_START_FOR_AI.md (if needed)
   ├─ Update PROJECT_README.md (if status changed)
   └─ Create session summary for user

5. Handoff
   ├─ Provide session summary to user
   ├─ Confirm all work is recorded
   └─ Provide clear next steps
```

---

## 🔍 Self-Check Before Ending Session

Before saying goodbye to the user, verify:

- [ ] I have added a new session entry to DEVELOPMENT_LOG.md
- [ ] All files created/modified are listed
- [ ] All decisions are documented with rationale
- [ ] All technical highlights are recorded
- [ ] Open questions are listed
- [ ] Next steps are clear for next AI assistant
- [ ] I have updated QUICK_START_FOR_AI.md if needed
- [ ] I have updated PROJECT_README.md if phase changed
- [ ] I have provided a session summary to the user
- [ ] User confirms the summary is accurate

**If ANY checkbox is unchecked, DO NOT end the session. Complete the recording first.**

---

## 🚫 Common Mistakes to Avoid

### ❌ Mistake 1: "I'll record it later"
**Problem**: "Later" never comes. The next AI assistant has no context.

**Solution**: Record BEFORE ending the session. Make it the last task.

---

### ❌ Mistake 2: Vague descriptions
**Bad**: "Fixed some bugs"
**Good**: "Fixed Whisper timeout issue (increased timeout from 5min to 10min in transcription-service/src/transcriber.py:45)"

---

### ❌ Mistake 3: Not recording decisions
**Bad**: Silently switch from Firestore to PostgreSQL
**Good**: Document why, what user said, trade-offs, and update plan.md

---

### ❌ Mistake 4: Not documenting failed attempts
**Bad**: Only record successful work
**Good**: Record what was tried, why it failed, what was learned

**Example**:
```markdown
#### Known Issues & Risks
1. **POC 2 failed with rate limit errors**
   - Attempted: Parallel execution of 10 cases (50 Gemini calls)
   - Result: 30% rate limit errors
   - Root Cause: Free tier limited to 15 RPM
   - Mitigation: Implemented token bucket (max 10 calls/min)
   - Status: Re-running POC 2 tomorrow
```

---

### ❌ Mistake 5: Incomplete handoff
**Bad**: "I did the POCs. Bye!"
**Good**: "I completed POC 1-3. Results in `poc-tests/results/`. POC 1 GO, POC 2 GO with mitigation, POC 3 NO-GO (need to switch to function calling). Next AI should: 1) Review POC 3 failure, 2) Implement Gemini function calling, 3) Re-run POC 3, 4) Continue with POC 4-6. All details in DEVELOPMENT_LOG.md Session 2."

---

## 📚 Documentation Hierarchy

### Level 1: Session Record (DEVELOPMENT_LOG.md)
- **Purpose**: Complete historical record
- **Audience**: Future AI assistants
- **Update Frequency**: Every session
- **Detail Level**: High (include everything)

### Level 2: Quick Reference (QUICK_START_FOR_AI.md)
- **Purpose**: Fast onboarding for new AI
- **Audience**: New AI assistants (first 5 minutes)
- **Update Frequency**: When critical info changes
- **Detail Level**: Medium (key decisions only)

### Level 3: Project Overview (PROJECT_README.md)
- **Purpose**: Project status and navigation
- **Audience**: Humans and AI (project overview)
- **Update Frequency**: When phase/status changes
- **Detail Level**: Low (high-level summary)

### Level 4: Technical Specs (spec.md, plan.md, research.md)
- **Purpose**: Detailed specifications
- **Audience**: Implementers
- **Update Frequency**: When requirements/design changes
- **Detail Level**: Very High (implementation details)

---

## 🔧 Special Scenarios

### Scenario 1: Emergency Stop (User Needs to Leave)

**If user must leave unexpectedly**:

1. Immediately save current work
2. Create a minimal session entry:
   ```markdown
   ### Session X: YYYY-MM-DD (Incomplete Session)

   **Status**: ⚠️ INCOMPLETE - User had to leave
   **Duration**: X hours (interrupted)
   **AI Model**: [Your model]

   #### Work in Progress
   - Started: [what you were doing]
   - Completed: [what was finished]
   - Not completed: [what was not finished]
   - Current state: [file changes, partial code, etc.]

   #### Next AI Must
   1. Review incomplete work in [file paths]
   2. Decide: Keep or discard partial implementation
   3. Continue from [specific point]

   #### Files with Unsaved Changes
   - `path/to/file` (has uncommitted changes)
   ```

3. Inform user: "I've saved an incomplete session record. Next AI will continue from here."

---

### Scenario 2: Pure Discussion (No Code Changes)

**If session was only discussion/planning**:

Still record it! Document:
- What was discussed
- Decisions made (even if not implemented yet)
- Questions answered
- Context clarified

**Example**:
```markdown
### Session X: YYYY-MM-DD (Planning Discussion)

**Duration**: 30 minutes
**AI Model**: Claude Sonnet 4.5
**User**: Stephen

#### Objectives Completed ✅
- [x] Clarified questionnaire feature requirements
- [x] Discussed cost optimization strategies

#### Files Created/Modified
None (discussion only)

#### Key Discussions & Decisions
##### 1. Questionnaire Auto-Completion Scope
**User Question**: "Agent 5 應該支援多少個功能？"
**Discussion**: Reviewed iCHEF product catalog, identified 22 features
**Decision**: Support all 22 features in prompt (not just top 5)
**Rationale**: Better user experience, minimal cost increase

#### Next Session Preparation
**For Next AI**:
- Begin implementing Agent 5 with 22-feature support
- Use template in `poc-tests/poc6_questionnaire/agent5_prompts/v1.md`
```

---

### Scenario 3: Bug Fix or Hot Fix

**Record all bug fixes** (even small ones):

```markdown
#### Bug Fixes
1. **Whisper timeout on long audio**
   - Symptom: 60-min audio files failed with timeout
   - Root Cause: Fixed 5-min timeout in config
   - Fix: Increased to 10-min in `transcription-service/config.py:23`
   - Affected Files: `services/transcription-service/src/config.py`
   - Tested: Verified with 60-min test audio (passed)
```

---

### Scenario 4: Reverted Changes

**Always document reversions**:

```markdown
#### Reverted Changes
1. **Switched back from PostgreSQL to Firestore**
   - Original Change: Session 3 switched to PostgreSQL for POC
   - Reason for Revert: PostgreSQL migration too complex for timeline
   - Decision: Use Firestore, accept slower POC queries
   - User Quote: "時程比效能重要，先用 Firestore"
   - Reverted Files:
     - Deleted `services/database/postgres_client.py`
     - Restored `services/database/firestore_client.py`
   - Updated: plan.md (removed PostgreSQL references)
```

---

## 📊 Recording Metrics

Track these metrics in each session entry:

### Time Metrics
- Session duration (hours)
- Time spent on each major task

### Work Metrics
- Files created (count)
- Files modified (count)
- Lines of code written
- Tests written (if applicable)

### Quality Metrics
- Objectives completed vs planned
- Open questions resolved
- Decisions made
- Risks identified

---

## 🎓 Training for New AI Assistants

### First Session Checklist

When a new AI assistant starts their first session:

1. [ ] Read `QUICK_START_FOR_AI.md` (5 min)
2. [ ] Read `DEVELOPMENT_LOG.md` (all sessions, 10-15 min)
3. [ ] Read `DEVELOPMENT_GUIDELINES.md` (this file, 5 min)
4. [ ] Read latest spec/plan files relevant to current work
5. [ ] Confirm understanding of recording requirements
6. [ ] Begin work
7. [ ] **Record session before ending** ⚠️ MANDATORY

---

## ✅ Recording Template Quick Access

### Full Template

See bottom of `DEVELOPMENT_LOG.md` for complete template.

### Quick Template (Copy & Paste)

```markdown
### Session X: YYYY-MM-DD (Title)

**Duration**: X hours
**AI Model**: [Model Name]
**User**: Stephen

#### Objectives Completed ✅
- [ ] Objective 1
- [ ] Objective 2

#### Files Created/Modified
**Created**:
- `path/to/file` (description)

**Modified**:
- `path/to/file` (changes made)

#### Key Discussions & Decisions
##### 1. Decision Topic
**User Request**: "..."
**Decision**: ...
**Rationale**: ...

#### Technical Highlights
- Key implementation detail 1
- Key implementation detail 2

#### Known Issues & Risks
1. **Issue**: Description
   - Mitigation: Solution

#### Open Questions
1. **Question**: ...
   - Status: Pending/Resolved

#### Next Session Preparation
**For Next AI Assistant**:
- Action item 1
- Action item 2
- Must read: [specific files]
- Blockers: [if any]
```

---

## 🚨 Enforcement

### For AI Assistants

**At the end of EVERY session, you MUST**:

1. Ask yourself: "Have I recorded this session?"
2. If NO → Do not end session, record first
3. If YES → Verify using self-check checklist
4. Only then → Provide session summary to user

### For Users

**If an AI assistant tries to end session without recording**:

Say: "請先記錄這次 session 到 DEVELOPMENT_LOG.md，然後更新 session summary 給我。"

---

## 📝 Summary

### The Golden Rule

**"Every session MUST be recorded before it ends. No exceptions."**

### The Three Must-Updates

Every session MUST update:
1. ✅ DEVELOPMENT_LOG.md (new session entry)
2. ✅ Session summary (message to user)
3. ✅ QUICK_START_FOR_AI.md (if critical changes)

### The Self-Check Question

**Before saying goodbye**: "Have I updated DEVELOPMENT_LOG.md and given user a session summary?"

- If YES → ✅ Good to go
- If NO → ❌ Do it now

---

**This guideline is effective immediately and applies to all development activities.**

*Last Updated: 2025-01-29*
*Version: 1.0*
