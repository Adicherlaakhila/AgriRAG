"""AgriRAG — Streamlit farmer advisory with Groq + Supabase + TF-IDF RAG."""
from __future__ import annotations

import streamlit as st
from groq import Groq

from db import (
    get_supabase,
    load_chat_history,
    load_knowledge_chunks,
    load_pest_rows,
    load_weather,
    save_chat_message,
    save_profile,
)
from rag import (
    FICTIONAL_ESCALATION,
    answer_needs_escalation,
    build_grounded_prompt,
    dosage_refusal_message,
    is_dosage_request,
    pest_match,
    retrieve_top_chunks,
    safe_dosage_match,
    weak_retrieval_message,
)

st.set_page_config(
    page_title="AgriRAG | Farmer advisory",
    page_icon=":material/agriculture:",
    layout="wide",
    initial_sidebar_state="expanded",
)

DISTRICTS = ["Warangal", "Nalgonda"]
CROPS = ["Paddy", "Cotton", "Tomato"]
SEASONS = ["Kharif", "Rabi", "Summer"]
SOILS = ["Clay", "Sandy loam", "Red loam", "Black cotton soil", "Alluvial"]
LANGUAGES = ["English", "Telugu", "Hindi"]

PUBLIC_REFS = [
    ("TNAU Rice production", "https://agritech.tnau.ac.in/agriculture/agri_cropproduction_cereals_rice2.html"),
    ("TNAU Rice water management", "https://agritech.tnau.ac.in/expert_system/paddy/cultivationpractices3.html"),
    ("TNAU Cotton IPM", "https://agritech.tnau.ac.in/crop_protection/crop_prot_ipm_cotton.html"),
    ("NIPHM Tomato IPM package", "https://niphm.gov.in/IPMPackages/Tomato-R.pdf"),
    ("TNAU Soil Health Card", "https://agritech.tnau.ac.in/agriculture/agri_soil_soilhealthcard.html"),
]


def init_state() -> None:
    defaults = {
        "profile": None,
        "messages": [],
        "farmer_id": None,
        "history_loaded": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


@st.cache_resource(show_spinner=False)
def get_groq_client() -> Groq | None:
    try:
        key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        key = ""
    if not key:
        return None
    return Groq(api_key=key)


def ask_advisor(question: str, profile: dict, weather_df, chunks: list[dict]) -> str:
    if not chunks:
        return (
            "Knowledge base is empty. Place CSV files under `data/` or run "
            "`python seed_supabase.py` after configuring Supabase."
        )

    top_chunks = retrieve_top_chunks(question, profile, chunks, top_k=3)

    # Deterministic dosage gate BEFORE any Groq call.
    if is_dosage_request(question):
        approved = safe_dosage_match(question, profile, top_chunks)
        if approved:
            return (
                f"**Limited guide-backed information:** {approved['content']}\n\n"
                f"**Citation:** [{approved['guide_title']} — {approved['section']}]"
                f"({approved.get('source_url', '')})\n\n"
                "Do not generalize this to another crop or pest. Confirm current label "
                "directions and local suitability with the Agriculture Officer/KVK."
            )
        return dosage_refusal_message()

    if not top_chunks:
        return weak_retrieval_message()

    client = get_groq_client()
    if client is None:
        return (
            "Groq API key is not configured. Add `GROQ_API_KEY` in "
            "`.streamlit/secrets.toml`, then restart the app."
        )

    prompt = build_grounded_prompt(question, profile, top_chunks, weather_df, prompt_version="v2")
    try:
        completion = client.chat.completions.create(
            model=st.secrets.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]},
            ],
            temperature=0.1,
            max_tokens=900,
        )
        answer = completion.choices[0].message.content or "I could not generate a grounded answer."
    except Exception as exc:
        return (
            f"Groq request failed: {exc}. "
            "Check your API key, model access and internet connection."
        )

    citation_lines = [
        f"- [{c['guide_title']} — {c['section']}]({c.get('source_url', '')}) "
        f"(score {c.get('_score', 0):.3f})"
        for c in top_chunks
    ]
    answer += "\n\n**Retrieved guide references:**\n" + "\n".join(citation_lines)
    if answer_needs_escalation(answer, top_chunks):
        answer += (
            "\n\n**Please verify with your Agriculture Officer/KVK before acting.**\n\n"
            f"{FICTIONAL_ESCALATION}"
        )
    return answer


def render_sidebar(supabase) -> None:
    with st.sidebar:
        st.header(":material/person: Farmer profile")
        with st.form("profile_form"):
            farmer_name = st.text_input("Name (optional)", max_chars=60)
            district = st.selectbox("District", DISTRICTS)
            crop = st.selectbox("Crop", CROPS)
            season = st.selectbox("Season", SEASONS)
            soil = st.selectbox("Soil type", SOILS)
            land = st.number_input(
                "Land size (acres)",
                min_value=0.1,
                max_value=1000.0,
                value=1.0,
                step=0.1,
            )
            language = st.selectbox("Preferred language", LANGUAGES)
            save = st.form_submit_button("Save profile", type="primary", width="stretch")
            if save:
                if land <= 0:
                    st.error("Land size must be greater than zero.")
                else:
                    profile = {
                        "name": farmer_name.strip() or "Farmer",
                        "district": district,
                        "crop": crop,
                        "season": season,
                        "soil": soil,
                        "land_acres": float(land),
                        "language": language,
                    }
                    st.session_state.profile = profile
                    st.session_state.messages = []
                    st.session_state.history_loaded = False
                    st.session_state.farmer_id = None
                    if supabase:
                        try:
                            st.session_state.farmer_id = save_profile(supabase, profile)
                            st.success("Profile saved to Supabase.")
                        except Exception as exc:
                            st.warning(
                                f"Profile active for this session, but database save failed: {exc}"
                            )
                    else:
                        st.warning(
                            "Profile saved for this session only. "
                            "Configure Supabase secrets to enable persistence."
                        )

        st.divider()
        db_label = "Connected" if supabase else "Local CSV fallback"
        st.caption(f"Database: {db_label}")
        if st.button("Clear visible chat", width="stretch"):
            st.session_state.messages = []
            st.rerun()


def main() -> None:
    init_state()

    st.title("AgriRAG")
    st.caption(
        "Educational prototype · Groq · Supabase PostgreSQL · TF-IDF RAG · "
        "English | తెలుగు | हिन्दी — not an official agricultural service."
    )

    try:
        supabase = get_supabase()
    except Exception as exc:
        supabase = None
        st.error(f"Database connection issue: {exc}")

    render_sidebar(supabase)

    profile = st.session_state.profile
    if not profile:
        st.info(
            title="Complete your farmer profile",
            body="Use the sidebar form (district, crop, season, soil, land size and language) to enable advisory chat.",
        )
        st.subheader("Ask about sowing, nutrients, irrigation, soil or pest symptoms")
        st.markdown(
            "After saving a profile, you can chat for cited crop advice, match pest symptoms, "
            "and review knowledge sources. Dosage questions are gated in application code."
        )
        return

    metrics = st.container(horizontal=True, gap="medium")
    with metrics:
        st.metric("Crop", profile["crop"])
        st.metric("District", profile["district"])
        st.metric("Season", profile["season"])
        st.metric("Land", f'{profile["land_acres"]:.1f} acres')
        st.metric("Language", profile["language"])

    weather_df = load_weather(supabase, profile["district"])
    chunks = load_knowledge_chunks(supabase)
    pests = load_pest_rows(supabase)

    with st.expander("District weather sample (synthetic)", expanded=False):
        if weather_df is not None and not weather_df.empty:
            st.dataframe(weather_df.head(7), hide_index=True, alt="Synthetic district weather sample")
        else:
            st.info("No weather rows loaded. Check `data/weather_14day.csv` or seed Supabase.")
        st.warning(
            title="Synthetic test data",
            body="The supplied 14-day CSV is SYNTHETIC TEST DATA, not a live or official forecast.",
        )

    tabs = st.tabs(
        [
            ":material/chat: Advisory chat",
            ":material/bug_report: Pest matcher",
            ":material/menu_book: Knowledge base",
            ":material/shield: Sources & safety",
        ]
    )

    with tabs[0]:
        st.subheader("Farmer advisory chat")
        if (
            supabase
            and st.session_state.farmer_id
            and not st.session_state.history_loaded
            and not st.session_state.messages
        ):
            try:
                history = load_chat_history(supabase, st.session_state.farmer_id)
                st.session_state.messages = [
                    {"role": x["role"], "content": x["content"]} for x in history
                ]
            except Exception:
                pass
            st.session_state.history_loaded = True

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        question = st.chat_input("Ask a question about your crop…")
        if question:
            st.session_state.messages.append({"role": "user", "content": question})
            if supabase and st.session_state.farmer_id:
                try:
                    save_chat_message(supabase, st.session_state.farmer_id, "user", question)
                except Exception:
                    pass

            with st.spinner("Retrieving guides and drafting a grounded answer…"):
                answer = ask_advisor(question, profile, weather_df, chunks)

            st.session_state.messages.append({"role": "assistant", "content": answer})
            if supabase and st.session_state.farmer_id:
                try:
                    save_chat_message(supabase, st.session_state.farmer_id, "assistant", answer)
                except Exception:
                    pass
            st.rerun()

    with tabs[1]:
        st.subheader("Pest symptom matching")
        st.caption("Results are possible matches only — never a confirmed diagnosis.")
        pest_crop = st.selectbox("Crop", CROPS, key="pest_crop")
        symptoms = st.text_area(
            "Describe symptoms",
            placeholder="Example: tiny white insects under leaves and sticky honeydew",
            height=120,
        )
        if st.button("Find possible pest match", type="primary"):
            st.markdown(pest_match(pest_crop, symptoms, pests))

    with tabs[2]:
        st.subheader("Knowledge base")
        rows = chunks
        relevant = [item for item in rows if item.get("crop") in {profile["crop"], "Soil", "General"}]
        if not relevant:
            st.info("No knowledge chunks loaded.")
        for item in relevant:
            with st.expander(f'{item["guide_title"]} — {item["section"]}'):
                st.write(item["content"])
                if item.get("source_url"):
                    st.link_button("Open source", item["source_url"], width="content")
                if item.get("dosage_approved"):
                    st.badge("Dosage-approved record", icon=":material/verified:")

    with tabs[3]:
        st.subheader("Sources, privacy and safe use")
        st.markdown(
            """
- Answers use the retrieved knowledge base and your farmer profile.
- Every crop recommendation should cite a guide title and section.
- Chemical pesticide dosage is returned only by an exact approved-guide match; otherwise it is refused and escalated.
- Synthetic weather is for software testing only, not a forecast.
- Do not enter bank details, Aadhaar numbers or other sensitive personal data.
- Officer names and phone numbers shown by the app are **fictional assignment placeholders**.
            """
        )
        st.markdown("**Public extension references**")
        for title, url in PUBLIC_REFS:
            st.markdown(f"- [{title}]({url})")
        st.info(
            title="Escalation",
            body=FICTIONAL_ESCALATION.replace("**", ""),
        )


if __name__ == "__main__":
    main()
