"""
Feature selection for dispense method prediction.
Runs BEFORE summary stats/distribution generation.
Produces visualizations of candidate features and their association with dispense_method.
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.feature_selection import chi2, mutual_info_classif
from sklearn.preprocessing import LabelEncoder

# Candidate features (all known before dispense)
CANDIDATE_FEATURES = [
    "product_type",
    "wh_name",
    "level_2",
    "level_3",
    "unit_of_measure",
    "is_compound",
    "is_rx",
]

TARGET = "dispense_method"
WEIGHT_COL = "order_qty"
OUTPUT_DIR = Path("output/feature_selection")

# Scope: internal pharmacies only (Ohio, Arizona)
ALLOWED_WH = {"OHIO", "BEYONDRX_OH", "BEYONDRX_AZ"}


def load_data(path: str) -> pd.DataFrame:
    """Load base data from CSV (output of 01_base_data.sql)."""
    for enc in ("utf-8-sig", "utf-8", "utf-16", "cp1252"):
        try:
            df = pd.read_csv(path, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"Could not decode {path} with common encodings")
    df.columns = df.columns.str.strip()
    if "wh_name" in df.columns:
        df = df[df["wh_name"].astype(str).str.upper().isin(ALLOWED_WH)].copy()
    return df


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure features exist and are encoded for analysis."""
    df = df.copy()
    # Fill missing categoricals
    for col in CANDIDATE_FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna("(missing)").astype(str)
    if WEIGHT_COL not in df.columns:
        df[WEIGHT_COL] = 1
    return df


def chi_square_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Compute chi-square statistic and p-value for each feature vs dispense_method."""
    results = []
    for feat in CANDIDATE_FEATURES:
        if feat not in df.columns:
            continue
        le_x = LabelEncoder()
        le_y = LabelEncoder()
        X = le_x.fit_transform(df[feat].astype(str).fillna("(missing)"))
        y = le_y.fit_transform(df[TARGET].astype(str))
        chi2_val, p_val = chi2(X.reshape(-1, 1), y)
        results.append({"feature": feat, "chi2": chi2_val[0], "p_value": p_val[0]})
    return pd.DataFrame(results).sort_values("chi2", ascending=False)


def mutual_info_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Compute mutual information for each feature vs dispense_method."""
    results = []
    for feat in CANDIDATE_FEATURES:
        if feat not in df.columns:
            continue
        le_x = LabelEncoder()
        le_y = LabelEncoder()
        X = le_x.fit_transform(df[feat].astype(str).fillna("(missing)"))
        y = le_y.fit_transform(df[TARGET].astype(str))
        w = df[WEIGHT_COL].values if WEIGHT_COL in df.columns else None
        mi = mutual_info_classif(
            X.reshape(-1, 1), y, discrete_features=[True], random_state=42
        )
        results.append({"feature": feat, "mutual_info": mi[0]})
    return pd.DataFrame(results).sort_values("mutual_info", ascending=False)


def plot_feature_distributions(df: pd.DataFrame) -> None:
    """Bar charts of each candidate feature distribution (weighted by order_qty)."""
    n_feats = len([f for f in CANDIDATE_FEATURES if f in df.columns])
    n_cols = 2
    n_rows = (n_feats + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(12, 4 * n_rows))
    axes = np.atleast_2d(axes)

    for idx, feat in enumerate(CANDIDATE_FEATURES):
        if feat not in df.columns:
            continue
        row, col = idx // n_cols, idx % n_cols
        ax = axes[row, col]
        if WEIGHT_COL in df.columns:
            counts = df.groupby(feat, dropna=False)[WEIGHT_COL].sum()
        else:
            counts = df.groupby(feat, dropna=False).size()
        counts = counts.sort_values(ascending=True).tail(30)
        counts.plot(kind="barh", ax=ax, legend=False, color="steelblue", alpha=0.8)
        ax.set_title(f"Distribution: {feat}")
        ax.set_xlabel("order_qty sum" if WEIGHT_COL in df.columns else "fill count")
        ax.tick_params(axis="y", labelsize=8)

    for idx in range(len(CANDIDATE_FEATURES), n_rows * n_cols):
        row, col = idx // n_cols, idx % n_cols
        axes[row, col].axis("off")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "01_feature_distributions.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {OUTPUT_DIR / '01_feature_distributions.png'}")


def plot_feature_vs_dispense(df: pd.DataFrame) -> None:
    """Stacked bar charts: each feature value vs dispense_method mix."""
    for feat in CANDIDATE_FEATURES:
        if feat not in df.columns:
            continue
        cross = (
            df.groupby([feat, TARGET])[WEIGHT_COL]
            .sum()
            .unstack(fill_value=0)
        )
        cross_pct = cross.div(cross.sum(axis=1), axis=0) * 100
        cross_pct = cross_pct.sort_values(cross_pct.columns[0], ascending=False).tail(30)

        fig_h = 6 + max(0, (len(cross_pct) - 12) * 0.35)
        fig, ax = plt.subplots(figsize=(10, fig_h))
        cross_pct.plot(kind="barh", stacked=True, ax=ax, colormap="Set3")
        ax.set_title(f"{feat} vs dispense_method (% by order_qty)")
        ax.set_xlabel(feat)
        ax.legend(title=TARGET, bbox_to_anchor=(1.02, 1), loc="upper left")
        ax.set_xlim(0, 100)
        plt.tight_layout()
        safe_name = feat.replace(" ", "_")
        plt.savefig(OUTPUT_DIR / f"02_{safe_name}_vs_dispense.png", dpi=150, bbox_inches="tight")
        plt.close()
        print(f"  Saved: {OUTPUT_DIR / f'02_{safe_name}_vs_dispense.png'}")


def plot_association_strength(chi_df: pd.DataFrame, mi_df: pd.DataFrame) -> None:
    """Bar charts of chi-square and mutual information scores."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    chi_df.plot(x="feature", y="chi2", kind="bar", ax=axes[0], color="steelblue", legend=False)
    axes[0].set_title("Chi-square statistic (vs dispense_method)")
    axes[0].set_xticklabels(chi_df["feature"], rotation=45, ha="right")
    axes[0].set_ylabel("Chi-square")

    mi_df.plot(x="feature", y="mutual_info", kind="bar", ax=axes[1], color="coral", legend=False)
    axes[1].set_title("Mutual information (vs dispense_method)")
    axes[1].set_xticklabels(mi_df["feature"], rotation=45, ha="right")
    axes[1].set_ylabel("Mutual information")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "03_association_strength.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {OUTPUT_DIR / '03_association_strength.png'}")


def plot_dispense_method_overview(df: pd.DataFrame) -> None:
    """Overall dispense_method distribution and top feature cross-tabs."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    overall = df.groupby(TARGET)[WEIGHT_COL].sum()
    overall.plot(kind="bar", ax=axes[0], color="teal", alpha=0.8)
    axes[0].set_title("Overall dispense_method (order_qty)")
    axes[0].set_xticklabels(axes[0].get_xticklabels(), rotation=45, ha="right")
    axes[0].set_ylabel("order_qty sum")

    # Top feature by chi2 (product_type typically)
    top_feat = CANDIDATE_FEATURES[0] if CANDIDATE_FEATURES[0] in df.columns else None
    if top_feat:
        cross = df.groupby([top_feat, TARGET])[WEIGHT_COL].sum().unstack(fill_value=0)
        cross_pct = cross.div(cross.sum(axis=1), axis=0) * 100
        cross_pct = cross_pct.sort_values(cross_pct.columns[0], ascending=False).head(10)
        cross_pct.plot(kind="barh", stacked=True, ax=axes[1], colormap="Set3")
        axes[1].set_title(f"{top_feat} vs dispense_method (%)")
        axes[1].set_xlim(0, 100)
        axes[1].legend(title=TARGET, bbox_to_anchor=(1.02, 1), loc="upper left")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "00_dispense_overview.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {OUTPUT_DIR / '00_dispense_overview.png'}")


def save_selected_features(chi_df: pd.DataFrame, mi_df: pd.DataFrame) -> list[str]:
    """Select features (p < 0.05 and top by MI) and save to file."""
    sig = chi_df[chi_df["p_value"] < 0.05]["feature"].tolist()
    top_mi = mi_df.nlargest(5, "mutual_info")["feature"].tolist()
    selected = list(dict.fromkeys(sig + top_mi))  # union, preserve order
    with open(OUTPUT_DIR / "selected_features.txt", "w") as f:
        f.write("# Feature selection output\n")
        f.write("# Use these features for summary stats and model training\n\n")
        for s in selected:
            f.write(f"{s}\n")
    return selected


def main():
    parser = argparse.ArgumentParser(description="Feature selection for dispense method prediction")
    parser.add_argument(
        "data_path",
        nargs="?",
        default="output/base_data.csv",
        help="Path to base data CSV (output of 01_base_data.sql)",
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading data...")
    df = load_data(args.data_path)
    df = prepare_features(df)

    if TARGET not in df.columns:
        raise ValueError(f"Target column '{TARGET}' not found. Columns: {list(df.columns)}")

    print("Running feature selection...")
    chi_df = chi_square_scores(df)
    mi_df = mutual_info_scores(df)

    print("\nChi-square results:")
    print(chi_df.to_string(index=False))
    print("\nMutual information results:")
    print(mi_df.to_string(index=False))

    print("\nGenerating visualizations...")
    plot_dispense_method_overview(df)
    plot_feature_distributions(df)
    plot_feature_vs_dispense(df)
    plot_association_strength(chi_df, mi_df)

    selected = save_selected_features(chi_df, mi_df)
    chi_df.to_csv(OUTPUT_DIR / "chi_square_scores.csv", index=False)
    mi_df.to_csv(OUTPUT_DIR / "mutual_info_scores.csv", index=False)

    print(f"\nSelected features: {selected}")
    print(f"Outputs saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
