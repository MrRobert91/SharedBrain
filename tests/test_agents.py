from unittest.mock import patch

from pydantic import BaseModel
from pydantic_ai import PromptedOutput

from sharedbrain.agents import build_agent


class ExampleOutput(BaseModel):
    value: str


def test_openrouter_uses_prompted_output():
    with patch("sharedbrain.agents.Agent") as agent:
        build_agent("openrouter:minimax/minimax-m3", ExampleOutput, "system")

    output_type = agent.call_args.kwargs["output_type"]
    assert isinstance(output_type, PromptedOutput)
    assert output_type.outputs is ExampleOutput


def test_direct_providers_keep_tool_output():
    with patch("sharedbrain.agents.Agent") as agent:
        build_agent("anthropic:claude-fable-5", ExampleOutput, "system")

    assert agent.call_args.kwargs["output_type"] is ExampleOutput
