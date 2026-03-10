"""
Generate summary stats and distribution CSVs from base_data.csv.
Use when BigQuery is not available - computes equivalent of 02, 02b, 03, 03b from base data.
Scope: internal pharmacies only (Ohio, Arizona).
"""

import pandas as pd
from pathlib import Path

BASE = Path("output/base_data.csv")
OUT = Path("output")
ALLOWED_WH = {"OHIO", "BEYONDRX_OH", "BEYONDRX_AZ"}


def main():
    df = pd.read_csv(BASE)
    df.columns = df.columns.str.strip()
    if "wh_name" in df.columns:
        df = df[df["wh_name"].astype(str).str.upper().isin(ALLOWED_WH)].copy()
    w = "order_qty" if "order_qty" in df.columns else None
    if w is None:
        df["order_qty"] = 1
        w = "order_qty"

    # 02_summary_stats equivalent
    tot_fills = df["fill_id"].nunique()
    tot_qty = df[w].sum()
    s1 = df.groupby("dispense_method").agg(
        fill_count=("fill_id", "nunique"),
        order_qty_sum=(w, "sum"),
    ).reset_index()
    s1["pct_of_total_fills"] = (s1["fill_count"] / tot_fills * 100).round(2)
    s1["pct_of_total_order_qty"] = (s1["order_qty_sum"] / tot_qty * 100).round(2)
    s1.insert(0, "cut_dimension", "Overall")
    s1.to_csv(OUT / "summary_stats.csv", index=False)
    print(f"  {OUT / 'summary_stats.csv'}")

    # 02b_summary_by_dimensions
    pt = "product_type" if "product_type" in df.columns else None
    if pt:
        s2 = df.groupby([pt, "dispense_method"]).agg(
            fill_count=("fill_id", "nunique"),
            order_qty_sum=(w, "sum"),
        ).reset_index()
        s2.insert(0, "dimension", "product_type")
        s2.to_csv(OUT / "summary_by_dimensions.csv", index=False)
        print(f"  {OUT / 'summary_by_dimensions.csv'}")

    # 03_distributions
    if pt:
        by_pt = s2.copy()
        pt_totals = by_pt.groupby(pt)[["fill_count", "order_qty_sum"]].sum().reset_index()
        by_pt = by_pt.merge(pt_totals, on=pt, suffixes=("", "_total"))
        by_pt["pct_within_product_type_by_fills"] = (by_pt["fill_count"] / by_pt["fill_count_total"] * 100).round(2)
        by_pt["pct_within_product_type_by_order_qty"] = (by_pt["order_qty_sum"] / by_pt["order_qty_sum_total"] * 100).round(2)
        by_pt = by_pt.drop(columns=["fill_count_total", "order_qty_sum_total"])
        by_pt.to_csv(OUT / "distribution_by_product_type.csv", index=False)
        print(f"  {OUT / 'distribution_by_product_type.csv'}")

    # 03b_distribution_by_wh
    wh = "wh_name" if "wh_name" in df.columns else None
    if wh:
        by_wh = df.groupby([wh, "dispense_method"]).agg(
            fill_count=("fill_id", "nunique"),
            order_qty_sum=(w, "sum"),
        ).reset_index()
        wh_totals = by_wh.groupby(wh)[["fill_count", "order_qty_sum"]].sum().reset_index()
        by_wh = by_wh.merge(wh_totals, on=wh, suffixes=("", "_total"))
        by_wh["pct_within_wh_by_fills"] = (by_wh["fill_count"] / by_wh["fill_count_total"] * 100).round(2)
        by_wh["pct_within_wh_by_order_qty"] = (by_wh["order_qty_sum"] / by_wh["order_qty_sum_total"] * 100).round(2)
        by_wh = by_wh.drop(columns=["fill_count_total", "order_qty_sum_total"])
        by_wh.to_csv(OUT / "distribution_by_wh.csv", index=False)
        print(f"  {OUT / 'distribution_by_wh.csv'}")

    print("Summary and distribution CSVs generated.")

if __name__ == "__main__":
    main()
