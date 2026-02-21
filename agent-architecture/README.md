# Agent Architect

An AI-powered assistant that generates production-ready spec files for AI agent projects. Describe your agent idea and get back structured requirements, design, and implementation task files compatible with [Kiro IDE](https://kiro.dev) and [Claude Code](https://claude.ai/claude-code).

## What It Does

1. **Validates** your idea — determines if it's a script, single agent, or multi-agent system
2. **Retrieves** relevant architecture knowledge using RAG (Retrieval-Augmented Generation)
3. **Generates** three spec files:
   - `requirements.md` — User stories and acceptance criteria (EARS notation)
   - `design.md` — Architecture, components, data flow, risk matrix
   - `tasks.md` — Phased implementation tasks with sub-tasks

## Architecture

```
User Request
    │
    ▼
┌─────────────────┐
│  Input Guardrail │ ── validates query length
└────────┬────────┘
         ▼
┌─────────────────┐
│   RAG Pipeline   │ ── embeds query → searches knowledge base → retrieves relevant chunks
└────────┬────────┘
         ▼
┌─────────────────┐
│ Idea Validation  │ ── Claude (Haiku) classifies: script / agent / multi-agent
└────────┬────────┘
         ▼
┌─────────────────┐
│ Spec Generation  │ ── Claude (Sonnet) generates requirements, design, and tasks
└────────┬────────┘
         ▼
┌─────────────────┐
│ Output Guardrail │ ── verifies all three files are present and sufficient
└────────┬────────┘
         ▼
    JSON Response
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API Server | FastAPI + Uvicorn |
| LLM | Claude (Anthropic SDK) |
| Embeddings | Voyage AI |
| Vector Store | In-memory (pure Python) |
| Validation | Pydantic |

## Project Structure

```
agent-architect/
├── app.py                      # FastAPI server — wires everything together
├── lib/
│   ├── embed.py                # Voyage AI embedding wrapper
│   ├── vector_store.py         # In-memory vector store with cosine similarity
│   ├── rag.py                  # RAG pipeline — retrieve relevant knowledge
│   ├── prompts.py              # System prompt (role, rules, CoT, few-shot, output format)
│   ├── tools.py                # Claude tool definitions (validate, select, generate)
│   ├── guardrails.py           # Input and output validation
│   └── models.py               # Model routing (Haiku for validation, Sonnet for generation)
├── scripts/
│   └── index_knowledge.py      # Index knowledge files into the vector store
├── knowledge/
│   ├── 01_AGENT_FUNDAMENTALS.md
│   ├── 02_BUILD_PLAYBOOK.md
│   ├── 03_ARCHITECTURE_PATTERNS.md
│   ├── 04_FRAMEWORKS_GUIDE.md
│   ├── 05_PROMPT_ENGINEERING.md
│   ├── 06_EVAL_METHODOLOGY.md
│   ├── 07_PRODUCTION_CHECKLIST.md
│   ├── 08_SPEC_OUTPUT_FORMAT.md
│   └── 09_TOOL_DESIGN.md
├── requirements.txt
├── .env.example
└── LEARNINGS.md                # Python learnings from a JS/TS developer
```

## Setup

### Prerequisites
- Python 3.9+
- [Anthropic API key](https://console.anthropic.com)
- [Voyage AI API key](https://dash.voyageai.com)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/agent-architect.git
cd agent-architect

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and add your API keys
```

### Index Knowledge Base

Run this once to embed the knowledge files into the vector store:

```bash
python scripts/index_knowledge.py
```

### Start the Server

```bash
uvicorn app:app --reload
```

The API will be available at `http://localhost:8000`.

## Usage

Send a POST request with your agent idea:

```bash
curl -X POST http://localhost:8000/generate -H "Content-Type: application/json" -d '{"query": "I want to build an AI agent that reviews pull requests, checks for bugs, and suggests improvements"}'
```

### Response

Returns a JSON object with three fields:

```json
{
  "requirements": "# Requirements — PR Review Agent\n\n## Introduction\n...",
  "design": "# Design — PR Review Agent\n\n## Architecture\n...",
  "tasks": "# Tasks — PR Review Agent\n\n## Phase 1\n..."
}
```

### Error Response

```json
{
  "error": "Idea not suitable for an agent: This can be achieved with a simple script..."
}
```

## Concepts Applied

This project applies concepts from a complete AI Engineering learning path:

| Concept | Lesson | Where Used |
|---------|--------|-----------|
| API Basics & Streaming | L1-L2 | `app.py` |
| System Prompts | L3 | `lib/prompts.py` |
| Function Calling | L4 | `lib/tools.py`, `app.py` |
| Structured Outputs | L5 | `lib/tools.py` |
| Prompt Engineering (FSP, CoT, Grounding) | L6 | `lib/prompts.py` |
| Embeddings | L7 | `lib/embed.py` |
| Vector Databases | L8 | `lib/vector_store.py` |
| RAG Pipeline | L9 | `lib/rag.py` |
| Evals | L10 | `evals/` (planned) |
| Guardrails | L11 | `lib/guardrails.py` |
| Cost Optimization (Model Routing) | L12 | `lib/models.py` |

## License

MIT
