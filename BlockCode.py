import streamlit as st
import requests
import base64
import json
from PIL import Image
import io

# ==============================
# 🔮 Seitenkonfiguration
# ==============================

st.set_page_config(
    page_title="Archiv der Numismatischen Mysterien",
    page_icon="🕯",
    layout="centered"
)

# ==============================
# 🎨 Mystisches Design
# ==============================

st.markdown("""
<style>
body {
    background-color: #0f1117;
}

.library-card {
    background: #1a1c23;
    padding: 20px;
    border-radius: 14px;
    box-shadow: 0 0 25px rgba(255,215,0,0.08);
    margin-bottom: 20px;
}

.library-title {
    font-size: 22px;
    font-weight: bold;
    color: #d4af37;
    margin-bottom: 10px;
}

.stButton>button {
    background-color: #2a2d3a;
    color: #d4af37;
    border-radius: 12px;
    border: 1px solid #d4af37;
}

.stButton>button:hover {
    background-color: #3a3f52;
}
</style>
""", unsafe_allow_html=True)

# ==============================
# 🖼 Bildoptimierung
# ==============================

def optimize_image(image_bytes, max_size=(768, 768), quality=80):
    image = Image.open(io.BytesIO(image_bytes))

    if image.mode != "RGB":
        image = image.convert("RGB")

    image.thumbnail(max_size)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)

    return buffer.getvalue()

# ==============================
# 🔍 Hauptanalyse
# ==============================

def analyze_coin(image1_bytes, image2_bytes):

    base64_image1 = base64.b64encode(image1_bytes).decode("utf-8")
    base64_image2 = base64.b64encode(image2_bytes).decode("utf-8")

    prompt = """
    Du bist ein numismatischer Ermittler und eine Münz-Analyse-KI.

    Analysiere ausschließlich sichtbare Merkmale(Jahr, Nennwert, Währung, Land, Symbole
    Keine Spekulation.
    Keine erfundenen Daten.
    Prüfe auf Plausibilität (passt Jahr zur Epoche?, Widersprüche).

    Antworte nur als JSON:

    {
      "moegliche_identifikation": "",
      "land": "",
      "jahr_oder_zeitraum": "",
      "material": "",
      "beschreibung": "",
      "confidence": 0.0
    }
    """

    headers = {
        "Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image1}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image2}"}}
                ]
            }
        ],
        "max_tokens": 700,
        "response_format": {"type": "json_object"}
    }

    response = requests.post(
"https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=payload
    )

    if response.status_code != 200:
        st.error("Analyse fehlgeschlagen.")
        return None

    return json.loads(response.json()["choices"][0]["message"]["content"])

# ==============================
# 🔎 Self Verification
# ==============================

def verify_analysis(analysis_json):

    verification_prompt = f"""
    Du bist ein Archiv-Wächter.

    Prüfe die folgende Analyse auf:
    - Spekulation
    - erfundene Details
    - übertriebene Sicherheit

    Antworte nur als JSON:

    {{
      "hallucination_detected": false,
      "confidence_adjustment": 0.0,
      "reason": ""
    }}

    Analyse:
    {json.dumps(analysis_json)}
    """

    headers = {
        "Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": verification_prompt}],
        "max_tokens": 300,
        "response_format": {"type": "json_object"}
    }

    response = requests.post(
"https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=payload
    )

    if response.status_code != 200:
        return None

    return json.loads(response.json()["choices"][0]["message"]["content"])

# ==============================
# 🕯 UI Bereich
#
