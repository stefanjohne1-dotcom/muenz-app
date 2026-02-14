import streamlit as st
import requests
import base64
import json
import io
from PIL import Image
from supabase import create_client, Client

# --- 1. INITIALISIERUNG (GEHIRN DER APP) ---
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'foto1' not in st.session_state: st.session_state.foto1 = None
if 'foto2' not in st.session_state: st.session_state.foto2 = None

# --- 2. PREISE (LIVE & UNEDLE METALLE) ---
def get_live_prices():
    # Alle deine gewünschten Metalle mit korrekter Syntax (Punkt & Komma)
    p = {
        "Gold": 135.9, "Silber": 1.59, "Kupfer": 0.009, 
        "Nickel": 0.015, "Messing": 0.006, "Zink": 0.003,
        "Stahl": 0.001, "Eisen": 0.001, "source": "Schätzwerte"
    }
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        res_g = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/XAU-EUR=X", headers=h, timeout=5).json()
        p["Gold"] = round(res_g['chart']['result'][0]['meta']['regularMarketPrice'] / 31.1035, 2)
        res_s = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/XAG-EUR=X", headers=h, timeout=5).json()
        p["Silber"] = round(res_s['chart']['result'][0]['meta']['regularMarketPrice'] / 31.1035, 2)
        p["source"] = "Yahoo Live 📈"
    except: pass
    return p

# --- 3. HILFSFUNKTIONEN ---
@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def optimiere(file):
    img = Image.open(file)
    img.thumbnail((800, 800))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=75)
    return buf.getvalue()

def analysiere_ki(f1, f2, zustand):
    b1 = base64.b64encode(f1).decode()
    b2 = base64.b64encode(f2).decode()
    headers = {"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"}
    prompt = f"""Identifiziere diese Münze. Zustand: {zustand}. Antworte NUR als JSON:
    {{'name': '...', 'jahr': '...', 'land': '...', 'metall': 'Gold/Silber/Kupfer/Nickel/Messing/Zink/Stahl', 
    'reinheit': 0.9, 'gewicht': 15.55, 'groesse': '28mm', 'auflage': '100.000', 'marktwert_num': 850.0, 
    'besonderheiten': '...', 'info': '...'}}"""
    
    payload = {
        "model": "gpt-4o-mini", "messages": [{"role": "user", "content": [{"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b1}"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b2}"}}]}],
        "response_format": { "type": "json_object" }
    }
    res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']

# --- 4. APP DESIGN ---
st.set_page_config(page_title="Münz-Archiv", layout="centered")

# --- HOME ---
if st.session_state.page == 'home':
    st.title("🪙 PAPAS MÜNZ-ARCHIV")
    p = get_live_prices()
    st.markdown(f'<div style="background:#ffc107;padding:15px;border-radius:15px;text-align:center;color:#333;"><b>{p["source"]}</b><br>Gold: {p["Gold"]}€/g | Silber: {p["Silber"]}€/g</div>', unsafe_allow_html=True)
    
    if st.button("📸 NEUE MÜNZE SCANNEN", type="primary"):
        st.session_state.foto1 = None; st.session_state.foto2 = None
        st.session_state.page = 'scanner'; st.rerun()
    if st.button("📚 MEINE SAMMLUNG"):
        st.session_state.page = 'sammlung'; st.rerun()

# --- SCANNER (DIREKT IM BROWSER) ---
elif st.session_state.page == 'scanner':
    if st.button("⬅️ ZURÜCK"): st.session_state.page = 'home'; st.rerun()
    st.subheader("Münze digitalisieren")
    zst = st.select_slider("Zustand:", options=["Gebraucht", "Normal", "Sehr gut", "Neuwertig"])
    
    # Der Clou: camera_input bleibt in der App
    c1 = st.camera_input("1. VORDERSEITE AUFNEHMEN")
    if c1: st.session_state.foto1 = optimiere(c1)
    
    if st.session_state.foto1:
        st.success("Vorderseite gespeichert! ✅")
        c2 = st.camera_input("2. RÜCKSEITE AUFNEHMEN")
        if c2: st.session_state.foto2 = optimiere(c2)

    if st.session_state.foto1 and st.session_state.foto2:
        if st.button("ANALYSE STARTEN ✨", type="primary"):
            with st.spinner("KI berechnet Werte..."):
                try:
                    res = json.loads(analysiere_ki(st.session_state.foto1, st.session_state.foto2, zst))
                    client = init_supabase()
                    client.table("muenzen").insert({
                        "name": res['name'], "jahr": str(res['jahr']), "land": res['land'], 
                        "metall": res['metall'], "reinheit": res['reinheit'], "gewicht": res['gewicht'],
                        "groesse": res['groesse'], "auflage": res['auflage'], 
                        "marktwert_num": res['marktwert_num'], "besonderheiten": res['besonderheiten'], "info": res['info']
                    }).execute()
                    st.balloons(); st.success(f"Erfolg: {res['name']} gespeichert!"); st.session_state.page = 'sammlung'; st.rerun()
                except Exception as e: st.error(f"Fehler: {e}")

# --- SAMMLUNG (MIT ALLEN WÜNSCHEN) ---
elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"): st.session_state.page = 'home'; st.rerun()
    st.title("📚 Sammlung")
    p = get_live_prices()
    
    try:
        client = init_supabase()
        db = client.table("muenzen").select("*").order("created_at", desc=True).execute()
        
        if db.data:
            # Filter & Summen
            all_m = sorted(list(set([m['metall'] for m in db.data])))
            selected = st.multiselect("Filtern nach Metall:", options=all_m, default=all_m)
            filtered = [m for m in db.data if m['metall'] in selected]
            
            t_mat, t_hand = 0, 0
            for m in filtered:
                k = p.get(m['metall'], 0.001)
                t_mat += (m['gewicht'] or 0) * (m['reinheit'] or 0) * k
                t_hand += (m['marktwert_num'] or 0)

            # Dashboard
            st.markdown(f"""<div style="background:#f0f2f6;padding:20px;border-radius:15px;border:2px solid #007bff;">
                <h3 style="margin:0;text-align:center;">GESAMTWERT</h3>
                <table style="width:100%;margin-top:10px;">
                    <tr><td>Materialwert (Schmelzwert):</td><td style="text-align:right;"><b>{t_mat:.2f}€</b></td></tr>
                    <tr><td>Handelswert (Marktwert):</td><td style="text-align:right;color:#007bff;"><b>{t_hand:.2f}€</b></td></tr>
                </table></div>""", unsafe_allow_html=True)

            for m in filtered:
                with st.expander(f"🪙 {m['name']} ({m['jahr']})"):
                    k = p.get(m['metall'], 0.001)
                    m_w = (m['gewicht'] or 0) * (m['reinheit'] or 0) * k
                    st.write(f"**Material:** {m_w:.2f}€ | **Handel:** {m['marktwert_num']}€")
                    st.write(f"**Daten:** {m['metall']} | {m['gewicht']}g | {m['groesse']} | Auflage: {m['auflage']}")
                    st.write(f"**Besonderheit:** {m['besonderheiten']}")
                    st.info(m['info'])
                    if st.button("🗑️ Löschen", key=f"del_{m['id']}"):
                        client.table("muenzen").delete().eq("id", m['id']).execute(); st.rerun()
        else: st.info("Noch keine Münzen im Archiv.")
    except Exception as e: st.error(f"Fehler: {e}")


