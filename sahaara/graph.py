"""LangGraph workflow:
understand -> measure -> context -> triage -> (escalate | clarify | retrieve -> support -> referral -> literacy -> audit)
audit -> finalize | support (one retry) | fallback ; every path ends in the case summary (except clarify).
"""
from langgraph.graph import END, StateGraph

from . import agents as a
from .state import SahaaraState


def build_graph():
    g = StateGraph(SahaaraState)
    g.add_node("understand", a.understanding_agent)
    g.add_node("measure", a.measurement_agent)
    g.add_node("context", a.context_agent)
    g.add_node("triage", a.triage_agent)
    g.add_node("escalate", a.escalation_node)
    g.add_node("clarify", a.clarification_agent)
    g.add_node("retrieve", a.retrieval_agent)
    g.add_node("support", a.support_agent)
    g.add_node("referral", a.referral_agent)
    g.add_node("literacy", a.literacy_agent)
    g.add_node("audit", a.audit_agent)
    g.add_node("finalize", a.finalize_node)
    g.add_node("fallback", a.fallback_node)
    g.add_node("summary", a.summary_agent)

    g.set_entry_point("understand")
    g.add_edge("understand", "measure")
    g.add_edge("measure", "context")
    g.add_edge("context", "triage")
    g.add_conditional_edges("triage", a.route_after_triage,
                            {"escalate": "escalate", "clarify": "clarify", "retrieve": "retrieve"})
    g.add_conditional_edges("clarify", a.route_after_clarify, {"end": END, "retrieve": "retrieve"})
    g.add_edge("retrieve", "support")
    g.add_edge("support", "referral")
    g.add_edge("referral", "literacy")
    g.add_edge("literacy", "audit")
    g.add_conditional_edges("audit", a.route_after_audit,
                            {"finalize": "finalize", "support": "support", "fallback": "fallback"})
    g.add_edge("escalate", "summary")
    g.add_edge("finalize", "summary")
    g.add_edge("fallback", "summary")
    g.add_edge("summary", END)
    return g.compile()
