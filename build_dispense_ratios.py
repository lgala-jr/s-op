"""
Build dispense method ratio lookup from prior 6 months of data.
Uses recommended features (product_type, wh_name) to compute % split by dispense_method.
Output: ratios you can apply to forecast volume (e.g., forecast × pct = estimated dispense volume).

Application: Given forecast volume by (product_type, wh_name), multiply by pct_of_volume
to estimate automated vs manual vs other. Use hierarchical fallback if no exact match.
"""

import pandas as pd
from pathlib import Path

BASE = Path("output/base_data.csv")
OUT = Path("output")
ALLOWED_WH = {"OHIO", "BEYONDRX_OH", "BEYONDRX_AZ"}
VOLUME_COL = "order_qty"


def load_and_filter() -> pd.DataFrame:
    df = pd.read_csv(BASE)
    df.columns = df.columns.str.strip()
    if "wh_name" in df.columns:
        df = df[df["wh_name"].astype(str).str.upper().isin(ALLOWED_WH)].copy()
    if VOLUME_COL not in df.columns:
        df[VOLUME_COL] = 1
    return df.dropna(subset=["dispense_method"])


def build_ratios(df: pd.DataFrame, group_cols: list[str], level: int) -> pd.DataFrame:
    """Compute pct_of_volume by dispense_method within each group."""
    by = group_cols + ["dispense_method"] if group_cols else ["dispense_method"]
    agg = df.groupby(by).agg(
        fill_count=("fill_id", "nunique"),
        order_qty_sum=(VOLUME_COL, "sum"),
    ).reset_index()
    tot_by = group_cols if group_cols else []
    totals = agg.groupby(tot_by)["order_qty_sum"].transform("sum") if tot_by else agg["order_qty_sum"].sum()
    agg["pct_of_volume"] = (agg["order_qty_sum"] / totals * 100).round(2)
    agg["level"] = level
    return agg


def main():
    df = load_and_filter()
    rows = []

    # Level 1: product_type × wh_name (primary for forecast)
    if "product_type" in df.columns and "wh_name" in df.columns:
        r1 = build_ratios(df, ["product_type", "wh_name"], level=1)
        rows.append(r1)

    # Level 2: product_type only (fallback when wh not in forecast)
    if "product_type" in df.columns:
        r2 = build_ratios(df, ["product_type"], level=2)
        r2["wh_name"] = "(all)"
        rows.append(r2[["product_type", "wh_name", "dispense_method", "fill_count", "order_qty_sum", "pct_of_volume", "level"]])

    # Level 3: wh_name only (fallback when product not in forecast)
    if "wh_name" in df.columns:
        r3 = build_ratios(df, ["wh_name"], level=3)
        r3["product_type"] = "(all)"
        rows.append(r3[["product_type", "wh_name", "dispense_method", "fill_count", "order_qty_sum", "pct_of_volume", "level"]])

    # Level 4: overall
    r4 = build_ratios(df, [], level=4)
    r4["product_type"] = "(all)"
    r4["wh_name"] = "(all)"
    rows.append(r4[["product_type", "wh_name", "dispense_method", "fill_count", "order_qty_sum", "pct_of_volume", "level"]])

    out = pd.concat(rows, ignore_index=True)
    out = out[["level", "product_type", "wh_name", "dispense_method", "pct_of_volume", "fill_count", "order_qty_sum"]]
    out.to_csv(OUT / "dispense_ratio_lookup.csv", index=False)
    print(f"Saved: {OUT / 'dispense_ratio_lookup.csv'}")
    print(f"  Levels: 1=product_type×wh_name, 2=product_type, 3=wh_name, 4=overall")
    print(f"  Use level 1 first; fall back to 2/3/4 if no match.")


if __name__ == "__main__":
    main()
