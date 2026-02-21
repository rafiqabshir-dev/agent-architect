# 06 — Evaluation Methodology

## How to Measure Whether Your Agent Actually Works

Without systematic evaluation, you're flying blind. This applies to every agent, regardless of what it does.

---

## The Eval Pipeline

Every agent needs this pipeline running before it goes to production:

```
┌─────────────┐     ┌───────────────┐     ┌──────────────┐     ┌─────────────┐
│ Test Dataset │────▶│ Run Agent on  │────▶│ Compare to   │────▶│ Metrics     │
│ (labeled)    │     │ Each Case     │     │ Ground Truth │     │ Report      │
└─────────────┘     └───────────────┘     └──────────────┘     └─────────────┘
```

### Pipeline Code (Pseudocode — Adapt to Your Agent)

```typescript
interface EvalResult {
  testCaseId: string;
  input: any;
  expectedOutput: any;
  actualOutput: any;
  correct: boolean;
  latencyMs: number;
  tokensUsed: number;
  error?: string;
}

async function runEval(dataset: TestCase[]): Promise<EvalResult[]> {
  const results: EvalResult[] = [];
  for (const testCase of dataset) {
    const start = Date.now();
    try {
      const output = await runAgentNode(testCase.input);
      results.push({
        testCaseId: testCase.id,
        input: testCase.input,
        expectedOutput: testCase.expectedOutput,
        actualOutput: output,
        correct: isCorrect(output, testCase.expectedOutput),
        latencyMs: Date.now() - start,
        tokensUsed: getTokensUsed(),
      });
    } catch (error) {
      results.push({
        testCaseId: testCase.id,
        input: testCase.input,
        expectedOutput: testCase.expectedOutput,
        actualOutput: null,
        correct: false,
        latencyMs: Date.now() - start,
        tokensUsed: 0,
        error: error.message,
      });
    }
  }
  return results;
}
```

---

## Universal Metrics

These apply to any agent. Customize the specific values for your use case.

### Primary Metrics

| Metric | What It Measures | How to Compute |
|--------|-----------------|----------------|
| **Overall Accuracy** | General quality | Correct / Total |
| **Dangerous Failure Rate** | How often the worst failure happens | Count of dangerous failures / Total |
| **Latency (p50, p95)** | Speed | Median and 95th percentile of response time |
| **Cost per Run** | Sustainability | Total tokens × price per token |
| **Error Rate** | Reliability | Runs with exceptions / Total runs |

### Per-Class Metrics (For Classification Agents)

| Metric | Formula | Why It Matters |
|--------|---------|---------------|
| **Precision** | TP / (TP + FP) | How often we're right when we predict this class |
| **Recall** | TP / (TP + FN) | How often we catch items that belong to this class |
| **F1 Score** | 2 × (Precision × Recall) / (Precision + Recall) | Balanced measure |

### Setting Targets

Define targets BEFORE running evals (not after, to avoid moving goalposts):

| Metric | Minimum Viable | Target | Stretch |
|--------|---------------|--------|---------|
| Overall accuracy | 85% | 90% | 95% |
| Dangerous failure rate | <5% | <2% | <1% |
| Latency (p95) | <30s | <10s | <5s |
| Cost per run | <$0.05 | <$0.01 | <$0.005 |

---

## When to Run Evals

| Trigger | Why |
|---------|-----|
| Before every prompt change deployment | Catch regressions |
| Before every model change | New model may behave differently |
| Before every code change to agent logic | Ensure no side effects |
| Weekly (even with no changes) | Catch environmental drift |
| After adding new test cases | Establish new baseline |

---

## A/B Testing Prompts

Never change prompts in production without comparing:

1. Run **old prompt** against the holdout set → record all metrics
2. Run **new prompt** against the **same** holdout set → record all metrics
3. Compare side by side
4. **Deploy only if:**
   - Primary metric (e.g., dangerous failure rate) is same or better
   - No metric regresses by more than 5%
   - If there's a trade-off (e.g., better recall but worse precision), decide explicitly whether it's acceptable for your use case

---

## Growing the Dataset

Your eval dataset is a living document:

- Every misclassification found in production → add to dataset with correct label
- Every new edge case encountered → add to dataset
- Every user correction → add to dataset
- Review and clean the dataset monthly (remove duplicates, fix mislabeled cases)

**Target:** Start with 50, grow to 200+ within the first month of production use.

---

## Weekly Scorecard

Track these every week. It's your evidence that the agent is improving and your early warning when it regresses.

```markdown
| Week | Inputs Processed | Accuracy | Dangerous Failure Rate | Latency p95 | Daily Cost | Subjective Rating (1-5) |
|------|-----------------|----------|----------------------|-------------|------------|------------------------|
| 1    |                 |          |                      |             |            |                        |
| 2    |                 |          |                      |             |            |                        |
| 3    |                 |          |                      |             |            |                        |
```

---

## Debugging Failures

When the agent gets something wrong:

1. **Pull the trace** — LangSmith or equivalent, full input/output of every LLM call
2. **Classify the failure:**
   - **Prompt issue:** The LLM had the right information but reasoned incorrectly → fix the prompt
   - **Context issue:** The LLM didn't have enough information → add more context to the input
   - **Truncation issue:** Input was too long and key info was cut → improve preprocessing
   - **Format issue:** LLM returned malformed output → add format enforcement or retry logic
   - **Architecture issue:** The wrong node handled this case → fix routing/edges
3. **Add the failure to the test dataset** with the correct label
4. **Fix and verify** — ensure the fix doesn't break existing test cases

---

## Anti-Patterns

- **Evaluating on the development set only:** You'll overfit. Always use the holdout set for final measurement.
- **Manual-only evaluation:** You'll stop doing it after week 2. Automate it.
- **Changing prompts and code simultaneously:** You won't know what caused behavior changes.
- **No baseline:** If you don't measure before changes, you can't prove improvement.
- **Subjective-only assessment:** "It feels better" is not a metric. Measure.
