import streamlit as st
import requests
import base64
import json
import io
import re
from PIL import Image
from supabase import create_client, Client

# --- 1. INITIALISIERUNG (GEHIRN DER APP) ---
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'foto1' not in st.session_state: st.session_state.foto1 = None
if 'foto2' not in st.session_state: st.session_state.foto2 = None
if 'analysis_result' not in st.session_state: st.session_state.analysis_result = None

# --- 2. PREISE (LIVE & ALLE METALLE) ---
def get_live_prices():
    # Standardwerte (Punkte statt Kommas nutzen!)
    p = {
        "Gold": 135.9, "Silber": 1.6, "Kupfer": 0.009, 
        "Nickel": 0.015, "Messing": 0.006, "Zink": 0.003,
        "Stahl": 0.001, "Eisen": 0.001, "source": "Schätzwerte"
    }
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        # Gold-Abfrage
        res_g = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/XAU-EUR=X", headers=h, timeout=5).json()
        # Prüfen, ob die Daten-Struktur wirklich existiert (verhindert NoneType-Fehler)
        if res_g and 'chart' in res_g and res_g['chart']['result']:
            p["Gold"] = round(res_g['chart']['result'][0]['meta']['regularMarketPrice'] / 31.1035, 2)
            
        # Silber-Abfrage
        res_s = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/XAG-EUR=X", headers=h, timeout=5).json()
        if res_s and 'chart' in res_s and res_s['chart']['result']:
            p["Silber"] = round(res_s['chart']['result'][0]['meta']['regularMarketPrice'] / 31.1035, 2)
            p["source"] = "Yahoo Live 📈"
    except Exception:
        # Falls irgendwas schiefgeht, bleiben einfach die Schätzwerte stehen
        pass
    return p

# --- 3. HILFSFUNKTIONEN ---
@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def reinige_zahl(text):
    """Extrahiert reine Zahlen aus KI-Texten wie '15,55 g'"""
    if isinstance(text, (int, float)): return float(text)
    match = re.search(r"[-+]?\d*\.?\d+", str(text).replace(",", "."))
    return float(match.group()) if match else 0.0

def optimiere(file):
    img = Image.open(file)
    img.thumbnail((1024, 1024))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=80)
    return buf.getvalue()

def analysiere_ki(f1, f2, zustand):
    b1 = base64.b64encode(f1).decode(); b2 = base64.b64encode(f2).decode()
    headers = {"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"}
    
    # Der "strenge" Experten-Prompt:
    prompt = f"""
    Du bist ein numismatischer Sachverständiger und Experte für Edelmetallmünzen. Identifiziere diese Münze.
    
    WICHTIGSTE REGELN:
    1. PRÄGEJAHR-CHECK: Das Jahr ist dein wichtigster Parameter.
    2. LOGIK-ABGLEICH: Gleiche das Prägejahr zwingend mit den Symbolen/Wappen ab. 
       Beispiel: Ein Jahr von 1950 passt nicht zu einem Kaiser-Porträt oder Wappen des 19. Jahrhunderts.
    3. WICHTIG: MODERNE SONDERMÜNZEN (ab 2000) haben oft ungewöhnliche Nennwerte (wie z.B. 11 Euro z.B. Deutschland 2024, 25 Euro oder andere ungewöhnliche Gedenkmünzen-Werte. Das ist KORREKT und KEIN Fehler!
    4. Nur wenn das Jahr absolut NICHT zur Epoche passt (z.B. Jahr 2024 bei einem Kaiserreich-Adler oder Eisernes Kreuz), beginne den "name" mit dem Wort "FEHLER:".
    
    Zustand: {zustand}.
    Antworte NUR als JSON:
    {{
      "name": "Vollständiger Name der Münze",
      "jahr": "Gefundenes Prägejahr",
      "land": "Land",
      "metall": "Gold/Silber/Kupfer/Nickel/Messing/Zink/Stahl/Eisen/Aluminium", 
      "reinheit": 0.9, 
      "gewicht": 15.55, 
      "groesse": "mm", 
      "auflage": "Auflagenzahl", 
      "marktwert_num": 0.0, 
      "besonderheiten": "Begründung der Logikprüfung (z.B. Warum das Nominal zum Jahr passt)", 
      "info": "Historischer Kontext, Sind Fehlprägungen bekannt? (3-4 Sätze)"
    }}
    """
    
    payload = {
        "model": "gpt-4o-mini", 
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b1}"}},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b2}"}}
        ]}],
        "response_format": { "type": "json_object" }
    }
    res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']


# --- 4. APP DESIGN ---
st.set_page_config(page_title="Papas Münz-App", layout="centered")

# --- SEITE: HOME ---
if st.session_state.page == 'home':
    st.markdown("""
        <div style="background-color: #ffd700; padding: 10px; border-radius: 10px; text-align: center;">
            <h1 style="color: #333; margin: 0;">Papas Münz-APP</h1>
        </div><br>
    """, unsafe_allow_html=True)
    
    p = get_live_prices()
    st.markdown(f'<div style="background:#f0f2f6;padding:15px;border-radius:15px;text-align:center;color:#333;"><b>{p["source"]}</b><br>Gold: {p["Gold"]}€/g | Silber: {p["Silber"]}€/g</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📸 NEUE MÜNZE SCANNEN", type="primary"):
            st.session_state.foto1, st.session_state.foto2 = None, None
            st.session_state.analysis_result = None
            st.session_state.page = 'scanner'; st.rerun()
    with col2:
        if st.button("📚 MEINE SAMMLUNG"):
            st.session_state.page = 'sammlung'; st.rerun()

# --- SEITE: SCANNER (GALERIE-UPLOAD & BESTÄTIGUNG) ---
elif st.session_state.page == 'scanner':
    if st.button("⬅️ ABBRECHEN"): st.session_state.page = 'home'; st.rerun()
    
    if st.session_state.analysis_result is None:
        st.subheader("Fotos aus Galerie einfügen")
        zst = st.select_slider("Zustand wählen:", options=["Gebraucht", "Normal", "Sehr gut", "Neuwertig"])
        
        u1 = st.file_uploader("1. VORDERSEITE einfügen", type=["jpg", "jpeg", "png"], key="u1")
        if u1: st.session_state.foto1 = optimiere(u1)
        u2 = st.file_uploader("2. RÜCKSEITE einfügen", type=["jpg", "jpeg", "png"], key="u2")
        if u2: st.session_state.foto2 = optimiere(u2)

        if st.session_state.foto1 and st.session_state.foto2:
            st.divider()
            if st.button("ANALYSE STARTEN ✨", type="primary"):
                with st.spinner("KI prüft Logik von Jahr und Wappen..."):
                    res_raw = analysiere_ki(st.session_state.foto1, st.session_state.foto2, zst)
                    st.session_state.analysis_result = json.loads(res_raw)
                    st.rerun()
    
    else:
        res = st.session_state.analysis_result
        p = get_live_prices()
        
        # --- LOGIK-CHECK & MANUELLE KORREKTUR ---
        ist_fehler = "FEHLER" in res['name'].upper()
        
        if ist_fehler:
            st.error(f"🛑 LOGIK-FEHLER: {res['name']}")
            st.info("Das Jahr scheint nicht zum Wappen zu passen. Du kannst es unten korrigieren, um den Speicher-Button freizugeben.")
        
        # Manuelle Korrektur-Möglichkeit
        col_edit1, col_edit2 = st.columns([1, 2])
        with col_edit1:
            neu_jahr = st.text_input("Korrektes Jahr:", value=res['jahr'])
        with col_edit2:
            # Wenn der Nutzer das Jahr ändert, "entsperren" wir den Fehler
            freigabe = st.checkbox("Daten trotz Warnung freigeben (Jahr manuell geprüft)")

        # Button freigeben, wenn kein Fehler vorliegt ODER die Freigabe angehakt ist
        button_aktiv = (not ist_fehler) or freigabe

        # Berechnungen mit dem (evtl. neuen) Jahr
        kurs = p.get(res['metall'], 0.001)
        gew, rein = reinige_zahl(res['gewicht']), reinige_zahl(res['reinheit'])
        m_w = gew * rein * kurs

        st.markdown(f"""
        <div style="background:white; padding:20px; border-radius:15px; border:2px solid {'#ff4b4b' if (ist_fehler and not freigabe) else '#ffd700'}; color:#333;">
            <h3 style="margin-top:0;">{res['name'] if not ist_fehler else '⚠️ Überprüfung notwendig'}</h3>
            <p><b>Jahr:</b> {neu_jahr} | <b>Materialwert:</b> {m_w:.2f}€</p>
            <hr>
            <p><b>KI-Bericht:</b> {res['besonderheiten']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        c_ok, c_no = st.columns(2)
        with c_ok:
            if button_aktiv:
                if st.button("✅ JETZT SPEICHERN", type="primary"):
                    client = init_supabase()
                    client.table("muenzen").insert({
                        "name": res['name'].replace("FEHLER: ", ""), # Entfernt das Fehler-Präfix
                        "jahr": str(neu_jahr), # Nutzt das manuell eingetragene Jahr
                        "land": res['land'], "metall": res['metall'], 
                        "reinheit": rein, "gewicht": gew,
                        "groesse": res['groesse'], "auflage": res['auflage'], 
                        "marktwert_num": reinige_zahl(res['marktwert_num']), 
                        "besonderheiten": res['besonderheiten'], "info": res['info']
                    }).execute()
                    st.balloons(); st.session_state.analysis_result = None; st.session_state.page = 'sammlung'; st.rerun()
            else:
                st.button("🚫 SPEICHERN GESPERRT", disabled=True)
        
        with c_no:
            if st.button("❌ VERWERFEN"):
                st.session_state.analysis_result = None; st.rerun()

# --- SEITE: SAMMLUNG (MIT ALLEN DETAILS) ---
elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()
    
    st.markdown("""
        <div style="background-color: #ffd700; padding: 10px; border-radius: 10px; text-align: center;">
            <h1 style="color: #333; margin: 0;">📚 DEINE SAMMLUNG</h1>
        </div><br>
    """, unsafe_allow_html=True)
    
    p = get_live_prices()
    try:
        client = init_supabase()
        db = client.table("muenzen").select("*").order("created_at", desc=True).execute()
        
        if db.data:
            all_m = sorted(list(set([m['metall'] for m in db.data])))
            selected = st.multiselect("Filtern nach Metall:", options=all_m, default=all_m)
            filtered = [m for m in db.data if m['metall'] in selected]
            
            t_mat, t_hand = 0, 0
            for m in filtered:
                k = p.get(m['metall'], 0.001)
                t_mat += (m['gewicht'] or 0) * (m['reinheit'] or 0) * k
                t_hand += (m['marktwert_num'] or 0)

            st.markdown(f"""<div style="background:#f0f2f6;padding:20px;border-radius:15px;border:2px solid #007bff;">
                <h3 style="margin:0;text-align:center;">GESAMTWERT</h3>
                <table style="width:100%;margin-top:10px;">
                    <tr><td>Materialwert (Schmelzwert):</td><td style="text-align:right;"><b>{t_mat:.2f}€</b></td></tr>
                    <tr><td>Handelswert (Marktwert):</td><td style="text-align:right;color:#007bff;"><b>{t_hand:.2f}€</b></td></tr>
                </table></div>""", unsafe_allow_html=True)

            for m in filtered:
                # Expander zeigt alle Zusatzinfos an
                with st.expander(f"🪙 {m['name']} ({m['jahr']})"):
                    k = p.get(m['metall'], 0.001)
                    m_w = (m['gewicht'] or 0) * (m['reinheit'] or 0) * k
                    
                    st.write(f"**Land:** {m['land']}")
                    st.write(f"**Materialwert:** {m_w:.2f}€ | **Handelswert:** {m['marktwert_num']}€")
                    st.write(f"**Technische Daten:** {m['metall']} | {m['gewicht']}g | {m['groesse']}")
                    st.write(f"**Auflage:** {m['auflage']}")
                    st.write(f"**Besonderheiten:** {m['besonderheiten']}")
                    st.info(f"**Hintergrund-Info:** {m['info']}")
                    
                    if st.button("🗑️ Löschen", key=f"del_{m['id']}"):
                        client.table("muenzen").delete().eq("id", m['id']).execute(); st.rerun()
            else:
                st.info("Archiv ist noch leer.")
    except Exception as e:
        st.error(f"Datenbankfehler: {e}")









