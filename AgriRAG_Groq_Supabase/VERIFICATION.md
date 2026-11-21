# Verification table (refinements)

| Suggestion | How checked | Result | Change |
|------------|-------------|--------|--------|
| Dosage must not rely on TF-IDF alone | Ran T6/T7 in `test_pipeline.py`; cotton dosage request returns `None` from gate | Pass | Deterministic `safe_dosage_match` + `is_dosage_request` before Groq |
| Weak retrieval should escalate | Empty/low-score retrieval returns refusal helper | Pass | Added `MIN_RETRIEVAL_SCORE` and `weak_retrieval_message()` |
| App must not require service-role key | Reviewed `db.py` and secrets example | Pass | App uses `SUPABASE_ANON_KEY`; seed uses service-role via env only |
| Offline demo without Supabase | Loaded `data/*.csv` via `local_data.py` when DB missing | Pass | CSV fallback for guides, pests, weather |
| Synthetic weather must be labelled | UI expander warning + prompt weather note | Pass | Explicit SYNTHETIC TEST DATA warning in UI and prompt |
| Citations must use guide title — section | Chat footer lists retrieved title/section/URL/score | Pass | Citation footer appended after Groq answer |

## Before / after evidence (two refinements)

### 1. Unrelated dosage retrieval
- **Before:** A dosage-like question could reach Groq and risk invented product names.
- **After:** `is_dosage_request` intercepts first; only tomato + serpentine leaf miner + NSKE with `dosage_approved=True` may return a dose; otherwise refusal + fictional officer escalation.

### 2. Low-confidence pest match treated as diagnosis
- **Before risk:** Keyword overlap could be presented as a firm pest ID.
- **After:** Matches require ≥2 token overlaps; copy says **possible match (not a confirmed diagnosis)**; below threshold → low-confidence escalation with no spray advice.
