# Chatbot / AI assistance log

| # | Tool / assistant | Request | Output used |
|---|------------------|---------|-------------|
| 1 | Cursor Agent (Composer) | Build AgriRAG from handoff: Streamlit UI, Groq, Supabase, TF-IDF RAG, safety gates | Full app modules (`app.py`, `rag.py`, `db.py`, `local_data.py`, seed, schema, tests, theme) |
| 2 | Cursor Agent | Preserve existing working retrieval and dosage gate | Kept exact tomato NSKE dosage gate; expanded CSV knowledge base and local fallback |
| 3 | Cursor Agent | Align secrets with security requirements | Switched Streamlit app to `SUPABASE_ANON_KEY`; service-role limited to `seed_supabase.py` |
| 4 | Streamlit bundled skill | Theme and chat UI best practices | `.streamlit/config.toml` green agricultural theme; native chat elements; `width="stretch"` |
| 5 | Cursor Agent | Assignment artifacts | `PROMPT_LOG.md`, this log, verification/reflection notes, `test_pipeline.py` |

Unused drafts: none retained. Hardcoded service-role usage in the Streamlit client was removed in favour of the anon key + CSV fallback.
