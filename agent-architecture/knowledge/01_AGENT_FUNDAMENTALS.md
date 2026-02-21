# 01 — Agent Fundamentals

## What Is an AI Agent?

An AI agent is an autonomous system that **perceives** its environment, **reasons** about how to achieve a given goal, takes **actions** using tools, and **adapts** based on outcomes — in a continuous loop with minimal human direction.

## The Five Core Elements

Every AI agent, regardless of what it does, has these five elements:

| Element | What It Does | Example |
|---------|-------------|---------|
| **Perception** | Takes in information from the environment | Reading emails, parsing code, receiving user messages, watching a database |
| **Reasoning** | Thinks about what to do next | Classifying urgency, planning a multi-step approach, deciding which tool to use |
| **Action** | Does something in the world using tools | Calling APIs, writing files, sending messages, modifying data |
| **Adaptation** | Adjusts based on outcomes | Learning from feedback, refining approach after errors, updating priorities |
| **Autonomy** | Operates with minimal human direction | Running on schedule, making decisions without asking, escalating only when truly uncertain |

## Agent vs Script vs Automation — The Decision Framework

Before building an agent, answer three questions:

### 1. Does this task require judgment calls?
- **No → Script.** If every decision can be captured in if/else logic, you don't need an LLM.
- **Yes → Possibly an agent.** If decisions require understanding context, nuance, or ambiguity.

### 2. Does this task require multiple steps that depend on each other?
- **No → Function.** If it's a single API call with fixed input/output.
- **Yes → Possibly an agent.** If the output of step N changes what step N+1 should be, and the number of steps isn't fixed.

### 3. Does this task require adapting to new situations?
- **No → Automation.** If inputs are predictable and bounded.
- **Yes → Agent.** If the system will encounter things you can't enumerate in advance.

**Must answer YES to at least one (ideally two or three) to justify building an agent.** Otherwise, you're adding LLM cost and latency to something that could be solved with deterministic code.

## The Agentic Spectrum

Systems aren't binary agent/not-agent. They exist on a spectrum (Andrew Ng's framing):

```
Simple LLM Call ←──────────────────────────────→ Fully Autonomous Agent

Single prompt     Chain of       Tool-using      Autonomous        Multi-agent
with one output   prompts        LLM             loop with         collaboration
                  (pipeline)                     planning
```

Start as far LEFT as possible. Move right only when the simpler approach demonstrably fails.

## Industry Definitions

| Source | Key Insight |
|--------|------------|
| **Anthropic** | Workflows = predefined code paths; Agents = LLMs dynamically direct their own processes |
| **OpenAI** | Three core components: Model, Tools, Instructions/Guardrails |
| **Google** | Emphasizes: reasoning, acting, observing, planning, learning |
| **LangChain** | "System that uses an LLM to decide the control flow of an application" |
| **Andrew Ng** | Agentic spectrum — systems are agent-like to different degrees |

The consensus: an agent uses an LLM for reasoning and decision-making, has access to tools for taking actions, maintains some form of memory, and operates with a degree of autonomy in pursuing a goal.

## Six Architectural Modules

Every serious agent framework maps to these six modules:

1. **Model/Reasoning Engine (The Brain):** LLM powering reasoning — chain-of-thought, planning, self-reflection
2. **Perception/Input (The Senses):** Gathers and interprets data — NLP, APIs, webhooks, file parsing
3. **Memory (Short-term + Long-term):** Short-term tracks current task; long-term uses vector stores or databases for persistence across sessions
4. **Tools & Actions (The Hands):** External functions/APIs for real-world action. Anthropic's MCP emerging as a standard for tool integration.
5. **Planning & Orchestration (Executive Function):** Control loop — what to do next, task decomposition, retries, error handling
6. **Guardrails & Safety (Governance):** Input validation, output filtering, permission boundaries, human-in-the-loop checkpoints

## Common Mistakes

- **Over-agentifying:** Using an agent when a script would work. Every LLM call adds cost, latency, and non-determinism.
- **Starting multi-agent:** A single well-prompted agent handles 95% of use cases. Add agents only when one demonstrably can't do the job.
- **Skipping eval:** Without systematic measurement, you don't know if your agent works. You just think it does.
- **Prompt as afterthought:** The prompt IS the agent's brain. Spend more time on it than on the orchestration code.
- **No guardrails:** Every action has a risk level. Classify them and add appropriate gates.
