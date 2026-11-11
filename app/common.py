"""Shared pieces used by every page: the cached model bundle, standard text and the feedback box."""
import streamlit as st

from investor_app import load_bundle

DISCLAIMER = (
    "For learning only, not personal financial advice. "
    "Confirm product terms and provider licensing before acting."
)
DATA_NOTE = (
    "Built on the 2024 FinAccess Household Survey (Central Bank of Kenya, KNBS and FSD Kenya): "
    "20,870 Kenyan adults aged 16 and over."
)


@st.cache_resource(show_spinner="Loading the model...")
def get_bundle():
    # Load the saved models once and reuse them for every visitor
    return load_bundle()


def feedback_box(page):
    # Thumbs up / down plus an optional comment. Saved to the app logs (Manage app -> Logs)
    st.divider()
    st.markdown("**Was this page useful?**")
    rating = st.feedback("thumbs", key=f"{page}_rating")
    comment = st.text_input("Anything we should improve? (optional)", key=f"{page}_comment")
    if st.button("Send feedback", key=f"{page}_send", disabled=rating is None and not comment):
        verdict = {0: "thumbs down", 1: "thumbs up", None: "no rating"}[rating]
        print(f"FEEDBACK | page={page} | {verdict} | {comment!r}", flush=True)
        st.success("Thank you! Your feedback helps us improve the app.")
