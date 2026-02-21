# 08 — Spec Output Format (Kiro + Claude Code Compatible)

## Overview

When the user describes an agent to build, the Claude Project outputs a **three-file specification** compatible with both Kiro IDE (`.kiro/specs/`) and Claude Code (`.claude/specs/` or project root). This is the primary deliverable of the project.

The three files follow Kiro's spec-driven development format:

```
.kiro/specs/{agent-name}/
├── requirements.md    # WHAT to build (user stories + EARS acceptance criteria)
├── design.md          # HOW to build it (architecture, components, data flow)
└── tasks.md           # STEPS to build it (discrete, trackable implementation tasks)
```

---

## File 1: requirements.md

### Structure

```markdown
# Requirements — {Agent Name}

## Introduction

{One paragraph: what the agent does, who it's for, and why it matters.}

## Requirements

### Requirement 1: {Short Name}

**User Story:** As a {persona}, I want {goal}, so that {benefit}.

**Acceptance Criteria:**
1. WHEN {condition/event} THE SYSTEM SHALL {expected behavior}
2. WHEN {condition/event} THE SYSTEM SHALL {expected behavior}
3. WHEN {condition/event} THE SYSTEM SHALL {expected behavior}

### Requirement 2: {Short Name}

**User Story:** As a {persona}, I want {goal}, so that {benefit}.

**Acceptance Criteria:**
1. WHEN {condition/event} THE SYSTEM SHALL {expected behavior}
2. WHEN {condition/event} THE SYSTEM SHALL {expected behavior}

{...continue for all requirements}

## Non-Functional Requirements

### Performance
1. THE SYSTEM SHALL {performance requirement}

### Reliability
1. THE SYSTEM SHALL {reliability requirement}

### Cost
1. THE SYSTEM SHALL {cost requirement}

### Security
1. THE SYSTEM SHALL {security requirement}
```

### EARS Notation Rules

EARS (Easy Approach to Requirements Syntax) uses these patterns:

| Pattern | Template | Use When |
|---------|----------|----------|
| **Ubiquitous** | THE SYSTEM SHALL {behavior} | Always true, no condition |
| **Event-driven** | WHEN {event} THE SYSTEM SHALL {behavior} | Triggered by an event |
| **State-driven** | WHILE {state} THE SYSTEM SHALL {behavior} | Behavior during a state |
| **Optional** | WHERE {feature included} THE SYSTEM SHALL {behavior} | Configurable feature |
| **Unwanted** | IF {condition} THEN THE SYSTEM SHALL {behavior} | Error/edge case handling |

### Guidelines for Writing Requirements

- Each requirement maps to ONE user story
- Acceptance criteria are testable — you can write a test for each one
- Use concrete values, not vague language ("within 60 seconds" not "quickly")
- Include edge cases and error scenarios as acceptance criteria
- Include non-functional requirements (performance, cost, security) separately
- Number everything for traceability (tasks will reference requirement numbers)

---

## File 2: design.md

### Structure

```markdown
# Design — {Agent Name}

## Overview

{2-3 sentences: high-level architecture and key design decisions.}

## Architecture

### System Diagram

{Mermaid diagram showing components and their relationships}

### Components

#### {Component 1 Name}
- **Purpose:** {what it does}
- **Type:** {LLM node / pure function / external API / database}
- **Inputs:** {what it receives}
- **Outputs:** {what it produces}
- **Error handling:** {how failures are managed}

#### {Component 2 Name}
{...same structure}

### Data Flow

{Mermaid sequence diagram showing how data moves through the system}

## Data Model

### State Schema

{TypeScript interfaces or equivalent defining the agent's state}

### Database Schema

{If persistent storage is needed — tables, indexes, relationships}

## Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| {layer} | {tech} | {why} |

## API Integrations

### {API Name}
- **Purpose:** {why it's needed}
- **Auth:** {OAuth2 / API key / etc.}
- **Key endpoints:** {which ones the agent uses}
- **Rate limits:** {known constraints}
- **Error handling:** {retry strategy}

## LLM Prompts

### {Prompt Name}
- **Used by:** {which component}
- **Model:** {which LLM}
- **Temperature:** {value and why}
- **System prompt:** {the actual prompt text}
- **Expected output format:** {JSON schema or example}

## Guardrails & Risk Matrix

| Action | Risk Level | Guardrail |
|--------|-----------|-----------|
| {action} | {read-only/low/medium/high/irreversible} | {mitigation} |

## Cost Estimate

| Operation | Volume/Day | Tokens/Call | Daily Cost |
|-----------|-----------|-------------|------------|
| {operation} | {count} | {tokens} | {cost} |
```

### Guidelines for Design Docs

- Include Mermaid diagrams where they aid understanding (system architecture, sequence diagrams, state machines)
- Define every LLM prompt in full — these are the agent's brain
- Be explicit about error handling for every external dependency
- Include the guardrails/risk matrix — classify every action
- Include cost estimates based on expected volume

---

## File 3: tasks.md

### Structure

```markdown
# Tasks — {Agent Name}

## Implementation Plan

Tasks are organized by phase and ordered by dependency. Each task is discrete, testable, and maps to specific requirements.

### Phase 1: {Phase Name}

- [ ] **Task 1.1:** {Clear description of what to build}
  - **Requirement:** REQ-{n}
  - **Details:** {Implementation specifics, key decisions}
  - **Acceptance:** {How to verify this task is done}
  - [ ] Sub-task 1.1.1: {Specific step}
  - [ ] Sub-task 1.1.2: {Specific step}
  - [ ] Sub-task 1.1.3: {Specific step}

- [ ] **Task 1.2:** {Clear description}
  - **Requirement:** REQ-{n}
  - **Details:** {Implementation specifics}
  - **Acceptance:** {Verification criteria}
  - [ ] Sub-task 1.2.1: {Specific step}
  - [ ] Sub-task 1.2.2: {Specific step}

### Phase 2: {Phase Name}

- [ ] **Task 2.1:** {Clear description}
  - **Requirement:** REQ-{n}
  - **Depends on:** Task 1.1, Task 1.2
  - **Details:** {Implementation specifics}
  - **Acceptance:** {Verification criteria}
  - [ ] Sub-task 2.1.1: {Specific step}

{...continue for all phases and tasks}

### Phase N: Evaluation & Deployment

- [ ] **Task N.1:** Build eval pipeline
- [ ] **Task N.2:** Run shadow mode (3+ days)
- [ ] **Task N.3:** Set up monitoring and alerting
- [ ] **Task N.4:** Deploy to production
- [ ] **Task N.5:** Set up feedback collection
```

### Guidelines for Tasks

- Every task maps to a requirement (traceability)
- Tasks are ordered by dependency — each task only depends on tasks above it
- Each task has clear acceptance criteria (how do you know it's done?)
- Sub-tasks are concrete coding steps, not abstract concepts
- Include evaluation and deployment as explicit tasks (don't let them be afterthoughts)
- Tasks should be sized for 1-4 hours of work each
- Always include: eval pipeline, shadow mode, monitoring, deployment as final-phase tasks

### Task Phases Should Follow the Build Playbook

| Phase | Maps to Playbook Phase | Focus |
|-------|----------------------|-------|
| Phase 1: Foundation | Phase 3 (Dev) | Project setup, data source connection, basic types |
| Phase 2: Core Logic | Phase 3 (Dev) | LLM nodes, processing pipeline, storage |
| Phase 3: Integration | Phase 3 (Dev) | Wire components together, end-to-end flow |
| Phase 4: Output & Delivery | Phase 3 (Dev) | Output formatting, delivery channels |
| Phase 5: Evaluation | Phase 4 (Eval) | Test dataset, eval pipeline, metrics, prompt tuning |
| Phase 6: Deployment | Phase 5 (Deploy) | Docker, monitoring, alerting, go-live |
| Phase 7: Feedback | Phase 6 (Iterate) | Feedback collection, iteration process |

---

## Using the Output

### In Kiro IDE
1. Copy the three files to `.kiro/specs/{agent-name}/`
2. Open Kiro, navigate to Specs panel
3. Use `#spec:{agent-name}` to reference the spec in conversations
4. Click "Start Task" on any task to begin implementation

### In Claude Code
1. Copy the three files to project root or `.claude/specs/{agent-name}/`
2. Reference in CLAUDE.md: "Read specs in .claude/specs/ for project context"
3. Use commands like: `claude -p "Read design.md and implement Task 2.1 from tasks.md"`
4. Or use `cc-sdd` / `claude-code-spec-workflow` for automated execution

### In Claude.ai Projects
The spec files can also be uploaded as knowledge files to a project-specific Claude.ai Project for interactive guidance during implementation.
