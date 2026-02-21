tools = [
    {
        "name": "validate_agent_idea",
        "description": "Validate whether the user's idea is suitable to be built as an AI agent or if it can be achieved with a simple script. If suitable for an agent, determine whether it should be a single-agent or multi-agent system.",
        "input_schema": {
            "type": "object",
            "properties": {
                "is_suitable_for_agent": {
                    "type": "boolean",
                    "description": "Whether the idea requires an AI agent (True) or can be solved with a simple script (False)",
                },
                "agent_type": {
                    "type": "string",
                    "description": "The recommended system type based on the idea's complexity and requirements",
                    "enum": ["script", "single-agent", "multi-agent"],
                },
                "reasoning": {
                    "type": "string",
                    "description": "Explanation of why this classification was chosen",
                },
            },
            "required": ["is_suitable_for_agent", "agent_type", "reasoning"],
        },
    },
    {
        "name": "select_architecture",
        "description": "Select the best architecture pattern for the user's agent based on their requirements. Use after validate_agent_idea confirms the idea is viable.",
        "input_schema": {
            "type": "object",
            "properties": {
                "complexity": {
                    "type": "string",
                    "enum": ["simple", "moderate", "complex"],
                    "description": "How complex the agent's task is",
                },
                "needs_determinism": {
                    "type": "boolean",
                    "description": "Whether the agent needs predictable, repeatable behavior",
                },
                "parallel_subtasks": {
                    "type": "boolean",
                    "description": "Whether the agent has independent subtasks that can run simultaneously",
                },
                "reasoning": {
                    "type": "string",
                    "description": "Explanation of the architecture decisions for complexity, determinism, and parallelism",
                },
            },
            "required": ["complexity", "needs_determinism", "reasoning"],
        },
    },
    {
        "name": "generate_spec",
        "description": "Generate the three spec files (requirements.md, design.md, tasks.md) for the user's AI agent, formatted for Kiro IDE and Claude Code compatibility.",
        "input_schema": {
            "type": "object",
            "properties": {
                "requirements": {
                    "type": "string",
                    "description": "The full content of requirements.md including user stories, acceptance criteria in EARS notation, and non-functional requirements",
                },
                "design": {
                    "type": "string",
                    "description": "The full content of design.md including architecture diagrams, components, data flow, technology stack, prompts, and risk matrix",
                },
                "tasks": {
                    "type": "string",
                    "description": "The full content of tasks.md with phased implementation tasks, sub-tasks, dependencies, and acceptance criteria. Tasks must be individually executable in Kiro IDE",
                },
            },
            "required": ["requirements", "design", "tasks"],
        },
    },
]
