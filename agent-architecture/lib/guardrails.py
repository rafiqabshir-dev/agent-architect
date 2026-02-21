def validate_input(query):
    if len(query) < 10:
        return "Query is too short. Please describe your agent idea in more detail."
    if len(query) > 800:
        return "Query is too long. Please keep your description under 800 characters."
    return None


def validate_output(output):
    if not output:
        return "No response generated. Please try again."
    if "requirements" not in output or "design" not in output or "tasks" not in output:
        return "Missing spec files. Expected requirements, design, and tasks."
    if len(output["requirements"]) < 100 or len(output["design"]) < 100 or len(output["tasks"]) < 100:
        return "Spec files are too short. Please provide a more detailed description."
    return None
