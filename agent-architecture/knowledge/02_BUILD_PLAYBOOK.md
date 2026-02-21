# 02 — The Build Playbook (7 Phases)

## The Universal Process for Building Any AI Agent

Development is Phase 3 of 7. The phases before and after it are what separate agents that work from agents that just demo well.

---

## Phase 0: Problem Validation (1-2 days)

**Goal:** Confirm you need an agent and scope it ruthlessly.

### Steps:
1. Run the agent litmus test (see 01_AGENT_FUNDAMENTALS.md) — does this require judgment, multi-step reasoning, AND adaptation?
2. Write a one-paragraph scope. If it takes two paragraphs, you're building two agents.
3. Define success criteria:
   - What does a correct output look like? (Write 5 real examples)
   - What does a dangerous failure look like? (Write 5 examples of things that must never happen)
   - What accuracy threshold makes this useful?
   - What latency is acceptable?
   - What's the cost ceiling?
4. Check if someone's already built this (GitHub, Product Hunt, commercial tools)

**Output:** Scope paragraph, success criteria, dangerous failure list, build-vs-buy decision.

---

## Phase 1: Research & Design (2-3 days)

**Goal:** Choose the right architecture and tools before coding.

### Steps:
1. Map the agent loop explicitly — what does Perceive/Reason/Act/Adapt look like for THIS agent?
2. Choose an architecture pattern (see 03_ARCHITECTURE_PATTERNS.md):
   - Single agent + tools
   - Pipeline (DAG)
   - Router
   - Multi-agent collaboration
   - Hierarchical
3. Design the state schema — what data flows between steps?
4. Identify risks and classify every action by risk level:
   - Read-only → no guardrail
   - Low-risk write → log it
   - Medium-risk write → rate limit
   - High-risk write → human-in-the-loop
   - Irreversible → hard block without approval
5. Choose framework and tech stack (see 04_FRAMEWORKS_GUIDE.md)

**Output:** Architecture diagram, state schema, risk matrix, tech stack decision.

---

## Phase 2: Prompt Engineering (3-5 days)

**Goal:** Get the LLM making the right decisions before building anything around it.

This is the most underrated phase. Your agent is only as good as its prompts.

### Steps:
1. Build a test dataset — 50-100 real inputs with manually labeled correct outputs
2. Split 70% development / 30% holdout
3. Iterate prompts in 5 rounds:
   - Round 1: Simplest possible prompt → note failures
   - Round 2: Add guidelines for each failure pattern
   - Round 3: Add 3-5 few-shot examples of tricky cases
   - Round 4: Force structured output (JSON) with reasoning field
   - Round 5: Adversarial testing — try to break it
4. Evaluate against holdout set (see 06_EVAL_METHODOLOGY.md)
5. Document every prompt iteration with date and reason

**Output:** Tested prompts with measured accuracy, evaluation results, prompt changelog.

---

## Phase 3: Development (5-7 days)

**Goal:** Build the agent, test it, get it running locally.

### Steps:
1. Set up project scaffold with strict typing and test framework
2. Build bottom-up — each component in isolation:
   - Data source connector (API wrapper)
   - LLM reasoning node (test against your dataset)
   - Storage layer
   - Output/delivery mechanism
   - State management / checkpointing
   - Graph/pipeline assembly
3. Run in shadow mode for 3+ days:
   - Agent runs and processes, but outputs go to a test channel
   - Manually compare agent output against what you'd have done
   - Track accuracy daily
4. Handle discovered edge cases:
   - Empty/malformed inputs
   - Extremely long inputs (token limits)
   - API rate limits and timeouts
   - LLM API errors
   - Malformed LLM responses

**Output:** Working agent in shadow mode, 3+ days of comparison data, edge case handling.

---

## Phase 4: Evaluation & Tuning (3-5 days)

**Goal:** Systematically measure and improve before going live.

### Steps:
1. Build automated eval pipeline (see 06_EVAL_METHODOLOGY.md)
2. Establish metrics baseline on holdout set
3. Identify failure patterns and fix:
   - Prompt issues → refine prompt, add guidelines/examples
   - Architecture issues → restructure nodes/flow
   - Data issues → add preprocessing, better parsing
4. A/B test every prompt change:
   - Run old AND new prompt against same test cases
   - Only deploy if new prompt is strictly better on primary metrics
5. Run evals on every change (prompt, model, code) — automated, not manual

**Output:** Eval pipeline, metrics baseline, tuned prompts with measured improvements.

---

## Phase 5: Deployment (2-3 days)

**Goal:** Ship it with monitoring so you know when it breaks.

### Steps:
1. Containerize (Docker) with all dependencies
2. Set up persistent storage (database for state + checkpointing)
3. Set up scheduling (cron, queue, or webhook triggers)
4. Implement monitoring and alerting:
   - Heartbeat: is the agent running?
   - Output alert: did the expected output happen? (e.g., morning briefing by 7:15)
   - API health: are external services responding?
   - Auth health: are tokens still valid?
   - Cost tracking: daily spend within budget?
5. Set up LLM tracing (LangSmith or equivalent) — every LLM call logged with full input/output
6. Run deployment checklist (see 07_PRODUCTION_CHECKLIST.md)

**Output:** Running production deployment, monitoring dashboard, alerting rules.

---

## Phase 6: Feedback & Iteration (Ongoing)

**Goal:** Make the agent smarter every week using real-world data.

### Steps:
1. Collect feedback naturally:
   - Quick reactions (thumbs up/down) on outputs
   - Correction commands for misclassifications
   - Weekly manual review (10 minutes)
2. Turn feedback into improvement:
   - Add corrections to eval dataset
   - Re-run evals with current prompts
   - Iterate prompts to fix new failures
   - Verify old tests still pass
   - Deploy updated prompts
3. Track improvement with weekly scorecard
4. The eval dataset grows every week → prompts get more precise every week

**Output:** Growing eval dataset, weekly metrics, continuously improving prompts.

---

## Phase 7: Expansion (When Ready)

**Goal:** Add capabilities once the core is solid.

### Prerequisites:
- Core agent running reliably for 4+ weeks
- Weekly metrics consistently meeting targets
- Eval pipeline catching regressions

### Each expansion is its own mini-cycle through Phases 2-6.

### Resist building:
- Auto-actions without human approval (trust bar is extremely high)
- Sentiment analysis (rarely actionable)
- Fine-tuned models (unless >10K inputs/day)
- Multi-agent architecture (unless single agent demonstrably bottlenecks)

---

## Timeline Summary

| Phase | Duration | Key Output |
|-------|----------|-----------|
| 0. Validation | 1-2 days | Scope + success criteria |
| 1. Design | 2-3 days | Architecture + risk matrix |
| 2. Prompts | 3-5 days | Tested prompts + eval results |
| 3. Development | 5-7 days | Working agent in shadow mode |
| 4. Eval & Tuning | 3-5 days | Eval pipeline + metrics baseline |
| 5. Deployment | 2-3 days | Production + monitoring |
| 6. Iteration | Ongoing | Weekly improvement |
| 7. Expansion | As needed | New capabilities |
| **Total to production** | **3-4 weeks** | |
