from __future__ import annotations
from typing import Optional, Dict, Any
from langgraph.graph import StateGraph, END
# from .schema import UserQuery, Feedback
from ..contracts.feature_orchestrator.feature_orchestrator import UserQuery, Feedback
from ..contracts.feature_orchestrator.orchestrator_state import OrchestratorState
from ..nodes.feature_orchestrator.parse_query_node import parse_query_node
from ..nodes.feature_orchestrator.propose_features import propose_features_node
from ..nodes.feature_orchestrator.refine_with_feedback import refine_with_feedback_node
from ..nodes.feature_orchestrator.finalize_features import finalize_node
from ..nodes.feature_orchestrator.memory import OrchestratorMemory
from ..utils.feature_orchestrator.LLMAdapter import RunnableLLMAdapter

PARSE = "parse_query"
PROPOSE = "propose_features"
REFINE = "refine_with_feedback"
FINALIZE = "finalize_features"
DECIDE_AFTER_PROPOSE = "decide_after_propose"   # router
DECIDE_AFTER_REFINE  = "decide_after_refine"    # router
class OrchestratorGraph:
    def __init__(self, llm: RunnableLLMAdapter, max_features: int = 5):
        self.llm = llm
        self.max_features = max_features
        self.mem = OrchestratorMemory()
        self.graph = self._build_graph()

    # ---- node wrappers (pure functions over state) ----
    def _parse_node(self, state: OrchestratorState) -> OrchestratorState:
        query = state["query"]
        self.mem.save_query(query)
        parsed = parse_query_node(self.llm, query)  # {"intents": str}
        return {"intents": parsed["intents"]}

    def _propose_node(self, state: OrchestratorState) -> OrchestratorState:
        intents = state["intents"]
        draft = propose_features_node(self.llm, intents, max_features=self.max_features)
        self.mem.save_draft(draft)
        return {"draft": draft}

    def _refine_node(self, state: OrchestratorState) -> OrchestratorState:
        draft = state["draft"]
        feedback = state.get("feedback")
        if not feedback:
            return {}
        new_draft = refine_with_feedback_node(self.llm, draft, feedback, max_features=self.max_features)
        self.mem.save_draft(new_draft)
        return {"draft": new_draft}

    def _finalize_node(self, state: OrchestratorState) -> OrchestratorState:
        draft = state["draft"]
        final = finalize_node(self.llm, draft, max_features=self.max_features)
        self.mem.save_final(final)
        return {"finalized": final, "stage": "final"}

    
    # ---- routers (conditional edges) ----
    def _decide_after_propose(self, state: OrchestratorState) -> str:
        """After propose, choose refine or finalize/draft return."""
        if state.get("feedback"):
            return REFINE
        if state.get("finalize_flag", True):
            return FINALIZE
        # draft only
        return END

    def _decide_after_refine(self, state: OrchestratorState) -> str:
        """After refine, choose finalize or stop at draft."""
        if state.get("finalize_flag", True):
            return FINALIZE
        return END
    
    def _build_graph(self):
        g = StateGraph(OrchestratorState)

        # register nodes
        g.add_node(PARSE, self._parse_node)
        g.add_node(PROPOSE, self._propose_node)
        g.add_node(REFINE, self._refine_node)
        g.add_node(FINALIZE, self._finalize_node)

        g.set_entry_point(PARSE)
        g.add_edge(PARSE, PROPOSE)
        
        g.add_conditional_edges(
            PROPOSE,
            self._decide_after_propose,
            {
                REFINE: REFINE,
                FINALIZE: FINALIZE,
                END: END,
            },
        )

        g.add_conditional_edges(
            REFINE,
            self._decide_after_refine,
            {
                FINALIZE: FINALIZE,
                END: END,
            },
        )

        g.add_edge(FINALIZE, END)

        return g.compile()
    
    # ---- public API: keep same signature as before ----
    def run(
        self,
        query: UserQuery,
        feedback: Optional[Feedback] = None,
        finalize: bool = True,
    ) -> Dict[str, Any]:
        # seed initial state
        initial: OrchestratorState = {
            "query": query,
            "feedback": feedback,
            "finalize_flag": finalize,
            "stage": "draft",  # default; will become 'final' if finalized
        }
        out = self.graph.invoke(initial)

        # shape response to match your previous run() contract
        if out.get("stage") == "final":
            return {
                "stage": "final",
                "draft": out.get("draft").model_dump() if out.get("draft") else None,
                "finalized": out.get("finalized").model_dump(),
            }
        return {
            "stage": "draft",
            "draft": out.get("draft").model_dump() if out.get("draft") else None,
        }
