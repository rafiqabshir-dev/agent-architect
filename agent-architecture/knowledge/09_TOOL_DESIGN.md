# 09 — Tool Design Best Practices

## How to Design Tools That LLMs Can Actually Use

Tools are how your agent takes action. A poorly designed tool confuses the LLM, causes errors, and wastes tokens. A well-designed tool is self-explanatory — the LLM knows exactly when and how to use it.

---

## The Three Parts of a Tool Definition

Every tool has three parts the LLM sees:

| Part | Purpose | Example |
|------|---------|---------|
| **Name** | When to use it | `search_documentation` |
| **Description** | What it does and when to pick it | "Search the project documentation for relevant sections. Use this when the user asks about how something works." |
| **Parameters** | What inputs it needs | `{ "query": "string", "max_results": "number" }` |

The LLM never sees your implementation code — only these three parts. Design them for the LLM as your audience.

---

## Naming Conventions

### Do:
- Use verb_noun format: `search_docs`, `create_ticket`, `validate_input`
- Be specific: `get_user_by_email` not `get_user`
- Make the action clear from the name alone

### Don't:
- Use generic names: `process`, `handle`, `do_thing`
- Use abbreviations the LLM might not understand: `proc_req` instead of `process_request`
- Use names that overlap in meaning: `find_docs` and `search_docs` doing different things

---

## Writing Descriptions

The description is the most important part. It tells the LLM WHEN to use the tool, not just what it does.

### Bad:
```
"Searches the database"
```

### Good:
```
"Search the knowledge base for architecture patterns, frameworks, and best practices. Use this tool when the user asks about how to design, structure, or build an AI agent. Returns the top 3 most relevant text chunks with similarity scores."
```

### Include in Every Description:
1. **What it does** — one sentence
2. **When to use it** — what kind of user request triggers this tool
3. **What it returns** — so the LLM knows what to expect
4. **When NOT to use it** (optional) — prevents misuse

---

## Parameter Design

### Rules:
- Use descriptive parameter names: `user_email` not `e` or `param1`
- Mark required vs optional clearly
- Include parameter descriptions — the LLM reads these
- Use enums for constrained choices: `"risk_level": {"enum": ["low", "medium", "high"]}`
- Set sensible defaults for optional parameters

### Example — Well-Designed Parameters:
```json
{
  "name": "select_architecture",
  "description": "Select the best architecture pattern for the user's agent based on their requirements. Use after validate_agent_idea confirms the idea is viable.",
  "parameters": {
    "type": "object",
    "properties": {
      "complexity": {
        "type": "string",
        "enum": ["simple", "moderate", "complex"],
        "description": "How complex the agent's task is"
      },
      "needs_determinism": {
        "type": "boolean",
        "description": "Whether the agent needs predictable, repeatable behavior"
      },
      "parallel_subtasks": {
        "type": "boolean",
        "description": "Whether the agent has independent subtasks that can run simultaneously"
      }
    },
    "required": ["complexity", "needs_determinism"]
  }
}
```

---

## Action Tools vs Structure Tools

From Lesson 5 — two different purposes for tools:

| Type | Purpose | Example |
|------|---------|---------|
| **Action tool** | Claude calls it to DO something | `search_docs`, `create_ticket`, `send_email` |
| **Structure tool** | Claude calls it to RETURN data in a specific shape | `format_spec_output`, `structure_analysis` |

Structure tools aren't "real" tools — they don't execute any external action. They exist to force Claude's response into a predictable JSON shape. Your code receives the structured data and uses it directly.

### When to Use Structure Tools:
- You need Claude's response in exact JSON format
- You want to guarantee specific fields are always present
- You're feeding Claude's output into another system that expects a schema

---

## Error Responses

When a tool fails, return a clear error message — not a stack trace. The LLM needs to understand what went wrong so it can decide what to do next.

### Bad:
```
"Error: KeyError: 'user_id' at line 42 in db_connector.py"
```

### Good:
```
"Error: No user found with email 'test@example.com'. The email may be misspelled or the user may not exist in the system."
```

The LLM can act on the second message. The first is meaningless to it.

---

## Common Mistakes

1. **Too many tools:** More than 10-15 tools confuses the LLM about which to pick. Consolidate related actions.
2. **Overlapping tools:** Two tools that seem similar forces the LLM to guess. Make boundaries clear.
3. **Missing descriptions:** The LLM won't reliably use a tool if it doesn't understand when to use it.
4. **Huge parameter objects:** Tools with 15+ parameters overwhelm the LLM. Break into multiple focused tools.
5. **No error handling:** If the tool can fail, define what the error response looks like so the LLM can recover.

---

## Tool Count Guidelines

| Agent Complexity | Recommended Tools | Example |
|-----------------|-------------------|---------|
| Simple (single task) | 2-4 | validate, process, format |
| Moderate (multi-step) | 5-8 | search, classify, route, generate, validate, format |
| Complex (multi-domain) | 8-15 | Multiple domains with 2-4 tools each |
| Too many | 15+ | LLM struggles to pick the right tool — consolidate |
