import streamlit as st
from openai import OpenAI

from core.config import CASE_CITATION, CASE_NAME
from core.rag import LEVELS, answer

st.set_page_config(page_title="MNR v Cameron — Q&A", page_icon="⚖️")

# ---------- Memory for this browser session ----------
defaults = {
    "authenticated": False,   # has the user entered the right password?
    "stage": "welcome",       # "welcome" page or "chat" page
    "name": "",
    "level": list(LEVELS)[0],
    "exchanges": [],          # each item: {question, answer, level, sources}, oldest first
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def history_before(index):
    """The conversation up to (not including) exchange number `index`, for follow-up questions."""
    history = []
    for ex in st.session_state.exchanges[:index][-3:]:   # last 3 exchanges is plenty
        history.append({"role": "user", "content": ex["question"]})
        history.append({"role": "assistant", "content": ex["answer"]})
    return history


# ---------- Screen 1: password ----------
def password_screen():
    st.title("⚖️ MNR v Cameron — Q&A")
    st.write("This app is password protected.")
    with st.form("password_form"):
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Enter"):
            if password == st.secrets["APP_PASSWORD"]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password.")


# ---------- Screen 2: welcome ----------
def welcome_screen():
    st.title("⚖️ Understand MNR v Cameron")
    st.caption(f"{CASE_NAME} {CASE_CITATION} — Supreme Court of Canada")
    st.write(
        "Ask questions about this tax case in plain language. "
        "Tell us a little about yourself so answers are pitched at the right level."
    )
    with st.form("welcome_form"):
        name = st.text_input("Your name")
        level = st.selectbox("How familiar are you with tax?", list(LEVELS))
        if st.form_submit_button("Start"):
            if not name.strip():
                st.warning("Please enter your name.")
            else:
                st.session_state.name = name.strip()
                st.session_state.level = level
                st.session_state.stage = "chat"
                st.rerun()


# ---------- Screen 3: chat ----------
def chat_screen():
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    st.title(f"Welcome, {st.session_state.name}.")
    st.subheader(f"How can I help you understand *{CASE_NAME}*?")

    # --- The question box, with the level picker directly above it ---
    with st.form("ask_form", clear_on_submit=True):
        level = st.selectbox(
            "Answer level",
            list(LEVELS),
            index=list(LEVELS).index(st.session_state.level),
        )
        question = st.text_input(
            "Your question",
            placeholder="Ask a question about the case...",
            label_visibility="collapsed",
        )
        asked = st.form_submit_button("Ask ➤", type="primary")

    if asked and question.strip():
        st.session_state.level = level   # remember the last level used
        with st.spinner("Reading the judgment..."):
            reply, sources = answer(client, question, level, history_before(len(st.session_state.exchanges)))
        st.session_state.exchanges.append(
            {"question": question, "answer": reply, "level": level, "sources": sources}
        )
        st.rerun()

    # --- Answers, newest first ---
    exchanges = st.session_state.exchanges
    for i in reversed(range(len(exchanges))):
        ex = exchanges[i]
        st.divider()
        with st.chat_message("user"):
            st.markdown(ex["question"])
        with st.chat_message("assistant"):
            st.markdown(ex["answer"])
            st.caption(f"Answered for: {ex['level']}")

            col1, col2 = st.columns(2)
            with col1:
                with st.expander("📄 Sources from the judgment"):
                    for s in ex["sources"]:
                        st.markdown(f"**{s['title']}** · {s['page_label']} · _{s['voice']}_")
                        st.write(s["text"])
            with col2:
                with st.popover("🔄 Re-answer at another level"):
                    other_levels = [l for l in LEVELS if l != ex["level"]]
                    new_level = st.selectbox("Level", other_levels, key=f"regen_level_{i}")
                    if st.button("Re-answer", key=f"regen_button_{i}"):
                        with st.spinner("Rewriting..."):
                            reply, sources = answer(client, ex["question"], new_level, history_before(i))
                        ex.update(answer=reply, level=new_level, sources=sources)
                        st.rerun()


# ---------- Decide which screen to show ----------
if not st.session_state.authenticated:
    password_screen()
elif st.session_state.stage == "welcome":
    welcome_screen()
else:
    chat_screen()