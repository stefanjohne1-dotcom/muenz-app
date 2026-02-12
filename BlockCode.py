import streamlit as st
import requests
import base64
import json

# --- 1. OPTIK DER APP ---
st.set_page_config(page_title="Papas Münz-Experte", layout="centered")

st.markdown("""
    <style>
    div.stButton > button {
        width: 100%;
        height: 100px;
        border-radius: 15px;
        font-size: 18px !important;
        font-weight: bold;
        margin-bottom: 15px;
    }
    .stButton > button[kind="primary"] { background-color: #28a745 !important; color: white !important; }
    .stButton > button[kind="secondary"] { background-color: #007bff !important; color: white !important; }
    
    .price-tile {
        background-color: #ffc107;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        font-weight: bold;
        color: #333;
    }
    .result-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 15px;
        border-left: 8px solid #ffd700;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
        color: #333;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DIE KI-FUNKTION (JETZT MIT 2 BILDERN) ---
def analysiere_muenze(img1, img2, zustand):
    if "OPENAI_API_KEY" not in st.secrets:
        st.error("API-Key fehlt in den Secrets!")
        return None

    # Beide Bilder umwandeln
    b64_1 = base64.b64encode(img1.read()).decode('utf-8')
    b64_2 = base64.b64encode(img2.read()).decode('utf-8')
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"
    }

    prompt = f"Hier sind Vorder- und Rückseite einer Münze. Zustand: {zustand}. Identifiziere sie genau. Antworte als JSON mit: name, jahr, metall, reinheit, gewicht, marktwert_min, marktwert_max, info."

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_1}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_2}"}}
                ]
            }
        ],
        "response_format": { "type": "json_object" }
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return response.json()['choices'][0]['message']['content']

# --- 3. SEITEN-STEUERUNG ---
if 'page' not in st.session_state:
    st.session_state.page = 'home'
if 'sammlung' not in st.session_state:
    st.session_state.sammlung = []

# --- HAUPTMENÜ ---
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
            💰 MARKT-INFO<br>
            <span style='font-size: 14px;'>Fotografiere beide Seiten für beste Ergebnisse</span>
        </div>
    """, unsafe_allow_html=True)

# --- SCANNER-SEITE ---
elif st.session_state.page == 'scanner':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()

    st.write("### 1. Zustand & Fotos")
    zustand = st.select_slider("Zustand:", options=["Gebraucht", "Normal", "Sehr gut", "Neuwertig"])

    col_a, col_b = st.columns(2)
    with col_a:
        foto1 = st.camera_input("Vorderseite")
    with col_b:
        foto2 = st.camera_input("Rückseite")

    if foto1 and foto2:
        if st.button("MÜNZE JETZT ANALYSIEREN ✨"):
            with st.spinner("KI vergleicht beide Seiten..."):
                try:
                    ergebnis = json.loads(analysiere_muenze(foto1, foto2, zustand))
                    st.markdown("<div class='result-card'>", unsafe_allow_html=True)
                    st.header(f"{ergebnis['name']} ({ergebnis['jahr']})")
                    st.write(f"**Wert:** {ergebnis['marktwert_min']}€ - {ergebnis['marktwert_max']}€")
                    st.write(f"**Info:** {ergebnis['info']}")
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    if st.button("In Album speichern"):
                        st.session_state.sammlung.append(ergebnis)
                        st.toast("Gespeichert!")
                except:
                    st.error("Fehler! Bitte Fotos nochmal schärfer machen.")

# --- SAMMLUNG-SEITE ---
elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()
    st.title("📚 Dein Album")
    for m in st.session_state.sammlung:
        with st.expander(f"{m['name']} ({m['jahr']})"):
            st.write(f"Wert: {m['marktwert_min']}-{m['marktwert_max']}€")

































