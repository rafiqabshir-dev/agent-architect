# 04 — Frameworks Guide

## Choosing the Right Framework for Your Agent

This is a decision guide, not a tutorial. Pick the framework that matches your problem, not the one with the most GitHub stars.

---

## Framework Comparison Matrix

| Framework | Best For | Language | Control Level | Production Ready | GitHub Stars |
|-----------|---------|----------|--------------|-----------------|-------------|
| **LangGraph** | Custom agents with deterministic control flow | Python, TypeScript | Full control (you define every node and edge) | Yes (v1.0+) | ~112K (with LangChain) |
| **LangChain** | Rapid prototyping, exploring what an agent should do | Python, TypeScript | High-level (LLM decides control flow) | Prototyping yes, production use LangGraph | ~112K |
| **CrewAI** | Multi-agent collaboration with distinct roles | Python | Medium (define roles, framework handles coordination) | Growing | ~30K |
| **AutoGen** | Research, flexible multi-agent conversations | Python | Medium (define agents, conversation patterns emerge) | Research-grade | ~40K |
| **AutoGPT** | General-purpose autonomous agent, experimentation | Python | Low (give it a goal, it figures out the rest) | Experimental | ~177K |
| **OpenHands** | Autonomous software engineering | Python | Low (point at issue, it codes the fix) | Growing (ICLR 2025) | ~61K |
| **GPT Researcher** | Deep autonomous research | Python | Low (give topic, get report) | Yes (for research tasks) | ~15K |

---

## Decision Guide

### "I want to BUILD a custom agent from scratch"
**→ LangGraph**

Why: Full control over every node, edge, and state transition. You define the architecture. Deterministic control flow. Production-hardened with checkpointing, human-in-the-loop, durable execution. TypeScript and Python support.

When to start with LangChain instead: You don't know what the agent should do yet. Prototype with LangChain's high-level agent, learn the flow, then rewrite in LangGraph.

### "I want multiple agents working together as a team"
**→ CrewAI or AutoGen**

CrewAI: When you have distinct roles (researcher, writer, reviewer) and want a structured collaboration. Easier to set up, more opinionated.

AutoGen: When you want flexible, research-oriented conversations between agents. Less structured, more experimental.

### "I want an agent that writes code and fixes issues"
**→ OpenHands**

Gives the agent a full development environment (terminal, browser, editor) in a Docker sandbox. Points at GitHub issues, plans fixes, writes code, runs tests, opens PRs.

### "I want an agent that does deep research on a topic"
**→ GPT Researcher**

Single-purpose: plans queries, searches the web, cross-references sources, produces comprehensive reports with citations. Clean example of the full agent loop.

### "I want to experiment with autonomous agents"
**→ AutoGPT**

The original. Give it a goal, watch it go. Best for learning what autonomous agents feel like. Not recommended for production due to loop risk and token burn.

---

## LangGraph vs LangChain — The Key Distinction

This comes up constantly, so here's the detailed comparison:

### LangChain (High-Level)
- You define **tools + a system prompt**
- The **LLM decides** what to call, when, and in what order
- The LLM IS the control flow
- Less code (~110 lines for a typical agent)
- Less predictable (LLM might skip steps, call tools out of order)
- Higher token cost (LLM reasons about routing + tool selection every cycle)
- Best for: prototyping, fuzzy workflows, learning

### LangGraph (Low-Level)
- You define **nodes + edges + state**
- **You control** the exact flow; LLM only runs inside specific nodes
- Deterministic control flow
- More code (~270 lines for the same agent)
- Highly predictable (impossible to skip steps or call things out of order)
- Lower token cost (LLM only called for reasoning tasks, not routing)
- Best for: production, reliability, unattended operation

### Cost Comparison (100 daily inputs)
- LangChain: ~$15-24/month (LLM handles routing + reasoning)
- LangGraph: ~$9/month (LLM handles reasoning only)

### The Recommended Path
1. Prototype in LangChain to learn what the agent should do
2. Productionize in LangGraph to ensure it always does that
3. Prompts transfer directly — only the orchestration changes

---

## Framework Selection by Use Case

| Use Case | Recommended | Runner-Up |
|----------|------------|-----------|
| Email triage agent | LangGraph | LangChain (prototype) |
| Code review agent | LangGraph + OpenHands (reference) | LangChain |
| Customer support agent | LangGraph (router pattern) | CrewAI |
| Research report generator | GPT Researcher | LangGraph |
| Content creation pipeline | LangGraph (pipeline pattern) | CrewAI |
| Data analysis agent | LangGraph | LangChain |
| Workflow automation | LangGraph | LangChain |
| Multi-agent simulation | AutoGen | CrewAI |
| Autonomous coding | OpenHands | LangGraph + tools |

## TypeScript Considerations

If you're a TypeScript developer:

- **LangGraph.js** — First-class support. Runs in Node, Deno, Cloudflare Workers, Vercel Edge. Full type safety on state, nodes, edges.
- **LangChain.js** — Full support. Share types between agent and UI.
- **All other frameworks** — Python only. You'd need to wrap them in an API or switch languages.

If TypeScript is non-negotiable, your realistic choices are LangGraph.js or LangChain.js.
