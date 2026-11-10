"""Helper functions for the Investment Readiness and Recommendation app.

Loads the saved models (models/investor_app_bundle.joblib, made in notebook section 9.1) and gives:
- clean_app_answers(): raw app answers -> the same form as X in the notebook (section 4.3)
- investor_likelihood(): institution view - likelihood, band and top reasons (SHAP)
- recommend(): individual view - suggested options from similar people (section 8)
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

BUNDLE_PATH = Path(__file__).resolve().parent.parent / "models" / "investor_app_bundle.joblib"

AVERAGE_RATE = 0.027  # share of Kenyan adults in the training data who invest (2.7%)
NUMERIC_COLS = ["age", "household_size", "monthly_income", "literacy_score"]
LITERACY_MAP = {"None correct": 0, "One correct": 1, "Two correct": 2, "All correct": 3}
LITERACY_WORDS = {value: key for key, value in LITERACY_MAP.items()}


def load_bundle(path=BUNDLE_PATH):
    # Load everything saved in notebook section 9.1
    return joblib.load(path)


# ---------------------------------------------------------------------------
# Cleaning (same steps as notebook section 4.3)
# ---------------------------------------------------------------------------
def clean_app_answers(answers):
    """
    Convert raw app answers into the same form as X:
    - monthly_income in KSh -> log1p(income); blank stays blank
    - literacy_score words -> 0 to 3 (numbers 0 to 3 are kept)
    - unclear education / marital answers -> blank
    """
    cleaned = dict(answers)
    income = cleaned.get("monthly_income")
    cleaned["monthly_income"] = (
        np.nan if income is None or pd.isna(income) else np.log1p(float(income))
    )
    if cleaned.get("literacy_score") in LITERACY_MAP:
        cleaned["literacy_score"] = LITERACY_MAP[cleaned["literacy_score"]]
    if cleaned.get("education") == "Other":
        cleaned["education"] = np.nan
    if cleaned.get("marital_status") == "Don't Know/Refused'":
        cleaned["marital_status"] = np.nan
    return cleaned


def to_model_row(bundle, answers):
    # One cleaned row with exactly the 11 model inputs, in the right order and types
    features = bundle["settings"]["FEATURES"]
    cleaned = clean_app_answers(answers)
    row = pd.DataFrame([{feature: cleaned.get(feature, np.nan) for feature in features}])
    for column in NUMERIC_COLS:
        row[column] = pd.to_numeric(row[column], errors="coerce")
    if row.loc[0, "monthly_income"] > 20:
        raise ValueError("monthly_income looks like KSh after cleaning. Pass raw answers to clean_app_answers() once only.")
    if row.loc[0, "literacy_score"] not in [0, 1, 2, 3]:
        raise ValueError("literacy_score must be 0 to 3, or the words 'None correct' to 'All correct'.")
    return row


# ---------------------------------------------------------------------------
# Institution view: investor likelihood, band and reasons (notebook sections 6 and 7)
# ---------------------------------------------------------------------------
def likelihood_band(prob, settings):
    # High = cut-off from 6.2 (about 3x the average) or more, Medium = around the average, Low = below
    if prob >= settings["CUTOFF"]:
        return "High"
    if prob >= settings["MEDIUM_CUTOFF"]:
        return "Medium"
    return "Low"


def _original_question(column, features):
    # Map one of the 72 prepared columns back to one of the 11 questions (e.g. county_Nairobi -> county)
    if column.startswith("missingindicator_"):
        return "monthly_income"
    return next(f for f in features if column == f or column.startswith(f + "_"))


def _answer_text(question, raw_answers):
    # How to show a person's answer inside a reason sentence
    answer = raw_answers.get(question)
    if question == "monthly_income":
        return "not given" if answer is None or pd.isna(answer) else f"KSh {float(answer):,.0f}"
    if question in ["age", "household_size"]:
        return str(int(answer))
    if question == "literacy_score" and answer in LITERACY_WORDS:
        return LITERACY_WORDS[answer]
    if question == "has_id" and isinstance(answer, str):
        return answer.split("(")[0].strip()
    return str(answer)


def top_reasons(bundle, row, raw_answers, n=3):
    """
    The n answers that pushed this person's likelihood the most, as plain sentences.
    SHAP is calculated with XGBoost's own method on the same sparse data the model was trained on
    (a normal table gives wrong results - see notebook section 7).
    """
    pipeline = bundle["shap_model"]
    prep = pipeline.named_steps["prep"]
    model = pipeline.named_steps["model"]
    features = bundle["settings"]["FEATURES"]

    contributions = model.get_booster().predict(xgb.DMatrix(prep.transform(row)), pred_contribs=True)[0][:-1]
    names = [c.split("__", 1)[1] for c in prep.get_feature_names_out()]

    per_question = {}
    for name, value in zip(names, contributions):
        question = _original_question(name, features)
        per_question[question] = per_question.get(question, 0.0) + float(value)

    pushes = pd.Series(per_question).sort_values(key=abs, ascending=False).head(n)
    sentences = []
    for question, push in pushes.items():
        direction = "raises" if push > 0 else "lowers"
        label = question.replace("_", " ").capitalize()
        sentences.append(f"{label} ({_answer_text(question, raw_answers)}) {direction} this person's likelihood.")
    return sentences


def investor_likelihood(bundle, answers):
    # Calibrated likelihood, band, comparison with the average, and top 3 reasons
    row = to_model_row(bundle, answers)
    prob = float(bundle["final_model"].predict_proba(row)[:, 1][0])
    return {
        "likelihood": prob,
        "band": likelihood_band(prob, bundle["settings"]),
        "times_average": prob / AVERAGE_RATE,
        "reasons": top_reasons(bundle, row, answers),
    }


# ---------------------------------------------------------------------------
# Individual view: recommendations from similar people (notebook section 8)
# ---------------------------------------------------------------------------
def recommend(bundle, answers, top_n=3):
    """
    Two options most used by the 50 most similar training people, plus an investment
    "next step" that similar people use more than average. If evidence is weak, only
    starter options that similar people actually use. No score about the person.
    """
    rec = bundle["recommender"]
    options = rec["OPTIONS"]
    row = to_model_row(bundle, answers)

    distances, positions = rec["nearest_neighbours"].kneighbors(
        rec["preprocessor"].transform(row), n_neighbors=rec["N_NEIGHBORS"]
    )
    distances, positions = distances[0], positions[0]
    usage = rec["train_option_usage"].iloc[positions][options]

    weights = 1.0 / (distances + rec["DISTANCE_EPSILON"])
    weights = weights / weights.sum()
    support = pd.Series(np.average(usage.to_numpy(), axis=0, weights=weights), index=options)
    scores = pd.DataFrame({
        "weighted_support": support,
        "neighbour_user_count": usage.sum().astype(int),
        "training_rate": rec["training_rate"][options],
    })
    scores["uplift_vs_average"] = scores["weighted_support"] - scores["training_rate"]

    active_neighbours = int(usage[rec["INVESTMENT_OPTIONS"]].any(axis=1).sum())
    mean_distance = float(distances.mean())
    starter_step = (
        active_neighbours < rec["MIN_ACTIVE_NEIGHBORS"] or mean_distance > rec["MAX_MEAN_DISTANCE"]
    )

    scores["reason"] = ""
    if starter_step:
        # Only starter options (savings, chama, SACCO) that similar people actually use, most used first
        chosen = (
            scores.loc[rec["STARTER_OPTIONS"]]
            .query("weighted_support > 0")
            .sort_values(["weighted_support", "neighbour_user_count"], ascending=False)
            .index[:top_n].tolist()
        ) or ["savings"]
        scores.loc[chosen, "reason"] = "Starter option"
    else:
        common_order = scores.sort_values(
            ["weighted_support", "neighbour_user_count"], ascending=False
        ).index.tolist()
        chosen = common_order[:top_n - 1]
        scores.loc[chosen, "reason"] = "Common among similar people"
        candidates = scores.loc[[o for o in rec["INVESTMENT_OPTIONS"] if o not in chosen]]
        if len(candidates) and candidates["uplift_vs_average"].max() > 0:
            next_step = candidates["uplift_vs_average"].idxmax()
            scores.loc[next_step, "reason"] = "Next step"
        else:
            next_step = [o for o in common_order if o not in chosen][0]
            scores.loc[next_step, "reason"] = "Common among similar people"
        chosen = chosen + [next_step]

    result = scores.loc[chosen].join(rec["product_reference"]).reset_index().rename(columns={"index": "option"})
    result["plain_sentence"] = result.apply(describe_suggestion, axis=1)
    return {
        "suggestions": result,
        "starter_step": starter_step,
        "active_neighbours": active_neighbours,
        "mean_distance": mean_distance,
    }


def describe_suggestion(suggestion):
    # Turn the numbers into one plain sentence for the user (no score about the person)
    share = suggestion["weighted_support"]
    if share >= 0.95:
        how_many = "Almost everyone like you"
    elif share >= 0.1:
        how_many = f"About {round(share * 10)} in 10 people like you"
    elif share >= 0.01:
        how_many = f"About {round(share * 100)} in 100 people like you"
    else:
        how_many = "A few people like you"

    if suggestion["reason"] == "Next step":
        ratio = share / suggestion["training_rate"] if suggestion["training_rate"] > 0 else 1
        if ratio >= 1.5:
            return f"A good next step: people like you are about {ratio:.1f} times as likely as the average Kenyan adult to use this."
        return "A good next step: people like you use this a bit more than the average Kenyan adult."
    if suggestion["reason"] == "Starter option":
        return f"A good place to start. {how_many} use this."
    return f"{how_many} use this."
