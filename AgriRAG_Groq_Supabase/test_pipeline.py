"""Minimum 8 assignment tests for AgriRAG retrieval and safety gates."""
from rag import (
    retrieve_top_chunks,
    is_dosage_request,
    safe_dosage_match,
    pest_match,
    build_grounded_prompt,
    dosage_refusal_message,
    weak_retrieval_message,
)
from local_data import load_guides_csv, load_pests_csv

chunks = load_guides_csv()
if not chunks:
    # Fallback inline fixtures if CSV missing
    chunks = [
        {
            "crop": "Paddy",
            "guide_title": "TNAU Rice Water Management",
            "section": "Water management stages",
            "content": "Rice water needs vary by soil, season and crop stage.",
            "source_url": "https://agritech.tnau.ac.in/expert_system/paddy/cultivationpractices3.html",
            "keywords": "paddy rice irrigation water stage",
            "dosage_approved": False,
        },
        {
            "crop": "Paddy",
            "guide_title": "TNAU Rice Production Guide",
            "section": "Rice nutrient management",
            "content": "Use soil-test-based nutrient recommendations.",
            "source_url": "https://agritech.tnau.ac.in/agriculture/agri_cropproduction_cereals_rice2.html",
            "keywords": "paddy rice nutrient fertilizer soil test",
            "dosage_approved": False,
        },
        {
            "crop": "Cotton",
            "guide_title": "TNAU Cotton IPM",
            "section": "Pest surveillance",
            "content": "Scout cotton for sucking pests and bollworms.",
            "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_ipm_cotton.html",
            "keywords": "cotton whitefly pest scouting traps",
            "dosage_approved": False,
        },
        {
            "crop": "Tomato",
            "guide_title": "TNAU Tomato Crop Guide",
            "section": "Soil and season",
            "content": "Tomato performs best in well-drained loamy or sandy-loam soil.",
            "source_url": "https://agritech.tnau.ac.in/govt_schemes_services/aas/tomato.html",
            "keywords": "tomato soil sandy loam drainage",
            "dosage_approved": False,
        },
        {
            "crop": "Tomato",
            "guide_title": "TNAU Tomato Crop Protection Guide",
            "section": "Serpentine leaf miner – botanical option",
            "content": "NSKE at 50 g per litre for serpentine leaf miner.",
            "source_url": "https://agritech.tnau.ac.in/govt_schemes_services/aas/tomato.html",
            "keywords": "tomato serpentine leaf miner NSKE 50 g litre",
            "dosage_approved": True,
        },
    ]

pests = load_pests_csv()


def check(name, condition):
    print(("PASS" if condition else "FAIL") + " | " + name)
    return bool(condition)


results = []
paddy = {
    "district": "Warangal",
    "crop": "Paddy",
    "season": "Kharif",
    "soil": "Clay",
    "land_acres": 2,
    "language": "English",
    "name": "Test Farmer",
}
cotton = {**paddy, "crop": "Cotton", "soil": "Black cotton soil"}
tomato = {**paddy, "crop": "Tomato", "soil": "Sandy loam"}

results.append(
    check(
        "T1 Paddy irrigation retrieves cited water note",
        any(
            "water" in x["section"].lower() or "irrigation" in x["section"].lower()
            for x in retrieve_top_chunks("How should I manage paddy irrigation?", paddy, chunks, 3)
        ),
    )
)
results.append(
    check(
        "T2 Cotton pest scouting retrieves cotton IPM note",
        any(
            x["crop"] == "Cotton"
            for x in retrieve_top_chunks("How do I monitor cotton whitefly and scout pests?", cotton, chunks, 3)
        ),
    )
)
results.append(
    check(
        "T3 Tomato soil retrieves soil/drainage advice",
        any(
            "soil" in x["section"].lower()
            for x in retrieve_top_chunks("What soil is suitable for tomato?", tomato, chunks, 3)
        ),
    )
)
results.append(
    check(
        "T4 Paddy nutrient query retrieves nutrient note",
        any(
            "nutrient" in x["section"].lower()
            for x in retrieve_top_chunks("How should paddy nutrients be managed with soil test?", paddy, chunks, 3)
        ),
    )
)

te_profile = {**paddy, "language": "Telugu"}
prompt = build_grounded_prompt(
    "నీటి పారుదల ఎలా నిర్వహించాలి?",
    te_profile,
    retrieve_top_chunks("paddy irrigation నీటి పారుదల", te_profile, chunks, 3),
    None,
)
results.append(
    check(
        "T5 Telugu question passes selected language to prompt",
        "Telugu" in prompt["user"] and "AgriRAG" in prompt["system"],
    )
)

covered = retrieve_top_chunks("NSKE dosage tomato serpentine leaf miner", tomato, chunks, 3)
results.append(
    check(
        "T6 Covered tomato leaf-miner NSKE dose passes exact-match gate",
        safe_dosage_match(
            "What is NSKE dosage for tomato serpentine leaf miner?", tomato, covered
        )
        is not None,
    )
)
results.append(
    check(
        "T7 Uncovered cotton dosage is refused by gate",
        safe_dosage_match("What is pesticide dosage for cotton bollworm?", cotton, chunks) is None
        and is_dosage_request("What is pesticide dosage for cotton bollworm?")
        and "cannot provide a verified dosage" in dosage_refusal_message().lower(),
    )
)

unknown = pest_match("Tomato", "purple mosaic dots and unknown stem rings", pests or [])
results.append(
    check(
        "T8 Unknown pest escalates without a diagnosis",
        "Low-confidence" in unknown or "escalation" in unknown.lower(),
    )
)

# Extra regression: weak retrieval path exists
results.append(
    check(
        "Weak retrieval message is defined for escalation",
        "No sufficiently relevant" in weak_retrieval_message(),
    )
)

passed = sum(results)
print(f"\n{passed}/{len(results)} tests passed.")
raise SystemExit(0 if passed == len(results) else 1)
