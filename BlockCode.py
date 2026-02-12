import streamlit as st
import requests
import base64
import json

# --- OPTIK ---
st.set_page_config(page_title="Papas Münz-Archiv", layout="centered")

st.markdown("""
    <style>
    .stButton > button { width: 100%; height: 70px; border-radius: 12px; font-weight: bold; }
    .result-card { background-color: #ffffff; padding: 25px; border-radius: 15px; border-left: 10px solid #ffd700; box-shadow: 0px 4px 15px rgba(0,0,0,0.1); color: #333; }
    .info-label { color: #555; font-size: 0.9em; font-weight: bold; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- ERWEITERTE KI-FUNKTION ---
def analysiere_muenze_profi(img1, img2, zustand):
    if "OPENAI_API_KEY" not in st.secrets:
        st.error("API-Key fehlt!")
        return None
    
    try:
        b64_1 = base64.b64encode(img1.getvalue()).decode('utf-8')
        b64_2 = base64.b64encode(img2.getvalue()).decode('utf-8')
        
        headers = {"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"}

        # Der verbesserte Prompt für viel mehr Details
        prompt = f"""
        Identifiziere diese Münze präzise (beide Seiten). Zustand: {zustand}.
        Antworte NUR als JSON mit diesen Feldern:
        {{
          "name": "Vollständiger Name",
          "jahr": "Prägejahr",
          "land": "Herkunftsland",
          "metall": "Gold/Silber/etc.",
          "reinheit": "z.B. 900/1000",
          "gewicht": "Gewicht in g",
          "auflage": "Geschätzte Auflagezahl",
          "marktwert": "Spanne in €",
          "geschichte": "3-4 Sätze zum historischen Hintergrund",
          "merkmale": "Worauf muss man bei diesem Jahrgang achten? (Fehlprägungen etc.)"
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

# --- APP LOGIK ---
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'sammlung' not in st.session_state: st.session_state.sammlung = []

if st.session_state.page == 'home':
    st.title("🪙 Papas Münz-Archiv")
    if st.button("📸 NEUE ANALYSE STARTEN", type="primary"):
        st.session_state.page = 'scanner'
        st.rerun()
    if st.button("📚 ZUR SAMMLUNG"):
        st.session_state.page = 'sammlung'
        st.rerun()

elif st.session_state.page == 'scanner':
    if st.button("⬅️ ZURÜCK"): st.session_state.page = 'home'; st.rerun()
    
    zustand = st.select_slider("Zustand:", options=["Gebraucht", "Normal", "Sehr gut", "Neuwertig"])
    f1 = st.camera_input("Vorderseite")
    if f1:
        f2 = st.camera_input("Rückseite")
        if f2:
            if st.button("EXPERTE FRAGEN ✨", type="primary"):
                with st.spinner("KI durchsucht Datenbanken..."):
                    res = analysiere_muenze_profi(f1, f2, zustand)
                    if res:
                        d = json.loads(res)
                        st.markdown("<div class='result-card'>", unsafe_allow_html=True)
                        st.header(f"{d['name']} ({d['jahr']})")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"📍 **Land:** {d['land']}")
                            st.write(f"🧪 **Metall:** {d['metall']} ({d['reinheit']})")
                        with col2:
                            st.write(f"⚖️ **Gewicht:** {d['gewicht']}")
                            st.write(f"📉 **Auflage:** {d['auflage']}")
                        
                        st.divider()
                        st.subheader(f"Marktwert: {d['marktwert']}")
                        
                        st.write("**📜 Geschichte:**")
                        st.write(d['geschichte'])
                        
                        st.write("**🔍 Sammler-Tipp:**")
                        st.info(d['merkmale'])
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        if st.button("✅ Im Album speichern"):
                            st.session_state.sammlung.append(d)
                            st.toast("Gespeichert!")

elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"): st.session_state.page = 'home'; st.rerun()
    st.title("📚 Dein Album")
    for m in st.session_state.sammlung:
        with st.expander(f"{m['name']} ({m['jahr']}) - {m['marktwert']}"):
            st.write(f"Material: {m['metall']} | Auflage: {m['auflage']}")
            st.write(m['geschichte'])







































