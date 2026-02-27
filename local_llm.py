import ollama
import re

MODEL = "llama3:8b"

# -----------------------------
# Helpers
# -----------------------------

def contains_devanagari(text):
    return bool(re.search(r'[\u0900-\u097F]', text))


def should_apply_correction(text):
    triggers = [" no ", " wait ", " actually ", " i mean ", " sorry ", " correction "]
    t = f" {text.lower()} "
    return any(word in t for word in triggers)


# -----------------------------
# Core Functions
# -----------------------------

def convert_hindi_to_roman(text):
    prompt = f"""
Convert this Hindi sentence into casual Hinglish written in Roman letters.

Rules:
- Do NOT translate to English
- Keep meaning identical
- Do NOT add words
- Return only converted sentence

Text:
{text}
"""

    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0}
    )

    return response["message"]["content"].strip()


def apply_correction(text):
    prompt = f"""
You are a text editor.

Return ONLY the final corrected sentence.
Do NOT explain.
Do NOT add commentary.
Do NOT add quotes.
Do NOT add extra words.

If there is a spoken correction, apply it.
If there is no correction, return the text unchanged.

Examples:
meeting at 4 pm no 5 pm -> meeting at 5 pm
send tomorrow actually today -> send today
i will go now actually later -> i will go later
no wait change it -> change it

Text:
{text}

Final:
"""

    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={
            "temperature": 0,
            "top_p": 0.1,
        }
    )

    cleaned = response["message"]["content"].strip()

    # HARD GUARD: strip model narration if it still happens
    if "\n" in cleaned:
        cleaned = cleaned.split("\n")[-1].strip()

    # remove quotes
    cleaned = cleaned.strip('"').strip("'")

    return cleaned if cleaned else text


# -----------------------------
# Main Public Function
# -----------------------------

def process_text(text):
    """
    Main entry point.
    Handles:
    1. Hindi → Roman conversion
    2. Spoken correction fixing
    """

    if not text.strip():
        return text

    # Step 1: convert Hindi script if present
    if contains_devanagari(text):
        text = convert_hindi_to_roman(text)

    # Step 2: apply correction if needed
    if should_apply_correction(text):
        text = apply_correction(text)

    return text