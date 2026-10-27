---
name: "cam-business-income"
description: "Analyse a Precisa-style CAM / bank-statement Excel report to estimate a borrower's yearly business income and flag cashflow irregularities, output as JSON."
---

# CAM Report → Yearly Business Income (JSON)

Use this when the user attaches a CAM / bank-statement analysis Excel (Precisa "Account Report" format, single- or multi-account: sheets like Summary, Overview, Counterparty, Transactions / UPI txns, Loans, Inter Bank Transfers, Irregularities, Categories, Daily balance) and wants business income for underwriting.

## 1. Inputs (ask with AskUserQuestion only for what is missing)

- **Type of business**: Retail / Wholesale / Manufacturing / Services
- **Nature of business activity** (e.g. "Kirana store", "Contract stitching – men's shorts")
- **Profit %** (margin applied to turnover). If the user doesn't give one, use the default for the type. The script applies it automatically when `--profit` is left out, so don't ask for it:

  | Type | Default margin |
  |---|---|
  | Wholesale trading | 8% |
  | Retail trading | 20% |
  | Services | 40% |
  | Manufacturing | 25% |

- Optional: **family member names** (credits from them are excluded); **other own-account names/aliases**

## 2. Run the analyser

1. Copy the upload into its own empty folder in the scratchpad (e.g. `<scratch>/in/report.xlsx`).
2. Write the script at the bottom of this file to `<scratch>/cam_income.py` (outside the input folder).
3. Run:
```
python3 -I -W ignore <scratch>/cam_income.py <scratch>/in/report.xlsx --type "<type>" --nature "<nature>" [--profit <pct>] [--family "A,B"] [--own "alias"] --out <scratch>/draft.json
```
The draft contains accounts, balances, a counterparty-level credit classification, the income computation, the channel mix, business-match checks and the evidence for irregularities. `inputs.profit_margin_source` says whether the margin was given ("user") or defaulted ("default").

## 3. Income rule

**Business income = all credits − own other accounts − loans/credit lines − family members − personal (two-way) parties − refunds/reversals/interest − suspected card-rotation credits.**

**Micro and small businesses sell through mixed channels.** One shop may have a retail counter, sell wholesale and do job-work. So:
- UPI/NEFT/IMPS receipts coming from **many different payers count as business income**, whether the payer is a firm or an individual and whatever the ticket size.
- An individual payer is excluded as "personal" only when money also flows **back to the same party** (two-way / accommodation), when they are own or family, or when the analyst decides after review.
- Do not exclude a payer just because the business type is "B2B" or "B2C".
- **Payment-aggregator / QR settlements** (PhonePe, Paytm, BharatPe, Razorpay, etc.) are sales if they are frequent (about 8 or more a month). If they are occasional, treat them as card-to-account rotation, especially when the same amount leaves within a day.

## 4. Review and correct (do not skip)

Check every party above about ₹10K in `credit_classification`. Fix any mistakes with an overrides file (`{"name substring": "class"}`) and re-run with `--overrides`. The classes are: business | own | loan | family | personal | card_rotation | refund_reversal | unidentified.

Things to check by hand:
- **Report mislabels.** "Tax Return" may actually be an RTGS from a lender (Transactree = Lendbox). "Charges Reversed" may contain real receipts (for example, a narration like "Stiching Charges").
- **Own accounts.** Look for the holder's own name, self cheques and inter-bank transfers. Own-name credits that don't match a submitted account point to an **undisclosed account**; note it.
- **Two-way name matching is fuzzy.** Confirm a match before excluding the party, and drop false matches (app names, truncated names).
- **"Unknown" counterparty credits.** Split them by narration (loan, refund, OTP/cashback, interest). Some banks hide most payer names; then most inflows stay "unidentified" but still count as business. Say so in the notes.

## 5. Cashflow vs business type (mixed channels allowed)

Report `channel_mix` (B2B business-named % vs individual payers %, number of unique payers, share of small-ticket UPI, QR/P2M receipts). Then check that the **declared primary channel is visible**. Don't demand a pure pattern.

| Type | Should be visible |
|---|---|
| Retail (Kirana, tea, sweets, bakery, tyre shop) | Frequent small UPI receipts from many payers; supplier purchases. Bulk/wholesale orders are fine as well |
| Services (salon, auto repair, electrician, plumber, carpenter, software, hotel, restaurant) | Frequent small UPI receipts from many payers |
| Services as job-work / contract manufacturing | Some bulk receipts from principals, plus individual payers; many small payouts to workers |
| Wholesale | Bulk receipts from trade buyers; regular bulk payments to suppliers. Counter sales are fine as well |
| Manufacturing | B2B receipts; raw-material purchases; wage payouts |

Verdict: MATCH / PARTIAL MATCH / MISMATCH, plus a note on how uneven the volume is month to month. If no supplier purchases are visible, say so (they may be paid in cash or from another account).

## 6. Irregularities to look for

- Gambling (betting, fantasy and rummy apps). F&O, crypto or trading platforms, including unknown "trade" merchants. If many debits have no payee name, say that these cannot be fully ruled out.
- Credit card rotation: aggregator/card-to-account credits, the same amount coming in and going out within a day, CRED or card bill payments.
- The same party with flows in both directions.
- Money laundering and other suspicious patterns: ₹1 test payments followed by amounts just under a threshold (9,999 / 49,999); loan money diverted soon after it is disbursed; undisclosed accounts; repeated UTRs.
- Large instant withdrawals followed by deposits, and large credits drained within a few days.
- Cash handling: cash as a % of credits or debits (above 30% is high, 15–30% is moderate).
- Also: missed EMIs, bounces, many lenders, dormant accounts. If the declared margin looks unrealistic, give the income at a typical margin as well.

## 7. Output

Write `/mnt/user-data/outputs/<Borrower>_Yearly_Income.json` (values in ₹). Do **not** include a combined_balance section. Set `profit_margin_source` to "default" when the default margin was used, otherwise "user".

```json
{
  "inputs": {"business_type": "", "nature_of_business": "", "profit_margin_pct": 0, "profit_margin_source": "user"},
  "accounts": [{"bank": "", "account_no": "", "type": "", "active_period": "", "duration_months": 0, "average_monthly_balance": 0}],
  "yearly_income": {
    "total_credits": 0, "less_own_accounts": 0, "less_loans_and_credit_lines": 0, "less_family_members": 0,
    "less_two_way_personal_parties": 0, "less_card_rotation_aggregator_credits": 0, "less_refunds_reversals_interest": 0,
    "net_business_inflows": 0, "monthly_business_turnover": 0, "yearly_business_turnover": 0,
    "profit_margin_pct": 0, "yearly_income": 0, "monthly_income": 0,
    "channel_mix": {"b2b_pct": 0, "individual_upi_payers_pct": 0, "unique_payers": 0}
  },
  "notes": ["max 6 very short points"]
}
```

**Notes: at most 6 points. Keep each to one short line (about 15 words or fewer)**, using key ₹ figures and no long explanations. Cover these in order:
1. Business fit
2. Exclusions
3. Card rotation and two-way flows
4. Red flags (gambling/F&O/suspicious)
5. Cash and loans/EMIs
6. Margin sensitivity and risk rating (LOW / MEDIUM / MEDIUM-HIGH / HIGH)

Example: `"Card rotation likely: PhonePe credits sent out the same day (Rs 19,622 x2)."`

Yearly turnover = net business inflows ÷ assessment-window months × 12. Yearly income = turnover × profit %. Validate the JSON with `python3 -m json.tool`. In chat, reply in 2–3 lines.

## Analyser script (`cam_income.py`)

```python
#!/usr/bin/env python3
"""Analyse a Precisa-style CAM / bank-statement Excel report and estimate yearly business income.

Usage:
  python3 cam_income.py REPORT.xlsx --type services --nature "Contract stitching - men shorts" \
      [--profit 50] [--family "Name1,Name2"] [--own "alias1,alias2"] [--overrides overrides.json] \
      [--out result.json]

overrides.json (optional) lets the analyst correct counterparty classes after review:
  {"Riya International": "business", "Mohd Saif Naqvi": "personal", "Rtgstransactree": "loan"}
  Keys are case-insensitive substrings of the counterparty name. Classes:
  business | own | loan | family | personal | card_rotation | refund_reversal | unidentified
"""
import argparse, json, re, sys
from datetime import datetime
from collections import defaultdict
import openpyxl
import pandas as pd

# ----------------------------------------------------------------- keyword lists
GAMBLING = r"dream ?11|\bmpl\b|my11|rummy|junglee|a23|poker|winzo|zupee|ludo|teen ?patti|casino|\bbet|1xbet|parimatch|stake\.|fun88|aviator|colou?r ?pred|probo|lottery|satta|gamezy|howzat|playship|fantasy|\bgame|gaming"
FNO = r"zerodha|groww|upstox|angel ?(one|broking)|\bdhan\b|fyers|5paisa|sharekhan|icici ?sec|hdfc ?sec|kotak ?sec|motilal|iifl ?sec|nse ?clearing|bse ?ltd|indian clearing|binance|wazirx|coindcx|coinswitch|mudrex|crypto|olymp|iq ?option|quotex|forex|\bfx|smart ?tr"
LOAN = r"financ|fincorp|fintech|capital|lendbox|transactree|kreditbee|money ?view|navi fin|cashe|\bfibe|earlysalary|smartcoin|nbfc|loan|piramal|bajaj fin|bajaj fi|tata cap|hdb|muthoot|manappuram|iifl|aditya birla|poonawalla|ugro|lendingkart|indifi|flexiloans|home credit|india finance|credit for l|kissht|lazypay|simpl|slice|faircent|i2i|mpokket|stashfin|branch|truebalance|paysense|ring|uni ?card"
AGGREGATOR = r"payment ?aggregat|phonepe ?l(imi)?te?d|phonepelimited|paytm payments|pine ?labs|cashfree|razorpay|billdesk|ccavenue|easebuzz|payu|bharatpe|mswipe|ezetap|instamojo"
CARD_BILL = r"\bcred\b|payment on ?cred|credit ?card|card ?bill|cc ?payment|billdesk.*card|sbi ?card|amex|onecard"
REFUND = r"amazon|flipkart|meesho|myntra|refund|reversal|\brev\b|cashback|otp|interest|int\.? ?pd|charges? rev|tax refund|return"
BUSINESS_NAME = r"international|industr|textile|traders?|trading|enterprise|pvt|private|\bltd|limited|llp|& ?co|\bco\b|store|mart|agenc|garment|fashion|export|import|impex|works|solution|services|hotel|restaurant|creation|apparel|fabric|mills?|corporation|\bcorp|associates|brothers|bros|sons|emporium|wholesale|distribut|supplier|kirana|medical|pharma|electric|motor|auto|steel|plast|packag|logistic|transport|infotech|technolog|systems"
NAME_STOP = {"mohammad", "mohammed", "mohd", "md", "mohamad", "muhammad", "mr", "mrs", "ms", "shri", "smt",
             "kumar", "kumari", "singh", "devi", "bhai", "ben", "lal", "ram", "sri", "upi", "the", "and"}
# Default profit margins (%) by business type, used when no margin is given.
DEFAULT_MARGIN = {"wholesale": 8, "retail": 20, "services": 40, "manufacturing": 25}

def default_margin(btype):
    b = str(btype).lower()
    for k, v in DEFAULT_MARGIN.items():
        if b.startswith(k[:4]): return v
    return None

JOBWORK = r"contract|job ?work|stitch|stich|tailor|fabricat|embroider|printing|dyeing|assembl|processing"

def low(x): return str(x or "").lower()
def rx(p, s): return re.search(p, low(s), re.I) is not None
def num(x):
    try: return float(x)
    except Exception: return 0.0
def pdate(s):
    for f in ("%d/%m/%Y", "%d/%b/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try: return datetime.strptime(str(s).strip()[:11], f)
        except Exception: pass
    return None

# ----------------------------------------------------------------- loaders
def rows(wb, name):
    if name not in wb.sheetnames: return []
    return [r for r in wb[name].iter_rows(values_only=True) if any(c is not None for c in r)]

def accounts(wb):
    r = rows(wb, "Summary")
    acc = []
    if not r: return acc
    hdr = {}
    for x in r:
        if str(x[0]).strip().lower().startswith("monthwise"): break
        if x[0]: hdr[str(x[0]).strip()] = x[1:]
    n = len([c for c in hdr.get("Description", []) if c])
    for i in range(n):
        g = lambda k: (hdr.get(k) or [None] * n)[i]
        acc.append({"description": g("Description"), "holder": g("Account Holders"), "bank": g("Bank Name"),
                    "account_no": g("Account Number"), "type": g("Account Type"),
                    "statement_from": g("Statement From"), "statement_to": g("Statement To"),
                    "txn_start": g("Txn Start Date"), "txn_end": g("Txn End Date")})
    # per-account monthly avg balance & txn count from Overview
    ov = rows(wb, "Overview")
    for x in ov:
        k = str(x[0] or "").strip()
        for i, a in enumerate(acc):
            v = x[1 + i] if len(x) > 1 + i else None
            if k == "Monthly avg balance": a["average_monthly_balance_inr"] = num(v)
            if k.startswith("Transaction (Count"): a["txn_count_info"] = v
            if k.lower() == "account age": a["account_age"] = v
            if k == "No transactions month" and v and v != "-": a["no_txn_months"] = str(v)[:200]
    if len(acc) == 1 and not acc[0].get("average_monthly_balance_inr"):  # single-account report layout
        mab = summary_row(wb, "Monthly Average Balance")
        if mab: acc[0]["average_monthly_balance_inr"] = mab[-1]
    for a in acc:
        s, e = pdate(a["txn_start"]), pdate(a["txn_end"])
        if s and e:
            a["active_days"] = (e - s).days + 1
            a["active_months"] = round(a["active_days"] / 30.4375, 2)
    return acc

def summary_row(wb, label):
    for x in rows(wb, "Summary"):
        if str(x[0] or "").strip() == label:
            vals = [num(v) for v in x[1:] if v not in (None, "-", "")]
            return vals  # monthly..., total last
    return []

def counterparties(wb):
    cr, dr = {}, {}
    for x in rows(wb, "Counterparty")[2:]:
        if x[0] and isinstance(x[1], (int, float)): cr[str(x[0]).strip()] = (num(x[1]), int(num(x[2])))
        if len(x) > 7 and x[5] and isinstance(x[6], (int, float)): dr[str(x[5]).strip()] = (num(x[6]), int(num(x[7])))
    return cr, dr

def txns(wb):
    frames = []
    for ws in wb:
        r = rows(wb, ws.title)
        if not r: continue
        h = [str(c).strip() if c else "" for c in r[0]]
        if {"Txn date", "Particulars", "Debit(₹)", "Credit(₹)"} <= set(h):
            df = pd.DataFrame(r[1:], columns=h)
            df["sheet"] = ws.title
            df["_order"] = range(len(df))
            frames.append(df)
    if not frames: return pd.DataFrame()
    t = pd.concat(frames, ignore_index=True)
    t["date"] = t["Txn date"].map(pdate)
    t["dr"] = t["Debit(₹)"].map(num); t["cr"] = t["Credit(₹)"].map(num)
    t["bal"] = t.get("Balance(₹)", pd.Series([None] * len(t))).map(num)
    t["acct"] = t.get("Bank name", pd.Series([""] * len(t))).fillna("").astype(str)
    t["cp"] = t.get("Counterparty", pd.Series([""] * len(t))).fillna("").astype(str)
    t = t.dropna(subset=["date"]).drop_duplicates(subset=["date", "Particulars", "dr", "cr", "bal"])
    # fill missing account from any sheet that has 'Bank Account' + 'Particulars'
    amap = {}
    for ws in wb:
        r = rows(wb, ws.title)
        if not r: continue
        h = [str(c).strip() if c else "" for c in r[0]]
        if "Bank Account" in h and "Particulars" in h:
            ia, ip = h.index("Bank Account"), h.index("Particulars")
            for x in r[1:]:
                if x[ia] and x[ip]: amap[str(x[ip]).strip()] = str(x[ia])
    acodes = {}
    for _, x in t[t.acct != ""].iterrows():
        acodes.setdefault(str(x["Account number"])[-4:] if "Account number" in t.columns else "", x.acct)
    def fill(rw):
        if rw.acct: return rw.acct
        code = amap.get(str(rw.Particulars).strip(), "")
        for k, v in acodes.items():
            if k and k in code: return v
        return code
    t["acct"] = t.apply(fill, axis=1)
    t["hidden"] = False
    # reconstruct non-UPI txns from balance gaps inside the UPI sheet (sheet order = chronological per account)
    hid = []
    if "UPI txns" in t.sheet.values and "Transactions" not in t.sheet.values:
        for ac, g in t[t.sheet == "UPI txns"].groupby("acct", sort=False):
            prev = None
            for _, x in g.iterrows():
                if prev is not None:
                    gap = x.bal - (prev - x.dr + x.cr)
                    if abs(gap) > 1:
                        hid.append({"date": x.date, "Particulars": "[inferred from balance gap - non-UPI txn]",
                                    "dr": max(-gap, 0), "cr": max(gap, 0), "bal": prev + gap, "acct": ac,
                                    "cp": "[non-UPI, inferred]", "sheet": "inferred", "hidden": True})
                prev = x.bal
    if hid: t = pd.concat([t, pd.DataFrame(hid)], ignore_index=True)
    return t.sort_values("date", kind="stable").reset_index(drop=True)

def table(wb, name):
    """Header-driven rows of a simple table sheet -> list of dicts (handles single/multi-account layouts)."""
    r = rows(wb, name)
    if not r: return []
    h = [str(c).strip() if c else f"c{i}" for i, c in enumerate(r[0])]
    return [dict(zip(h, x)) for x in r[1:]]

def section(wb, sheet, title):
    """Return rows under a section heading in a sectioned sheet (e.g. Irregularities)."""
    out, on = [], False
    for x in rows(wb, sheet):
        first = str(x[0] or "").strip()
        nonnull = [c for c in x if c is not None]
        if len(nonnull) == 1 and first:  # heading row
            on = first.lower().startswith(title.lower()); continue
        if on: out.append(x)
    return out[1:] if out else []

# ----------------------------------------------------------------- classification
def classify(name, amt, cnt, ctx):
    n = low(name)
    for k, v in ctx["overrides"].items():
        if k.lower() in n: return v, "analyst override"
    if any(f and f in n for f in ctx["family"]): return "family", "matches family name supplied"
    if any(t in n for t in ctx["own_tokens"]): return "own", "matches account-holder name"
    if name in ctx["loan_parties"] or rx(LOAN, n): return "loan", "loan/NBFC/credit-line counterparty"
    if rx(REFUND, n): return "refund_reversal", "refund / reversal / interest"
    if rx(AGGREGATOR, n):
        if cnt / max(ctx["months"], 1) >= 8:
            return "business", "payment-aggregator / QR settlements (frequent, counter sales)"
        return "card_rotation", "payment-aggregator credit without merchant pattern (card-to-account suspected)"
    if n in ("unknown", "", "nan"): return "unidentified", "no counterparty name in narration"
    is_biz = rx(BUSINESS_NAME, n)
    avg = amt / max(cnt, 1)
    two_way = twoway_amt(key(name), ctx["debit_by_key"])
    if not is_biz and two_way >= 0.25 * amt and amt >= 5000:
        return "personal", f"two-way flows with same party (debits Rs {two_way:,.0f})"
    if not is_biz and ctx["personal_ticket"] and avg >= ctx["personal_ticket"]:
        return "personal", f"individual, avg ticket Rs {avg:,.0f} >= {ctx['personal_ticket']:,} (round P2P / borrowing)"
    return "business", "business-named party" if is_biz else "individual payer (multi-source receipts)"

def twoway_amt(k, dk):
    if not k or k == "unknown" or len(k) < 3: return 0.0
    return sum(v for kk, v in dk.items() if kk and len(kk) >= 3 and (kk.startswith(k) or k.startswith(kk)))

def key(name):
    s = re.sub(r"^(upi_|phonepe_|paytm_|sent using upi_|paid via|na_|supermoney upi_)", "", low(name))
    s = re.sub(r"[^a-z ]", " ", s)
    def stopish(t):  # drop titles and truncated fragments like "moha", "mmad", "mohamm"
        return t in NAME_STOP or "mmad" in t or any(len(w) >= 4 and (w.startswith(t) or t.startswith(w)) for w in NAME_STOP)
    apps = {"cred", "paytm", "phonepe", "jiop", "ybl", "okaxis", "paidviakotakapp", "supermoney", "navi", "staticqr"}
    toks = [re.sub(r"^(mohd|mohammad|mohamad|muhammad|md)(?=[a-z]{3})", "", t) for t in s.split() if t not in apps]
    toks = [t for t in toks if not stopish(t) and len(t) > 2]
    return toks[0] if toks else s.strip()

# ----------------------------------------------------------------- irregularity checks
def irregularities(wb, t, cr, dr, acc, total_cr, total_dr, months):
    notes = {}
    text = []
    for ws in wb:
        for x in ws.iter_rows(values_only=True):
            s = " | ".join(str(c) for c in x if c is not None)
            if s: text.append((ws.title, s))
    def hits(p):
        seen, out = set(), []
        for sh, s in text:
            if re.search(p, s, re.I) and s not in seen:
                seen.add(s); out.append(s[:180])
        return out[:15]
    notes["gambling"] = {"hits": hits(GAMBLING)}
    notes["futures_options_crypto_trading"] = {"hits": hits(FNO)}
    unnamed = t[(t.dr > 0) & (t.cp.str.strip().isin(["", "nan", "Unknown"]))]
    notes["unnamed_debits"] = {"count": int(len(unnamed)), "amount": round(unnamed.dr.sum(), 2),
                               "comment": "Payee not visible in narration; gambling/F&O cannot be fully ruled out for these"}
    # card rotation
    pairs = []
    for _, c in t[t.cr >= 10000].iterrows():
        m = t[(t.dr > 0) & ((t.date - c.date).abs().dt.days <= 1) & ((t.dr - c.cr).abs() <= 0.01 * c.cr)]
        for _, d in m.iterrows():
            pairs.append(f"{c.date:%d-%b-%y} CR {c.cr:,.2f} [{(str(c.cp) or str(c.Particulars))[:30]}] <-> {d.date:%d-%b-%y} DR {d.dr:,.2f} [{(str(d.cp) or str(d.Particulars))[:30]}]")
    card_bills = sum(v[0] for k, v in dr.items() if rx(CARD_BILL, k))
    agg_total = sum(v[0] for k, v in cr.items() if rx(AGGREGATOR, k))
    via_cred = sum(v[0] for k, v in cr.items() if "cred" in low(k))
    notes["credit_card_rotation"] = {"aggregator_credits": round(agg_total, 2), "same_amount_in_out_within_1_day": pairs[:20],
                                     "credit_card_bill_payments": round(card_bills, 2), "p2p_received_via_cred": round(via_cred, 2)}
    # two-way parties
    dk = defaultdict(float)
    for k, v in dr.items(): dk[key(k)] += v[0]
    tw = []
    for k, v in cr.items():
        kk = key(k)
        amt = twoway_amt(kk, dk)
        if amt > 0 and v[0] >= 5000 and not rx(LOAN, k):
            tw.append({"party": k, "credit": v[0], "debit": round(amt, 2)})
    tw.sort(key=lambda z: -z["credit"])
    sec_rows = section(wb, "Irregularities", "Parties present in both")
    ci = 1 if any(str(x[0]).strip().lower() == "bank account" for x in rows(wb, "Irregularities")) else 0
    rep = [str(x[ci]).strip() for x in sec_rows if x[ci] and not str(x[ci]).startswith(" ") and str(x[ci]).strip() != "Counterparty"]
    notes["same_party_two_way_flows"] = {"computed": tw[:20], "flagged_by_report": sorted(set(rep))}
    # in-and-out / threshold structuring
    big = 25000
    io = []
    for _, c in t[t.cr >= big].iterrows():
        m = t[(t.acct == c.acct) & (t.dr >= 0.8 * c.cr) & (t.date >= c.date) & ((t.date - c.date).dt.days <= 2)]
        if len(m): io.append(f"{c.date:%d-%b-%y} CR {c.cr:,.0f} ({str(c.cp)[:25]}) -> DR {m.dr.iloc[0]:,.0f} on {m.date.iloc[0]:%d-%b-%y}")
    wd = []
    for _, d in t[t.dr >= big].iterrows():
        m = t[(t.acct == d.acct) & (t.cr >= 0.8 * d.dr) & (t.date >= d.date) & ((t.date - d.date).dt.days <= 3)]
        if len(m): wd.append(f"{d.date:%d-%b-%y} DR {d.dr:,.0f} -> CR {m.cr.iloc[0]:,.0f} ({str(m.cp.iloc[0])[:25]}) on {m.date.iloc[0]:%d-%b-%y}")
    drain = []
    for _, c in t[t.cr >= 50000].iterrows():
        after = t[(t.acct == c.acct) & (t.index > c.name) & (t.date >= c.date) & ((t.date - c.date).dt.days <= 7) & (t.bal > 0)]
        if len(after) and after.bal.min() < 0.1 * c.cr:
            drain.append(f"{c.date:%d-%b-%y} CR {c.cr:,.0f} -> balance fell to {after.bal.min():,.0f} within 7 days")
    notes["instant_large_withdrawal_and_deposit"] = {"credit_then_quick_debit": io[:15], "debit_then_quick_credit": wd[:15],
                                                     "balance_drained_after_large_credit": drain[:15]}
    thr = t[t.dr.isin([9999, 19999, 24999, 48999, 49999, 99999, 199999])]
    penny = t[(t.dr == 1)]
    notes["structuring_signals"] = {"just_below_threshold_debits": [f"{r.date:%d-%b-%y} {r.dr:,.0f}" for r in thr.itertuples()],
                                    "rs1_penny_tests": int(len(penny))}
    # cash
    cats = {}
    sec = None
    for x in rows(wb, "Categories"):
        if str(x[0]).strip() in ("Inflow", "Outflow"): sec = str(x[0]).strip(); continue
        if sec and isinstance(x[3], (int, float)): cats[(sec, str(x[0]).strip())] = num(x[3])
    cash_in = cats.get(("Inflow", "Cash & ATM"), 0) or cats.get(("Inflow", "Cash Deposit"), 0)
    cash_out = cats.get(("Outflow", "Cash & ATM withdrawals"), 0)
    pin, pout = cash_in / max(total_cr, 1) * 100, cash_out / max(total_dr, 1) * 100
    lvl = "HIGH" if max(pin, pout) > 30 else "MODERATE" if max(pin, pout) > 15 else "LOW"
    big_atm = section(wb, "Irregularities", "ATM Withdrawals above")
    notes["cash_handling"] = {"cash_deposits": cash_in, "cash_deposit_pct_of_credits": round(pin, 1),
                              "cash_withdrawals": cash_out, "cash_withdrawal_pct_of_debits": round(pout, 1),
                              "atm_above_20k_count": len([x for x in big_atm if x[0]]), "level": lvl}
    # loans: end use and EMI misses
    lo = []
    for x in table(wb, "Loans"):
        if x.get("Start date"):
            lo.append({"account": x.get("Bank Account"), "start": x.get("Start date"), "end": x.get("End date"),
                       "counterparty": x.get("Counterparty"), "debit": x.get("Debit(₹)"), "credit": x.get("Credit(₹)"),
                       "txns": x.get("Txn count"), "misses": x.get("Misses"), "miss_dates": x.get("Misses date")})
    enduse = []
    for _, c in t[(t.cr >= 100000) & t.Particulars.astype(str).str.contains(LOAN, case=False, regex=True)].iterrows():
        w = t[(t.date > c.date) & ((t.date - c.date).dt.days <= 30)]
        enduse.append(f"{c.date:%d-%b-%y} loan CR {c.cr:,.0f}: Rs {w.dr.sum():,.0f} debited in next 30 days (visible txns)")
    notes["loans"] = {"report_loan_lines": lo, "large_loan_end_use": enduse}
    # report's own irregularity counters
    ov = {}
    on = False
    for x in rows(wb, "Overview"):
        if str(x[0]).strip() == "Activity": on = True; continue
        if on and str(x[0]).strip() in ("Outflow", "Category"): break
        if on and x[0]: ov[str(x[0]).strip()] = x[1]
    notes["report_irregularity_counters"] = {k: v for k, v in ov.items() if str(v) not in ("0", "None")}
    b = summary_row(wb, "I/W Cheque Bounces: Insufficient Funds Count")
    notes["cheque_bounces_inward"] = b[-1] if b else None
    return notes

def business_profile(t, cr, dr, btype, nature, months, cls_amt, net_inflow):
    c = t[t.cr > 0]
    upi_c = c[c.Tags.astype(str).str.contains("UPI", case=False)] if "Tags" in c.columns else c[c.sheet.str.contains("UPI", case=False)]
    total = sum(v[0] for v in cr.values())
    biz_cp = sorted([(k, v[0]) for k, v in cr.items() if cls_amt.get(k) == "business" and low(k) != "unknown"], key=lambda z: -z[1])
    top5 = sum(v for _, v in biz_cp[:5]) / max(sum(v for _, v in biz_cp), 1) * 100
    p2m = 0
    if "Tags" in t.columns: p2m = int(upi_c.Tags.astype(str).str.contains("P2M").sum())
    dbiz = sum(v[0] for k, v in dr.items() if rx(BUSINESS_NAME, k) and not rx(LOAN, k) and not rx(CARD_BILL, k))
    d = t[t.dr > 0]
    m = {"credit_txns_per_month": round(sum(v[1] for v in cr.values()) / months, 1),
         "unique_credit_counterparties": len(cr),
         "upi_credit_median_ticket": float(upi_c.cr.median()) if len(upi_c) else None,
         "upi_credits_below_2000_pct": round((upi_c.cr < 2000).mean() * 100, 1) if len(upi_c) else None,
         "upi_p2m_credit_count": p2m,
         "top5_business_counterparty_concentration_pct": round(top5, 1),
         "top_business_counterparties": [{"name": k, "amount": v} for k, v in biz_cp[:8]],
         "debits_to_business_named_parties": round(dbiz, 2),
         "debit_median_ticket": float(d.dr.median()) if len(d) else None,
         "debits_below_2000_pct": round((d.dr < 2000).mean() * 100, 1) if len(d) else None}
    bt = btype.lower(); jw = rx(JOBWORK, nature)
    biz_total = max(sum(v for _, v in biz_cp), 1)
    b2b = sum(v for k, v in biz_cp if rx(BUSINESS_NAME, k))
    payers = len(biz_cp)
    # MSMEs mix channels (retail counter + wholesale + job-work), so report the channel mix and
    # check that the declared primary channel is visible, rather than demanding a pure B2B/B2C shape.
    m["channel_mix"] = {"b2b_business_named_pct": round(b2b / biz_total * 100, 1),
                        "individual_payers_pct": round((biz_total - b2b) / biz_total * 100, 1),
                        "unique_business_payers": payers,
                        "upi_small_ticket_credits_pct": m["upi_credits_below_2000_pct"],
                        "qr_p2m_credits": p2m}
    diverse = ("diverse payer base (>= 20 unique payers)", payers >= 20)
    if jw:
        exp = "Job-work/contract (often mixed): bulk receipts from garment/industrial principals plus receipts from many individual traders/customers; many small payouts to workers."
        checks = [("B2B principals visible (business-named payers >= 20% of business inflows)", b2b >= 0.2 * biz_total),
                  ("many small worker payouts (>= 50% debits < 2k)", (m["debits_below_2000_pct"] or 0) >= 50), diverse]
    elif bt.startswith("retail") or bt.startswith("serv"):
        exp = "Retail/services counter (may also sell wholesale): frequent small UPI receipts from many payers; bulk orders and supplier purchases may also appear."
        checks = [("frequent receipts (>= 30 credits/month)", m["credit_txns_per_month"] >= 30),
                  ("small-ticket UPI receipts present (>= 30% of UPI credits < 2k)", (m["upi_credits_below_2000_pct"] or 0) >= 30), diverse]
        if bt.startswith("retail"): checks.append(("purchases from business suppliers", dbiz > 0.1 * total))
    elif bt.startswith("whole"):
        exp = "Wholesale (may also run a retail counter): bulk receipts from trade buyers plus counter sales; regular bulk payments to suppliers."
        checks = [("bulk trade receipts visible (business-named or median UPI credit >= 10k)", b2b >= 0.3 * biz_total or (m["upi_credit_median_ticket"] or 0) >= 10000),
                  ("regular supplier purchases (business-named debits >= 25% of credits)", dbiz >= 0.25 * total), diverse]
    else:
        exp = "Manufacturing (may also sell direct): B2B receipts plus direct sales; raw-material purchases; wage payouts."
        checks = [("B2B receipts visible (>= 20% of business inflows)", b2b >= 0.2 * biz_total),
                  ("raw-material purchases from suppliers (>= 15% of credits)", dbiz >= 0.15 * total),
                  ("wage-like small payouts (>= 40% debits < 2k)", (m["debits_below_2000_pct"] or 0) >= 40)]
    passed = sum(1 for _, ok in checks if ok)
    verdict = "MATCH" if passed == len(checks) else "PARTIAL MATCH" if passed else "MISMATCH"
    return {"expected_pattern": exp, "profile_used": "job-work/contract" if jw else bt, "metrics": m,
            "checks": [{"check": c_, "passed": bool(ok)} for c_, ok in checks], "verdict": verdict}

# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report"); ap.add_argument("--type", required=True); ap.add_argument("--nature", required=True)
    ap.add_argument("--profit", type=float, default=None, help="profit %%; defaults by type: wholesale 8, retail 20, services 40, manufacturing 25"); ap.add_argument("--family", default="")
    ap.add_argument("--own", default=""); ap.add_argument("--overrides"); ap.add_argument("--out")
    ap.add_argument("--personal-ticket", type=int, default=None)
    a = ap.parse_args()
    margin_source = "user"
    if a.profit is None:
        a.profit = default_margin(a.type)
        margin_source = "default"
        if a.profit is None: ap.error("unknown --type; pass --profit explicitly")
    wb = openpyxl.load_workbook(a.report, data_only=True, read_only=False)
    acc = accounts(wb)
    starts = [pdate(x["txn_start"]) for x in acc if pdate(x["txn_start"])]
    ends = [pdate(x["txn_end"]) for x in acc if pdate(x["txn_end"])]
    days = (max(ends) - min(starts)).days + 1 if starts and ends else 365
    months = days / 30.4375
    cr, dr = counterparties(wb)
    t = txns(wb)
    total_cr = (summary_row(wb, "Credit Txns") or [sum(v[0] for v in cr.values())])[-1]
    total_dr = (summary_row(wb, "Debit Txns") or [sum(v[0] for v in dr.values())])[-1]
    holders = " ".join(str(x.get("holder") or "") for x in acc)
    own_tokens = {w for w in re.sub(r"[^a-z ]", " ", holders.lower()).split() if w not in NAME_STOP and len(w) > 2}
    own_tokens |= {w.strip().lower() for w in a.own.split(",") if w.strip()}
    loan_parties = {str(x.get("Counterparty")).strip() for x in table(wb, "Loans") if num(x.get("Credit(₹)")) > 0}
    dk = defaultdict(float)
    for k, v in dr.items(): dk[key(k)] += v[0]
    bt = a.type.lower()
    b2c = (bt.startswith("retail") or bt.startswith("serv")) and not rx(JOBWORK, a.nature)
    ctx = {"overrides": json.load(open(a.overrides)) if a.overrides else {},
           "family": [f.strip().lower() for f in a.family.split(",") if f.strip()],
           "own_tokens": own_tokens, "loan_parties": loan_parties, "b2c": b2c, "months": months,
           "debit_by_key": dk,
           # MSMEs sell through mixed channels (counter, wholesale, job-work), so UPI/NEFT credits from
           # many different payers are counted as business. Individuals are excluded only for two-way
           # flows (or above --personal-ticket if the analyst sets one).
           "personal_ticket": a.personal_ticket}
    ibp = set()
    for x in rows(wb, "Inter Bank Transfers")[2:]:
        for i in (1, 6):
            if len(x) > i + 2 and x[i] and num(x[i + 2]) > 0: ibp.add(str(x[i]).strip())
    for nm in t[(t.cr > 0) & t.Particulars.astype(str).str.strip().isin(ibp)].cp:
        if nm and nm != "nan" and nm in cr:
            ctx["overrides"].setdefault(low(nm), "own")
    buckets = defaultdict(lambda: {"amount": 0.0, "txns": 0, "parties": []})
    cls_amt = {}
    for name, (amt, cnt) in sorted(cr.items(), key=lambda z: -z[1][0]):
        c, why = classify(name, amt, cnt, ctx)
        cls_amt[name] = c
        b = buckets[c]; b["amount"] += amt; b["txns"] += cnt
        b["parties"].append({"name": name, "amount": round(amt, 2), "txns": cnt, "reason": why})
    # split the 'Unknown' counterparty using narrations of visible txns
    if buckets["unidentified"]["amount"] > 0:
        unk = t[(t.cr > 0) & (~t.hidden.astype(bool)) & t.cp.str.strip().isin(["", "nan", "Unknown"])]
        for _, x in unk.iterrows():
            pt = str(x.Particulars)
            c = "loan" if rx(LOAN, pt) else "refund_reversal" if rx(REFUND, pt) else None
            if c and buckets["unidentified"]["amount"] >= x.cr:
                buckets["unidentified"]["amount"] -= x.cr; buckets["unidentified"]["txns"] -= 1
                buckets[c]["amount"] += x.cr; buckets[c]["txns"] += 1
                buckets[c]["parties"].append({"name": "Unknown: " + pt[:60], "amount": x.cr, "txns": 1,
                                              "reason": "narration indicates " + c})
    for pp in buckets["unidentified"]["parties"]:
        pp["amount"] = round(buckets["unidentified"]["amount"], 2); pp["reason"] += " (after splitting out loans/refunds by narration)"
    # interest from Categories sheet (usually unnamed)
    for x in rows(wb, "Categories"):
        already = any("int" in low(pp["name"]) for pp in buckets["refund_reversal"]["parties"])
        if str(x[0]).strip() == "Interest" and not already and isinstance(x[3], (int, float)) and buckets["unidentified"]["amount"] >= num(x[3]):
            buckets["unidentified"]["amount"] -= num(x[3]); buckets["refund_reversal"]["amount"] += num(x[3])
            buckets["refund_reversal"]["parties"].append({"name": "Interest (Categories)", "amount": num(x[3]), "txns": int(num(x[6])), "reason": "bank interest"})
            break
    # inter-bank transfers matched by the report (own accounts) not captured by name
    ib = 0.0
    for x in rows(wb, "Inter Bank Transfers")[2:]:
        if x[1] == "Total": ib = max(num(x[2]), num(x[3]), num(x[7]) if len(x) > 7 else 0, num(x[8]) if len(x) > 8 else 0); break
    cp_total = sum(v[0] for v in cr.values())
    gap = total_cr - cp_total
    excl = ["own", "loan", "family", "personal", "card_rotation", "refund_reversal"]
    excluded = sum(buckets[k]["amount"] for k in excl)
    business = buckets["business"]["amount"]; unident = buckets["unidentified"]["amount"]
    net_inflow = total_cr - excluded
    yearly = net_inflow / months * 12
    yearly_verified = business / months * 12
    p = a.profit / 100
    res = {
        "inputs": {"business_type": a.type, "nature_of_business": a.nature, "profit_margin_pct": a.profit,
                   "profit_margin_source": margin_source,
                   "family_names_excluded": ctx["family"], "report_file": a.report.split("/")[-1]},
        "accounts": [{k: v for k, v in x.items() if v not in (None, "")} for x in acc],
        "balance_summary": {
            "combined_average_monthly_balance": (summary_row(wb, "Monthly Average Balance") or [None])[-1],
            "combined_median_daily_balance": None,
            "assessment_window_days": days, "assessment_window_months": round(months, 2),
            "monthly_average_balance_series": dict(zip([c for c in rows(wb, "Summary")[13][1:] if c and c != "Total"],
                                                      summary_row(wb, "Monthly Average Balance")[:-1]))},
        "income_computation": {
            "total_credits": round(total_cr, 2),
            "less": {k: round(buckets[k]["amount"], 2) for k in excl},
            "total_excluded": round(excluded, 2),
            "net_business_inflows": round(net_inflow, 2),
            "of_which_identified_business_parties": round(business, 2),
            "of_which_unidentified_credits": round(unident, 2),
            "credits_not_mapped_to_counterparty": round(gap, 2),
            "report_inter_bank_transfers_matched": ib,
            "monthly_business_inflow": round(net_inflow / months, 2),
            "yearly_business_turnover": round(yearly, 2),
            "yearly_income_at_profit_margin": round(yearly * p, 2),
            "conservative_yearly_turnover_identified_parties_only": round(yearly_verified, 2),
            "conservative_yearly_income": round(yearly_verified * p, 2)},
        "credit_classification": {k: {"amount": round(v["amount"], 2), "txns": v["txns"], "parties": v["parties"][:25]}
                                  for k, v in buckets.items()},
        "business_cashflow_match": business_profile(t, cr, dr, a.type, a.nature, months, cls_amt, net_inflow),
        "irregularities": irregularities(wb, t, cr, dr, acc, total_cr, total_dr, months),
    }
    db = rows(wb, "Daily balance")
    for x in db:
        if str(x[0]).strip() == "Median": res["balance_summary"]["combined_median_daily_balance"] = num(x[1])
    out = json.dumps(res, indent=2, default=str)
    if a.out: open(a.out, "w").write(out)
    print(out)

if __name__ == "__main__":
    main()
```