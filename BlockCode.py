import streamlit as st
import requests
import base64
import json
import io
from PIL import Image
from supabase import create_client, Client

# --- 1. VERBINDUNGEN ---
@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def get_live_prices():
    if "GOLD_API_KEY" not in st.secrets: return {"Gold": 73.50, "Silber": 0.92}
    try:
        headers = {"x-access-token": st.secrets["GOLD_API_KEY"]}
        g = requests.get("https://www.goldapi.io/api/XAU/EUR", headers=headers, timeout=5).json()['price_gram_24k']
        s = requests.get("https://www.goldapi.io/api/XAG/EUR", headers=headers, timeout=5).json()['price_gram_24k']
        return {"Gold": round(g, 2), "Silber": round(s, 2)}
    except: return {"Gold": 73.50, "Silber": 0.92}

# --- 2. HILFSFUNKTIONEN ---
def optimiere_bild(upload_file):
    img = Image.open(upload_file)
    img.thumbnail((1024, 1024))
    buffer = io.BytesIO()
    img.convert("RGB").save(buffer, format="JPEG", quality=80)
    return buffer.getvalue()

def analysiere_muenze(img1_bytes, img2_bytes, zustand):
    b64_1 = base64.b64encode(img1_bytes).decode('utf-8')
    b64_2 = base64.b64encode(img2_bytes).decode('utf-8')
    headers = {"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"}
    
    # Erweiterter Prompt für alle Details
    prompt = f"""
    Identifiziere diese Münze (Vorder- und Rückseite). Zustand: {zustand}.
    Antworte STRENG als JSON:
    {{
      "name": "Name der Münze",
      "jahr": "Jahr",
      "land": "Land",
      "metall": "Gold oder Silber oder Unedel",
      "reinheit": 0.999,
      "gewicht": "Gewicht in g",
      "groesse": "Durchmesser in mm",
      "auflage": "Stückzahl",
      "marktwert": "Sammlerpreis in €",
      "besonderheiten": "Fehlprägungen oder Besonderheiten",
      "info": "Kurze Geschichte zur Münze"
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
    res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']

# --- 3. APP SETUP ---
st.set_page_config(page_title="Papas Münz-Archiv", layout="centered")

if 'foto_vorder' not in st.session_state: st.session_state.foto_vorder = None
if 'foto_rueck' not in st.session_state: st.session_state.foto_rueck = None
if 'page' not in st.session_state: st.session_state.page = 'home'

# --- STARTSEITE ---
if st.session_state.page == 'home':
    st.title("🪙 PAPAS MÜNZ-APP")
    p = get_live_prices()
    st.markdown(f"""<div style="background:#ffc107;padding:15px;border-radius:15px;text-align:center;font-weight:bold;color:#333;">
        LIVE: Gold {p['Gold']}€/g | Silber {p['Silber']}€/g</div>""", unsafe_allow_html=True)
    
if st.button("📸 NEUE MÜNZE SCANNEN", type="primary"):
   st.session_state.foto_vorder = None
   st.session_state.foto_rueck = None
   st.session_state.page = 'scanner'
   st.rerun()
if st.button("📚 SAMMLUNG ANSEHEN"):
   st.session_state.page = 'sammlung'
   st.rerun()

# --- SCANNER ---
elif st.session_state.page == 'scanner':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()
    
    zustand = st.select_slider("Zustand:", options=["Gebraucht", "Normal", "Sehr gut", "Neuwertig"])
    
    f1 = st.file_uploader("📸 VORDERSEITE aufnehmen", type=["jpg", "jpeg", "png"], key="u1")
    if f1:
        st.session_state.foto_vorder = optimiere_bild(f1)
        f2 = st.file_uploader("📸 RÜCKSEITE aufnehmen", type=["jpg", "jpeg", "png"], key="u2")
        if f2:
            st.session_state.foto_rueck = optimiere_bild(f2)
            
            if st.button("ANALYSE STARTEN ✨", type="primary"):
                with st.spinner("Experte prüft die Münze..."):
                    try:
                        res_raw = analysiere_muenze(st.session_state.foto_vorder, st.session_state.foto_rueck, zustand)
                        d = json.loads(res_raw)
                        p = get_live_prices()
                        
                        # Metallwert berechnen
                        metall = d.get('metall', 'Unedel')
                        kurs = p.get(metall, 0)
                        # Gewicht säubern (falls die KI "7.96g" statt 7.96 schickt)
                        gew_str = str(d.get('gewicht', '0')).replace('g','').strip()
                        metallwert = float(gew_str) * d.get('reinheit', 0) * kurs
                        
                        # In Datenbank speichern
                        client = init_supabase()
                        client.table("muenzen").insert({
                            "name": d['name'], "jahr": str(d['jahr']),
                            "land": d['land'], "marktwert": d['marktwert']
                        }).execute()
                        
                        st.balloons()
                        # SCHÖNE ERGEBNIS-KARTE
                        st.markdown(f"""
                        <div style="background:white; padding:20px; border-radius:15px; border-left:10px solid #ffd700; color:#333; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
                            <h2 style="margin-bottom:0;">{d['name']} ({d['jahr']})</h2>
                            <p style="color:#666;">{d['land']} | {d['metall']} ({d['reinheit']})</p>
                            <hr>
                            <table style="width:100%">
                                <tr><td><b>Börsen-Metallwert:</b></td><td style="text-align:right; color:green; font-size:1.2em;"><b>{metallwert:.2f}€</b></td></tr>
                                <tr><td><b>Sammler-Marktpreis:</b></td><td style="text-align:right; color:blue; font-size:1.2em;"><b>{d['marktwert']}</b></td></tr>
                            </table>
                            <hr>
                            <p>⚖️ <b>Gewicht:</b> {d['gewicht']} | 📏 <b>Größe:</b> {d['groesse']}</p>
                            <p>📉 <b>Auflage:</b> {d['auflage']}</p>
                            <p>🌟 <b>Besonderheit:</b> {d['besonderheiten']}</p>
                            <p style="font-style:italic; background:#f9f9f9; padding:10px; border-radius:5px;">{d['info']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    except Exception as e:
                        st.error(f"Fehler: {e}")

# --- SAMMLUNG ---
elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()
    st.title("📚 Deine Schätze")
    try:
        client = init_supabase()
        res = client.table("muenzen").select("*").order("created_at", desc=True).execute()
        for m in res.data:
            with st.expander(f"{m['name']} ({m['jahr']})"):
                st.write(f"Wert: {m['marktwert']} | Land: {m['land']}")
    except:
        st.error("Datenbank-Fehler")
