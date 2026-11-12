"""
For individuals:
answer the questions, see options that people like you use,
and try "what if".
"""

import logging

import streamlit as st

from common import (
    DATA_NOTE,
    DISCLAIMER,
    feedback_box,
    get_bundle
)
from investor_app import (
    EXAMPLE_PEOPLE,
    recommend,
    standardise_answer
)

from llm_layer import (
    build_individual_prompt,
    generate_explanation
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Validation limits
# ------------------------------------------------------------------

MIN_AGE = 16
MAX_AGE = 105

MIN_HOUSEHOLD_SIZE = 1
MAX_HOUSEHOLD_SIZE = 20

MIN_MONTHLY_INCOME = 0
MAX_MONTHLY_INCOME = 10_000_000


# ------------------------------------------------------------------
# Load the deployment bundle
# ------------------------------------------------------------------

bundle = get_bundle()
choices = bundle["form_choices"]


# ------------------------------------------------------------------
# Financial-literacy questions
# ------------------------------------------------------------------

QUIZ = {
    "ind_q1": (
        "1. You put KSh 100 in a savings account that pays "
        "10% interest a year. After one year, with no withdrawals, "
        "how much is in the account?",
        [
            "Less than KSh 110",
            "Exactly KSh 110",
            "More than KSh 110",
            "I don't know"
        ],
        "Exactly KSh 110"
    ),
    "ind_q2": (
        "2. Prices go up by 10% this year, and your savings earn "
        "5% interest. After one year, can your savings buy more, "
        "the same, or less than today?",
        [
            "More",
            "The same",
            "Less",
            "I don't know"
        ],
        "Less"
    ),
    "ind_q3": (
        "3. Which is usually safer?",
        [
            "Putting all your money in one investment",
            "Spreading your money across several investments",
            "I don't know"
        ],
        "Spreading your money across several investments"
    ),
}


FORM_FIELDS = [
    "urban_rural",
    "county",
    "education",
    "marital_status",
    "livelihood",
    "has_id",
    "mobile_money"
]


# ------------------------------------------------------------------
# Initial session-state values
# ------------------------------------------------------------------

st.session_state.setdefault("ind_age", None)
st.session_state.setdefault("ind_household_size", None)
st.session_state.setdefault("ind_income", None)
st.session_state.setdefault("ind_prefer_not", False)

st.session_state.setdefault(
    "ind_has_id",
    standardise_answer(
        bundle,
        "has_id",
        "Yes"
    )
)

st.session_state.setdefault(
    "ind_mobile_money",
    "Yes"
)


# ------------------------------------------------------------------
# Example-profile loader
# ------------------------------------------------------------------

def load_example(name):
    """
    Fill the form using an illustrative example profile.

    If an example profile cannot be loaded, log the technical
    failure and show a safe message to the user.
    """
    try:
        person = EXAMPLE_PEOPLE[name]

        st.session_state["ind_age"] = person["age"]
        st.session_state["ind_household_size"] = (
            person["household_size"]
        )
        st.session_state["ind_income"] = person["monthly_income"]
        st.session_state["ind_prefer_not"] = False

        for field in FORM_FIELDS:
            st.session_state[f"ind_{field}"] = standardise_answer(
                bundle,
                field,
                person[field]
            )

        for key, answer in zip(QUIZ, person["quiz"]):
            st.session_state[key] = answer

        st.session_state["answers"] = {
            field: st.session_state[f"ind_{field}"]
            for field in FORM_FIELDS
        }

        st.session_state["answers"].update({
            "age": person["age"],
            "household_size": person["household_size"],
            "monthly_income": person["monthly_income"],
            "literacy_score": sum(
                answer == QUIZ[key][2]
                for key, answer in zip(
                    QUIZ,
                    person["quiz"]
                )
            ),
        })

        st.session_state["example_name"] = name

        st.toast(
            f"Loaded {name}. Scroll down to see the options."
        )

    except Exception:
        logger.exception(
            "Illustrative profile failed to load | example=%s",
            name
        )

        st.error(
            "We couldn't load that example profile. "
            "Please enter your answers manually."
        )


# ------------------------------------------------------------------
# Page introduction
# ------------------------------------------------------------------

st.title("Find options that suit people like you")

st.write(
    "Answer the questions below and press **See my options**. "
    "We compare your answers with thousands of Kenyans in a "
    "national survey and show the saving and investment options "
    "that people like you use. We never give you a score."
)

st.markdown("**Or try an example:**")

example_cols = st.columns(len(EXAMPLE_PEOPLE))

for col, name in zip(
    example_cols,
    EXAMPLE_PEOPLE
):
    col.button(
        name,
        on_click=load_example,
        args=(name,),
        use_container_width=True
    )

st.caption(
    "Example profiles are illustrative and do not identify "
    "FinAccess survey respondents."
)


# ------------------------------------------------------------------
# Individual questionnaire
# ------------------------------------------------------------------

with st.form("individual_form"):

    st.subheader("About you")

    col1, col2 = st.columns(2)

    with col1:

        # No min_value or max_value is applied here.
        # This lets the app show its own visible validation message
        # directly below the field after the form is submitted.
        st.number_input(
            "Age",
            value=None,
            step=1,
            placeholder="e.g. 30",
            help="Enter an age from 16 to 105.",
            key="ind_age"
        )

        # This placeholder is populated after submission if invalid.
        age_error_placeholder = st.empty()

        st.selectbox(
            "County",
            choices["county"],
            index=None,
            placeholder="Choose your county",
            key="ind_county"
        )

        st.selectbox(
            "Do you live in an urban or rural area?",
            choices["urban_rural"],
            index=None,
            placeholder="Choose one",
            key="ind_urban_rural"
        )

        # No min_value or max_value is applied here.
        # The app supplies a visible validation message below.
        st.number_input(
            "How many people live in your household?",
            value=None,
            step=1,
            placeholder="e.g. 4",
            help="Enter a household size from 1 to 20.",
            key="ind_household_size"
        )

        # This placeholder is populated after submission if invalid.
        household_error_placeholder = st.empty()

        st.selectbox(
            "Marital status",
            choices["marital_status"],
            index=None,
            placeholder="Choose one",
            key="ind_marital_status"
        )

    with col2:

        st.selectbox(
            "Highest level of education",
            choices["education"],
            index=None,
            placeholder="Choose one",
            key="ind_education"
        )

        st.selectbox(
            "Main source of income / type of work",
            choices["livelihood"],
            index=None,
            placeholder="Choose one",
            key="ind_livelihood"
        )

        st.number_input(
            "Monthly income (KSh)",
            min_value=MIN_MONTHLY_INCOME,
            max_value=MAX_MONTHLY_INCOME,
            step=1_000,
            placeholder="e.g. 15000",
            key="ind_income"
        )

        st.checkbox(
            "I prefer not to say my income",
            key="ind_prefer_not"
        )

        st.selectbox(
            "Do you have a national ID or passport?",
            choices["has_id"],
            key="ind_has_id",
            format_func=lambda label: (
                "Yes"
                if label.lower().startswith("has id")
                else "No"
            )
        )

        st.selectbox(
            "Do you use mobile money?",
            choices["mobile_money"],
            key="ind_mobile_money"
        )

    st.subheader("Three quick money questions")

    for key, (
        question,
        options,
        _
    ) in QUIZ.items():

        st.radio(
            question,
            options,
            index=None,
            key=key
        )

    submitted = st.form_submit_button(
        "See my options",
        type="primary"
    )


# ------------------------------------------------------------------
# Validate and store submitted answers
# ------------------------------------------------------------------

if submitted:

    st.session_state.pop(
        "example_name",
        None
    )

    age = st.session_state.get("ind_age")
    household_size = st.session_state.get(
        "ind_household_size"
    )

    # Track whether either numeric input has a range error.
    numeric_validation_failed = False

    # Age validation appears directly below the Age field.
    if age is not None and not MIN_AGE <= age <= MAX_AGE:
        age_error_placeholder.error(
            f"Please enter an age between "
            f"{MIN_AGE} and {MAX_AGE}."
        )
        numeric_validation_failed = True
    else:
        age_error_placeholder.empty()

    # Household-size validation appears directly below that field.
    if (
        household_size is not None
        and not (
            MIN_HOUSEHOLD_SIZE
            <= household_size
            <= MAX_HOUSEHOLD_SIZE
        )
    ):
        household_error_placeholder.error(
            "Please enter a household size between "
            f"{MIN_HOUSEHOLD_SIZE} and "
            f"{MAX_HOUSEHOLD_SIZE}."
        )
        numeric_validation_failed = True
    else:
        household_error_placeholder.empty()

    required_fields = [
        ("age", "age"),
        ("county", "county"),
        ("urban_rural", "urban or rural"),
        ("household_size", "household size"),
        ("marital_status", "marital status"),
        ("education", "education"),
        ("livelihood", "type of work")
    ]

    missing = [
        label
        for field, label in required_fields
        if st.session_state.get(
            f"ind_{field}"
        ) is None
    ]

    if (
        st.session_state.get("ind_income") is None
        and not st.session_state["ind_prefer_not"]
    ):
        missing.append(
            "monthly income "
            "(or tick 'I prefer not to say')"
        )

    if missing:
        st.warning(
            "Please answer: "
            + ", ".join(missing)
            + "."
        )

    # Stop before calling the recommender if anything is missing
    # or if Age/Household size is outside the accepted range.
    if missing or numeric_validation_failed:
        st.stop()

    st.session_state["answers"] = {
        "age": age,
        "urban_rural": (
            st.session_state["ind_urban_rural"]
        ),
        "county": st.session_state["ind_county"],
        "education": (
            st.session_state["ind_education"]
        ),
        "marital_status": (
            st.session_state["ind_marital_status"]
        ),
        "household_size": household_size,
        "livelihood": (
            st.session_state["ind_livelihood"]
        ),
        "monthly_income": (
            None
            if st.session_state["ind_prefer_not"]
            else st.session_state["ind_income"]
        ),
        "has_id": st.session_state["ind_has_id"],
        "mobile_money": (
            st.session_state["ind_mobile_money"]
        ),
        "literacy_score": sum(
            st.session_state.get(key) == correct
            for key, (
                _,
                _,
                correct
            ) in QUIZ.items()
        ),
    }


# ------------------------------------------------------------------
# Wait for a submitted or example profile
# ------------------------------------------------------------------

if "answers" not in st.session_state:

    st.info(
        "Fill in the form, or try an example, "
        "to see your options."
    )

    feedback_box("individuals")
    st.stop()


answers = st.session_state["answers"]


# ------------------------------------------------------------------
# Recommendation display helper
# ------------------------------------------------------------------

def show_suggestions(result, compact=False):
    """
    Display one card for each recommended option.
    """
    for _, suggestion in result["suggestions"].iterrows():

        with st.container(border=True):

            st.markdown(
                f"**{suggestion['display_name']}**"
            )

            st.write(
                suggestion["plain_sentence"]
            )

            if not compact:

                with st.expander("Product details"):

                    st.markdown(
                        f"- **Risk:** "
                        f"{suggestion['risk']}\n"
                        f"- **Typical minimum:** "
                        f"{suggestion['typical_minimum']}\n"
                        f"- **Getting your money out:** "
                        f"{suggestion['access']}\n"
                        f"- **Time horizon:** "
                        f"{suggestion['time_horizon']}\n"
                        f"- **Regulator:** "
                        f"{suggestion['regulator']}"
                    )


# ------------------------------------------------------------------
# Generate recommendations
# ------------------------------------------------------------------

try:
    with st.spinner(
        "Finding people like you..."
    ):
        result = recommend(
            bundle,
            answers
        )

except Exception:
    logger.exception(
        "Recommendation generation failed"
    )

    st.error(
        "Sorry, we couldn't generate recommendations. "
        "Please check your answers and try again."
    )

    st.stop()


# ------------------------------------------------------------------
# Display current recommendations
# ------------------------------------------------------------------

st.subheader(
    "Options that people like you use"
)

if st.session_state.get("example_name"):

    st.caption(
        "Showing the example: "
        f"{st.session_state['example_name']}. "
        "Change any answer above and press "
        "**See my options** to try your own."
    )

if result["starter_step"]:

    st.write(
        "Few people with answers like yours use "
        "investment products yet, so here are "
        "good places to start."
    )

show_suggestions(result)

# ------------------------------------------------------------------
# Ask Gemini to explain the suggested options
# ------------------------------------------------------------------
if st.button("Explain my options"):

    try:
        with st.spinner("Preparing your explanation..."):

            prompt = build_individual_prompt(
                result["suggestions"],
                bundle["recommender"]["product_reference"]
            )

            explanation = generate_explanation(prompt)

        st.subheader("Understanding your options")
        st.write(explanation)

    except Exception as e:
        logger.exception("Gemini explanation failed")
        st.error(f"Gemini error: {type(e).__name__}: {e}")

st.caption(
    f"You answered {answers['literacy_score']} "
    "of 3 money questions correctly."
)

# ------------------------------------------------------------------
# What-if analysis
# ------------------------------------------------------------------

st.subheader("What if...?")

st.write(
    "Change an answer to see how the options for "
    "people like you would change."
)

st.caption(
    "What-if results show how recommendations change when "
    "an input changes. They do not prove that changing the "
    "input will cause a person to invest."
)

wcol1, wcol2, wcol3 = st.columns(3)

what_if = dict(answers)

what_if["education"] = wcol1.selectbox(
    "Education",
    choices["education"],
    index=choices["education"].index(
        answers["education"]
    ),
    key="wi_education"
)

current_income = (
    answers["monthly_income"]
    if answers["monthly_income"] is not None
    else 15_000
)

what_if["monthly_income"] = wcol2.number_input(
    "Monthly income (KSh)",
    min_value=MIN_MONTHLY_INCOME,
    max_value=MAX_MONTHLY_INCOME,
    value=int(current_income),
    step=5_000,
    key="wi_income"
)

what_if["literacy_score"] = wcol3.slider(
    "Money questions correct",
    0,
    3,
    int(answers["literacy_score"]),
    key="wi_literacy"
)


if what_if == answers:

    st.caption(
        "Change one of the answers above to compare."
    )

else:

    try:
        with st.spinner(
            "Comparing the changed profile..."
        ):
            what_if_result = recommend(
                bundle,
                what_if
            )

    except Exception:
        logger.exception(
            "Individual what-if recommendation failed"
        )

        st.error(
            "We couldn't complete the what-if comparison. "
            "Please review the changed values and try again."
        )

        st.stop()

    now_col, then_col = st.columns(2)

    with now_col:

        st.markdown("**Your options now**")

        show_suggestions(
            result,
            compact=True
        )

    with then_col:

        st.markdown("**What if**")

        show_suggestions(
            what_if_result,
            compact=True
        )

    new_options = (
        set(
            what_if_result[
                "suggestions"
            ]["display_name"]
        )
        - set(
            result[
                "suggestions"
            ]["display_name"]
        )
    )

    if new_options:

        st.success(
            "New option(s) that would appear: "
            + ", ".join(
                sorted(new_options)
            )
            + "."
        )

    else:

        st.info(
            "The same options would be suggested."
        )


# ------------------------------------------------------------------
# Notes and feedback
# ------------------------------------------------------------------

st.caption(DATA_NOTE)
st.caption(DISCLAIMER)
feedback_box("individuals")
