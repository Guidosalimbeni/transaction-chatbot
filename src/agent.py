"""LangGraph agent.

A classic ReAct-style loop:
  llm node -> (if tool calls) -> tool node -> back to llm -> ... -> END

Uses an OpenAI-compatible client so the same code works against OpenAI,
Groq, Ollama, Azure OpenAI, etc. by just changing OPENAI_BASE_URL.
"""
from __future__ import annotations

import os
from typing import Annotated, TypedDict
from datetime import date
from langchain_core.messages import AnyMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from .tools import ALL_TOOLS

# ---------------------------------------------------------------------------
# System prompt — defines the agent's role and the hard rules of the MVP.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a helpful banking assistant for Lloyds customers.

Your job is strictly limited to three things:
  1. Telling the customer their current balance.
  2. Browsing their transaction history.
  3. Helping them identify charges they don't recognise.

Hard rules:
  - You ALWAYS use the provided tools to fetch data. NEVER invent figures.
  - For ANY question involving sums, totals, averages, counts, or
    breakdowns (e.g. 'how much did I spend on X', 'spend per merchant',
    'monthly totals') — call summarise_spending. NEVER add up
    transactions yourself; banking arithmetic must be deterministic.
  - You NEVER give financial, tax, or investment advice.
  - You NEVER discuss other products (mortgages, loans, insurance).
  - If asked to do anything other than the three jobs above, politely
    decline and suggest they contact a human agent through the app.
  - The customer_id for this session is provided in the first system
    message. Use it for every tool call.
  - Be concise. Customers want quick answers, not essays.
  - When showing transactions, format them clearly: date, merchant, amount.
  - When the user asks about unfamiliar charges, call find_unfamiliar_charges
    and, for each one, explain what the cryptic description probably means
    (e.g. 'SP*' usually indicates a Squarespace subscription, 'CRYPTO*' is
    a cryptocurrency exchange). Be honest when you're uncertain.
"""


class AgentState(TypedDict):
    """State passed between graph nodes. `add_messages` appends rather than overwriting."""
    messages: Annotated[list[AnyMessage], add_messages]


def _make_llm() -> ChatOpenAI:
    """Build the LLM client. Reads config from env vars so the reviewer
    can swap providers without changing code."""
    return ChatOpenAI(
        model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0,
    ).bind_tools(ALL_TOOLS)


def _call_llm(state: AgentState) -> dict:
    """LLM node: send the conversation to the model, return its response."""
    llm = _make_llm()
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


def _should_continue(state: AgentState) -> str:
    """Conditional edge: if the LLM asked for a tool, run it; else END."""
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return END


def build_agent():
    """Compile and return the agent graph."""
    graph = StateGraph(AgentState)
    graph.add_node("llm", _call_llm)
    graph.add_node("tools", ToolNode(ALL_TOOLS))
    graph.set_entry_point("llm")
    graph.add_conditional_edges("llm", _should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "llm")
    return graph.compile()


def initial_system_message(customer_id: str, customer_name: str) -> SystemMessage:
    """Builds the system message that anchors the conversation to a customer."""
    today = date.today().isoformat()
    return SystemMessage(
        content=(
            f"{SYSTEM_PROMPT}\n\n"
            f"Today's date is: {today}\n"
            f"The customer for this session is:\n"
            f"  customer_id: {customer_id}\n"
            f"  customer_name: {customer_name}\n"
        )
    )
