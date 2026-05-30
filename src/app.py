"""Streamlit demo UI for the transaction chatbot.

Run with:
    streamlit run src/app.py

Customer is selected from a dropdown — in production this would come
from the authenticated session, not a picker.
"""
from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

load_dotenv()

from src import data
from src.agent import build_agent, initial_system_message
from src.guardrails import check_input, check_output

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Lloyds Transaction Chatbot", page_icon="src/images/logo.png", layout="centered")

logo_col, title_col = st.columns([1, 5], vertical_alignment="center")
with logo_col:
    st.image("src/images/logo.png", width=50)
with title_col:
    st.title("Lloyds Transaction Assistant")
st.caption("Ask about your balance, recent transactions, or charges you don't recognise.")

# ---------------------------------------------------------------------------
# Sidebar — customer picker + reset
# ---------------------------------------------------------------------------
customers = data.list_customers()
customer_labels = {f"{c['customer_name']} ({c['customer_id']})": c for c in customers}

with st.sidebar:
    st.subheader("Demo session")
    selected_label = st.selectbox("Logged in as:", list(customer_labels.keys()))
    selected_customer = customer_labels[selected_label]

    st.markdown("---")
    st.markdown(
        "**Try asking:**\n"
        "- What's my balance?\n"
        "- Show me my recent transactions\n"
        "- How much did I spend on groceries?\n"
        "- Are there any charges I might not recognise?"
    )

    st.markdown("---")
    if st.button("🔄 Reset conversation"):
        st.session_state.pop("messages", None)
        st.session_state.pop("customer_id", None)
        st.rerun()

    if not os.getenv("OPENAI_API_KEY"):
        st.warning("⚠️ OPENAI_API_KEY not set. Set it in your environment to run the agent.")

# ---------------------------------------------------------------------------
# Session state — reset if customer changes
# ---------------------------------------------------------------------------
if st.session_state.get("customer_id") != selected_customer["customer_id"]:
    st.session_state["customer_id"] = selected_customer["customer_id"]
    st.session_state["messages"] = [
        initial_system_message(
            customer_id=selected_customer["customer_id"],
            customer_name=selected_customer["customer_name"],
        )
    ]

# ---------------------------------------------------------------------------
# Render conversation
# ---------------------------------------------------------------------------
for msg in st.session_state["messages"]:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.markdown(msg.content)
    elif isinstance(msg, AIMessage) and msg.content:
        with st.chat_message("assistant"):
            st.markdown(msg.content)
    elif isinstance(msg, ToolMessage):
        with st.chat_message("assistant"):
            with st.expander(f"🔧 tool result: {msg.name}", expanded=False):
                st.code(msg.content, language="json")

# ---------------------------------------------------------------------------
# Input box
# ---------------------------------------------------------------------------
user_input = st.chat_input("Ask about your balance or transactions…")

if user_input:
    # 1. Show user message
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state["messages"].append(HumanMessage(content=user_input))

    # 2. Input guardrails
    guard = check_input(user_input)
    if not guard["ok"]:
        with st.chat_message("assistant"):
            st.markdown(guard["reason"])
        st.session_state["messages"].append(AIMessage(content=guard["reason"]))
        st.stop()

    # 3. Run the agent
    with st.spinner("Thinking…"):
        try:
            agent = build_agent()
            result = agent.invoke({"messages": st.session_state["messages"]})

            # Append every new message from the agent run (tool calls + final reply).
            new_messages = result["messages"][len(st.session_state["messages"]):]
            st.session_state["messages"].extend(new_messages)

            # 4. Output guardrails on the final assistant message
            final = result["messages"][-1]
            if isinstance(final, AIMessage) and final.content:
                safe_text = check_output(final.content)
                # Overwrite the final message with the redacted version
                st.session_state["messages"][-1] = AIMessage(content=safe_text)

        except Exception as e:  # noqa: BLE001 — PoC-level handling
            err = f"Sorry, something went wrong: `{e}`"
            with st.chat_message("assistant"):
                st.markdown(err)
            st.session_state["messages"].append(AIMessage(content=err))
            st.stop()

    st.rerun()
