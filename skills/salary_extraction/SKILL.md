# Salary Extraction Skill — CAM Bank Statement → Salary JSON

This skill turns any CAM (bank statement) Excel file into a verified monthly-salary
result as JSON. It is self-contained and **fully dynamic**: a person or harness
needs only this file, the CAM file, and an LLM (or deterministic code).

**No data is hardcoded.** No employer name, amount, date, month, bank, or format
in this file is a fixed expectation. Every number here is a *threshold* (a limit
to compare against); every name, date, and amount in the output must be read
from the input file itself. Examples in this document are illustrative only —
never expect their exact values on a real file.

Scope: salary detection only. No credit-report logic, no EMI, no FOIR.

---

## 0. What you produce

One JSON object. Exact shape (values below are **illustrative placeholders**):

```json
{
  "success": true,
  "request_type": "cam_only",
  "agent": {
    "detected": true,
    "reason": "Five recurring monthly NEFT credits from one consistent payer with stable amounts support salary income."
  },
  "Income": {
    "type": "salary",
    "company": "PAYER NAME EXACTLY AS SHOWN IN THE FILE",
    "confidence_score": 93.0,
    "Payouts": [
      ["2025-01-05", 17900, "NEFT"],
      ["2025-02-05", 20000, "NEFT"],
      ["2025-03-06", 18400, "NEFT"],
      ["2025-04-05", 20600, "NEFT"],
      ["2025-05-05", 20050, "NEFT"]
    ]
  },
  "monthly_average_balance": 12345.67
}
```

Field contract:

| Field | Rule |
|---|---|
| `success` | `true` whenever analysis completed (even for a clean rejection) |
| `request_type` | always `"cam_only"` for this skill |
| `agent.detected` | `true` only if every hard gate in §9 passes |
| `agent.reason` | one sentence citing the winning features (count, cadence, payer, mode) or the failing gate |
| `Income` | the object above when `detected: true`, otherwise **`null`** |
| `Income.type` | always `"salary"` |
| `Income.company` | payer name resolved per §10 — from the file, never from this document; **`null` when the statement carries no payer name, which never affects `agent.detected`** |
| `Income.confidence_score` | float 0–100 per §8 |
| `Income.Payouts` | ascending by date; `[YYYY-MM-DD, amount, mode]`; amounts are the file's credit values rounded to 2 decimals; mode per §6 |
| `monthly_average_balance` | **read verbatim from the file's own figure** (§10 `monthly_average_balance` bullet) — never recomputed; `null` if the file carries none of the stated fields |

Never emit extra fields. Never emit markdown fences around the JSON.

---

## 1. What salary looks like (read this before touching the file)

Salary is an **employer → employee credit pattern**, not a single transaction.
When you look at the statement, salary income has this fingerprint:

**Positive features (any strong subset):**
- **Recurring monthly rhythm** — one credit every ~month, often on a pay-day
  cluster (month start, 7th, 10th, last working day, or a fixed date that
  repeats year-round).
- **One dominant payer** — the same counterparty/narration supplies a large
  share of the account's credit inflow over the statement period.
- **Stable amount with small drift** — amounts cluster around a center;
  variation is modest (increments, arrears, small deductions), not wild.
- **Employer-like payer identity** — entity tokens (`LTD`, `LIMITED`,
  `PVT`, `CORP`, `SERVICES`, `INDUSTRIES`, `TECHNOLOGIES`, `HOTELS`,
  `HOSPITALS`, `SCHOOLS`, `GOVERNMENT`, `DEPT`, bank payroll strings) or
  a staffing/PEO company paying on behalf of a principal employer.
- **Payroll vocabulary in narration/tags** — `SALARY`, `PAYROLL`, `SAL`,
  `WAGES`, `STIPEND`, `MONTHLY PAY`, `PAY SLIP`, `CTC`, `REG-SAL`.
- **Legitimate institutional channels** — NEFT / RTGS / IMPS / NACH / ACH /
  ECS / PFMS (government and PSU wages arrive via PFMS/NACH).
- **Consistent source mechanics** — same counterparty string, same
  narration template, same tags, or same mode across the run.

**What is NOT salary (reject/ignore):**
- One-off large credits: bonuses standing alone, loan disbursals, investment
  redemptions, gift/inheritance, insurance payouts.
- Random person-to-person transfers with varying names, amounts, and dates.
- Refunds, reversals, chargebacks, cashback, interest postings, bounced-EMI
  returns.
- Cash deposits (teller/CDM/ATM-cash) — informal and unverifiable.
- UPI credits — person-to-person/small-value rails; excluded by policy even
  when they recur.
- Transfers from the **account holder's own name/other own accounts**
  (counterparty resembling the statement's account-holder name) — that is
  moving money, not earning it.
- Credits whose amount or cadence appears once and never repeats.

A single transaction proves nothing here: **only a repeated pattern can be
salary.** Build the pattern first (§7), then judge it (§9).

---

## 2. Locate the transaction table (any workbook layout)

1. Open every sheet. Candidate transaction sheets contain ≥ 20 data rows and
   columns matching a date and an amount (exact names in §3).
2. Header row is not guaranteed to be row 1 — scan downward past title rows,
   logos, and merged banners until a row matches §3 names.
3. Skip sheets that are clearly KYC / account-summary / holder-details /
   interest-rate / cheque-book pages (no per-transaction date+amount rows).
4. If multiple sheets qualify, choose the one with the most transaction rows.
5. Read rows until dates stop (empty rows, or a totals/"closing balance" line).

---

## 3. Column mapping (case-insensitive partial match; first hit wins)

| Role | Accepted header names |
|---|---|
| date | `Txn date`, `Transaction Date`, `Date`, `Value Date`, `Posting Date` |
| credit | `Credit(₹)`, `Credit`, `Credit Amount`, `Credits`, `Credit Amount (INR)` |
| debit | `Withdrawal(₹)`, `Withdrawal`, `Debit`, `Debit Amount` (used for exclusion only) |
| particulars | `Particulars`, `Description`, `Narration`, `Transaction Details`, `Remarks` |
| counterparty | `Counterparty`, `Counter Party`, `Beneficiary`, `Payer`, `Sender` |
| tags | `Tags` |
| category | `Category` |
| balance | `Balance`, `Closing Balance`, `Running Balance` (optional) |

**Fallbacks for non-standard layouts:**
- No credit column, but an `Amount` column plus a `Dr/Cr` or
  `Withdrawal/Deposit` indicator → credit = rows marked `Cr` / `Deposit`
  (or amount > 0 if signed).
- No counterparty column → the counterparty is derived from the narration
  (§10 handles extraction).
- No date or credit column even after fallbacks → abort:
  `{"success": false, "error": "Transaction date/Credit column not found"}`.

---

## 4. Row normalization

**Amounts** — positive float: strip `,`, `₹`, `Rs.`, `Rs`; empty, `-`, `nan`,
`none`, `null` → skip; ≤ 0 or non-finite → skip.

**Dates** — normalize to `YYYY-MM-DD`. Accept Excel serial numbers,
`DD/MM/YYYY`, `DD-MM-YYYY`, `DD-Mon-YYYY`, and month-first formats where
unambiguous (prefer day > 12 interpretations only when the column mixes them).

**Text** — uppercase, collapse whitespace. For *matching* (§7 source check)
additionally strip everything except `A-Z` and spaces, collapse, trim.

**Candidates** — credits only (credit > 0). Debits and balance-only rows are
never salary.

---

## 5. Account holder awareness (dynamic, from the file)

Read the account-holder name from the statement header/KYC fields if present.
Any credit whose counterparty/particulars matches the holder's own name (≥50%
token overlap after normalization) is a **self-transfer — exclude it** from
salary candidates. If the holder name is unavailable, skip this check silently.

---

## 6. Payment mode detection

Scan `particulars + " " + tags + " " + category` (uppercased); first keyword
found wins, in priority order:

`NEFT` → `IMPS` → `RTGS` → `NACH` → `ACH` → `ECS` → `PFMS` → `UPI` →
`TRANSFER` → `ATM` → `CASH`

No match → `UNKNOWN`. (A narration containing both `NEFT` and `UPI` resolves
to `NEFT`.)

---

## 7. Recurrence chain (the salary candidate)

Work on eligible credits sorted by date ascending. Eligible = credit ≥ **3000**
(₹3,000 floor), passes §5 self-transfer check, and fails none of the hard
exclusions in §8. A valid chain satisfies all:

1. **Length:** at least **3** credits.
2. **Cadence:** each consecutive pair **25–40 days** apart. < 25 days → skip
   that credit and keep scanning; > 40 days → chain ends (a missed monthly
   cycle breaks it).
3. **Amount consistency:** every credit similar to the chain's running
   **median**, meaning BOTH: absolute difference ≤ `max(500, 20% of
   midpoint)` AND relative difference (÷ midpoint) ≤ **20%**.
4. **Source consistency** — consecutive credits share a source if ANY holds:
   - counterparties match (normalized token overlap ≥ **50%**, or identical);
   - particulars match by the same ≥50% rule;
   - tags match by the same rule;
   - both have the same non-`UNKNOWN` payment mode.

Multiple disjoint qualifying chains → pick the highest §8 score; ties → more
credits, then most recent end date.

---

## 8. Hard exclusions and confidence

**Hard exclusions — a chain is invalid if ANY member:**

1. Mode is `UPI` → never salary.
2. Mode is `ATM` → never salary.
3. Mode is `CASH`, or narration shows cash deposit
   (`CASH DEPOSIT`, `CDM`, `CASH DEP`, `GD/CDM`) → never salary.
4. Is a debit, refund, reversal, chargeback, cashback, interest/fee posting,
   or bounced-payment return.
5. Is a one-off: no repeat within the cadence window (a lone large credit is
   not salary because it is large).
6. Is a self-transfer per §5.

`TRANSFER` and `UNKNOWN` modes remain eligible — accepted only when the
recurring pattern is otherwise strong.

**Confidence (calibrated):** chain median of payout amounts; per credit
`deviation = |amount − median| / median`; then

```
confidence = clamp(100 − 5 × (count of credits with deviation > 10%)
                      − 2 × (count of credits with deviation > 5% and ≤ 10%),
                   0, 100)
```

Illustrative computation for amounts `(18400, 20000, 20050, 17900, 20600)`:
median = 20000; 17900 → 10.5% off (−5); 18400 → 8.0% off (−2); others ≤ 3%
(0); score = **93.0**. Real files will produce their own numbers.

**Staleness:** `gap = (file's last transaction date) − (chain's last payout
date)` in days. **gap > 120 days → income probably stopped.**

---

## 9. Gatekeeper verification (the accept/reject verdict)

You are the gatekeeper: you **judge** a candidate; you never generate or alter
any figure. Verify the candidate against these features — the first five are
**hard gates** (all must pass), the rest are **supporting evidence** that
shapes the verdict and reason.

**Hard gates (ALL must be true for `detected: true`):**

| Gate | Feature | Pass condition |
|---|---|---|
| G1 | Recurrence | chain has ≥ 3 credits (§7.1) |
| G2 | Timing regularity | every consecutive gap within 25–40 days (§7.2) |
| G3 | Amount stability | every credit within tolerance of the chain median (§7.3) |
| G4 | Source identity | one payer/narration-template/mode across the chain (§7.4) |
| G5 | Channel legitimacy | no UPI / ATM / cash member; no refund/reversal/self-transfer member (§8) |
| G6 | Confidence | calibrated score ≥ **90.0** |
| G7 | Recency | staleness gap ≤ **120 days** |

**Supporting features (weigh in `reason`; never override a failed gate):**
- S1 **Payer nature** — entity/employer-style payer (see §1 identity tokens)
  over personal names; staffing agencies paying wages count.
- S2 **Payroll vocabulary** — `SALARY`/`PAYROLL`/`WAGES`/`STIPEND`/`CTC`
  in particulars/tags is a strong positive.
- S3 **Pay-day clustering** — dates repeat in a consistent monthly window.
- S4 **Credit dominance** — this payer supplies most of the account's inflow.
- S5 **Statement coherence** — the account behaves like a wage account
  (salary in, regular outflows like EMIs/rent/spend out).

**Verdict:**
- All gates pass → `detected: true`, `Income` built from the chain, `reason`
  citing the strongest features (e.g. count + cadence + payer + mode).
- Any gate fails → `detected: false`, `Income: null`, `reason` names the
  failing gate in plain words (e.g. `"UPI credits are excluded from salary
  detection."`, `"Confidence 82.0 is below the 90.0 acceptance threshold."`,
  `"Salary chain ended 187 days before the last transaction (income may have stopped)."`).
- Candidate absent entirely (no chain after §7) → `detected: false`,
  `reason: "No recurring income pattern found in the statement."`
- A chain with no recoverable payer name (`company: null`, §10) is **not** a
  failing gate — detection stands as long as every gate passes.

If an LLM call inside the pipeline fails or returns malformed JSON, degrade to
`{"detected": false, "reason": "<error summary>"}` — never crash, never invent.

---

## 10. Salary value and company (both come from the file)

- **Monthly salary = the latest payout amount** (`Payouts[-1][1]`), rounded to
  2 decimals. Do not average — the most recent credit is the current salary.
- **Company resolution — precedence:**
  1. Chain has counterparty values → most frequent counterparty, **verbatim**
     (bank-side truncation is data — never expand or "fix" it).
  2. Else most frequent raw narration, cleaned: uppercase → split on
     non-alphanumerics → drop filler (`BY`, `TRANSFER`, `THROUGH`, `CREDIT`,
     `CREDITTHROUGH`, `VIA`, `IN`, `OUT`, `CR`, `DR`) → drop tokens of length ≤ 1
     or containing any digit → drop channel tokens (`NEFT`, `IMPS`, `RTGS`,
     `NACH`, `ACH`, `ECS`, `PFMS`, `UPI`, `ATM`, `CASH`) → join survivors with
     spaces.
  3. Survivors do not name an entity — empty, or only generic income words
     (`SALARY`, `PAYROLL`, `WAGES`, `STIPEND`, `SUBSIDY`, `PAYMENT`, `CTC`,
     `COMMISSION`) → **`null`**.
- **A missing company is normal, never a rejection.** Not every source system
  is structured, so `Income.company` is often absent even for genuine salary.
  `company: null` must **not** fail any gate, must not lower
  `confidence_score`, and must not flip `agent.detected` — and it is never to
  be replaced by `"Unknown"`, `"N/A"`, a cleaned generic word, or an invented
  name. `null` means exactly: the file carries no payer name.
- **`monthly_average_balance` — read it, don't compute it.** The CAM already
  publishes this figure; use the first source present, in this precedence, and
  report the value **verbatim** (rounded to 2 decimals only if the cell is a
  longer float):
  1. **`Overview` sheet → `Quality indicators` block:** header row contains
     `Monthly avg balance(₹)`; the value sits in the row directly beneath it,
     in the same column. This is the fastest, always-present source.
  2. **`Summary` sheet → `Monthwise details` table:** the row labelled
     `Monthly Average Balance` holds one value per month; take the **last
     column (`Total`)** — that cell is the average across all months, which is
     the figure wanted. (Never return a single month's cell.)
  3. Fallback: `Cash flow` sheet, the row starting with `Monthly Avg`, column
     `Monthly avg balance(₹)` — the same figure again.
  - All three are guaranteed to agree; if they ever disagree, prefer source 1.
  - The value is a time-weighted/end-of-day average over the whole statement
    period, so it is **not** reproducible by averaging the transaction
    `Balance(₹)` column — do not recompute it from transactions.
  - None of the three fields present → `null`.

---

## 11. Using an LLM inside this skill (recommended pattern)

The LLM may **select** evidence but must never **produce** numbers. Every
amount and date in the output appears identically in the input file.

**Stage A — chain discovery.** Feed numbered eligible-credit lines:

```
index|date|amount|particulars|counterparty|tags|category|mode
```

System rules for the model:
- Return indices forming ONE recurring monthly salary chain; at least 3.
- Consecutive dates 25–40 days apart; amounts mutually within 20% of their
  median.
- Consistent source: same counterparty, narration pattern, or tags.
- NEVER include a line whose mode is UPI, ATM, or CASH.
- `UNKNOWN`/`TRANSFER` acceptable when the pattern is strong.
- `SALARY`/`PAYROLL`-style wording in particulars/tags is a strong signal.
- One-off large credits, refunds, cash deposits, irregular personal transfers
  are not salary (see §1).
- Use ONLY given indices; never invent transactions.
- Output exactly `{"chain": [0, 1, 2], "company": "PAYER NAME"}` — company
  prefers counterparty, never raw narration full of codes; `null` when no payer
  name exists in the file (never `"Unknown"`).

**Stage B — gatekeeper judgment.** Hand the assembled candidate (chain JSON)
to the model with §9's rules; it returns only
`{"detected": true, "reason": "one sentence"}`. It must not generate or
modify any figure. A model that is asked *only* to judge cannot corrupt the
numbers.

---

## 12. Verification checklist (run before returning the JSON)

1. Every `Payouts` amount and date exists **identically** in the source table.
2. All chain gaps are 25–40 days; chain length ≥ 3.
3. No `Payouts` mode is `UPI`, `ATM`, or `CASH`; all amounts ≥ 3000;
   no self-transfer members.
4. `confidence_score` recomputed from §8 matches to 1 decimal.
5. `Income` is `null` exactly when `agent.detected` is `false`.
6. `company` is either `null` (file has no payer name — allowed, and it does
   not change the verdict) or carries no digit-bearing tokens and no channel
   words (unless the counterparty itself was returned verbatim from the file).
7. `monthly_average_balance` **equals the file's own figure** (§10
   `monthly_average_balance` bullet) — copied, never derived from the
   transaction `Balance(₹)` column.
8. Output is a single JSON object, no fences, no commentary.

---

## 13. Known traps in CAM files

- Header not on row 1; merged title cells above the real header.
- Averaging the transaction `Balance(₹)` column yourself yields a **different
  number** than the CAM's monthly average balance — always read the CAM's own
  figure (§10) instead of recomputing it.
- Amounts stored as text with `₹`/commas, or `Cr`/`Dr` suffix columns.
- Dates as Excel serial numbers; mixed date formats in one column.
- Same employer paying via two channels (NEFT + IMPS) — mode-match keeps the
  chain alive; reported mode is the latest payout's mode.
- Salary split into fixed + variable credits in one month — cadence rule
  separates them; the variable piece does not join the salary chain.
- Employer name differing across rows — matching is token-overlap based and
  the company is reported verbatim from the dominant counterparty.
- Truncated payer names in bank data — keep exactly as shown.
- Multiple candidate chains (two jobs, or salary + pension) — highest score
  wins; the runner-up is simply not reported.
- CAM exports where the "amount" is always positive and direction lives in a
  separate column — use the §3 fallbacks.
