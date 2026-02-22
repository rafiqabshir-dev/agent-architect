from dotenv import load_dotenv
load_dotenv()

import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from anthropic import Anthropic
from pydantic import BaseModel
from lib.prompts import system_prompt
from lib.tools import tools
from lib.rag import get_relevant_knowledge
from lib.guardrails import validate_input, validate_output
from lib.models import get_model
from lib.stream_parser import RawJsonStreamParser


class GenerateRequest(BaseModel):
    query: str


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
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


def format_sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@app.post("/generate-stream")
async def create_stream_request(request: GenerateRequest):
    query = request.query

    def event_generator():
        input_error = validate_input(query)
        if input_error is not None:
            yield format_sse({"type": "error", "message": input_error})
            return

        # Emit each progress step BEFORE the slow work so the user sees it right away
        yield format_sse({"type": "progress", "step": "retrieving"})

        relevant_knowledge = get_relevant_knowledge(query)
        knowledge_text = "\n\n".join([chunk["text"] for chunk in relevant_knowledge])
        full_system_prompt = system_prompt.replace("{context}", knowledge_text)

        yield format_sse({"type": "progress", "step": "validating"})

        validation_err = validate_idea(query=query, full_system_prompt=full_system_prompt)
        if validation_err is not None:
            yield format_sse({"type": "error", "message": f"Idea not suitable for an agent: {validation_err}"})
            return

        yield format_sse({"type": "progress", "step": "generating"})

        # Phase 1: Thinking — stream Claude's reasoning about the architecture
        try:
            with anthropic_client.messages.stream(
                model=get_model("generate"),
                system=full_system_prompt,
                max_tokens=4096,
                messages=get_user_message(content=query),
                thinking={"type": "enabled", "budget_tokens": 3072},
            ) as thinking_stream:
                for event in thinking_stream:
                    event_type = getattr(event, "type", None)
                    if event_type == "thinking":
                        yield format_sse({"type": "thinking", "content": event.thinking})
                    elif event_type == "text":
                        yield format_sse({"type": "thinking", "content": event.text})
        except Exception as e:
            yield format_sse({"type": "error", "message": str(e)})
            return

        # Phase 2: Spec generation — forced tool call, token-by-token streaming
        parser = RawJsonStreamParser()

        try:
            with anthropic_client.messages.stream(
                model=get_model("generate"),
                system=full_system_prompt,
                max_tokens=8192,
                tools=tools,
                messages=get_user_message(content=query),
                tool_choice={"type": "tool", "name": "generate_spec"},
            ) as spec_stream:
                for event in spec_stream:
                    event_type = getattr(event, "type", None)
                    if event_type == "input_json":
                        deltas = parser.feed(event.partial_json)
                        for field, content in deltas:
                            yield format_sse({"type": "delta", "field": field, "content": content})

                response = spec_stream.get_final_message()

            # Validate the final output
            tool_block = next(
                (block for block in response.content if block.type == "tool_use" and block.name == "generate_spec"),
                None,
            )
            if tool_block is None:
                yield format_sse({"type": "error", "message": "Unexpected response from model."})
                return

            specs = tool_block.input
            output_error = validate_output(specs)
            if output_error is not None:
                yield format_sse({"type": "error", "message": output_error})
                return

            yield format_sse({"type": "done"})

        except Exception as e:
            yield format_sse({"type": "error", "message": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
