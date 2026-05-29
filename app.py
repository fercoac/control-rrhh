import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import smtplib
from email.mime.text import MIMEText
import requests
import time

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="RRHH - Parque Automotor", layout="centered")

# --- DISEÑO PREMIUM ---
custom_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stSidebarNav"] {display: none;}
    .main { background-color: #f8fafc; }
    div.stButton > button {
        width: 100%; border-radius: 12px; height: 3.8em; 
        background-color: #ffffff; color: #1e293b; 
        border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        transition: all 0.2s ease; font-weight: 600; text-align: left;
        padding-left: 20px;
    }
    div.stButton > button:hover {
        border-color: #3b82f6; color: #3b82f6;
        transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
    }
    .stMetric {
        background-color: #ffffff; padding: 15px; 
        border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    </style>
    """
st.markdown(custom_style, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE DATOS ---
URL_MACRO = "https://script.google.com/macros/s/AKfycby42PKm1KqL0IaqAKfumxB_9_856yueCpJOWx1ersgmb218g6R3sU0Y0SKRQ-ZIQ4Fj/exec"
SHEET_ID = "1JwTFaSjcYLDLG6knoxXBkjPTZb2L9CGEWVCwXdswjpI"
GID_EMPLEADOS = "1680284558"
GID_MARCAS = "598259224"
GID_SOLICITUDES = "0"
GID_FERIADOS = "320254015" 

@st.cache_data(ttl=300)
def leer_hoja_cache(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    for i in range(5):
        try: return pd.read_csv(url)
        except: time.sleep(1)
    return pd.read_csv(url)

def enviar_correo(destinatario, asunto, cuerpo):
    remitente = "fercoac@gmail.com"
    password = "wqhosrswlhrssqrp" 
    msg = MIMEText(cuerpo)
    msg['Subject'] = asunto
    msg['From'] = remitente
    msg['To'] = destinatario
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(remitente, password)
        server.sendmail(remitente, destinatario, msg.as_string())
        server.quit()
        return True
    except: return False

if 'auth' not in st.session_state: st.session_state.auth = False
if 'view' not in st.session_state: st.session_state.view = "Home"

# --- LOGIN ---
if not st.session_state.auth:
    st.title("🔐 Control de Ingresos")
    st.caption("Subsecretaría del Parque Automotor")
    dni_i = st.text_input("DNI")
    pin_i = st.text_input("PIN (4 dígitos)", type="password")
    if st.button("Ingresar"):
        with st.spinner('Validando...'):
            try:
                df = leer_hoja_cache(GID_EMPLEADOS)
                df.columns = df.columns.str.strip()
                df['DNI'] = df['DNI'].astype(str).str.strip().str.replace('.0', '', regex=False)
                df['PIN'] = df['PIN'].astype(str).str.strip().str.replace('.0', '', regex=False).str.zfill(4)
                u = df[(df['DNI'] == str(dni_i).strip()) & (df['PIN'] == str(pin_i).strip())]
                if not u.empty:
                    st.session_state.auth = True
                    st.session_state.user = u.iloc[0].to_dict()
                    st.cache_data.clear()
                    st.rerun()
                else: st.error("Datos incorrectos")
            except: st.error("Error de conexión")

# --- APP ---
else:
    user = st.session_state.user
    st.sidebar.subheader("👤 Perfil")
    st.sidebar.write(user['Nombre'])
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.auth = False
        st.cache_data.clear()
        st.rerun()

    if st.session_state.view == "Home":
        nombre_pila = user['Nombre'].split()[-1] if len(user['Nombre'].split()) > 1 else user['Nombre']
        st.title(f"Hola, {nombre_pila} 👋")
        if st.button("📋 Mis Marcas Biométricas"): st.session_state.view = "Marcas"; st.rerun()
        if st.button("🏖️ Solicitar Licencia LAR"): st.session_state.view = "Vacaciones"; st.rerun()
        if st.button("📄 Solicitar Art. 74 (Particulares)"): st.session_state.view = "Art74"; st.rerun()
        if st.button("🔍 Ver Estado de Mis Solicitudes"): st.session_state.view = "Historial"; st.rerun()
        if st.button("🗓️ Consultar Calendario de Feriados"): st.session_state.view = "Feriados"; st.rerun()

    elif st.session_state.view == "Marcas":
        if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
        st.header("📋 Mis Registros")
        
        df = leer_hoja_cache(GID_MARCAS)
        df.columns = df.columns.str.strip()
        mi_id = str(int(float(user['ID_Biometrico'])))
        col_id = df.columns[0]
        df[col_id] = df[col_id].astype(str).str.strip().str.replace('.0', '', regex=False)
        m = df[df[col_id] == mi_id].copy()
        
        if not m.empty:
            m['temp_fecha'] = pd.to_datetime(m['Fecha'], dayfirst=True)
            m['temp_hora'] = pd.to_datetime(m['Hora'], format='%H:%M').dt.time
            m['dt'] = pd.to_datetime(m['Fecha'] + ' ' + m['Hora'], dayfirst=True)
            m = m.sort_values('dt', ascending=False)
            
            ultima = m.iloc[0]
            st.success(f"**Último movimiento:** {ultima['Evento']} el {ultima['Fecha']} a las {ultima['Hora']}")

            # --- LÓGICA DE LLEGADAS TARDE CORREGIDA ---
            hoy = datetime.now()
            mes_actual = m[(m['temp_fecha'].dt.month == hoy.month) & (m['temp_fecha'].dt.year == hoy.year)]
            limite_i = datetime.strptime("08:11", "%H:%M").time()
            limite_f = datetime.strptime("09:00", "%H:%M").time()
            
            # FILTRO: Rango horario + Solo eventos "Entrada" o "Acceso"
            tardanzas = mes_actual[
                (mes_actual['temp_hora'] >= limite_i) & 
                (mes_actual['temp_hora'] <= limite_f) & 
                (mes_actual['Evento'].str.strip().isin(['Entrada', 'Acceso']))
            ]
            
            tardanzas_u = tardanzas.drop_duplicates(subset=['Fecha'])

            if not tardanzas_u.empty:
                st.error(f"⚠️ **Llegadas tarde (Entradas/Accesos) en {hoy.strftime('%B')}:** {len(tardanzas_u)}")
                st.write(f"Días: {', '.join(tardanzas_u['Fecha'].tolist())}")
            
            st.dataframe(m.drop(columns=['dt', 'temp_fecha', 'temp_hora']), use_container_width=True, hide_index=True)
        else: st.info("Sin registros.")

    # (El resto de las vistas: Vacaciones, Art74, Historial, Feriados se mantienen igual)
    elif st.session_state.view == "Vacaciones":
        if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
        st.header("🏖️ Solicitar LAR")
        df_sol = leer_hoja_cache(GID_SOLICITUDES)
        dni_u = str(user['DNI']).split('.')[0]
        usados = df_sol[(df_sol['DNI'].astype(str) == dni_u) & (df_sol['Tipo'] == 'LAR')]['Dias_Habiles'].sum()
        rem = float(user['Dias_Totales']) - usados
        st.metric("Días LAR Disponibles", f"{int(rem)}")
        f_i = st.date_input("Inicio", format="DD/MM/YYYY", min_value=date.today())
        f_f = st.date_input("Fin", min_value=f_i, format="DD/MM/YYYY")
        try:
            df_f = leer_hoja_cache(GID_FERIADOS)
            l_f = set(pd.to_datetime(df_f['Fecha'], dayfirst=True, errors='coerce').dropna().dt.date.tolist())
        except: l_f = set()
        r = (f_f - f_i).days + 1
        d_p = len([f_i+timedelta(days=i) for i in range(r) if (f_i+timedelta(days=i)).weekday()<5 and (f_i+timedelta(days=i)) not in l_f])
        if d_p > 0:
            st.info(f"Días hábiles: {d_p}")
            if rem >= d_p and st.checkbox("Confirmo fechas"):
                if st.button("🚀 ENVIAR"):
                    p = {"dni": dni_u, "nombre": user['Nombre'], "inicio": f_i.strftime('%d/%m/%Y'), "fin": f_f.strftime('%d/%m/%Y'), "dias": d_p, "tipo": "LAR"}
                    if requests.post(URL_MACRO, json=p).status_code == 200:
                        st.success("Enviado")
                        st.cache_data.clear()

    elif st.session_state.view == "Art74":
        if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
        st.header("📄 Artículo 74")
        df_sol = leer_hoja_cache(GID_SOLICITUDES)
        dni_u = str(user['DNI']).split('.')[0]
        u_art = len(df_sol[(df_sol['DNI'].astype(str) == dni_u) & (df_sol['Tipo'] == 'Art74')])
        st.metric("Días Art. 74 Disponibles", f"{2 - u_art}")
        if u_art < 2:
            f_art = st.date_input("Fecha", format="DD/MM/YYYY")
            if st.button("🚀 ENVIAR ART. 74"):
                p = {"dni": dni_u, "nombre": user['Nombre'], "inicio": f_art.strftime('%d/%m/%Y'), "fin": f_art.strftime('%d/%m/%Y'), "dias": 1, "tipo": "Art74"}
                if requests.post(URL_MACRO, json=p).status_code == 200:
                    st.success("Enviado")
                    st.cache_data.clear()

    elif st.session_state.view == "Historial":
        if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
        st.header("🔍 Mis Solicitudes")
        df_sol = leer_hoja_cache(GID_SOLICITUDES)
        dni_u = str(user['DNI']).split('.')[0]
        mis_s = df_sol[df_sol['DNI'].astype(str) == dni_u].copy()
        if not mis_s.empty:
            st.dataframe(mis_s[['Tipo', 'Fecha_Inicio', 'Fecha_Fin', 'Dias_Habiles', 'Estado']], use_container_width=True, hide_index=True)
        else: st.info("Sin registros.")

    elif st.session_state.view == "Feriados":
        if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
        st.header("🗓️ Feriados")
        df_f = leer_hoja_cache(GID_FERIADOS)
        st.dataframe(df_f, use_container_width=True, hide_index=True)
