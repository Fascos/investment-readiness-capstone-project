"""
Shared pieces used by every page:
the cached model bundle, standard text and the feedback box.
"""

import logging

import streamlit as st

from investor_app import load_bundle


logger = logging.getLogger(__name__)


DISCLAIMER = (
    "For learning only, not personal financial advice. "
    "Confirm product terms and provider licensing before acting."
)

DATA_NOTE = (
    "Built on the 2024 FinAccess Household Survey "
    "(Central Bank of Kenya, KNBS and FSD Kenya): "
    "20,870 Kenyan adults aged 16 and over."
)


@st.cache_resource(show_spinner="Loading the model...")
def get_bundle():
    """
    Load the saved deployment bundle once and reuse it.

    Technical errors are written to the application logs.
    Users receive a short, non-technical error message.
    """
    try:
        bundle = load_bundle()
        return bundle

    except Exception:
        logger.exception(
            "Application model bundle failed to load"
        )

        st.error(
            "The application model could not be loaded. "
            "Please try again later."
        )

        st.stop()


def feedback_box(page):
    """
    Display privacy-safe thumbs feedback.

    Only the page and thumbs selection are written to the logs.
    No free-text feedback or personal information is collected.
    """
    st.divider()
    st.markdown("**Was this page useful?**")

    rating = st.feedback(
        "thumbs",
        key=f"{page}_rating"
    )

    if rating is not None:
        verdict = {
            0: "thumbs down",
            1: "thumbs up"
        }.get(rating, "unknown response")

        logger.info(
            "FEEDBACK | page=%s | rating=%s",
            page,
            verdict
        )

        st.success(
            "Thank you! Your feedback helps us improve the app."
        )