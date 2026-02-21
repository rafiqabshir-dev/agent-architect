from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI
from anthropic import Anthropic
from pydantic import BaseModel
from lib.prompts import system_prompt
from lib.tools import tools
from lib.rag import get_relevant_knowledge
from lib.guardrails import validate_input, validate_output
from lib.models import get_model


class GenerateRequest(BaseModel):
    query: str


app = FastAPI()
anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def get_user_message(content):
    return [{"role": "user", "content": content}]


def create_model_request(messages, full_system_prompt, task_type, tool_choice):
    response = anthropic_client.messages.create(
        model=get_model(task_type),
        system=full_system_prompt,
        max_tokens=8192,
        tools=tools,
        messages=messages,
        tool_choice=tool_choice,
    )
    return response.content


def validate_idea(query, full_system_prompt):
    messages = get_user_message(content=query)
    validation_response = create_model_request(
        messages=messages,
        full_system_prompt=full_system_prompt,
        task_type="validate",
        tool_choice={"type": "tool", "name": "validate_agent_idea"},
    )
    validation_response_input = validation_response[0].input
    if validation_response_input["is_suitable_for_agent"] is True:
        return None
    return validation_response_input["reasoning"]


def generate_spec(query, full_system_prompt):
    response = create_model_request(
        messages=get_user_message(content=query),
        full_system_prompt=full_system_prompt,
        task_type="generate",
        tool_choice={"type": "tool", "name": "generate_spec"},
    )
    if response[0].name == "generate_spec":
        specs = response[0].input
        output_error = validate_output(specs)
        if output_error is not None:
            return {"error": output_error}
        return specs
    return {"error": "Unexpected response from model."}


@app.post("/generate")
def create_request(request: GenerateRequest):
    query = request.query

    input_error = validate_input(query)
    if input_error is not None:
        return {"error": input_error}

    relevant_knowledge = get_relevant_knowledge(query)
    knowledge_text = "\n\n".join([chunk["text"] for chunk in relevant_knowledge])
    full_system_prompt = system_prompt.replace("{context}", knowledge_text)

    validation_err = validate_idea(query=query, full_system_prompt=full_system_prompt)
    if validation_err is not None:
        return {"error": f"Idea not suitable for an agent: {validation_err}"}

    return generate_spec(query=query, full_system_prompt=full_system_prompt)
