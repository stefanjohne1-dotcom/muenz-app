import streamlit as st
import requests
import base64
import json
import io
from PIL import Image
from supabase import create_client, Client

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "page" not in st.session_state:
    st.session_state.page = "home"

if "analysis" not in st.session_state:
    st.session_state.analysis = None

if "foto1" not in st.session_state:
    st.session_state.foto1 = None

if "foto2" not in st.session_state:
    st.session_state.foto2 = None

# --------------------------------------------------
# SUPABASE
# --------------------------------------------------

@st.cache_resource
def init_supabase() -> Client:
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

# --------------------------------------------------
# IMAGE OPTIMIZATION
# --------------------------------------------------

def optimize_image(file):
    img = Image.open(file)
    img.thumbnail((768, 768))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=80)
    return buf.getvalue()

# --------------------------------------------------
# OPENAI CALL
# --------------------------------------------------

def call_openai(payload):
    headers = {
        "Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"
    }

    response = requests.post(
"https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )

    return response.json()

# --------------------------------------------------
# ANALYSE STUFE 1
# --------------------------------------------------

def analyze_coin(img1, img2):

    b1 = base64.b64encode(img1).decode()
    b2 = base64.b64encode(img2).decode()

    prompt = """
Du bist ein visueller Münzidentifikations-Assistent.
Du bist KEINE Datenbank.
Du darfst KEINE Informationen erfinden.

GRUNDREGEL:
- Nur klar sichtbare Informationen verwenden.
- Keine Annahmen oder Ergänzungen.
- Wenn unsicher, dann null.

ARBEITSSCHRITTE:

1. Extrahiere nur sichtbare Fakten: (Jahr, Nennwert, Währung, Land, Symbole).
2. Identifiziere nur wenn logisch eindeutig.
3. Prüfe auf Widersprüche.
4. Material nur wenn klar erkennbar.

Antwort nur als JSON:

{
  "sichtbare_fakten": {
    "jahr": null,
    "nennwert": null,
    "waehrung": null,
    "land_text": null,
    "sichtbare_symbole": []
  },
  "identifikation": {
    "name": null,
    "epoche": null,
    "motiv": null
  },
  "material": null,
  "plausibilitaet": "ok | logik_warnung | unsicher",
  "analyse_begruendung": "",
  "confidence": 0.0
}
"""

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
        "response_format": {"type": "json_object"}
    }

    try:
        res = call_openai(payload)
        return json.loads(res["choices"][0]["message"]["content"])
    except:
        return None

# --------------------------------------------------
# SELF VERIFICATION STUFE 2
# --------------------------------------------------

def verify_analysis(analysis_json):

    verification_prompt = f"""
Du bist ein KI-Qualitätsprüfer.

Prüfe folgende Münzanalyse auf Halluzinationen:

- Wurden Informationen erfunden?
- Wurden nicht sichtbare Fakten ergänzt?
- Wurde spekuliert?
- Ist die Confidence übertrieben?

Antwort nur als JSON:

{{
  "hallucination_detected": false,
  "confidence_adjustment": 0.0,
  "reason": ""
}}

Analyse:
{json.dumps(analysis_json, indent=2)}
"""

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": verification_prompt}],
        "response_format": {"type": "json_object"}
    }

    try:
        res = call_openai(payload)
        return json.loads(res["choices"][0]["message"]["content"])
    except:
        return None

# --------------------------------------------------
# PIPELINE
# --------------------------------------------------

def run_analysis_pipeline(img1, img2):

    analysis = analyze_coin(img1, img2)

    if analysis is None:
        return None

    # 🔥 Nur prüfen wenn unsicher
    if analysis.get("confidence", 0) < 0.75 or analysis.get("plausibilitaet") != "ok":

        verification = verify_analysis(analysis)

        if verification:

            adjusted_conf = analysis.get("confidence", 0) + verification.get("confidence_adjustment", 0)
            adjusted_conf = max(0.0, min(1.0, adjusted_conf))
            analysis["confidence"] = adjusted_conf

            if verification.get("hallucination_detected"):
                analysis["plausibilitaet"] = "unsicher"
                analysis["verification_flag"] = verification.get("reason", "Halluzination erkannt")

    return analysis

    # Confidence anpassen
    adjusted_conf = analysis.get("confidence", 0) + verification.get("confidence_adjustment", 0)
    adjusted_conf = max(0.0, min(1.0, adjusted_conf))
    analysis["confidence"] = adjusted_conf

    # Falls Halluzination erkannt
    if verification.get("hallucination_detected"):
        analysis["plausibilitaet"] = "unsicher"
        analysis["verification_flag"] = verification.get("reason", "Halluzination erkannt")

    return analysis

# --------------------------------------------------
# UI
# --------------------------------------------------

st.set_page_config(page_title="Münz Scanner – Self Verified", layout="centered")

# HOME
if st.session_state.page == "home":

    st.title("🪙 Münz Scanner – Self Verified")

    if st.button("Neue Münze scannen"):
        st.session_state.page = "scan"
        st.rerun()

    if st.button("Sammlung"):
        st.session_state.page = "collection"
        st.rerun()

# SCAN
elif st.session_state.page == "scan":

    if st.button("⬅ Zurück"):
        st.session_state.page = "home"
        st.rerun()

    st.subheader("Fotos hochladen")

    f1 = st.file_uploader("Vorderseite", type=["jpg", "png"])
    f2 = st.file_uploader("Rückseite", type=["jpg", "png"])

    if f1 and f2:
        st.session_state.foto1 = optimize_image(f1)
        st.session_state.foto2 = optimize_image(f2)

        if st.button("Analyse starten"):

            with st.spinner("Analysiere & prüfe..."):
                result = run_analysis_pipeline(
                    st.session_state.foto1,
                    st.session_state.foto2
                )
                st.session_state.analysis = result
                st.rerun()

    if st.session_state.analysis:

        data = st.session_state.analysis

        st.divider()
        st.subheader("Analyse")

        if data is None:
            st.error("Fehler bei KI-Antwort.")
        else:
            st.json(data)

            confidence = data.get("confidence", 0)

            if "verification_flag" in data:
                st.error(f"⚠️ Self-Verification: {data['verification_flag']}")

            if confidence < 0.5:
                st.warning("⚠️ Identifikation unsicher.")
            elif data.get("plausibilitaet") == "logik_warnung":
                st.error("⚠️ Logik-Widerspruch erkannt.")
            else:
                st.success("Identifikation plausibel.")

            # Speicherung nur wenn sicher genug
            if confidence >= 0.6 and "verification_flag" not in data:

                if st.button("Speichern"):

                    init_supabase().table("muenzen").insert({
                        "jahr": data["sichtbare_fakten"]["jahr"],
                        "nennwert": data["sichtbare_fakten"]["nennwert"],
                        "land": data["sichtbare_fakten"]["land_text"],
                        "name": data["identifikation"]["name"],
                        "epoche": data["identifikation"]["epoche"],
                        "motiv": data["identifikation"]["motiv"],
                        "material": data["material"],
                        "confidence": confidence,
                        "analyse_begruendung": data["analyse_begruendung"]
                    }).execute()

                    st.success("Gespeichert!")
                    st.session_state.analysis = None
            else:
                st.button("Speichern gesperrt (zu unsicher)", disabled=True)

# COLLECTION
elif st.session_state.page == "collection":

    if st.button("⬅ Zurück"):
        st.session_state.page = "home"
        st.rerun()

    st.title("📚 Sammlung")

    client = init_supabase()
    db = client.table("muenzen").select("*").order("created_at", desc=True).execute()

    if db.data:
        for m in db.data:
            with st.expander(f"{m['name']} ({m['jahr']})"):
                st.write(f"Land: {m['land']}")
                st.write(f"Nennwert: {m['nennwert']}")
                st.write(f"Material: {m['material']}")
                st.write(f"Confidence: {m['confidence']}")
                st.write(f"Epoche: {m['epoche']}")
                st.write(f"Motiv: {m['motiv']}")
                st.write(f"Analyse: {m['analyse_begruendung']}")
    else:
        st.info("Noch keine Münzen gespeichert.")

