"""TF-IDF retrieval, dosage safety gate, pest matching, and grounded prompts."""
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DOSAGE_TERMS = [
    "dose",
    "dosage",
    "how much",
    "quantity",
    "ml/l",
    "g/l",
    "per litre",
    "per liter",
    "spray rate",
    "application rate",
    "मात्रा",
    "మోతాదు",
    "ఎంత మోతాదు",
]

# Minimum cosine similarity for a chunk to count as usable evidence.
MIN_RETRIEVAL_SCORE = 0.05

FICTIONAL_ESCALATION = (
    "**Fictional assignment escalation desk (placeholders only):** "
    "Dr. Kavya Rao, Mandal Agriculture Officer — 90000 10001; "
    "Mr. Ramesh Naik, KVK Support Desk — 90000 10002."
)

SYSTEM_PROMPT_V1 = (
    "You are a farmer assistant. Answer crop questions politely using the supplied "
    "guide notes. Use simple language and mention sources. Do not invent pesticide dosage."
)

SYSTEM_PROMPT_V2 = """You are AgriRAG, a cautious farmer-support assistant. Use only the supplied retrieved agricultural-extension notes and farmer profile/weather context. Answer in the farmer's selected language (English, Telugu or Hindi). Be concise, practical and respectful. Cite every factual recommendation exactly as [Guide Title — Section]. Never invent pesticide names, chemical recommendations, doses, application intervals, pre-harvest intervals or diagnoses. Dosage requests are blocked by deterministic application code unless an exact approved guide entry matches the same crop and pest. If evidence is missing, retrieval is weak, symptoms are ambiguous or advice is region-specific, refuse to guess and escalate to the Agriculture Officer/KVK. Treat synthetic weather as test data, never as a forecast. Do not claim to be an official government service."""


def tokens(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(s).lower())


def is_dosage_request(question: str) -> bool:
    q = question.lower()
    return any(x in q for x in DOSAGE_TERMS)


def retrieve_top_chunks(question: str, profile: dict, chunks: list[dict], top_k: int = 3) -> list[dict]:
    if not chunks:
        return []
    q = " ".join(
        [
            question,
            profile.get("crop", ""),
            profile.get("soil", ""),
            profile.get("season", ""),
            profile.get("district", ""),
        ]
    )
    docs = [
        f"{x.get('guide_title', '')} {x.get('section', '')} {x.get('crop', '')} "
        f"{x.get('content', '')} {x.get('keywords', '')}"
        for x in chunks
    ]
    vec = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    matrix = vec.fit_transform(docs + [q])
    scores = cosine_similarity(matrix[-1], matrix[:-1]).flatten()
    inds = scores.argsort()[::-1][:top_k]
    return [
        {**chunks[i], "_score": float(scores[i])}
        for i in inds
        if scores[i] > MIN_RETRIEVAL_SCORE
    ]


def retrieval_is_weak(chunks: list[dict]) -> bool:
    if not chunks:
        return True
    return max(c.get("_score", 0.0) for c in chunks) < MIN_RETRIEVAL_SCORE


def safe_dosage_match(question: str, profile: dict, retrieved: list[dict]) -> dict | None:
    """Exact crop+pest+approved-guide gate. Never return dosage from TF-IDF similarity alone."""
    q = question.lower()
    crop_ok = profile.get("crop", "").lower() == "tomato" and "tomato" in q
    pest_ok = ("serpentine" in q or "leaf miner" in q) and any(
        "serpentine" in str(c.get("section", "")).lower() for c in retrieved
    )
    botanical_ok = "nske" in q or "neem seed kernel" in q
    if not (crop_ok and pest_ok and botanical_ok):
        return None
    for c in retrieved:
        approved = str(c.get("dosage_approved", "")).lower() in {"true", "1", "yes"}
        if (
            approved
            and str(c.get("crop", "")).lower() == "tomato"
            and "serpentine" in str(c.get("section", "")).lower()
        ):
            return c
    return None


def dosage_refusal_message() -> str:
    return (
        "**I cannot provide a verified dosage for this request.** "
        "I will not guess or invent a pesticide name or quantity. "
        "Please contact the Agriculture Officer/KVK.\n\n"
        f"{FICTIONAL_ESCALATION}\n\n"
        "**Citation:** No exact matching dosage was found in the approved retrieved guide notes."
    )


def weak_retrieval_message() -> str:
    return (
        "**No sufficiently relevant guide notes were retrieved for this question.** "
        "I will not guess. Please rephrase with crop, stage and location details, "
        "or contact the Agriculture Officer/KVK.\n\n"
        f"{FICTIONAL_ESCALATION}"
    )


def build_grounded_prompt(
    question: str,
    profile: dict,
    chunks: list[dict],
    weather_df,
    prompt_version: str = "v2",
) -> dict[str, str]:
    context = []
    for i, c in enumerate(chunks, 1):
        context.append(
            f"[{i}] Guide: {c.get('guide_title')} | Section: {c.get('section')} | "
            f"Crop: {c.get('crop')} | Text: {c.get('content')} | Source: {c.get('source_url')}"
        )
    weather = "No weather sample available."
    if weather_df is not None and hasattr(weather_df, "empty") and not weather_df.empty:
        weather = (
            weather_df.head(5).to_string(index=False)
            + "\nNOTE: all these weather rows are SYNTHETIC test data, not a forecast."
        )
    system = SYSTEM_PROMPT_V2 if prompt_version == "v2" else SYSTEM_PROMPT_V1
    user = f"""FARMER PROFILE:
Name: {profile.get('name')}
District: {profile.get('district')}
Crop: {profile.get('crop')}
Season: {profile.get('season')}
Soil: {profile.get('soil')}
Land size: {profile.get('land_acres')} acres
Preferred language: {profile.get('language')}

SYNTHETIC WEATHER CONTEXT:
{weather}

RETRIEVED KNOWLEDGE (top 3 TF-IDF chunks):
{chr(10).join(context) if context else 'No relevant guide chunks retrieved.'}

FARMER QUESTION:
{question}

Give a concise, actionable answer in the preferred language. Cite the exact guide title and section. If confidence/evidence is inadequate, refuse to guess and escalate."""
    return {"system": system, "user": user}


def answer_needs_escalation(answer: str, chunks: list[dict]) -> bool:
    low = [
        "not available in the knowledge base",
        "cannot confirm",
        "not enough information",
        "uncertain",
        "escalate",
    ]
    return not chunks or any(x in answer.lower() for x in low)


def pest_match(crop: str, symptoms: str, rows: list[dict]) -> str:
    if len(symptoms.strip()) < 8:
        return (
            "Please describe symptoms in more detail "
            "(leaf colour, insects seen, crop stage). "
            "No diagnosis or pesticide recommendation can be made."
        )
    q = set(tokens(symptoms))
    ranked = []
    for row in rows:
        if str(row.get("crop", "")).lower() != crop.lower():
            continue
        hay = set(tokens(str(row.get("symptoms", "")) + " " + str(row.get("pest", ""))))
        score = len(q & hay)
        ranked.append((score, row))
    ranked.sort(key=lambda x: x[0], reverse=True)
    if not ranked or ranked[0][0] < 2:
        return (
            "**Low-confidence match — escalation required.** "
            "Symptoms do not uniquely identify a pest. "
            "Take clear photos and contact the Agriculture Officer/KVK. "
            "No pesticide or dosage is recommended.\n\n"
            f"{FICTIONAL_ESCALATION}"
        )
    score, row = ranked[0]
    return (
        f"**Possible match (not a confirmed diagnosis): {row['pest']}**\n\n"
        f"**Recorded symptoms:** {row['symptoms']}\n\n"
        f"**Cited management:** {row['management']}\n\n"
        f"**Guide reference:** {row['guide_reference']}\n\n"
        "Confirm with an Agriculture Officer/KVK before taking action. "
        "No chemical dosage is provided."
    )
