
"""Gemini LLM layer for investment explanations."""

import json
import streamlit as st
from google import genai

from common import DISCLAIMER


MODEL = "gemini-3.7-flash"


SYSTEM_INSTRUCTION = f"""
You are a friendly financial-literacy assistant for a Kenyan
investment education application.

Your role is to explain information, not make decisions.

Rules:
1. Use simple, clear and friendly language.
2. Only mention products included in the supplied product table
   or context.
3. Never recommend gambling or unregulated investment schemes.
4. Never judge a person or describe them as "not ready".
5. Do not invent product fees, returns, minimum deposits or terms.
6. Explain uncertainty where necessary.
7. Do not provide personalised financial advice.
8. Always end your response with this exact disclaimer:

{DISCLAIMER}
"""


@st.cache_resource
def get_client():
    """Create and reuse the Gemini API client."""

    api_key = st.secrets.get("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing from Streamlit Secrets.")

    return genai.Client(api_key=api_key)


def to_records(data):
    """Convert a DataFrame or list into JSON-friendly records."""

    if hasattr(data, "to_dict"):
        return data.to_dict(orient="records")

    return data


def build_individual_prompt(suggestions, product_table):
    """Build an individual explanation prompt without a model score."""

    supplied_data = {
        "suggested_options": to_records(suggestions),
        "approved_product_table": to_records(product_table)
    }

    return f"""
Explain these suggested saving and investment options to an
individual in Kenya.

Explain why the options appeared, what they generally involve,
and what the individual should understand before considering them.

Use only the supplied information. Do not calculate or mention
an investment likelihood score.

Information:
{json.dumps(supplied_data, indent=2, default=str)}
"""


def build_institution_prompt(likelihood_band, top_reasons):
    """Build an institutional explanation using the band and reasons."""

    supplied_data = {
        "likelihood_band": likelihood_band,
        "top_reasons": to_records(top_reasons)
    }

    return f"""
Explain this institutional model result in simple language.

Describe what the likelihood band means and explain the main
factors associated with the result.

Do not present the result as certainty or as a judgement about
the individual. Do not invent additional reasons.

Information:
{json.dumps(supplied_data, indent=2, default=str)}
"""


def build_followup_prompt(question, context):
    """Build a follow-up financial-literacy question."""

    return f"""
Answer the individual's follow-up question using the supplied
application context.

If the context does not contain enough information, say so.
Do not invent product details.

Application context:
{context}

Question:
{question}
"""


def generate_explanation(prompt):
    """Send a prompt to Gemini and return its explanation."""

    client = get_client()

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config={
            "system_instruction": SYSTEM_INSTRUCTION,
            "temperature": 0.3,
            "max_output_tokens": 700
        }
    )

    answer = response.text

    if not answer:
        raise ValueError("Gemini returned an empty response.")

    # Ensure the required disclaimer is always at the end.
    answer = answer.strip()

    if not answer.endswith(DISCLAIMER):
        answer = answer.rstrip() + "\n\n" + DISCLAIMER

    return answer
