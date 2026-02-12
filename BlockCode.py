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
    .price-tile { background-color: #ffc107; padding: 20px; border-radius: 15px; text-align: center; font-weight: bold; color: #333; margin-bottom: 20px; border: 2px solid #e0a800; }
    .result-card { background-color: #ffffff; padding: 25px; border-radius: 15px; border-left: 10px solid #ffd700; color: #333; box-shadow: 0px 4px 15px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LIVE-PREISE & KI LOGIK ---

def get_live_prices():
    """Holt die echten Börsenkurse für Gold und Silber in Euro"""
    if "GOLD_API_KEY" not in st.secrets:
        return {"Gold": 73.50, "Silber": 0.92} # Fallback-Werte
    
    try:
        headers = {"x-access-token": st.secrets["GOLD_API_KEY"], "Content-Type": "application/json"}
        # Goldpreis abfragen
gold_res = requests.get("https://www.goldapi.io/api/XAU/EUR", headers=headers).json()
        # Silberpreis abfragen
silber_res = requests.get("https://www.goldapi.io/api/XAG/EUR", headers=headers).json()
        
        return {
            "Gold": round(gold_res['price_gram_24k'], 2),
            "Silber": round(silber_res['price_gram_24k'], 2)
        }
    except:
        return {"Gold": 73.50, "Silber": 0.92}

def analysiere_muenze_profi(img1, img2, zustand):
    if "OPENAI_API_KEY" not in st.secrets:
        st.error("OpenAI Key fehlt!")
        return None
    
    try:
        b64_1 = base64.b64encode(img1.getvalue()).decode('utf-8')
        b64_2 = base64.b64encode(img2.getvalue()).decode('utf-8')
        
        headers = {"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"}
        prompt = f"""
        Identifiziere diese Münze (beide Seiten). Zustand: {zustand}.
        Antworte NUR als JSON:
        {{
          "name": "Name", "jahr": "Jahr", "land": "Land", "metall": "Gold oder Silber oder Unedel",
          "reinheit": 0.900, "gewicht": 7.96, "auflage": "Stückzahl",
          "marktwert_sammler": "Spanne in €",
          "geschichte": "Historischer Hintergrund",
          "merkmale": "Besonderheiten/Fehlprägungen"
        }}
        """
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_1}"}},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_2}"}}
            ]}],
            "response_format": { "type": "json_object" }
        }
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        return response.json()['choices'][0]['message']['content']
    except:
        return None

# --- 3. NAVIGATION ---
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'sammlung' not in st.session_state: st.session_state.sammlung = []

# HAUPTMENÜ
if st.session_state.page == 'home':
    st.markdown("<h1 style='text-align: center;'>🪙 PAPAS MÜNZ-ARCHIV</h1>", unsafe_allow_html=True)
    
    prices = get_live_prices()
    st.markdown(f"""
        <div class="price-tile">
            📊 LIVE-BÖRSENKURSE<br>
            Gold: {prices['Gold']}€/g | Silber: {prices['Silber']}€/g
        </div>
    """, unsafe_allow_html=True)

    if st.button("📸 NEUE MÜNZE SCANNEN", type="primary"):
        st.session_state.page = 'scanner'
        st.rerun()
    if st.button("📚 ZUR SAMMLUNG"):
        st.session_state.page = 'sammlung'
        st.rerun()

# SCANNER
elif st.session_state.page == 'scanner':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()

    zustand = st.select_slider("Zustand der Münze:", options=["Gebraucht", "Normal", "Sehr gut", "Neuwertig"])
    
    f1 = st.camera_input("1. VORDERSEITE")
    if f1:
        st.success("Vorderseite erfasst! ✅")
        f2 = st.camera_input("2. RÜCKSEITE")
        if f2:
            if st.button("EXPERTE FRAGEN & WERT BERECHNEN ✨", type="primary"):
                with st.spinner("Analysiere Markt- und Metallwerte..."):
                    res_raw = analysiere_muenze_profi(f1, f2, zustand)
                    if res_raw:
                        d = json.loads(res_raw)
                        p = get_live_prices()
                        
                        # Metallwert-Berechnung
                        gramm_preis = p.get(d['metall'], 0)
                        m_wert = d['gewicht'] * d['reinheit'] * gramm_preis
                        
                        st.markdown("<div class='result-card'>", unsafe_allow_html=True)
                        st.header(f"{d['name']} ({d['jahr']})")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Börsen-Metallwert:**")
                            st.subheader(f"{m_wert:.2f} €")
                            st.caption(f"({d['metall']}preis aktuell)")
                        with col2:
                            st.write(f"**Sammler-Marktwert:**")
                            st.subheader(f"{d['marktwert_sammler']}")
                            st.caption("Schätzung inkl. Zustand")
                        
                        st.divider()
                        st.write(f"📍 **Land:** {d['land']} | ⚖️ **Gewicht:** {d['gewicht']}g")
                        st.write(f"📉 **Auflage:** {d['auflage']}")
                        st.write(f"📜 **Geschichte:** {d['geschichte']}")
                        st.info(f"🔍 **Sammler-Tipp:** {d['merkmale']}")
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        if st.button("✅ In Sammlung speichern"):
                            st.session_state.sammlung.append(d)
                            st.success("Gespeichert!")
                    else:
                        st.error("KI-Fehler. Bitte schärfere Fotos machen.")

# SAMMLUNG
elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()
    st.title("📚 Dein Album")
    for m in st.session_state.sammlung:
        with st.expander(f"{m['name']} ({m['jahr']}) - {m['marktwert_sammler']}"):
            st.write(f"Material: {m['metall']} | Info: {m['geschichte']}")








































