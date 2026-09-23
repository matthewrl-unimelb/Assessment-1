import streamlit as st
from openai import OpenAI

from core import storage
from core.config import CASE_CITATION, CASE_NAME
from core.rag import LEVELS, answer

# "wide" lets comparison blocks use more of the screen; the CSS below keeps everything else narrow.
# The sidebar starts collapsed so the chat page is clean; open it with the » arrow at the top left.
st.set_page_config(
    page_title="MNR v Cameron — Q&A",
    page_icon=":material/gavel:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------- Memory for this browser session ----------
defaults = {
    "authenticated": False,   # has the user entered the right password?
    "stage": "welcome",       # "welcome" page or "chat" page
    "name": "",
    "level": list(LEVELS)[0],
    # each exchange: {"question": ..., "versions": [{"answer", "level", "sources"}, ...]}, oldest first
    "exchanges": [],
    "show_all": False,        # show every earlier question, or just the latest two?
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---------- Styling ----------
st.markdown(
    """
    <style>
    /* Keep the normal page at a comfortable reading width, centred */
    [data-testid="stMainBlockContainer"], .block-container {
        max-width: 50rem;
        margin: 0 auto;
    }

    /* Sidebar: drag its edge to resize, between 15rem and 26rem wide */
    section[data-testid="stSidebar"][aria-expanded="true"] {
        min-width: 15rem !important;
        max-width: 26rem !important;
    }

    /* While the sidebar is open, always show its collapse («) button, not just on hover */
    section[data-testid="stSidebar"][aria-expanded="true"] [data-testid="stSidebarCollapseButton"],
    section[data-testid="stSidebar"][aria-expanded="true"] [data-testid="stSidebarCollapseButton"] button {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
    }
    /* While it's closed, hide that button completely */
    section[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarCollapseButton"] {
        display: none !important;
    }

    /* The open (») button: pinned to the top-left corner of the screen */
    [data-testid="stExpandSidebarButton"] {
        position: fixed !important;
        top: 0.75rem !important;
        left: 0.75rem !important;
        z-index: 999999;
    }

    /* Comparison blocks break out of the reading width, growing with the number of versions */
    div[class*="st-key-compare"] {
        max-width: none !important;
        position: relative;
        left: 50%;
        transform: translateX(-50%);
    }
    div[class*="st-key-compare2_"] { width: min(94vw, 72rem) !important; }
    div[class*="st-key-compare3_"] { width: min(94vw, 92rem) !important; }
    div[class*="st-key-compare4_"] { width: min(94vw, 110rem) !important; }

    /* Each compared answer is a clean card */
    div[class*="st-key-card"] {
        background: #18293F;
        border: 1px solid rgba(201, 164, 92, 0.35) !important;
        border-radius: 14px;
        padding: 1.1rem 1.2rem;
        height: 100%;
    }

    /* Fade older answers; full brightness on hover */
    div[class*="st-key-older"] { opacity: 0.45; transition: opacity 0.2s ease; }
    div[class*="st-key-older"]:hover { opacity: 1; }

    /* Sidebar buttons: left-aligned text */
    section[data-testid="stSidebar"] button p { text-align: left; }
    </style>
    """,
    unsafe_allow_html=True,
)


def history_before(index):
    """The conversation up to (not including) exchange number `index`, for follow-up questions."""
    history = []
    for ex in st.session_state.exchanges[:index][-3:]:   # last 3 exchanges is plenty
        history.append({"role": "user", "content": ex["question"]})
        history.append({"role": "assistant", "content": ex["versions"][-1]["answer"]})
    return history


def title_folder(client, folder_id):
    """Ask gpt-4o for a short title that sums up everything saved in the folder."""
    questions = [it["question"] for it in storage.folder_items(folder_id)]
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.3,
        messages=[
            {"role": "system", "content": (
                "You name folders of saved notes about the tax case MNR v Cameron. "
                "Given the questions saved in a folder, reply with a short title (2 to 6 words) "
                "that captures their common theme. Title case, no quotation marks, no full stop."
            )},
            {"role": "user", "content": "\n".join(f"- {q}" for q in questions)},
        ],
    )
    title = response.choices[0].message.content.strip().strip('"').strip()
    storage.rename_folder(folder_id, title[:60])
    return title


# ---------- Save-to-folder button (under every answer) ----------
def save_to_folder_button(client, question, v, key):
    user = st.session_state.name
    with st.popover(":material/bookmark_add: Save to folder"):
        folders = storage.list_folders(user)
        options = ["+ New folder"] + [f["title"] for f in folders]
        choice = st.selectbox("Folder", options, key=f"folder_pick_{key}",
                              index=1 if folders else 0)
        if choice == "+ New folder":
            st.caption("The folder will be named automatically from what you save in it.")
        if st.button("Save", key=f"folder_save_{key}", type="primary"):
            if choice == "+ New folder":
                folder_id = storage.create_folder(user)
            else:
                folder_id = folders[options.index(choice) - 1]["id"]
            storage.save_to_folder(folder_id, question, v["level"], v["answer"])
            with st.spinner("Updating folder title..."):
                title = title_folder(client, folder_id)
            st.toast(f"Saved to “{title}”", icon=":material/check:")
            st.rerun()


def show_version(client, question, v, key, show_level_caption=True):
    """Draw one version of an answer: the text, its level, sources and save button."""
    st.markdown(v["answer"])
    if show_level_caption:
        st.caption(f"Answered for: {v['level']}")
    with st.expander(":material/menu_book: Sources from the judgment"):
        for s in v["sources"]:
            st.markdown(f"**{s['title']}** · {s['page_label']} · _{s['voice']}_")
            st.write(s["text"])
    save_to_folder_button(client, question, v, key)


def compare_button(client, i):
    """Popover to generate the same answer at another level."""
    ex = st.session_state.exchanges[i]
    used_levels = [v["level"] for v in ex["versions"]]
    other_levels = [l for l in LEVELS if l not in used_levels]
    if other_levels:
        with st.popover(":material/compare_arrows: Compare with another level"):
            new_level = st.selectbox("Level", other_levels, key=f"regen_level_{i}")
            if st.button("Generate", key=f"regen_button_{i}"):
                with st.spinner("Writing another version..."):
                    reply, sources = answer(client, ex["question"], new_level, history_before(i))
                ex["versions"].append({"answer": reply, "level": new_level, "sources": sources})
                st.rerun()


def show_exchange(client, i):
    """Draw one question and its answer(s). Multiple versions sit side by side in cards."""
    ex = st.session_state.exchanges[i]
    versions = ex["versions"]
    st.divider()
    with st.chat_message("user", avatar=":material/person:"):
        st.markdown(ex["question"])

    if len(versions) == 1:
        # Single answer: normal width
        with st.chat_message("assistant", avatar=":material/gavel:"):
            show_version(client, ex["question"], versions[0], key=f"{i}_0")
            compare_button(client, i)
    else:
        # Several versions: a block that widens with the number of cards
        with st.container(key=f"compare{len(versions)}_{i}"):
            columns = st.columns(len(versions), gap="medium")
            for j, (col, v) in enumerate(zip(columns, versions)):
                with col:
                    with st.container(key=f"card_{i}_{j}"):
                        st.markdown(f"#### {v['level']}")
                        show_version(client, ex["question"], v, key=f"{i}_{j}", show_level_caption=False)
            compare_button(client, i)


# ---------- Sidebar: clear chat and folders ----------
def sidebar():
    user = st.session_state.name
    with st.sidebar:
        st.markdown(f"### {user}")
        st.caption(f"Level: {st.session_state.level}")

        if st.button(":material/mop: Clear chat", use_container_width=True,
                     disabled=not st.session_state.exchanges):
            st.session_state.exchanges = []
            st.session_state.show_all = False
            st.rerun()

        st.markdown("#### Folders")
        folders = storage.list_folders(user)
        if not folders:
            st.caption("Use “Save to folder” under any answer. Folders are named automatically.")
        for f in folders:
            items = storage.folder_items(f["id"])
            with st.expander(f":material/folder: {f['title']} ({len(items)})"):
                for it in items:
                    st.markdown(f"**{it['question']}**")
                    st.caption(f"{it['level']} · saved {it['saved_at']}")
                    st.markdown(it["answer"])
                    if st.button(":material/delete: Remove", key=f"del_item_{it['id']}"):
                        storage.delete_item(it["id"])
                        st.rerun()
                    st.divider()
                if items:
                    st.download_button(
                        ":material/download: Download folder",
                        data=storage.folder_as_markdown(f["title"], items),
                        file_name=f"{f['title']}.md",
                        key=f"download_{f['id']}",
                        use_container_width=True,
                    )
                if st.button(":material/folder_delete: Delete folder", key=f"del_folder_{f['id']}",
                             use_container_width=True):
                    storage.delete_folder(user, f["id"])
                    st.rerun()


# ---------- Screen 1: password ----------
def password_screen():
    st.title("MNR v Cameron — Q&A")
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
    st.title("Understand MNR v Cameron")
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
    sidebar()

    st.title(f"Welcome, {st.session_state.name}.")
    st.subheader(f"How can I help you understand *{CASE_NAME}*?")
    st.caption("Your saved folders are in the sidebar. Open it with the » arrow at the top left.")

    exchanges = st.session_state.exchanges

    # --- Which exchanges to show: the latest two, unless "show more" is on ---
    oldest_first = list(range(len(exchanges)))
    shown = oldest_first if st.session_state.show_all else oldest_first[-2:]
    hidden = len(exchanges) - 2

    # "Show more" sits at the TOP, above the older answers
    if hidden > 0:
        if st.session_state.show_all:
            if st.button(":material/expand_less: Show less"):
                st.session_state.show_all = False
                st.rerun()
        else:
            label = f"Show {hidden} earlier question" + ("s" if hidden > 1 else "")
            if st.button(f":material/expand_more: {label}"):
                st.session_state.show_all = True
                st.rerun()

    # --- Answers, oldest at the top, latest at the bottom (older ones faded) ---
    for i in shown:
        is_latest = i == len(exchanges) - 1
        with st.container(key=f"latest_{i}" if is_latest else f"older_{i}"):
            show_exchange(client, i)

    if exchanges:
        st.divider()

    # --- The question box, directly under the latest answer ---
    with st.form("ask_form", clear_on_submit=True):
        level = st.selectbox(
            "Answer level",
            list(LEVELS),
            index=list(LEVELS).index(st.session_state.level),
        )
        placeholder = "Ask a follow-up question..." if exchanges else "Ask a question about the case..."
        question = st.text_input("Your question", placeholder=placeholder, label_visibility="collapsed")
        asked = st.form_submit_button(":material/send: Ask", type="primary")

    if asked and question.strip():
        st.session_state.level = level     # remember the last level used
        st.session_state.show_all = False  # collapse back to the latest two
        with st.spinner("Reading the judgment..."):
            reply, sources = answer(client, question, level, history_before(len(exchanges)))
        exchanges.append({
            "question": question,
            "versions": [{"answer": reply, "level": level, "sources": sources}],
        })
        st.rerun()


# ---------- Decide which screen to show ----------
if not st.session_state.authenticated:
    password_screen()
elif st.session_state.stage == "welcome":
    welcome_screen()
else:
    chat_screen()