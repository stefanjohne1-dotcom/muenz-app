import streamlit as st
import requests
import base64
import json
import io
from PIL import Image
from supabase import create_client, Client

# --- 1. VERBINDUNGEN (DATENBANK & PREISE) ---
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
    prompt = f"Identifiziere diese Münze. Zustand: {zustand}. Antworte als JSON: {{'name': '...', 'jahr': '...', 'land': '...', 'metall': 'Gold' oder 'Silber' oder 'Unedel', 'reinheit': 0.9, 'gewicht': 7.0, 'marktwert': '...€', 'info': '...'}}"
    
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

# --- 3. APP SETUP & NAVIGATION ---
st.set_page_config(page_title="Münz-Archiv", layout="centered")

# Speicher für die Bilder initialisieren (Das "Gedächtnis")
if 'foto_vorder' not in st.session_state: st.session_state.foto_vorder = None
if 'foto_rueck' not in st.session_state: st.session_state.foto_rueck = None
if 'page' not in st.session_state: st.session_state.page = 'home'

# --- SEITE: HOME ---
if st.session_state.page == 'home':
    st.title("🪙 PAPAS MÜNZ-APP")
    p = get_live_prices()
    st.markdown(f"""<div style="background:#ffc107;padding:20px;border-radius:15px;text-align:center;font-weight:bold;color:#333;border:2px solid #e0a800;">
        AKTUELL: Gold {p['Gold']}€/g | Silber {p['Silber']}€/g</div>""", unsafe_allow_html=True)
    
    st.write(" ")
if  st.button("📸 NEUE MÜNZE SCANNEN", type="primary"):
    st.session_state.page = 'scanner'
    st.rerun()
if  st.button("📚 SAMMLUNG ANSEHEN"):
    st.session_state.page = 'sammlung'
    st.rerun()

# --- SEITE: SCANNER ---
elif st.session_state.page == 'scanner':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()
    
    st.subheader("1. Zustand")
    zustand = st.select_slider("Wie erhalten?", options=["Gebraucht", "Normal", "Sehr gut", "Neuwertig"])
    
    st.subheader("2. Fotos")
    
    # Foto 1
    f1 = st.file_uploader("📸 VORDERSEITE aufnehmen", type=["jpg", "jpeg", "png"], key="u1")
    if f1:
        st.session_state.foto_vorder = optimiere_bild(f1)
        st.success("Vorderseite OK! ✅")

    # Foto 2 (Nur zeigen, wenn Foto 1 im Speicher ist)
    if st.session_state.foto_vorder:
        f2 = st.file_uploader("📸 RÜCKSEITE aufnehmen", type=["jpg", "jpeg", "png"], key="u2")
        if f2:
            st.session_state.foto_rueck = optimiere_bild(f2)
            st.success("Rückseite OK! ✅")

    # Analyse-Button (Nur wenn beide im Speicher sind)
    if st.session_state.foto_vorder and st.session_state.foto_rueck:
        st.write("---")
        if st.button("JETZT ANALYSIEREN ✨", type="primary"):
            with st.spinner("Experte prüft die Münze..."):
                try:
                    res_raw = analysiere_muenze(st.session_state.foto_vorder, st.session_state.foto_rueck, zustand)
                    d = json.loads(res_raw)
                    
                    # Metallwert-Berechnung
                    p = get_live_prices()
                    g_preis = p.get(d.get('metall', 'Unedel'), 0)
                    m_wert = d.get('gewicht', 0) * d.get('reinheit', 0) * g_preis
                    
                    # Speichern
                    client = init_supabase()
                    client.table("muenzen").insert({
                        "name": d['name'], "jahr": str(d['jahr']),
                        "land": d['land'], "marktwert": d['marktwert']
                    }).execute()
                    
                    st.balloons()
                    st.markdown(f"""<div style="background:white;padding:20px;border-radius:15px;border-left:10px solid #ffd700;color:#333;box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
                        <h2 style="margin-top:0;">{d['name']} ({d['jahr']})</h2>
                        <p>💰 <b>Marktwert:</b> {d['marktwert']}</p>
                        <p>⚖️ <b>Metallwert:</b> {m_wert:.2f}€</p>
                        <p>🌍 <b>Land:</b> {d['land']} | 🧪 <b>Material:</b> {d.get('metall', 'Unedel')}</p>
                        <hr>
                        <p>📜 <i>{d['info']}</i></p>
                    </div>""", unsafe_allow_html=True)
                    
                    # Speicher leeren für nächsten Scan
                    if st.button("Nächste Münze"):
                        st.session_state.foto_vorder = None
                        st.session_state.foto_rueck = None
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Fehler: {e}")

# --- SEITE: SAMMLUNG ---
elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()
        st.title("📚 Deine Schätze")
    try:
        client = init_supabase()
        res = client.table("muenzen").select("*").order("created_at", desc=True).execute()
        if not res.data:
               st.info("Noch keine Schätze gespeichert.")
        for m in res.data:
            with st.expander(f"{m['name']} ({m['jahr']})"):
                st.write(f"**Wert:** {m['marktwert']} | **Land:** {m['land']}")
                st.caption(f"Datum: {m['created_at'][:10]}")
    except Exception as e:
        st.error(f"Datenbank-Fehler: {e}")


