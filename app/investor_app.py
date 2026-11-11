"""Engine for the Investment Readiness and Recommendation app (no Streamlit code here).

Loads the saved models (models/investor_app_bundle.joblib, made in notebook section 9.1) and gives:
- clean_app_answers() / prepare_rows(): raw answers -> the same form as X in the notebook (section 4.3)
- validate_upload(): checks an institution's customer file and lists any problems
- score_customers(): institution view - likelihood, band and top reasons for many people at once
- investor_likelihood(): the same for one person
- recommend(): individual view - suggested options from similar people (section 8)
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

ROOT = Path(__file__).resolve().parent.parent
BUNDLE_PATH = ROOT / "models" / "investor_app_bundle.joblib"
SAMPLE_PATH = ROOT / "data" / "sample_customers.csv"

AVERAGE_RATE = 0.027  # share of Kenyan adults in the training data who invest (2.7%)
MAX_UPLOAD_ROWS = 10_000
NUMERIC_COLS = ["age", "household_size", "monthly_income", "literacy_score"]
NUMERIC_LIMITS = {"age": (16, 105), "household_size": (1, 20), "monthly_income": (0, 10_000_000)}
LITERACY_MAP = {"None correct": 0, "One correct": 1, "Two correct": 2, "All correct": 3}
LITERACY_WORDS = {value: key for key, value in LITERACY_MAP.items()}
YES = {"yes", "y", "true", "1", "has id"}
NO = {"no", "n", "false", "0", "no id"}

# Two example people for the "Try an example" buttons (labels match the survey answers exactly)
EXAMPLE_PEOPLE = {
    "Grace, 24, farmer in Kisii": {
        "age": 24, "urban_rural": "Rural", "county": "Kisii", "education": "Secondary",
        "marital_status": "Married/Living with partner", "household_size": 5, "livelihood": "Agriculture",
        "monthly_income": 8_000, "has_id": "Yes", "mobile_money": "Yes", "literacy_score": 2,
        "quiz": ["Exactly KSh 110", "More", "Spreading your money across several investments"],
    },
    "James, 41, teacher in Nairobi": {
        "age": 41, "urban_rural": "Urban", "county": "Nairobi City", "education": "Tertiary",
        "marital_status": "Married/Living with partner", "household_size": 4, "livelihood": "Employed",
        "monthly_income": 85_000, "has_id": "Yes", "mobile_money": "Yes", "literacy_score": 3,
        "quiz": ["Exactly KSh 110", "Less", "Spreading your money across several investments"],
    },
}


def load_bundle(path=BUNDLE_PATH):
    # Load everything saved in notebook section 9.1
    return joblib.load(path)


# ---------------------------------------------------------------------------
# Cleaning (same steps as notebook section 4.3)
# ---------------------------------------------------------------------------
def standardise_answer(bundle, column, value):
    """
    Match an answer to the exact survey label the model was trained on.
    Not case-sensitive; has_id and mobile_money also accept Yes / No.
    Returns None if the answer is not one of the allowed options.
    """
    if value is None or pd.isna(value):
        return None
    choices = bundle["form_choices"][column]
    text = str(value).strip()
    lookup = {choice.lower(): choice for choice in choices}
    if text.lower() in lookup:
        return lookup[text.lower()]
    if column == "has_id":
        if text.lower() in YES or text.lower().startswith("has id"):
            return next(c for c in choices if c.lower().startswith("has id"))
        if text.lower() in NO:
            return next(c for c in choices if c.lower().startswith("no"))
    if column == "mobile_money" and text.lower() in YES | NO:
        return "Yes" if text.lower() in YES else "No"
    if column == "county" and text.lower() == "nairobi":
        return "Nairobi City"
    return None


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


def prepare_rows(bundle, raw_df):
    # Cleaned rows with exactly the 11 model inputs, in the right order and types
    features = bundle["settings"]["FEATURES"]
    rows = [clean_app_answers(answers) for answers in raw_df[features].to_dict("records")]
    X = pd.DataFrame(rows, columns=features, index=raw_df.index)
    for column in NUMERIC_COLS:
        X[column] = pd.to_numeric(X[column], errors="coerce")
    return X


def to_model_row(bundle, answers):
    # One person's answers as a one-row table ready for the model
    raw = pd.DataFrame([answers])
    if raw.loc[0, "has_id"] not in bundle["form_choices"]["has_id"]:
        raw.loc[0, "has_id"] = standardise_answer(bundle, "has_id", raw.loc[0, "has_id"])
    row = prepare_rows(bundle, raw)
    if row.loc[0, "monthly_income"] > 20:
        raise ValueError("monthly_income looks like KSh after cleaning. Pass raw answers to clean_app_answers() once only.")
    if row.loc[0, "literacy_score"] not in [0, 1, 2, 3]:
        raise ValueError("literacy_score must be 0 to 3, or the words 'None correct' to 'All correct'.")
    return row


# ---------------------------------------------------------------------------
# Checking an institution's upload
# ---------------------------------------------------------------------------
def template_columns(bundle):
    # The columns an institution's file needs, what each may contain, and an example value
    choices = bundle["form_choices"]
    return pd.DataFrame([
        ("customer_id", "Optional. Your own reference for each person", "C001"),
        ("age", "Number, 16 to 105", "35"),
        ("urban_rural", " / ".join(choices["urban_rural"]), "Urban"),
        ("county", "One of the 47 counties (e.g. Nairobi City, Kisii, Nakuru)", "Nakuru"),
        ("education", " / ".join(choices["education"]), "Secondary"),
        ("marital_status", " / ".join(choices["marital_status"]), "Married/Living with partner"),
        ("household_size", "Number of people in the household, 1 to 20", "4"),
        ("livelihood", " / ".join(choices["livelihood"]), "Own Business"),
        ("monthly_income", "Monthly income in KSh. Leave blank if unknown", "20000"),
        ("has_id", "Yes / No", "Yes"),
        ("mobile_money", "Yes / No", "Yes"),
        ("literacy_score", "Number of the 3 money questions answered correctly: 0 to 3", "2"),
        ("sex", "Optional. Female / Male. Only used for the report by sex, never for the likelihood", "Female"),
    ], columns=["Column", "What to put", "Example"])


def template_csv(bundle):
    # A small example file institutions can download and fill in
    example = template_columns(bundle).set_index("Column")["Example"]
    return pd.DataFrame([example.to_dict()]).to_csv(index=False)


def validate_upload(bundle, raw_df):
    """
    Check an uploaded customer file.
    Returns (valid_rows, problems, missing_columns):
    - valid_rows: rows that passed, with answers matched to the survey labels
    - problems: one line per problem found (row number, column, value, what is wrong)
    - missing_columns: required columns that are not in the file (nothing can be scored if any)
    """
    features = bundle["settings"]["FEATURES"]
    df = raw_df.reset_index(drop=True).astype(object)
    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = [f for f in features if f not in df.columns]
    if missing:
        return df.iloc[0:0], pd.DataFrame(), missing

    problems = []
    for column in features:
        for position, value in df[column].items():
            row_number = df.index.get_loc(position) + 2   # +2: header row, and counting from 1
            if column in NUMERIC_LIMITS:
                if column == "monthly_income" and (pd.isna(value) or str(value).strip() == ""):
                    df.at[position, column] = np.nan
                    continue
                number = pd.to_numeric(str(value).replace(",", ""), errors="coerce")
                low, high = NUMERIC_LIMITS[column]
                if pd.isna(number) or not low <= number <= high:
                    problems.append((row_number, column, value, f"must be a number from {low:,} to {high:,}"))
                else:
                    df.at[position, column] = float(number)
            elif column == "literacy_score":
                if value in LITERACY_MAP:
                    df.at[position, column] = LITERACY_MAP[value]
                else:
                    number = pd.to_numeric(value, errors="coerce")
                    if number not in [0, 1, 2, 3]:
                        problems.append((row_number, column, value, "must be 0, 1, 2 or 3"))
                    else:
                        df.at[position, column] = int(number)
            else:
                label = standardise_answer(bundle, column, value)
                if label is None:
                    problems.append((row_number, column, value, "is not one of the allowed answers"))
                else:
                    df.at[position, column] = label

    problems = pd.DataFrame(problems, columns=["Row in file", "Column", "Value", "Problem"])
    bad_rows = set(problems["Row in file"])
    keep = [p for p in df.index if df.index.get_loc(p) + 2 not in bad_rows]
    return df.loc[keep], problems, []


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
        return str(int(float(answer)))
    if question == "literacy_score":
        return LITERACY_WORDS.get(answer, LITERACY_WORDS.get(int(float(answer)), str(answer)))
    if question == "has_id" and isinstance(answer, str):
        return answer.split("(")[0].strip()
    return str(answer)


def pushes_by_question(bundle, X):
    """
    SHAP push of each of the 11 questions, for every row of X (already cleaned).
    Calculated with XGBoost's own method on the same sparse data the model was trained on
    (a normal table gives wrong results - see notebook section 7).
    """
    pipeline = bundle["shap_model"]
    prep = pipeline.named_steps["prep"]
    model = pipeline.named_steps["model"]
    features = bundle["settings"]["FEATURES"]
    contributions = model.get_booster().predict(xgb.DMatrix(prep.transform(X)), pred_contribs=True)[:, :-1]
    names = [c.split("__", 1)[1] for c in prep.get_feature_names_out()]
    by_column = pd.DataFrame(contributions, columns=names, index=X.index)
    return by_column.T.groupby(lambda c: _original_question(c, features)).sum().T


def reason_sentences(pushes, raw_answers, n=3):
    # The n answers that pushed one person's likelihood the most, as plain sentences
    top = pushes.sort_values(key=abs, ascending=False).head(n)
    sentences = []
    for question, push in top.items():
        direction = "raises" if push > 0 else "lowers"
        label = question.replace("_", " ").capitalize()
        sentences.append(f"{label} ({_answer_text(question, raw_answers)}) {direction} the likelihood.")
    return sentences


def score_customers(bundle, raw_df):
    """
    Likelihood, band, comparison with the average and top 3 reasons for every row,
    ranked from most to least likely. raw_df holds raw answers (KSh, Yes/No, 0-3).
    """
    X = prepare_rows(bundle, raw_df)
    probs = bundle["final_model"].predict_proba(X)[:, 1]
    pushes = pushes_by_question(bundle, X)

    result = pd.DataFrame(index=raw_df.index)
    result["customer_id"] = raw_df["customer_id"] if "customer_id" in raw_df else [f"Row {i + 2}" for i in range(len(raw_df))]
    result["band"] = [likelihood_band(p, bundle["settings"]) for p in probs]
    result["likelihood_pct"] = (probs * 100).round(1)
    result["times_average"] = (probs / AVERAGE_RATE).round(1)
    reasons = [reason_sentences(pushes.loc[i], raw_df.loc[i].to_dict()) for i in raw_df.index]
    for k in range(3):
        result[f"reason_{k + 1}"] = [r[k] if len(r) > k else "" for r in reasons]
    if "sex" in raw_df:
        result["sex"] = raw_df["sex"]
    return result.sort_values("likelihood_pct", ascending=False)


def investor_likelihood(bundle, answers):
    # One person: calibrated likelihood, band, comparison with the average, and top 3 reasons
    raw = pd.DataFrame([answers])
    raw.loc[0, "has_id"] = standardise_answer(bundle, "has_id", raw.loc[0, "has_id"])
    scored = score_customers(bundle, raw).iloc[0]
    return {
        "likelihood": scored["likelihood_pct"] / 100,
        "band": scored["band"],
        "times_average": scored["times_average"],
        "reasons": [scored[f"reason_{k}"] for k in (1, 2, 3) if scored[f"reason_{k}"]],
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
        how_many = "Almost all people like you"
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
