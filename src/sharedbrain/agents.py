"""Construcción común de agentes LLM."""

from __future__ import annotations

from typing import Any

from pydantic_ai import Agent, PromptedOutput


def build_agent(model: str, output_type: type, system_prompt: str) -> Agent[Any, Any]:
    """Crea un agente con salida estructurada compatible con el proveedor."""
    # ToolOutput fuerza tool_choice=required; algunos modelos/rutas de OpenRouter
    # no lo soportan. PromptedOutput conserva validación Pydantic sin usar tools.
    output = PromptedOutput(output_type) if model.startswith("openrouter:") else output_type
    return Agent(model, output_type=output, system_prompt=system_prompt)
