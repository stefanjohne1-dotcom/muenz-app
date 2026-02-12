import streamlit as st
import requests
import base64
import json

# --- 1. OPTIK & STYLING ---
st.set_page_config(page_title="Papas Münz-Experte", layout="centered")

st.markdown("""
    <style>
    div.stButton > button { width: 100%; height: 80px; border-radius: 15px; font-size: 18px !important; font-weight: bold; margin-bottom: 20px; }
    .stButton > button[kind="primary"] { background-color: #28a745 !important; color: white !important; }
    .price-tile { background-color: #ffc107; padding: 20px; border-radius: 15px; text-align: center; font-weight: bold; color: #333; margin-bottom: 20px; }
    .result-card { background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 10px solid #ffd700; color: #333; box-shadow: 0px 4px 10px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HILFSFUNKTIONEN (PREISE & KI) ---

def get_market_prices():
    # In einer Profi-App kämen diese Daten live. Hier nutzen wir aktuelle Schätzwerte (Stand Feb 2026).
    return {"Gold": 73.50, "Silber": 0.92}

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

        # Der Prompt sagt der KI jetzt ganz genau, dass sie den MARKTWERT schätzen soll
        prompt = f"""
        Identifiziere diese Münze anhand beider Seiten. Der Zustand ist '{zustand}'.
        Antworte NUR als JSON mit:
        {{
          "name": "Name der Münze",
          "jahr": "Jahr",
          "metall": "Gold oder Silber oder Unedel",
          "reinheit": 0.900,
          "gewicht": 7.96,
          "marktwert_sammler": "150 - 200€",
          "info": "Warum wird sie so gehandelt? (z.B. Seltenheit, Erhaltung)"
        }}
        """

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
    except:
        return None

# --- 3. SEITEN-LOGIK ---
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'sammlung' not in st.session_state: st.session_state.sammlung = []

# HAUPTMENÜ
if st.session_state.page == 'home':
    st.markdown("<h1 style='text-align: center;'>🪙 PAPAS MÜNZ-APP</h1>", unsafe_allow_html=True)
    
    # Anzeige der aktuellen Kurse direkt oben
    prices = get_market_prices()
    st.markdown(f"""
        <div class="price-tile">
            BÖRSENKURSE HEUTE<br>
            Gold: {prices['Gold']}€/g | Silber: {prices['Silber']}€/g
        </div>
    """, unsafe_allow_html=True)

    if st.button("📸 NEUE MÜNZE SCANNEN", type="primary"):
        st.session_state.page = 'scanner'
        st.rerun()
    if st.button("📚 MEINE SAMMLUNG"):
        st.session_state.page = 'sammlung'
        st.rerun()

# SCANNER
elif st.session_state.page == 'scanner':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()

    st.write("### 1. Zustand & Fotos")
    zustand = st.select_slider("Zustand:", options=["Gebraucht", "Normal", "Sehr gut", "Neuwertig"])
    
    foto1 = st.camera_input("FOTO 1: VORDERSEITE")
    
    if foto1:
        st.success("Vorderseite OK! ✅")
        foto2 = st.camera_input("FOTO 2: RÜCKSEITE")
        
        if foto2:
            st.success("Rückseite OK! ✅")
            if st.button("WERT ERMITTELN ✨", type="primary"):
                with st.spinner("KI berechnet Metall- und Marktwert..."):
                    res_raw = analysiere_muenze(foto1, foto2, zustand)
                    if res_raw:
                        data = json.loads(res_raw)
                        prices = get_market_prices()
                        
                        # Berechnung des reinen Metallwerts
                        metall = data['metall']
                        gramm_preis = prices.get(metall, 0)
                        metallwert = data['gewicht'] * data['reinheit'] * gramm_preis
                        
                        st.markdown("<div class='result-card'>", unsafe_allow_html=True)
                        st.header(f"{data['name']} ({data['jahr']})")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**Börsen-Wert:**")
                            st.subheader(f"{metallwert:.2f} €")
                            st.caption(f"(Reiner {metall}wert)")
                        with col2:
                            st.write("**Marktwert:**")
                            st.subheader(f"{data['marktwert_sammler']}")
                            st.caption("(Sammler-Schätzung)")
                        
                        st.write(f"**Handel & Info:** {data['info']}")
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        if st.button("✅ In Album speichern"):
                            st.session_state.sammlung.append(data)
                            st.toast("Gespeichert!")
                    else:
                        st.error("Fehler bei der Analyse. Bitte nochmal versuchen.")

# SAMMLUNG
elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()
    st.title("📚 Album")
    for m in st.session_state.sammlung:
        with st.expander(f"{m['name']} ({m['jahr']})"):
            st.write(f"Sammlerwert: {m.get('marktwert_sammler', 'N/A')}")
            st.write(f"Hintergrund: {m['info']}")






































