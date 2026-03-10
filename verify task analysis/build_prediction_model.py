"""
Build and evaluate dispense method prediction model.
Uses selected features from feature selection; trains Random Forest; evaluates fit.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

BASE_DATA = Path("output/base_data.csv")
FEATURE_SELECTION_DIR = Path("output/feature_selection")
PREDICTION_DIR = Path("output/prediction")
TARGET = "dispense_method"
WEIGHT_COL = "order_qty"
RANDOM_STATE = 42
TEST_SIZE = 0.2
ALLOWED_WH = {"OHIO", "BEYONDRX_OH", "BEYONDRX_AZ"}


def load_data() -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "utf-16", "cp1252"):
        try:
            df = pd.read_csv(BASE_DATA, encoding=enc)
            df.columns = df.columns.str.strip()
            if "wh_name" in df.columns:
                df = df[df["wh_name"].astype(str).str.upper().isin(ALLOWED_WH)].copy()
            return df
        except (UnicodeDecodeError, pd.errors.EmptyDataError):
            continue
    raise FileNotFoundError(f"Could not load {BASE_DATA}")


def load_selected_features() -> list[str]:
    path = FEATURE_SELECTION_DIR / "selected_features.txt"
    if not path.exists():
        return ["product_type", "wh_name", "level_2", "level_3", "unit_of_measure", "is_compound", "is_rx"]
    with open(path) as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def prepare_features(df: pd.DataFrame, features: list[str]) -> tuple[pd.DataFrame, dict]:
    """Encode categorical features; return X and label encoders."""
    X = pd.DataFrame()
    encoders = {}
    for col in features:
        if col not in df.columns:
            continue
        le = LabelEncoder()
        vals = df[col].fillna("(missing)").astype(str)
        X[col] = le.fit_transform(vals)
        encoders[col] = le
    return X, encoders


def main():
    PREDICTION_DIR.mkdir(parents=True, exist_ok=True)

    print("1. Loading data and selected features...")
    df = load_data()
    features = load_selected_features()
    features = [f for f in features if f in df.columns]
    df = df.dropna(subset=[TARGET])
    df = df[features + [TARGET] + ([WEIGHT_COL] if WEIGHT_COL in df.columns else [])]

    print("2. Preparing features and target...")
    X, encoders = prepare_features(df, features)
    y = df[TARGET].astype(str)
    le_y = LabelEncoder()
    y_enc = le_y.fit_transform(y)
    weights = df[WEIGHT_COL].values if WEIGHT_COL in df.columns else None

    print("3. Train/test split (80/20 stratified)...")
    if weights is not None:
        X_train, X_test, y_train, y_test, w_train, _ = train_test_split(
            X, y_enc, weights, test_size=TEST_SIZE, stratify=y_enc, random_state=RANDOM_STATE
        )
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_enc, test_size=TEST_SIZE, stratify=y_enc, random_state=RANDOM_STATE
        )
        w_train = None

    print("4. Training Random Forest classifier...")
    clf = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=RANDOM_STATE)
    clf.fit(X_train, y_train, sample_weight=w_train)

    print("5. Evaluating on test set...")
    y_pred = clf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average="macro")
    weighted_f1 = f1_score(y_test, y_pred, average="weighted")
    cm = confusion_matrix(y_test, y_pred)
    class_names = le_y.classes_.tolist()
    report = classification_report(y_test, y_pred, target_names=class_names, output_dict=True)

    print("6. Saving outputs...")
    metrics = {
        "accuracy": float(accuracy),
        "macro_f1": float(macro_f1),
        "weighted_f1": float(weighted_f1),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "features": features,
        "classes": class_names,
    }
    with open(PREDICTION_DIR / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    report_df = pd.DataFrame(report).transpose()
    report_df.to_csv(PREDICTION_DIR / "classification_report.csv")

    cm_df = pd.DataFrame(cm, index=class_names, columns=class_names)
    cm_df.to_csv(PREDICTION_DIR / "confusion_matrix.csv")

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(cm_df, annot=True, fmt="d", cmap="Blues", ax=ax)
    ax.set_title("Confusion Matrix (Test Set)")
    ax.set_ylabel("Actual")
    ax.set_xlabel("Predicted")
    plt.tight_layout()
    plt.savefig(PREDICTION_DIR / "confusion_matrix.png", dpi=150, bbox_inches="tight")
    plt.close()

    fi = pd.DataFrame({"feature": features, "importance": clf.feature_importances_}).sort_values("importance", ascending=False)
    fi.to_csv(PREDICTION_DIR / "feature_importance.csv", index=False)
    fi.plot(x="feature", y="importance", kind="barh", legend=False, figsize=(8, 5))
    plt.title("Feature Importance")
    plt.tight_layout()
    plt.savefig(PREDICTION_DIR / "feature_importance.png", dpi=150, bbox_inches="tight")
    plt.close()

    print(f"\nModel fit summary:")
    print(f"  Accuracy:  {accuracy:.2%}")
    print(f"  Macro F1:  {macro_f1:.4f}")
    print(f"  Weighted F1: {weighted_f1:.4f}")
    print(f"  Outputs: {PREDICTION_DIR}")


if __name__ == "__main__":
    main()
