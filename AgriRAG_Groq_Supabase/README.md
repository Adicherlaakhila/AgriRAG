# AgriRAG — Groq + Supabase PostgreSQL + TF-IDF

Educational farmer-support prototype for sowing, nutrients, irrigation, soil and pest questions. Answers are grounded in curated agricultural-extension notes with guide-title/section citations, multilingual replies (English / Telugu / Hindi), a deterministic dosage safety gate, and officer/KVK escalation for unsupported advice.

**Not an official agricultural service.** Synthetic weather is test data. Officer contacts are fictional placeholders.

## Architecture

| Layer | Technology |
|-------|------------|
| Frontend | Streamlit |
| LLM | Groq Chat Completions |
| Database | Supabase PostgreSQL |
| Retrieval | scikit-learn TF-IDF (top 3) |
| Languages | English, Telugu, Hindi |

## Project layout

```
AgriRAG_Groq_Supabase/
├── app.py                 # Streamlit UI
├── rag.py                 # TF-IDF, dosage gate, pest match, prompts
├── db.py                  # Supabase CRUD (anon key)
├── local_data.py          # CSV fallback loaders
├── seed_supabase.py       # Seed script (service-role key, local only)
├── test_pipeline.py       # Minimum assignment tests T1–T8
├── supabase_schema.sql
├── requirements.txt
├── AgriRAG_PartB.ipynb
├── PROMPT_LOG.md
├── CHATBOT_LOG.md
├── VERIFICATION.md
├── REFLECTION.md
├── data/
│   ├── crop_guides.csv
│   ├── pest_database.csv
│   └── weather_14day.csv
└── .streamlit/
    ├── config.toml
    └── secrets.toml.example
```

## 1. Create Supabase project

1. Create a project at https://supabase.com/dashboard.
2. Open SQL Editor and run all of `supabase_schema.sql`.
3. In Project Settings → API, copy the **Project URL** and the **anon/publishable** key for the Streamlit app.
4. Keep the **service_role** key for local seeding only. Never commit it or paste it into chat.

## 2. Create Groq API key

1. Visit https://console.groq.com/keys and create a key.
2. Do not paste the key into source code or GitHub.

## 3. Configure local secrets

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`:

```toml
GROQ_API_KEY = "your-groq-key"
GROQ_MODEL = "llama-3.3-70b-versatile"
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_ANON_KEY = "your-anon-key"
```

For seeding only (PowerShell):

```powershell
$env:SUPABASE_URL="https://your-project.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
```

## 4. Install and run (Windows PowerShell)

```powershell
cd AgriRAG_Groq_Supabase
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python seed_supabase.py
python test_pipeline.py
streamlit run app.py
```

Open http://localhost:8501.

The app also works with **local CSV fallback** if Supabase secrets are missing (session-only profile; no chat persistence).

## 5. Deploy on Streamlit Community Cloud

1. Push this folder to a public GitHub repository (do not commit `secrets.toml` or `.env`).
2. Create an app in Streamlit Community Cloud with main file `app.py`.
3. Add secrets:

```toml
GROQ_API_KEY = "your-groq-key"
GROQ_MODEL = "llama-3.3-70b-versatile"
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_ANON_KEY = "your-anon-key"
```

4. Deploy and open the public URL (no login wall).

## Safety behaviour

- Dosage questions are intercepted **before** Groq.
- Only the approved tomato serpentine leaf miner NSKE guide entry may quote a dose.
- Unknown dosage → refuse, do not invent a pesticide, escalate.
- Pest matcher returns **possible matches**, never confirmed diagnoses.
- Weak TF-IDF retrieval → refuse and escalate.
- Weather expander and prompts label data as **SYNTHETIC TEST DATA**.

## Security notes

- Never commit `.streamlit/secrets.toml`, `.env`, API keys or the Supabase service-role key.
- Classroom anon write policies in `supabase_schema.sql` are for the assignment only — not production.
- For real farmer data, add Supabase Auth and owner-based RLS.
