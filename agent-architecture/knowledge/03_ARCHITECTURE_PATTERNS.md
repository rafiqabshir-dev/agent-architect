# 03 — Architecture Patterns

## Choosing the Right Agent Architecture

Start with the simplest pattern that solves the problem. Escalate only when the simpler pattern demonstrably fails.

---

## Pattern 1: Single Agent + Tools

```
User Input → [LLM + Tools] → Output
                ↑      │
                └──────┘  (ReAct loop)
```

**How it works:** One LLM with access to multiple tools. The LLM decides which tool to call, interprets results, and decides what to do next. Classic ReAct (Reason + Act) loop.

**When to use:**
- Straightforward tasks with clear tool boundaries
- The LLM can handle all reasoning in a single context
- You want fast prototyping
- Task complexity is moderate

**When NOT to use:**
- You need deterministic control flow (LLM might skip steps)
- Task requires more tokens than a single context window
- You need different models for different subtasks
- Reliability is more important than flexibility

**Framework fit:** LangChain's `createReactAgent`, OpenAI Assistants API

---

## Pattern 2: Pipeline (DAG)

```
START → [Node A] → [Node B] → [Node C] → END
                        ↑          │
                        └──────────┘ (conditional loop)
```

**How it works:** Predefined sequence of nodes. Some nodes use LLMs, some are pure code. Edges between nodes are deterministic — you define the exact flow. Loops are explicit and bounded.

**When to use:**
- Tasks with a known sequence of steps
- You need reliability and determinism
- Different steps need different prompts or models
- You want fine-grained error handling per step
- Production systems that run unattended

**When NOT to use:**
- You don't know the steps yet (prototype with Pattern 1 first)
- The task is truly open-ended with unpredictable branching

**Framework fit:** LangGraph, custom state machines

**This is the most common production pattern.** Most real-world agents are pipelines with 5-10 nodes, a few conditional branches, and one or two loops.

---

## Pattern 3: Router

```
                    ┌→ [Specialist A] → Output
Input → [Router] ──┼→ [Specialist B] → Output
                    └→ [Specialist C] → Output
```

**How it works:** A lightweight LLM (or classifier) examines the input and routes it to a specialized handler. Each handler is optimized for its domain.

**When to use:**
- Inputs fall into distinct categories requiring different handling
- You want to use cheaper/faster models for simple cases and smarter models for complex ones
- Different domains need different tools, prompts, or workflows

**When NOT to use:**
- Categories aren't clearly separable
- Most inputs need the same treatment

**Framework fit:** LangGraph conditional edges, custom routing logic

**Example:** Customer support agent that routes billing questions to a billing specialist (with database access), technical questions to a tech specialist (with docs access), and general inquiries to a generalist.

---

## Pattern 4: Multi-Agent Collaboration

```
[Agent A] ←→ [Agent B]
    ↑             ↑
    └─────┬───────┘
          ↓
      [Agent C]
```

**How it works:** Multiple agents with different roles, tools, and system prompts communicate with each other. They can share a workspace (shared state) or pass messages.

**When to use:**
- Task genuinely requires different expertise that can't fit in one context
- Subtasks are naturally independent and can run in parallel
- You want separation of concerns (each agent is simpler and testable)
- Complex workflows where one agent's output feeds another's input

**When NOT to use:**
- A single agent with good prompts can handle it (90% of cases)
- You're adding agents because it sounds cool, not because you've proven the need
- Communication overhead between agents exceeds the benefit

**Framework fit:** CrewAI, AutoGen, LangGraph (with subgraphs)

**Warning:** Multi-agent adds significant complexity — inter-agent communication, shared state management, coordination failures, harder debugging. Only use when single-agent demonstrably fails.

---

## Pattern 5: Hierarchical (Manager-Worker)

```
            [Manager Agent]
           /       |        \
    [Worker A] [Worker B] [Worker C]
```

**How it works:** A manager agent decomposes the task, delegates subtasks to specialized workers, collects results, and synthesizes the final output. Workers don't talk to each other — only to the manager.

**When to use:**
- Large tasks that decompose into independent subtasks
- You want centralized coordination and quality control
- Workers can operate in parallel
- The manager needs to synthesize disparate results

**When NOT to use:**
- Subtasks are tightly coupled (workers need to communicate)
- The decomposition itself is the hard part (manager might get it wrong)

**Framework fit:** AutoGen, CrewAI, LangGraph with subgraphs

**Example:** Research agent where a manager plans research questions, delegates each to a worker agent that searches and summarizes, then the manager synthesizes all findings into a final report.

---

## Decision Flowchart

```
Do you know the exact steps?
├── NO → Start with Pattern 1 (Single Agent + Tools)
│         Learn what the agent should do.
│         Then move to Pattern 2 when you understand the flow.
│
└── YES → Do steps need different models/prompts?
          ├── NO → Pattern 2 (Pipeline) — simplest reliable option
          │
          └── YES → Do inputs split into distinct categories?
                    ├── YES → Pattern 3 (Router) → each route can be Pattern 2
                    │
                    └── NO → Can one agent handle it with good prompts?
                              ├── YES → Pattern 2 (Pipeline)
                              │
                              └── NO → Are subtasks independent?
                                        ├── YES → Pattern 5 (Hierarchical)
                                        └── NO → Pattern 4 (Multi-Agent)
```

## Key Principle

**Always start with the simplest pattern that could work.** You can always add complexity later. You can never easily remove it.

The progression most agents follow:
1. Prototype as Pattern 1 (learn what the agent should do)
2. Productionize as Pattern 2 (make it reliable)
3. Expand to Pattern 3 if inputs diverge enough
4. Only reach Pattern 4/5 if the problem genuinely demands it
