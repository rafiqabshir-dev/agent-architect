# 05 — Prompt Engineering Methodology

## The Process for Getting LLM Prompts Right

Your agent is only as good as its prompts. This is the systematic process for designing, testing, and iterating them — applicable to any agent.

---

## Step 1: Build a Test Dataset

Before writing a single prompt, collect real examples.

### Requirements:
- **Minimum 50 examples** (target 100+)
- **Real inputs** your agent will actually see, not synthetic
- **Manually labeled** with the correct output (ground truth)
- **Include edge cases:** ambiguous inputs, adversarial inputs, empty inputs, extremely long inputs, inputs in unexpected formats
- **Split:** 70% development set (for iterating) / 30% holdout set (for final evaluation)

### Dataset Structure:
```typescript
interface TestCase {
  id: string;
  input: any;           // The raw input your agent will receive
  expectedOutput: any;  // The correct output, manually determined
  notes: string;        // Why this is the correct output
  tags: string[];       // Edge case categories: "ambiguous", "adversarial", "empty", etc.
}
```

**This dataset is your most valuable asset.** Everything else is built on top of it.

---

## Step 2: Iterate Prompts in 5 Rounds

### Round 1 — Baseline
Write the simplest possible prompt. No examples, no detailed guidelines. Just tell the LLM what to do.

Run against the development set. Note every failure — what went wrong and why.

### Round 2 — Add Guidelines
For each failure pattern, add a specific instruction. Be concrete, not abstract.

**Bad:** "Be careful with edge cases"
**Good:** "When the input contains an automated notification from a monitoring system (e.g., Jira, GitHub Actions, Datadog), classify as INFORMATIONAL unless it explicitly mentions a production outage or P0 incident"

### Round 3 — Add Few-Shot Examples
Include 3-5 examples IN the prompt showing correct handling of the trickiest cases. Choose examples that cover:
- The most common failure from Round 2
- An ambiguous case where the correct answer is non-obvious
- An adversarial case designed to trick the classifier
- An edge case (empty, extremely long, wrong format)

### Round 4 — Structured Output
Force the LLM to respond in structured format (JSON) with a "reasoning" field:
```json
{
  "output": "the classification or action",
  "reasoning": "why I made this decision",
  "confidence": "high | medium | low"
}
```

The reasoning field improves accuracy (chain-of-thought) AND gives you debugging visibility. The confidence field helps you decide when to escalate to human review.

### Round 5 — Adversarial Testing
Try to break the prompt:
- Inputs designed to trick the classifier
- Extremely long inputs that might cause truncation issues
- Inputs that look like one category but are actually another
- Inputs with conflicting signals
- Inputs in unexpected formats or languages

Patch the prompt for each failure. But resist adding too many rules — if the prompt becomes a 2000-word essay, the LLM may start ignoring parts of it. Keep it focused.

---

## Step 3: Evaluate Systematically

Run your final prompt against the **holdout** set (the 30% you haven't used for iteration).

### Universal Metrics:
- **Overall accuracy:** correct outputs / total
- **Per-class precision:** of the items predicted as X, how many actually are X?
- **Per-class recall:** of the items that are actually X, how many did we catch?
- **Dangerous failure rate:** how often does the worst failure mode occur?

### Define "Dangerous Failure" for Your Agent:
Every agent has a failure that's worse than all others. Identify it and measure it explicitly.

| Agent Type | Dangerous Failure | Acceptable Rate |
|-----------|-------------------|----------------|
| Email triage | Missing a critical email | <1% |
| Code review | Approving buggy code | <5% |
| Customer support | Giving wrong factual information | <2% |
| Research agent | Citing non-existent sources | <1% |
| Security alert | Missing a real threat | <0.5% |

---

## Step 4: Document Everything

Keep a prompt changelog:

```markdown
| Version | Date | Change | Reason | Accuracy Impact |
|---------|------|--------|--------|----------------|
| v1 | — | Baseline prompt | Initial | 72% |
| v2 | — | Added guidelines for automated notifications | False criticals from bots | 81% |
| v3 | — | Added 4 few-shot examples | Ambiguous cases | 88% |
| v4 | — | Added structured JSON output with reasoning | Debugging + chain-of-thought boost | 91% |
| v5 | — | Added adversarial handling | Edge cases | 93% |
```

When the prompt breaks in production (it will), this changelog is how you diagnose what went wrong.

---

## Prompt Design Principles

### Do:
- Be specific and concrete — "classify emails from automated systems as INFORMATIONAL" beats "use good judgment"
- Include the output format in the prompt — show exactly what the JSON should look like
- Use the reasoning field — it improves both accuracy and debuggability
- Keep the prompt focused — one job per prompt, not five
- Include negative examples — "do NOT classify as critical just because the subject line is in all caps"

### Don't:
- Don't make the prompt a novel — if it's over 1000 words, the LLM will start ignoring parts
- Don't assume the LLM knows your domain — spell out what "critical" means in YOUR context
- Don't rely on the LLM to handle infrastructure failures — that's code's job
- Don't A/B test in production without eval pipeline — you need measurable comparison
- Don't change prompts and code simultaneously — you won't know what caused the change in behavior

---

## Temperature Guidelines

| Task Type | Temperature | Why |
|-----------|------------|-----|
| Classification / triage | 0 | You want consistent, deterministic outputs |
| Structured extraction | 0 | Consistency matters more than creativity |
| Summarization | 0 - 0.3 | Slight variation in phrasing is fine |
| Creative writing | 0.5 - 0.8 | You want diversity and flair |
| Brainstorming | 0.7 - 1.0 | You want surprising ideas |

For most agent tasks, use temperature 0. Agent reasoning should be deterministic.
