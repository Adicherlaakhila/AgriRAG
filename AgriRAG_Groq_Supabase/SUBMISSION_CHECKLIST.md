# Submission checklist

## Supabase
- [ ] Run `supabase_schema.sql` in Supabase SQL Editor
- [ ] Seed knowledge chunks, pest records and synthetic weather (`python seed_supabase.py`)
- [ ] Confirm tables have rows in Table Editor

## Local app
- [ ] Create `.streamlit/secrets.toml` from the example (anon key, not service-role)
- [ ] Install `requirements.txt`
- [ ] Run `python test_pipeline.py`
- [ ] Run `streamlit run app.py`

## Screenshots (5)
1. Farmer profile saved
2. Cited crop advisory answer
3. Pest symptom match with guide reference
4. Unsupported dosage refused and escalated
5. Telugu/Hindi response

## Part B
- [ ] Run all notebook cells with real outputs
- [ ] Save terminal test output
- [ ] Include verification table, chatbot log and reflection

## Deployment
- [ ] Push to public GitHub repo (no secrets)
- [ ] Add Streamlit Cloud Secrets (`GROQ_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`)
- [ ] Deploy with main file `app.py`
- [ ] Test public URL without login
