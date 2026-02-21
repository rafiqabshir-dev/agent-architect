def get_model(task_type):
    if task_type == "validate":
        return "claude-haiku-4-5-20251001"
    return "claude-sonnet-4-5-20250929"
