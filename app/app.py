"""Investment Likelihood and Recommendation System - Streamlit entry point.

Pages (in app/views/):
- Home: what the app does and where to start
- For individuals: suggested options from similar people (no score about the person)
- For institutions: upload a customer list -> likelihood bands, reasons, download
- About and limits: data, method, fairness and limits

Run locally:  streamlit run app/app.py
"""
import streamlit as st

st.set_page_config(page_title="Investor Likelihood and Recommendations", page_icon="📈", layout="centered")

pages = [
    st.Page("views/home.py", title="Home", icon="🏠", default=True),
    st.Page("views/individuals.py", title="For individuals", icon="🙋"),
    st.Page("views/institutions.py", title="For institutions", icon="🏦"),
    st.Page("views/about.py", title="About and limits", icon="ℹ️"),
]
st.navigation(pages).run()
