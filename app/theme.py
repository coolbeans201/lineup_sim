"""App-wide light/dark appearance."""

from __future__ import annotations

import json

import streamlit as st
import streamlit.components.v1 as components

THEME_KEY = "app_theme"
LIGHT = "Light"
DARK = "Dark"
THEMES = (LIGHT, DARK)

# Injected into the parent document so every widget (including Reset lineup) picks it up.
_DARK_CSS = """
html[data-lineup-theme="dark"],
html[data-lineup-theme="dark"] body {
    color-scheme: dark;
}

html[data-lineup-theme="dark"] .stApp,
html[data-lineup-theme="dark"] [data-testid="stAppViewContainer"],
html[data-lineup-theme="dark"] [data-testid="stMainBlockContainer"],
html[data-lineup-theme="dark"] section.main {
    background-color: #0e1117;
    color: #fafafa;
}

html[data-lineup-theme="dark"] [data-testid="stHeader"] {
    background-color: rgba(14, 17, 23, 0.95);
}

html[data-lineup-theme="dark"] [data-testid="stSidebar"],
html[data-lineup-theme="dark"] [data-testid="stSidebarContent"],
html[data-lineup-theme="dark"] [data-testid="stSidebarNav"] {
    background-color: #262730;
    color: #fafafa;
}

html[data-lineup-theme="dark"] [data-testid="stSidebarNav"] a,
html[data-lineup-theme="dark"] [data-testid="stSidebarNav"] span,
html[data-lineup-theme="dark"] [data-testid="stMarkdownContainer"] p,
html[data-lineup-theme="dark"] [data-testid="stMarkdownContainer"] li,
html[data-lineup-theme="dark"] [data-testid="stMarkdownContainer"] h1,
html[data-lineup-theme="dark"] [data-testid="stMarkdownContainer"] h2,
html[data-lineup-theme="dark"] [data-testid="stMarkdownContainer"] h3,
html[data-lineup-theme="dark"] [data-testid="stMarkdownContainer"] h4,
html[data-lineup-theme="dark"] [data-testid="stWidgetLabel"],
html[data-lineup-theme="dark"] [data-testid="stCaptionContainer"],
html[data-lineup-theme="dark"] label,
html[data-lineup-theme="dark"] .stMarkdown,
html[data-lineup-theme="dark"] .stCaption {
    color: #fafafa !important;
}

html[data-lineup-theme="dark"] [data-testid="stMetricValue"] {
    color: #fafafa;
}

html[data-lineup-theme="dark"] [data-testid="stMetricLabel"],
html[data-lineup-theme="dark"] [data-testid="stMetricDelta"] {
    color: #c4c7cf;
}

html[data-lineup-theme="dark"] div[data-baseweb="input"] > div,
html[data-lineup-theme="dark"] div[data-baseweb="select"] > div,
html[data-lineup-theme="dark"] div[data-baseweb="textarea"] > div,
html[data-lineup-theme="dark"] [data-testid="stNumberInputContainer"] input,
html[data-lineup-theme="dark"] [data-testid="stTextInputRootElement"] input,
html[data-lineup-theme="dark"] [data-testid="stDateInput"] input,
html[data-lineup-theme="dark"] [data-testid="stDateInput"] div[data-baseweb="input"],
html[data-lineup-theme="dark"] [data-testid="stDateInput"] div[data-baseweb="input"] > div,
html[data-lineup-theme="dark"] [data-baseweb="datepicker"] input,
html[data-lineup-theme="dark"] input[type="date"],
html[data-lineup-theme="dark"] input[type="datetime-local"] {
    background-color: #262730 !important;
    color: #fafafa !important;
    border-color: #4a4f5c !important;
    color-scheme: dark;
}

html[data-lineup-theme="dark"] input[type="date"]::-webkit-calendar-picker-indicator,
html[data-lineup-theme="dark"] input[type="datetime-local"]::-webkit-calendar-picker-indicator,
html[data-lineup-theme="dark"] [data-testid="stDateInput"] svg {
    filter: invert(0.85);
}

html[data-lineup-theme="dark"] [data-testid="stDateInput"] [data-baseweb="input"] input,
html[data-lineup-theme="dark"] [data-testid="stDateInput"] [role="spinbutton"],
html[data-lineup-theme="dark"] [data-testid="stDateInput"] p,
html[data-lineup-theme="dark"] [data-testid="stDateInput"] span {
    color: #fafafa !important;
}

html[data-lineup-theme="dark"] [data-testid="stSidebar"] input,
html[data-lineup-theme="dark"] [data-testid="stSidebar"] [data-baseweb="input"] input,
html[data-lineup-theme="dark"] [data-testid="stSidebar"] [data-baseweb="input"] > div {
    background-color: #262730 !important;
    color: #fafafa !important;
    border-color: #4a4f5c !important;
}

html[data-lineup-theme="dark"] [data-baseweb="popover"],
html[data-lineup-theme="dark"] [data-baseweb="calendar"],
html[data-lineup-theme="dark"] [data-baseweb="menu"] {
    background-color: #262730 !important;
    color: #fafafa !important;
    border-color: #4a4f5c !important;
}

html[data-lineup-theme="dark"] [data-testid="stRadio"] label,
html[data-lineup-theme="dark"] [data-testid="stRadio"] div[role="radiogroup"] {
    color: #fafafa !important;
}

html[data-lineup-theme="dark"] [data-testid="stExpander"] details {
    background-color: #262730;
    border-color: #4a4f5c;
}

html[data-lineup-theme="dark"] [data-testid="stProgressBar"] > div > div {
    background-color: #ff6b6b;
}

html[data-lineup-theme="dark"] [data-testid="stProgressBar"] > div {
    background-color: #3a3f4b;
}

html[data-lineup-theme="dark"] [data-testid="stAlertContainer"] {
    background-color: #262730;
    color: #fafafa;
}

html[data-lineup-theme="dark"] [data-testid="stDataFrame"],
html[data-lineup-theme="dark"] [data-testid="stTable"] {
    background-color: #262730;
}

html[data-lineup-theme="dark"] .stButton > button,
html[data-lineup-theme="dark"] button[kind="secondary"],
html[data-lineup-theme="dark"] button[kind="primary"],
html[data-lineup-theme="dark"] [data-testid="stBaseButton-secondary"],
html[data-lineup-theme="dark"] [data-testid="stBaseButton-primary"],
html[data-lineup-theme="dark"] [data-testid="stFormSubmitButton"] button {
    background-color: #262730 !important;
    color: #fafafa !important;
    border: 1px solid #4a4f5c !important;
}

html[data-lineup-theme="dark"] .stButton > button:hover,
html[data-lineup-theme="dark"] button[kind="secondary"]:hover,
html[data-lineup-theme="dark"] [data-testid="stBaseButton-secondary"]:hover {
    background-color: #3a3f4b !important;
    border-color: #6b7280 !important;
    color: #fafafa !important;
}

html[data-lineup-theme="dark"] button[kind="primary"],
html[data-lineup-theme="dark"] [data-testid="stBaseButton-primary"],
html[data-lineup-theme="dark"] [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"] {
    background-color: #ff6b6b !important;
    border-color: #ff6b6b !important;
    color: #ffffff !important;
}

html[data-lineup-theme="dark"] hr {
    border-color: #4a4f5c;
}
"""


def current_theme() -> str:
    return st.session_state.get(THEME_KEY, LIGHT)


def apply_theme() -> None:
    theme = current_theme()
    mode = "dark" if theme == DARK else "light"
    css = _DARK_CSS if theme == DARK else ""
    components.html(
        f"""
        <script>
        (function () {{
            const doc = window.parent.document;
            const root = doc.documentElement;
            root.setAttribute("data-lineup-theme", {json.dumps(mode)});

            let style = doc.getElementById("lineup-theme-style");
            if (!style) {{
                style = doc.createElement("style");
                style.id = "lineup-theme-style";
                doc.head.appendChild(style);
            }}
            style.textContent = {json.dumps(css)};
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def render_theme_selector() -> None:
    st.sidebar.radio(
        "Appearance",
        THEMES,
        horizontal=True,
        key=THEME_KEY,
        help=(
            "Switch between light and dark mode. If the app looks unchanged, open the "
            "⋮ menu → Settings → Theme and choose Custom theme."
        ),
    )
