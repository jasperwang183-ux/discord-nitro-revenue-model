"""Write a formula-driven Excel workbook that mirrors cohorts.py cell for cell.

Every number traces back to the Assumptions sheet. The only pasted value is the conversion calibration scalar
(Params: k_cal), which Python solves; the Checks sheet shows it still hits the anchor.

Cohort sums use SUMPRODUCT of a sign-up row against a *reversed* survival curve, so a month's active subscribers
is one formula instead of a triangle. The Cohort_US_NitroM sheet lays one segment out as a full triangle so you can
rebuild a cohort by hand; Checks ties it back to the SUMPRODUCT line.
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from nitro_model.arpu import PLANS
from nitro_model.assumptions import Assumptions
from nitro_model.cohorts import calibrate
from nitro_model.params import BILLING, REACT_INTO, REGIONS, build_params

C0 = 3  # first month column (C)
HEAD = Font(bold=True)
INPUT = PatternFill("solid", fgColor="FFF2CC")
FMT_N, FMT_USD, FMT_PCT = "#,##0", "$#,##0", "0.0%"
PLATFORMS = ("WEB", "IOS", "ANDROID")

# (param name, assumption id, segment, scale)
SCALARS = [
    ("mau0", "mau_jan2025", "all", 1e6), ("mau_growth_first", "mau_growth_first", "all", 1),
    ("mau_growth_last", "mau_growth_last", "all", 1), ("conv_multiplier", "conv_multiplier", "all", 1),
    ("trial_share", "trial_share", "all", 1), ("trial_months", "trial_months", "all", 1),
    ("trial_to_paid", "trial_to_paid", "all", 1), ("count_trials_as_subs", "count_trials_as_subs", "all", 1),
    ("churn_m1", "churn_m1", "MONTHLY", 1), ("churn_m2", "churn_m2", "MONTHLY", 1),
    ("churn_m3", "churn_m3", "MONTHLY", 1), ("churn_tail", "churn_tail", "MONTHLY", 1),
    ("annual_renewal_first", "annual_renewal_first", "ANNUAL", 1),
    ("annual_renewal_later", "annual_renewal_later", "ANNUAL", 1),
    ("react_rate", "react_rate", "all", 1), ("react_window_months", "react_window_months", "all", 1),
    ("react_churn_tail", "react_churn_tail", "all", 1), ("open_subs", "open_subs", "all", 1e6),
    ("open_churn_tail", "open_churn_tail", "MONTHLY", 1), ("open_y1_share", "open_y1_share", "all", 1),
    ("avg_discount", "avg_discount", "all", 1), ("fee_web", "store_fee", "WEB", 1),
    ("fee_ios_y1", "store_fee", "IOS_Y1", 1), ("fee_ios_later", "store_fee", "IOS_LATER", 1),
    ("fee_android", "store_fee", "ANDROID", 1), ("cal_target_subs", "cal_subs_mid2025", "all", 1e6),
    ("cal_month_index", "cal_month_index", "all", 1),
]
REGION_VECTORS = ["mau_share", "conv_rate", "price_index", "indirect_tax", "open_region_mix"]
PLAN_VECTORS = ["plan_mix", "open_plan_mix", "list_price"]


def col(t: int) -> str:
    return get_column_letter(C0 + t)


class Book:
    def __init__(self, a: Assumptions, scenario: str = "base"):
        self.a, self.scenario = a, scenario
        self.p = build_params(a, scenario)
        self.T = len(self.p["months"])
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.ref: dict[str, str] = {}  # param name -> absolute cell, e.g. Params!$B$4
        self.rows: dict[tuple, int] = {}  # (sheet, key...) -> row
        self.last = col(self.T - 1)

    # ---------- helpers ----------
    def sheet(self, name: str, months: bool = True):
        ws = self.wb.create_sheet(name)
        if months:
            ws["A1"], ws["B1"] = "line", "segment"
            for t, m in enumerate(self.p["months"]):
                ws[f"{col(t)}1"] = m
                ws[f"{col(t)}2"] = t
            ws["A2"] = "month index (0 = Jan 2025)"
            for c in ws[1]:
                c.font = HEAD
            ws.freeze_panes = "C3"
            ws.column_dimensions["A"].width = 26
            ws.column_dimensions["B"].width = 18
        return ws

    def row_formula(self, ws, r: int, label: str, seg: str, fn, fmt: str = FMT_N):
        ws[f"A{r}"], ws[f"B{r}"] = label, seg
        for t in range(self.T):
            cell = ws[f"{col(t)}{r}"]
            cell.value = fn(t)
            cell.number_format = fmt

    def window(self, sheet: str, row: int, curve_row: int, t: int) -> str:
        rev_start = col(self.T - 1 - t)
        if t == 0:  # one-cell window: a plain product (pycel rejects one-cell SUMPRODUCT ranges)
            return f"{sheet}!$C${row}*Curves!${self.last}${curve_row}"
        return f"SUMPRODUCT({sheet}!$C${row}:${col(t)}${row},Curves!${rev_start}${curve_row}:${self.last}${curve_row})"

    def assumption_cell(self, aid: str, seg: str, column: str = "E") -> str:
        t = self.a.table
        rows = t[(t["id"] == aid) & (t["segment"] == seg) & t["scenario"].isin([self.scenario, "all"])]
        idx = rows.sort_values("scenario", key=lambda s: s.eq("all")).index[0]
        return f"Assumptions!${column}${idx + 2}"

    # ---------- sheets ----------
    def build(self) -> dict:
        self.readme()
        self.assumptions()
        self.params()
        self.curves()
        self.mau()
        self.prices()
        self.adds()
        self.paid()
        self.legacy()
        self.react()
        self.subs()
        self.revenue()
        self.cohort_sheet()
        self.checks()
        return {"rows": self.rows, "T": self.T}

    def readme(self):
        ws = self.sheet("README", months=False)
        lines = [
            "Discord Nitro subscription revenue model (portfolio project). All Discord figures are third-party estimates.",
            f"Scenario: {self.scenario}. Generated by nitro_model.excel_export from data/assumptions.csv; mirrors src/nitro_model/cohorts.py.",
            "Flow: Assumptions -> Params -> Curves / MAU / Prices -> Adds -> Paid, Legacy, React -> Subs -> Revenue -> Checks.",
            "Change inputs only on the Assumptions sheet (yellow cells on Params link there). Params!k_cal is solved in Python.",
            "Active subscribers = SUMPRODUCT(sign-ups to date, reversed survival curve). Cohort_US_NitroM shows one segment as a full triangle.",
            "Revenue is at reference (FY2025 average) FX; the FX path arrives in Milestone 3.",
        ]
        for i, line in enumerate(lines, 1):
            ws[f"A{i}"] = line
        ws.column_dimensions["A"].width = 120

    def assumptions(self):
        ws = self.sheet("Assumptions", months=False)
        t = self.a.table
        ws.append(list(t.columns))
        for c in ws[1]:
            c.font = HEAD
        for _, r in t.iterrows():
            ws.append([None if (isinstance(v, float) and v != v) else v for v in r.tolist()])
        ws.freeze_panes = "A2"

    def params(self):
        ws = self.sheet("Params", months=False)
        ws.append(["param", "value", "linked to"])
        for c in ws[1]:
            c.font = HEAD

        def add(name: str, formula, note: str, fmt: str = "General"):
            ws.append([name, formula, note])
            r = ws.max_row
            ws[f"B{r}"].number_format = fmt
            ws[f"B{r}"].fill = INPUT
            self.ref[name] = f"Params!$B${r}"

        for name, aid, seg, scale in SCALARS:
            cell = self.assumption_cell(aid, seg)
            add(name, f"={cell}*{scale:g}" if scale != 1 else f"={cell}", f"{aid}[{seg}]")
        lo, hi = (self.assumption_cell("cal_nitro_rev_2025", "all", c) for c in ("G", "H"))
        add("cal_rev_low", f"={lo}*1000000", "cal_nitro_rev_2025 low")
        add("cal_rev_high", f"={hi}*1000000", "cal_nitro_rev_2025 high")
        for v in REGION_VECTORS:
            for r in REGIONS:
                add(f"{v}[{r}]", f"={self.assumption_cell(v, r)}", f"{v}[{r}]")
        for r in REGIONS:
            for pl in PLATFORMS:
                add(f"platform_mix[{r}|{pl}]", f"={self.assumption_cell('platform_mix', f'{r}|{pl}')}", f"platform_mix[{r}|{pl}]")
        for v in PLAN_VECTORS:
            for pn in PLANS:
                add(f"{v}[{pn}]", f"={self.assumption_cell(v, pn)}", f"{v}[{pn}]")
        for pn, months in PLANS.items():
            add(f"billing_months[{pn}]", months, "structural: 1 = monthly, 12 = annual (recognized ratably)")
        add("k_cal", calibrate(self.p), "SOLVED in Python: conversion scalar that hits the subscriber anchor (see Checks)")
        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["C"].width = 70

    def curves(self):
        ws = self.sheet("Curves", months=False)
        R = self.ref
        T, last = self.T, self.last
        ws["A1"], ws["B1"] = "curve", "age (months) ->"
        for a in range(T):
            ws[f"{col(a)}1"] = a
        age = lambda a: f"{col(a)}$1"  # noqa: E731
        names = ["S_MONTHLY", "S_ANNUAL", "D_MONTHLY", "D_ANNUAL", "S_REACT", "D_REACT", "K_REACT",
                 "S_MONTHLY_Y1", "S_ANNUAL_Y1", "S_REACT_Y1"]
        fwd = {n: i + 2 for i, n in enumerate(names)}
        rev = {n: i + 2 + len(names) + 1 for i, n in enumerate(names)}
        hz = (f"IF({{a}}=1,{R['churn_m1']},IF({{a}}=2,{R['churn_m2']},IF({{a}}=3,{R['churn_m3']},{R['churn_tail']})))")
        for a in range(T):
            c, prev = col(a), col(a - 1) if a else None
            f = {
                "S_MONTHLY": "=1" if a == 0 else f"={prev}{fwd['S_MONTHLY']}*(1-{hz.format(a=age(a))})",
                "S_ANNUAL": f"=IF({age(a)}<12,1,{R['annual_renewal_first']}*{R['annual_renewal_later']}^(INT({age(a)}/12)-1))",
                "D_MONTHLY": "=0" if a == 0 else f"={prev}{fwd['S_MONTHLY']}-{c}{fwd['S_MONTHLY']}",
                "D_ANNUAL": "=0" if a == 0 else f"={prev}{fwd['S_ANNUAL']}-{c}{fwd['S_ANNUAL']}",
                "S_REACT": f"=(1-{R['react_churn_tail']})^{age(a)}",
                "D_REACT": "=0" if a == 0 else f"={prev}{fwd['S_REACT']}-{c}{fwd['S_REACT']}",
                "K_REACT": (f"=IF(AND({age(a)}>=1,{age(a)}<={R['react_window_months']}),"
                            f"{R['react_rate']}*(1-{R['react_rate']})^({age(a)}-1),0)"),
                "S_MONTHLY_Y1": f"=IF({age(a)}<12,{c}{fwd['S_MONTHLY']},0)",
                "S_ANNUAL_Y1": f"=IF({age(a)}<12,{c}{fwd['S_ANNUAL']},0)",
                "S_REACT_Y1": f"=IF({age(a)}<12,{c}{fwd['S_REACT']},0)",
            }
            for n in names:
                ws[f"{c}{fwd[n]}"] = f[n]
                ws[f"{c}{rev[n]}"] = f"=INDEX($C${fwd[n]}:${last}${fwd[n]},{T - a})"
        for n in names:
            ws[f"A{fwd[n]}"] = n
            ws[f"A{rev[n]}"] = f"{n} reversed"
            self.rows[("Curves", n)] = rev[n]
        ws[f"A{len(names) + 2}"] = "Reversed rows run oldest age first so SUMPRODUCT can pair them with sign-ups to date."
        ws.column_dimensions["A"].width = 22

    def mau(self):
        ws = self.sheet("MAU")
        R = self.ref
        years = self.T // 12
        g = f"({R['mau_growth_first']}+({R['mau_growth_last']}-{R['mau_growth_first']})*INT({{c}}$2/12)/{years - 1})"
        self.row_formula(ws, 3, "MAU total", "all",
                         lambda t: f"={R['mau0']}" if t == 0 else f"={col(t - 1)}3*(1+{g.format(c=col(t))})^(1/12)")
        for i, r in enumerate(REGIONS):
            row = 4 + i
            self.row_formula(ws, row, "MAU", r, lambda t, r=r: f"={col(t)}$3*{R[f'mau_share[{r}]']}")
            self.rows[("MAU", r)] = row

    def prices(self):
        ws = self.sheet("Prices", months=False)
        R = self.ref
        ws.append(["region", "plan", "list $/mo", "x regional index", "after discount & VAT",
                   "keep after fees (yr 1)", "keep after fees (later)", "net $/mo (yr 1)", "net $/mo (later)"])
        for c in ws[1]:
            c.font = HEAD
        for r in REGIONS:
            for pn in PLANS:
                n = ws.max_row + 1
                mix = [R[f"platform_mix[{r}|{pl}]"] for pl in PLATFORMS]
                ws.append([
                    r, pn,
                    f"={R[f'list_price[{pn}]']}/{R[f'billing_months[{pn}]']}",
                    f"=C{n}*{R[f'price_index[{r}]']}",
                    f"=D{n}*(1-{R['avg_discount']})*(1-{R[f'indirect_tax[{r}]']})",
                    f"={mix[0]}*(1-{R['fee_web']})+{mix[1]}*(1-{R['fee_ios_y1']})+{mix[2]}*(1-{R['fee_android']})",
                    f"={mix[0]}*(1-{R['fee_web']})+{mix[1]}*(1-{R['fee_ios_later']})+{mix[2]}*(1-{R['fee_android']})",
                    f"=E{n}*F{n}", f"=E{n}*G{n}",
                ])
                self.rows[("Prices", r, pn)] = n
        for row in ws.iter_rows(min_row=2, min_col=3):
            for c in row:
                c.number_format = "$0.000" if c.column in (3, 4, 5, 8, 9) else "0.000"

    def adds(self):
        ws = self.sheet("Adds")
        R = self.ref
        lines = ["gross adds", "trial starts", "direct paid starts", "trials ending", "trials converted",
                 "trials lost", "cum trial starts", "cum trials ending", "trials active", "paid starts"]
        row = 3
        for r in REGIONS:
            for pn in PLANS:
                seg = f"{r}|{pn}"
                k = {name: row + i for i, name in enumerate(lines)}
                rng = lambda name: f"$C${k[name]}:${self.last}${k[name]}"  # noqa: E731
                f = {
                    "gross adds": lambda t: (f"=MAU!{col(t)}{self.rows[('MAU', r)]}*{R[f'conv_rate[{r}]']}"
                                             f"*{R['conv_multiplier']}*{R['k_cal']}*{R[f'plan_mix[{pn}]']}"),
                    "trial starts": lambda t: f"={col(t)}{k['gross adds']}*{R['trial_share']}",
                    "direct paid starts": lambda t: f"={col(t)}{k['gross adds']}-{col(t)}{k['trial starts']}",
                    "trials ending": lambda t: (f"=IF({col(t)}$2>={R['trial_months']},"
                                                f"INDEX({rng('trial starts')},{col(t)}$2-{R['trial_months']}+1),0)"),
                    "trials converted": lambda t: f"={col(t)}{k['trials ending']}*{R['trial_to_paid']}",
                    "trials lost": lambda t: f"={col(t)}{k['trials ending']}-{col(t)}{k['trials converted']}",
                    "cum trial starts": lambda t: f"=SUM($C{k['trial starts']}:{col(t)}{k['trial starts']})",
                    "cum trials ending": lambda t: f"=SUM($C{k['trials ending']}:{col(t)}{k['trials ending']})",
                    "trials active": lambda t: f"={col(t)}{k['cum trial starts']}-{col(t)}{k['cum trials ending']}",
                    "paid starts": lambda t: f"={col(t)}{k['direct paid starts']}+{col(t)}{k['trials converted']}",
                }
                for name in lines:
                    self.row_formula(ws, k[name], name, seg, f[name])
                    self.rows[("Adds", name, r, pn)] = k[name]
                row += len(lines) + 1

    def paid(self):
        ws = self.sheet("Paid")
        row = 3
        for r in REGIONS:
            for pn in PLANS:
                seg, billing = f"{r}|{pn}", BILLING[pn]
                src = self.rows[("Adds", "paid starts", r, pn)]
                spec = [("active", f"S_{billing}"), ("active yr 1", f"S_{billing}_Y1"), ("churned", f"D_{billing}")]
                for i, (name, curve) in enumerate(spec):
                    cr = self.rows[("Curves", curve)]
                    self.row_formula(ws, row + i, name, seg, lambda t, cr=cr: "=" + self.window("Adds", src, cr, t))
                    self.rows[("Paid", name, r, pn)] = row + i
                row += len(spec) + 1

    def legacy(self):
        ws = self.sheet("Legacy")
        R = self.ref
        self.row_formula(ws, 3, "first-year share", "all",
                         lambda t: f"={R['open_y1_share']}*MAX(0,1-{col(t)}$2/12)", FMT_PCT)
        self.rows[("Legacy", "y1")] = 3
        row = 5
        rl = R["annual_renewal_later"]
        for r in REGIONS:
            for pn in PLANS:
                seg = f"{r}|{pn}"
                ws[f"A{row}"], ws[f"B{row}"] = "opening book (Jan 2025)", seg
                ws[f"C{row}"] = f"={R['open_subs']}*{R[f'open_region_mix[{r}]']}*{R[f'open_plan_mix[{pn}]']}"
                ws[f"C{row}"].number_format = FMT_N
                L0 = f"$C${row}"
                if BILLING[pn] == "ANNUAL":
                    fn = lambda t: (f"={L0}*((MOD({col(t)}$2,12)+1)*{rl}^(INT({col(t)}$2/12)+1)"
                                    f"+(11-MOD({col(t)}$2,12))*{rl}^INT({col(t)}$2/12))/12")
                else:
                    fn = lambda t: f"={L0}*(1-{R['open_churn_tail']})^({col(t)}$2+1)"
                self.row_formula(ws, row + 1, "active", seg, fn)
                self.row_formula(ws, row + 2, "churned", seg, lambda t: (f"={L0}-C{row + 1}" if t == 0
                                                                         else f"={col(t - 1)}{row + 1}-{col(t)}{row + 1}"))
                self.rows[("Legacy", "L0", r, pn)] = row
                self.rows[("Legacy", "active", r, pn)] = row + 1
                self.rows[("Legacy", "churned", r, pn)] = row + 2
                row += 4

    def react(self):
        ws = self.sheet("React")
        lines = ["churn pool inflow", "reactivations out", "reactivated in", "active", "active yr 1", "churned"]
        row = 3
        k = {}
        for r in REGIONS:
            for pn in PLANS:
                k[(r, pn)] = {name: row + i for i, name in enumerate(lines)}
                row += len(lines) + 1
        cur = {n: self.rows[("Curves", n)] for n in ("K_REACT", "S_REACT", "S_REACT_Y1", "D_REACT")}
        for r in REGIONS:
            for pn in PLANS:
                seg, kk = f"{r}|{pn}", k[(r, pn)]
                sources = [src for src in PLANS if REACT_INTO[src] == pn]
                f = {
                    "churn pool inflow": lambda t: (f"=Paid!{col(t)}{self.rows[('Paid', 'churned', r, pn)]}"
                                                    f"+Legacy!{col(t)}{self.rows[('Legacy', 'churned', r, pn)]}"),
                    "reactivations out": lambda t: "=" + self.window("React", kk["churn pool inflow"], cur["K_REACT"], t),
                    "reactivated in": lambda t: ("=" + "+".join(f"{col(t)}{k[(r, s)]['reactivations out']}" for s in sources)
                                                 if sources else "=0"),
                    "active": lambda t: "=" + self.window("React", kk["reactivated in"], cur["S_REACT"], t),
                    "active yr 1": lambda t: "=" + self.window("React", kk["reactivated in"], cur["S_REACT_Y1"], t),
                    "churned": lambda t: "=" + self.window("React", kk["reactivated in"], cur["D_REACT"], t),
                }
                for name in lines:
                    self.row_formula(ws, kk[name], name, seg, f[name])
                    self.rows[("React", name, r, pn)] = kk[name]

    def subs(self):
        ws = self.sheet("Subs")
        R = self.ref
        lines = ["opening", "new", "reactivated", "churned", "closing", "paying"]
        total = {name: 3 + i for i, name in enumerate(lines)}
        row = 3 + len(lines) + 1
        seg_rows = {name: [] for name in lines}
        cnt = R["count_trials_as_subs"]
        for r in REGIONS:
            for pn in PLANS:
                seg = f"{r}|{pn}"
                kk = {name: row + i for i, name in enumerate(lines)}
                g = lambda sheet, name, t: f"{sheet}!{col(t)}{self.rows[(sheet, name, r, pn)]}"  # noqa: E731
                f = {
                    "opening": lambda t: (f"=Legacy!$C${self.rows[('Legacy', 'L0', r, pn)]}" if t == 0
                                          else f"={col(t - 1)}{kk['closing']}"),
                    "new": lambda t: (f"={g('Adds', 'direct paid starts', t)}+IF({cnt}=1,"
                                      f"{g('Adds', 'trial starts', t)},{g('Adds', 'trials converted', t)})"),
                    "reactivated": lambda t: f"={g('React', 'reactivated in', t)}",
                    "churned": lambda t: (f"={g('Legacy', 'churned', t)}+{g('Paid', 'churned', t)}"
                                          f"+{g('React', 'churned', t)}+{cnt}*{g('Adds', 'trials lost', t)}"),
                    "paying": lambda t: f"={g('Legacy', 'active', t)}+{g('Paid', 'active', t)}+{g('React', 'active', t)}",
                    "closing": lambda t: f"={col(t)}{kk['paying']}+{cnt}*{g('Adds', 'trials active', t)}",
                }
                for name in lines:
                    self.row_formula(ws, kk[name], name, seg, f[name])
                    self.rows[("Subs", name, r, pn)] = kk[name]
                    seg_rows[name].append(kk[name])
                row += len(lines) + 1
        for name in lines:
            self.row_formula(ws, total[name], name, "TOTAL",
                             lambda t, name=name: "=SUM(" + ",".join(f"{col(t)}{x}" for x in seg_rows[name]) + ")")
            for c in ws[total[name]]:
                c.font = HEAD
            self.rows[("Subs", name, "TOTAL")] = total[name]

    def revenue(self):
        ws = self.sheet("Revenue")
        y1row = self.rows[("Legacy", "y1")]
        row, seg_rows = 5, []
        for r in REGIONS:
            for pn in PLANS:
                pr = self.rows[("Prices", r, pn)]
                g = lambda sheet, name, t: f"{sheet}!{col(t)}{self.rows[(sheet, name, r, pn)]}"  # noqa: E731
                y1 = lambda t: (f"({g('Paid', 'active yr 1', t)}+{g('React', 'active yr 1', t)}"  # noqa: E731
                                f"+{g('Legacy', 'active', t)}*Legacy!{col(t)}${y1row})")
                self.row_formula(ws, row, "net revenue $", f"{r}|{pn}", lambda t: (
                    f"={y1(t)}*Prices!$H${pr}+({g('Subs', 'paying', t)}-{y1(t)})*Prices!$I${pr}"), FMT_USD)
                self.rows[("Revenue", r, pn)] = row
                seg_rows.append(row)
                row += 1
        self.row_formula(ws, 3, "net revenue $", "TOTAL",
                         lambda t: "=SUM(" + ",".join(f"{col(t)}{x}" for x in seg_rows) + ")", FMT_USD)
        for c in ws[3]:
            c.font = HEAD
        self.rows[("Revenue", "TOTAL")] = 3

    def cohort_sheet(self):
        r, pn = "US_CA", "NITRO_M"
        ws = self.sheet("Cohort_US_NitroM")
        src = self.rows[("Adds", "paid starts", r, pn)]
        s_row = 2  # Curves forward S_MONTHLY
        ws["A3"] = "Rows: sign-up month (cohort). Columns: calendar month. Cell = sign-ups x survival at age (month - cohort)."
        first = 5
        for c in range(self.T):
            row = first + c
            ws[f"A{row}"] = f"cohort {self.p['months'][c]}"
            ws[f"B{row}"] = f"=INDEX(Adds!$C${src}:${self.last}${src},{c + 1})"
            ws[f"B{row}"].number_format = FMT_N
            for t in range(c, self.T):
                cell = ws[f"{col(t)}{row}"]
                cell.value = f"=$B{row}*INDEX(Curves!$C${s_row}:${self.last}${s_row},{col(t)}$2-{c}+1)"
                cell.number_format = FMT_N
        tot = first + self.T + 1
        self.row_formula(ws, tot, "sum of cohorts", f"{r}|{pn}", lambda t: f"=SUM({col(t)}{first}:{col(t)}{tot - 2})")
        self.row_formula(ws, tot + 1, "Paid sheet active", f"{r}|{pn}",
                         lambda t: f"=Paid!{col(t)}{self.rows[('Paid', 'active', r, pn)]}")
        self.rows[("Cohort", "sum")], self.rows[("Cohort", "paid")] = tot, tot + 1

    def checks(self):
        ws = self.sheet("Checks")
        R, S = self.ref, self.rows
        rf = {n: S[("Subs", n, "TOTAL")] for n in ("opening", "new", "reactivated", "churned", "closing")}
        self.row_formula(ws, 3, "roll-forward gap", "TOTAL", lambda t: (
            f"=Subs!{col(t)}{rf['opening']}+Subs!{col(t)}{rf['new']}+Subs!{col(t)}{rf['reactivated']}"
            f"-Subs!{col(t)}{rf['churned']}-Subs!{col(t)}{rf['closing']}"), "0.000000")
        self.row_formula(ws, 4, "cohort triangle tie gap", "US_CA|NITRO_M", lambda t: (
            f"=Cohort_US_NitroM!{col(t)}{S[('Cohort', 'sum')]}-Cohort_US_NitroM!{col(t)}{S[('Cohort', 'paid')]}"), "0.000000")
        last = self.last
        closing = f"Subs!$C${rf['closing']}:${last}${rf['closing']}"
        rev = f"Revenue!$C${S[('Revenue', 'TOTAL')]}:$N${S[('Revenue', 'TOTAL')]}"
        checks = [
            ("Roll-forward holds every month", f"=MAX(C3:{last}3)-MIN(C3:{last}3)<0.001"),
            ("Cohort triangle ties every month", f"=MAX(C4:{last}4)-MIN(C4:{last}4)<0.001"),
            ("Subscribers at calibration month", f"=INDEX({closing},{R['cal_month_index']})"),
            ("Anchor", f"={R['cal_target_subs']}"),
            ("Calibration hits anchor", "=ABS(C8-C9)<1"),
            ("FY2025 net revenue", f"=SUM({rev})"),
            ("Inside public band", f"=AND(C11>={R['cal_rev_low']},C11<={R['cal_rev_high']})"),
        ]
        for i, (label, formula) in enumerate(checks):
            ws[f"A{6 + i}"], ws[f"C{6 + i}"] = label, formula
            ws[f"C{6 + i}"].number_format = FMT_N
        self.rows[("Checks", "fy25")] = 11


def export(path: Path, scenario: str = "base") -> dict:
    book = Book(Assumptions.load(), scenario)
    layout = book.build()
    path.parent.mkdir(parents=True, exist_ok=True)
    book.wb.save(path)
    return layout
