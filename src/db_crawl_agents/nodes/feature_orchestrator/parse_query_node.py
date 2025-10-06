from __future__ import annotations
from typing import Dict, Any
# from ..schema import UserQuery
from ...contracts.feature_orchestrator.feature_orchestrator import UserQuery
from ...utils.feature_orchestrator.LLMAdapter import RunnableLLMAdapter
def parse_query_node(llm:RunnableLLMAdapter, query: UserQuery) -> Dict[str, Any]:
    """
    Normalize/clarify the raw user query into a structured 'intents' string.
    This is a light pre-step before proposing features.
    """
    system = llm.render_system("parse")
    msg = f"""User query:
{query.text}

Please provide a normalized summary of the analytical intent (2–4 sentences)."""
    analysis = llm.generate(system=system, prompt=msg)
    return {"intents": analysis.strip()}