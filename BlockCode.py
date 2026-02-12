import streamlit as st
import requests
import base64
import json

# --- 1. DESIGN & STYLING ---
st.set_page_config(page_title="Papas Münz-Experte", layout="centered")

st.markdown("""
    <style>
    /* Große Kacheln */
    div.stButton > button {
        width: 100%;
        height: 140px;
        border-radius: 20px;
        font-size: 22px !important;
        font-weight: bold;
        margin-bottom: 20px;
        border: none;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
    }
    /* Farben */
    .stButton > button[kind="primary"] { background-color: #28a745 !important; color: white !important; }
    .stButton > button[kind="secondary"] { background-color: #007bff !important; color: white !important; }
    
    .price-tile {
        background-color: #ffc107;
        padding: 25px;
        border-radius: 20px;
        text-align: center;
        font-weight: bold;
        font-size: 20px;
        border: 2px solid #e0a800;
    }
    .result-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 15px;
        border-left: 10px solid #ffd700;
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. KI LOGIK ---
def analysiere_muenze(image_file, zustand):
    if "OPENAI_API_KEY" not in st.secrets:
        st.error("API Key fehlt in den Secrets!")
        return None

    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"
    }

    prompt = f"""
    Analysiere diese Münze. Der Benutzer gibt den Zustand als '{zustand}' an.
    Antworte NUR im JSON-Format mit diesen Feldern:
    {{
      "name": "Vollständiger Name der Münze",
      "jahr": "Prägejahr",
      "metall": "Gold, Silber oder Unedel",
      "reinheit": 0.900 (als Dezimalzahl),
      "gewicht": 7.96 (in Gramm),
      "metallwert": 0.00 (geschätzt),
      "marktwert_min": 0,
      "marktwert_max": 0,
      "info": "Ein Satz zur Geschichte"
    }}
    Berücksichtige den Zustand '{zustand}' bei der Marktwert-Schätzung.
    """

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ],
        "response_format": { "type": "json_object" }
    }

response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
return response.json()['choices'][0]['message']['content']

# --- 3. NAVIGATION & SPEICHER ---
if 'page' not in st.session_state:
    st.session_state.page = 'home'
if 'sammlung' not in st.session_state:
    st.session_state.sammlung = []

# --- SEITE: HAUPTMENÜ ---
if st.session_state.page == 'home':
    st.markdown("<h1 style='text-align: center;'>🪙 PAPAS MÜNZ-APP</h1>", unsafe_allow_html=True)
    
    if st.button("📸 NEUE MÜNZE SCANNEN", type="primary"):
        st.session_state.page = 'scanner'
        st.rerun()

    if st.button("📚 MEINE SAMMLUNG", type="secondary"):
        st.session_state.page = 'sammlung'
        st.rerun()

    st.markdown("""
        <div class="price-tile">
            💰 KURSE HEUTE<br>
            <span style='font-size: 16px;'>Gold: ~73€/g | Silber: ~0,90€/g</span>
        </div>
    """, unsafe_allow_html=True)

# --- SEITE: SCANNER ---
elif st.session_state.page == 'scanner':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()

    st.subheader("1. Zustand wählen")
    zustand = st.select_slider(
        "Wie gut ist die Münze erhalten?",
        options=["Stark abgenutzt", "Schön", "Vorzüglich", "Stempelglanz (wie neu)"]
    )

    st.subheader("2. Foto machen")
    foto = st.camera_input("Kamera starten")

    if foto:
        with st.spinner("KI berechnet Marktwert..."):
            try:
                ergebnis = json.loads(analysiere_muenze(foto, zustand))
                
                st.markdown("<div class='result-card'>", unsafe_allow_html=True)
                st.header(f"{ergebnis['name']} ({ergebnis['jahr']})")
                
                c1, c2 = st.columns(2)
                c1.metric("Material", f"{ergebnis['metall']}")
                c1.write(f"Gewicht: {ergebnis['gewicht']}g")
                
                # Berechnung Metallwert (vereinfacht für App)
                preis_g = 73.0 if ergebnis['metall'] == "Gold" else 0.90
                if ergebnis['metall'] == "Unedel": preis_g = 0
                echter_metallwert = ergebnis['gewicht'] * ergebnis['reinheit'] * preis_g
                
                c2.metric("Sammler-Marktwert", f"{ergebnis['marktwert_min']}€ - {ergebnis['marktwert_max']}€")
                c2.write(f"Metallwert: ca. {echter_metallwert:.2f}€")
                
st.info(f"**Hintergrund:** {ergebnis['info']}")
                st.markdown("</div>", unsafe_allow_html=True)
                
                if st.button("✅ In Sammlung speichern"):
                    st.session_state.sammlung.append(ergebnis)
                    st.success("Gespeichert!")
            except:
                st.error("Hoppla! Die KI konnte das Bild nicht auswerten. Probier es nochmal heller.")

# --- SEITE: SAMMLUNG ---
elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()
    
    st.title("📚 Deine Schätze")
    if not st.session_state.sammlung:
st.info("Noch keine Münzen im Album.")
    else:
        for m in st.session_state.sammlung:
            with st.expander(f"{m['name']} ({m['jahr']})"):
                st.write(f"Material: {m['metall']} | Marktwert: {m['marktwert_min']}-{m['marktwert_max']}€")
                st.write(f"Info: {m['info']}")

