import streamlit as st
import requests
import base64
import json
from PIL import Image
import io

# ======================================
# 🔮 Seitenkonfiguration
# ======================================

st.set_page_config(
    page_title="Archiv der Numismatischen Mysterien",
    page_icon="🕯",
    layout="centered"
)

# ======================================
# 🎨 Mystisches Design
# ======================================

st.markdown("""
<style>
body { background-color: #0f1117; }

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

# ======================================
# 🖼 Bildoptimierung
# ======================================

def optimize_image(image_bytes, max_size=(768, 768), quality=80):
    try:
        image = Image.open(io.BytesIO(image_bytes))

        if image.mode != "RGB":
            image = image.convert("RGB")

        image.thumbnail(max_size)

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality, optimize=True)

        return buffer.getvalue()
    except Exception:
        return None

# ======================================
# 🔧 JSON Absicherung
# ======================================

def enforce_structure(data):

    if not isinstance(data, dict):
        return {}

    defaults = {
        "moegliche_identifikation": "",
        "land": "",
        "jahr_oder_zeitraum": "",
        "material": "",
        "beschreibung": "",
        "confidence": 0.0
    }

    for key, value in defaults.items():
        data.setdefault(key, value)

    return data

# ======================================
# 🔍 Analyse
# ======================================

def analyze_coin(img1, img2):

    try:
        b1 = base64.b64encode(img1).decode()
        b2 = base64.b64encode(img2).decode()

        prompt = """
        Du bist eine Münz-Analyse-KI. KEINE Datenbank.
        Analysiere ausschließlich sichtbare Merkmale(Nennwert, Land, Symbol, Zahl, Währung).
        Prüfe auf Plausibilität (passt das Jahr zur Epoche? Widersprüche?)
        Keine Spekulation, kein Raten.
        Antworte nur als JSON.
        """

        headers = {
            "Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "gpt-4o-mini",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b1}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b2}"}}
                ]
            }],
            "max_tokens": 600,
            "response_format": {"type": "json_object"}
        }

        response = requests.post(
"https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            return None

        content = response.json()["choices"][0]["message"]["content"]

        parsed = json.loads(content)

        return enforce_structure(parsed)

    except Exception:
        return None

# ======================================
# 🔎 Self Verification
# ======================================

def verify_analysis(result):

    try:
        verification_prompt = f"""
        Prüfe auf Halluzination oder Spekulation.
        Antworte als JSON:
        {{
            "hallucination_detected": false,
            "confidence_adjustment": 0.0,
            "reason": ""
        }}

        Analyse:
        {json.dumps(result)}
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
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            return None

        verification = json.loads(
            response.json()["choices"][0]["message"]["content"]
        )

        verification.setdefault("hallucination_detected", False)
        verification.setdefault("confidence_adjustment", 0.0)
        verification.setdefault("reason", "")

        return verification

    except Exception:
        return None

# ======================================
# 🕯 UI
# ======================================

st.markdown("""
<div class="library-card">
<div class="library-title">🔎 Beweisaufnahme</div>
Lade beide Seiten der Münze hoch.
</div>
""", unsafe_allow_html=True)

foto1 = st.file_uploader("Vorderseite", type=["jpg","jpeg","png"])
foto2 = st.file_uploader("Rückseite", type=["jpg","jpeg","png"])

if st.button("🔍 Beweis analysieren") and foto1 and foto2:

    with st.spinner("🕯 Untersuchung läuft..."):
        img1 = optimize_image(foto1.read())
        img2 = optimize_image(foto2.read())

        if not img1 or not img2:
            st.error("Bildverarbeitung fehlgeschlagen.")
            st.stop()

        result = analyze_coin(img1, img2)

    if not result:
        st.error("Analyse fehlgeschlagen.")
        st.stop()

    confidence = result.get("confidence", 0)

    # 🔮 Self Verification nur bei Bedarf
    if confidence < 0.75:

        with st.spinner("🔮 Archivwächter prüfen die Aussage..."):
            verification = verify_analysis(result)

        if verification:

            adjustment = verification.get("confidence_adjustment", 0)
            result["confidence"] = max(
                0.0,
                min(1.0, confidence + adjustment)
            )

            if verification.get("hallucination_detected"):
                result["beschreibung"] += (
                    f"\n\n⚠ Prüfhinweis: {verification.get('reason','')}"
                )

    # ======================================
    # 📜 Ausgabe
    # ======================================

    st.markdown('<div class="library-card">', unsafe_allow_html=True)
    st.json(result)
    st.markdown('</div>', unsafe_allow_html=True)
