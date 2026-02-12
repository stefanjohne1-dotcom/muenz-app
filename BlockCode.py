import streamlit as st
import requests
import base64
import json

# --- 1. OPTIK ---
st.set_page_config(page_title="Papas Münz-Experte", layout="centered")

st.markdown("""
    <style>
    div.stButton > button { width: 100%; height: 80px; border-radius: 15px; font-size: 18px !important; font-weight: bold; margin-bottom: 20px; }
    .stButton > button[kind="primary"] { background-color: #28a745 !important; color: white !important; }
    .result-card { background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 8px solid #ffd700; color: #333; box-shadow: 0px 4px 10px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. KI FUNKTION ---
def analysiere_muenze(img1, img2, zustand):
    if "OPENAI_API_KEY" not in st.secrets:
        st.error("API-Key fehlt in den Secrets!")
        return None
    try:
        b64_1 = base64.b64encode(img1.getvalue()).decode('utf-8')
        b64_2 = base64.b64encode(img2.getvalue()).decode('utf-8')
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"
        }

        prompt = f"Identifiziere diese Münze (beide Seiten). Zustand: {zustand}. Antworte als JSON: {{'name': '...', 'jahr': '...', 'metall': '...', 'reinheit': 0.0, 'gewicht': 0.0, 'marktwert_min': 0, 'marktwert_max': 0, 'info': '...'}}"

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
    except Exception as e:
        return None

# --- 3. LOGIK ---
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'sammlung' not in st.session_state: st.session_state.sammlung = []

# HAUPTMENÜ
if st.session_state.page == 'home':
    st.markdown("<h1 style='text-align: center;'>🪙 PAPAS MÜNZ-APP</h1>", unsafe_allow_html=True)
    if st.button("📸 NEUE MÜNZE SCANNEN", type="primary"):
        st.session_state.page = 'scanner'
        st.rerun()
    if st.button("📚 MEINE SAMMLUNG"):
        st.session_state.page = 'sammlung'
        st.rerun()

# SCANNER (SCHRITT FÜR SCHRITT)
elif st.session_state.page == 'scanner':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()

    zustand = st.select_slider("Zustand:", options=["Gebraucht", "Normal", "Sehr gut", "Neuwertig"])
    
    # Foto 1: Vorderseite
    foto1 = st.camera_input("1. FOTO: VORDERSEITE")
    
    # Erst wenn Foto 1 existiert, zeigen wir das Feld für Foto 2
    if foto1:
        st.success("Vorderseite erfasst! ✅")
        foto2 = st.camera_input("2. FOTO: RÜCKSEITE")
        
        if foto2:
            st.success("Rückseite erfasst! ✅")
            if st.button("MÜNZE JETZT ANALYSIEREN ✨", type="primary"):
                with st.spinner("KI vergleicht beide Seiten..."):
                    res_raw = analysiere_muenze(foto1, foto2, zustand)
                    if res_raw:
                        data = json.loads(res_raw)
                        st.markdown("<div class='result-card'>", unsafe_allow_html=True)
                        st.header(f"{data['name']} ({data['jahr']})")
                        st.write(f"**Wert:** {data['marktwert_min']}€ - {data['marktwert_max']}€")
                        st.write(f"**Material:** {data['metall']}")
st.info(data['info'])
                        st.markdown("</div>", unsafe_allow_html=True)
                        if st.button("In Album speichern"):
                            st.session_state.sammlung.append(data)
                            st.toast("Gespeichert!")
                    else:
                        st.error("Fehler bei der KI-Verbindung.")

# SAMMLUNG
elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()
    st.title("📚 Album")
    for m in st.session_state.sammlung:
        with st.expander(f"{m['name']} ({m['jahr']})"):
            st.write(f"Wert: {m['marktwert_min']}-{m['marktwert_max']}€")



































