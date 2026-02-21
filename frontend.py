"""
frontend.py — Streamlit UI for the AI Agent Platform
Run with: streamlit run frontend.py
Requires: pip install streamlit requests
"""

import requests
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="AI Agent Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    /* ── 1. Hide default sidebar and collapse toggle ── */
    [data-testid="stSidebar"]        { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }

    /* ── 2. Push content below the native Streamlit top toolbar ── */
    .block-container {
        padding-top: 3.5rem !important;
        padding-bottom: 0.5rem !important;
        max-width: 100% !important;
    }

    /* ── 3. Blue chat header bar ── */
    .chat-header {
        background: linear-gradient(90deg, #1a73e8, #1558b0);
        border-radius: 10px 10px 0 0;
        padding: 10px 18px;
        color: white !important;
        font-weight: 700;
        font-size: 1.05rem;
        margin-bottom: 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* ── 4. Green "Create Agent" submit button (Bootstrap btn-success) ── */
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #28a745 !important;
        border-color:     #28a745 !important;
        color: white !important;
        border-radius: 6px;
        font-weight: 600;
        width: 100%;
        transition: background-color 0.2s;
    }
    div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #218838 !important;
        border-color:     #1e7e34 !important;
    }

    /* ── 5. Tighten vertical spacing inside columns ── */
    div[data-testid="stVerticalBlock"] > div { gap: 0.35rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# Session State Initialisation
# ─────────────────────────────────────────────────────────────────────────────

defaults = {
    "current_agent_id":     None,
    "current_agent_name":   "No Agent Selected",
    "current_session_id":   None,
    "sessions_list":        [],      # list of {"id": ..., "label": ...}
    "last_audio_bytes":     None,
    "processed_audio_hash": None,    # prevents re-sending the same recording
    "editing_agent":        None,    # dict of agent being edited {id, name, prompt}
}
for key, val in defaults.items():
    st.session_state.setdefault(key, val)

# ─────────────────────────────────────────────────────────────────────────────
# API Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def api(method: str, path: str, **kwargs):
    """Generic API caller with error toast."""
    try:
        r = requests.request(method, f"{API_BASE}{path}", timeout=60, **kwargs)
        r.raise_for_status()
        return r
    except Exception as exc:
        st.toast(f"❌ API error: {exc}", icon="🚨")
        return None

def api_json(method, path, **kwargs):
    r = api(method, path, **kwargs)
    return r.json() if r else None

# ─────────────────────────────────────────────────────────────────────────────
# Main Layout (two columns)
# ─────────────────────────────────────────────────────────────────────────────

left_col, right_col = st.columns([1, 2.5], gap="large")

# ╔══════════════════════════════════════════════════════════╗
# ║                    LEFT — Agents                        ║
# ╚══════════════════════════════════════════════════════════╝
with left_col:
    st.markdown("### 🤖 Agents")
    agents = api_json("GET", "/agents") or []

    # ── Agent List ────────────────────────────────────────────────────
    with st.container(border=True):
        if not agents:
            st.caption("No agents yet. Create one below.")
        for agent in agents:
            is_selected = (st.session_state.current_agent_id == agent["id"])
            a_col, b_col = st.columns([4, 1])
            with a_col:
                if st.button(
                    agent["name"],
                    key=f"sel_{agent['id']}",
                    type="primary" if is_selected else "secondary",
                    use_container_width=True,
                ):
                    if st.session_state.current_agent_id != agent["id"]:
                        st.session_state.current_agent_id   = agent["id"]
                        st.session_state.current_agent_name = agent["name"]
                        st.session_state.current_session_id = None
                        st.session_state.sessions_list      = []
                        st.session_state.last_audio_bytes   = None
                        st.session_state.editing_agent      = None
                    st.rerun()
            with b_col:
                # ── Edit button: populates the edit form below ────────
                if st.button("✏️", key=f"edit_{agent['id']}", help="Edit this agent"):
                    st.session_state.editing_agent = {
                        "id":     agent["id"],
                        "name":   agent["name"],
                        "prompt": agent["prompt"],
                    }
                    st.rerun()

    # ── Edit Agent Form (shown when ✏️ clicked) ────────────────────────
    if st.session_state.editing_agent:
        ea = st.session_state.editing_agent
        with st.container(border=True):
            st.markdown(f"**✏️ Edit — {ea['name']}**")
            with st.form("edit_agent_form", clear_on_submit=False):
                edit_name   = st.text_input("Agent Name",    value=ea["name"])
                edit_prompt = st.text_area( "System Prompt", value=ea["prompt"], height=110)
                c1, c2 = st.columns(2)
                save    = c1.form_submit_button("💾 Save",   use_container_width=True)
                cancel  = c2.form_submit_button("✖ Cancel", use_container_width=True)

                if save:
                    if not edit_name.strip() or not edit_prompt.strip():
                        st.warning("Name and prompt cannot be empty.")
                    else:
                        res = api_json(
                            "PUT", f"/agents/{ea['id']}",
                            json={"name": edit_name.strip(), "prompt": edit_prompt.strip()},
                        )
                        if res:
                            # Update selected name if this was the active agent
                            if st.session_state.current_agent_id == ea["id"]:
                                st.session_state.current_agent_name = res["name"]
                            st.session_state.editing_agent = None
                            st.success("✅ Agent updated!")
                            st.rerun()
                if cancel:
                    st.session_state.editing_agent = None
                    st.rerun()

    # ── Create Agent Form ─────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("**➕ New Agent**")
        with st.form("create_agent_form", clear_on_submit=True):
            new_name   = st.text_input("Agent Name",    placeholder="e.g. Support Bot")
            new_prompt = st.text_area( "System Prompt", placeholder="You are a helpful assistant...", height=110)
            if st.form_submit_button("Create Agent"):
                if not new_name.strip() or not new_prompt.strip():
                    st.warning("Name and prompt are required.")
                else:
                    res = api_json("POST", "/agents", json={"name": new_name.strip(), "prompt": new_prompt.strip()})
                    if res:
                        st.success(f"✅ '{res['name']}' created!")
                        st.rerun()


# ╔══════════════════════════════════════════════════════════╗
# ║                  RIGHT — Chat Interface                 ║
# ╚══════════════════════════════════════════════════════════╝
with right_col:

    # ── Blue header ────────────────────────────────────────────────────
    st.markdown(
        f'<div class="chat-header">🤖 {st.session_state.current_agent_name}</div>',
        unsafe_allow_html=True,
    )

    # ── Session selector + New Chat row ───────────────────────────────
    sess_col, new_col = st.columns([4, 1])

    with sess_col:
        session_ids    = [s["id"]    for s in st.session_state.sessions_list]
        session_labels = [s["label"] for s in st.session_state.sessions_list]

        if session_ids:
            cur = st.session_state.current_session_id
            idx = session_ids.index(cur) if cur in session_ids else 0
            chosen_label = st.selectbox(
                "Session", session_labels, index=idx,
                key="session_selector", label_visibility="collapsed",
            )
            chosen_id = session_ids[session_labels.index(chosen_label)]
            if chosen_id != st.session_state.current_session_id:
                st.session_state.current_session_id = chosen_id
                st.session_state.last_audio_bytes   = None
                st.rerun()
        else:
            st.caption("No sessions — click ＋ New Chat to start")

    with new_col:
        if st.button(
            "＋ New Chat",
            key="new_chat_btn",
            type="primary",
            disabled=(st.session_state.current_agent_id is None),
            use_container_width=True,
        ):
            res = api_json("POST", "/sessions", json={"agent_id": st.session_state.current_agent_id})
            if res:
                n = len(st.session_state.sessions_list) + 1
                st.session_state.sessions_list.append({"id": res["id"], "label": f"Session {n}"})
                st.session_state.current_session_id = res["id"]
                st.session_state.last_audio_bytes   = None
                st.rerun()

    st.divider()

    # ── Scrollable Chat History ────────────────────────────────────────
    with st.container(height=450, border=True):
        if st.session_state.current_session_id:
            session_data = api_json("GET", f"/sessions/{st.session_state.current_session_id}")
            messages = (session_data or {}).get("messages", [])

            if not messages:
                st.markdown(
                    "<p style='color:#888;text-align:center;margin-top:60px;'>"
                    "No messages yet — type or record below ⬇️</p>",
                    unsafe_allow_html=True,
                )
            else:
                for msg in messages:
                    if msg["role"] == "system":
                        continue
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

            # Auto-play last TTS audio response
            if st.session_state.last_audio_bytes:
                st.audio(st.session_state.last_audio_bytes, format="audio/mpeg", autoplay=True)
                st.session_state.last_audio_bytes = None
        else:
            hint = (
                "Click **＋ New Chat** to start a conversation."
                if st.session_state.current_agent_id
                else "👈 Select or create an agent first."
            )
            st.markdown(
                f"<p style='color:#888;text-align:center;margin-top:60px;'>{hint}</p>",
                unsafe_allow_html=True,
            )

    # ── Input Row ──────────────────────────────────────────────────────
    text_col, voice_col = st.columns([5, 1])

    with text_col:
        user_text = st.chat_input(
            "Type a message...",
            disabled=(st.session_state.current_session_id is None),
        )

    with voice_col:
        voice_input = st.audio_input(
            "🎙️",
            key="voice_recorder",
            disabled=(st.session_state.current_session_id is None),
        )

    # ── Handle Text Message ────────────────────────────────────────────
    if user_text and st.session_state.current_session_id:
        with st.spinner("Thinking…"):
            api_json(
                "POST", "/messages/text",
                json={"session_id": st.session_state.current_session_id, "content": user_text},
            )
        st.session_state.last_audio_bytes = None
        st.rerun()

    # ── Handle Voice Message (hash-guarded against re-runs) ───────────
    if voice_input is not None and st.session_state.current_session_id:
        audio_bytes = voice_input.read()
        if audio_bytes:
            audio_hash = hash(audio_bytes)
            if audio_hash != st.session_state.processed_audio_hash:
                st.session_state.processed_audio_hash = audio_hash
                with st.spinner("Transcribing & generating response…"):
                    r = api(
                        "POST", "/messages/voice",
                        params={"session_id": st.session_state.current_session_id},
                        files={"audio": ("recording.wav", audio_bytes, "audio/wav")},
                    )
                if r and r.content:
                    st.session_state.last_audio_bytes = r.content
                st.rerun()
