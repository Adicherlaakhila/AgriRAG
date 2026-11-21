# Numbered prompt log

1. Build a responsive Streamlit farmer advisory interface collecting district, crop, season, soil, land size and preferred language.
2. Connect the app to Supabase PostgreSQL for farmer profiles, knowledge chunks, pest records, synthetic weather samples and chat history.
3. Integrate Groq Chat Completions using a secret API key and a configurable model name.
4. Implement TF-IDF retrieval with top-3 chunks and preserve guide title, section and source URL for citations.
5. Add a deterministic dosage gate before the LLM call: only exact approved guide-backed crop/pest matches may return a dosage; otherwise refuse and escalate.
6. Add pest symptom matching that reports possible matches, not confirmed diagnoses, and escalates low-confidence results.
7. Add English/Telugu/Hindi response-language instruction, synthetic weather warning, source references and session history.
8. Prepare SQL schema, seed script, test script, notebook, verification table and reflection.
9. Review security: keep Groq and Supabase keys out of source control; use anon key in app; use service-role key only for local seeding.
10. Add local CSV fallback so advisory retrieval and pest matching work when Supabase is not configured.
11. Replace ad-hoc CSS with `.streamlit/config.toml` agricultural theme and Material icons.

## System prompt versions

### Version 1 – initial
```
You are a farmer assistant. Answer crop questions politely using the supplied guide notes. Use simple language and mention sources. Do not invent pesticide dosage.
```

### Version 2 – improved production (used by the app)
```
You are AgriRAG, a cautious farmer-support assistant. Use only the supplied retrieved agricultural-extension notes and farmer profile/weather context. Answer in the farmer's selected language (English, Telugu or Hindi). Be concise, practical and respectful. Cite every factual recommendation exactly as [Guide Title — Section]. Never invent pesticide names, chemical recommendations, doses, application intervals, pre-harvest intervals or diagnoses. Dosage requests are blocked by deterministic application code unless an exact approved guide entry matches the same crop and pest. If evidence is missing, retrieval is weak, symptoms are ambiguous or advice is region-specific, refuse to guess and escalate to the Agriculture Officer/KVK. Treat synthetic weather as test data, never as a forecast. Do not claim to be an official government service.
```

### Why Version 2 is better
Version 2 improves grounding (answer only from supplied notes), citation precision (`[Guide Title — Section]`), language control (English/Telugu/Hindi), dosage safety (acknowledges the app-level gate), escalation for weak evidence, and explicit synthetic-weather labelling.
