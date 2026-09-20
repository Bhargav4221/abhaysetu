from __future__ import annotations

from .enums import EmergencyCategory, Priority

# Lightweight offline classifier. Assistive only — never blocks SOS.
KEYWORD_MAP: list[tuple[EmergencyCategory, tuple[str, ...]]] = [
    (EmergencyCategory.MEDICAL, ("medical", "ambulance", "heart", "stroke", "unconscious", "bleeding", "వైద్య", "चिकित्सा", "मदद")),
    (EmergencyCategory.FIRE, ("fire", "smoke", "burn", "आग", "మంట", "fire outbreak")),
    (EmergencyCategory.FLOOD, ("flood", "drowning", "water rising", "వరద", "बाढ़")),
    (EmergencyCategory.CYCLONE, ("cyclone", "hurricane", "typhoon", "తుఫాను", "चक्रवात")),
    (EmergencyCategory.EARTHQUAKE, ("earthquake", "tremor", "భూకంపం", "भूकंप")),
    (EmergencyCategory.LANDSLIDE, ("landslide", "mudslide", "కొండచరియ", "भूस्खलन")),
    (EmergencyCategory.TRAPPED_PERSON, ("trapped", "stuck", "under debris", "ఇరుక్కుపోయారు", "फंसे")),
    (EmergencyCategory.RESCUE_REQUIRED, ("rescue", "help me", "save", "రక్షణ", "बचाओ")),
    (EmergencyCategory.ACCIDENT, ("accident", "crash", "collision", "ప్రమాదం", "दुर्घटना")),
    (EmergencyCategory.MISSING_PERSON, ("missing", "lost person", "తప్పిపోయారు", "लापता")),
    (EmergencyCategory.SHELTER_REQUIRED, ("shelter", "homeless", "ఆశ్రయం", "आश्रय")),
    (EmergencyCategory.FOOD_REQUIRED, ("food", "hungry", "ఆహారం", "भोजन")),
    (EmergencyCategory.WATER_REQUIRED, ("water", "thirst", "నీరు", "पानी")),
    (EmergencyCategory.MEDICINE_REQUIRED, ("medicine", "insulin", "మందు", "दवा")),
]


def classify_text(text: str) -> tuple[EmergencyCategory, Priority, str]:
    blob = (text or "").lower()
    if not blob.strip():
        return EmergencyCategory.OTHER, Priority.HIGH, "No description provided; defaulted to OTHER."
    for category, keywords in KEYWORD_MAP:
        if any(keyword.lower() in blob for keyword in keywords):
            priority = Priority.CRITICAL if category in {
                EmergencyCategory.MEDICAL,
                EmergencyCategory.FIRE,
                EmergencyCategory.TRAPPED_PERSON,
                EmergencyCategory.RESCUE_REQUIRED,
                EmergencyCategory.EARTHQUAKE,
                EmergencyCategory.FLOOD,
                EmergencyCategory.CYCLONE,
            } else Priority.HIGH
            return category, priority, f"Matched local keyword rules for {category.value}."
    return EmergencyCategory.OTHER, Priority.HIGH, "No keyword match; classified as OTHER."
