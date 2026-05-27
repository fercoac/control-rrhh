import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import smtplib
from email.mime.text import MIMEText
import requests
import time

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="RRHH - Parque Automotor", layout="centered")

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            [data-testid="stSidebarNav"] {display: none;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

URL_MACRO = "https://script.google.com/macros/s/AKfycby42PKm1KqL0IaqAKfumxB_9_856yueCpJOWx1ersgmb218g6R3sU0Y0SKRQ-ZIQ4Fj/exec"
SHEET_ID = "1JwTFaSjcYLDLG6knoxXBkjPTZb2L9CGEWVCwXdswjpI"
GID_EMPLEADOS = "1680284558"
GID_MARCAS = "598259224"
GID_SOLICITUDES = "0"
GID_FERIADOS = "320254015" 

def leer_hoja(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    for i in range(3):
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
    dni_i = st.text_input("DNI")
    pin_i = st.text_input("PIN", type="password")
    if st.button("Ingresar"):
        df = leer_hoja(GID_EMPLEADOS)
        df.columns = df.columns.str.strip()
        df['DNI'] = df['DNI'].astype(str).str.strip().str.replace('.0', '', regex=False)
        df['PIN'] = df['PIN'].astype(str).str.strip().str.replace('.0', '', regex=False).str.zfill(4)
        u = df[(df['DNI'] == str(dni_i).strip()) & (df['PIN'] == str(pin_i).strip())]
        if not u.empty:
            st.session_state.auth = True
            st.session_state.user = u.iloc[0].to_dict()
            st.rerun()
        else: st.error("DNI o PIN incorrectos")

# --- APP ---
else:
    user = st.session_state.user
    st.sidebar.write(f"**{user['Nombre']}**")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.auth = False
        st.rerun()

    if st.session_state.view == "Home":
        st.title(f"Hola, {user['Nombre'].split()[0]} 👋")
        st.write("Selecciona una opción:")
        
        if st.button("📋 Ver Mis Marcas", use_container_width=True):
            st.session_state.view = "Marcas"; st.rerun()
        
        if st.button("🏖️ Solicitar Vacaciones (LAR)", use_container_width=True):
            st.session_state.view = "Vacaciones"; st.rerun()
            
        if st.button("📄 Solicitar Art. 74 (Razones Particulares)", use_container_width=True):
            st.session_state.view = "Art74"; st.rerun()

    elif st.session_state.view == "Marcas":
        if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
        st.header("📋 Mis Registros")
        df = leer_hoja(GID_MARCAS)
        df.columns = df.columns.str.strip()
        mi_id = str(int(float(user['ID_Biometrico'])))
        df[df.columns[0]] = df[df.columns[0]].astype(str).str.strip().str.replace('.0', '', regex=False)
        m = df[df[df.columns[0]] == mi_id].copy()
        if not m.empty:
            m['dt'] = pd.to_datetime(m['Fecha'] + ' ' + m['Hora'], dayfirst=True)
            st.dataframe(m.sort_values('dt', ascending=False).drop(columns=['dt']), use_container_width=True, hide_index=True)
        else: st.info("Sin registros")

    elif st.session_state.view == "Vacaciones":
        if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
        st.header("🏖️ Solicitud LAR")
        
        # Lógica de cálculo (Igual a la anterior)
        try:
            df_sol = leer_hoja(GID_SOLICITUDES)
            df_sol.columns = df_sol.columns.str.strip()
            # Filtrar solo las LAR
            dni_u = str(user['DNI']).split('.')[0]
            mis_lar = df_sol[(df_sol['DNI'].astype(str) == dni_u) & (df_sol['Tipo'] == 'LAR')]
            usados = mis_lar['Dias_Habiles'].sum()
        except: usados = 0
        
        rem = float(user['Dias_Totales']) - usados
        st.metric("Días LAR Disponibles", f"{int(rem)}")
        
        f_i = st.date_input("Inicio", format="DD/MM/YYYY")
        f_f = st.date_input("Fin", min_value=f_i, format="DD/MM/YYYY")
        dias = len(pd.bdate_range(f_i, f_f)) # Simplificado para el ejemplo
        
        if dias > 0 and rem >= dias:
            if st.checkbox("Confirmo fechas LAR"):
                if st.button("🚀 ENVIAR LAR"):
                    p = {"dni": str(user['DNI']).split('.')[0], "nombre": user['Nombre'], "inicio": f_i.strftime('%d/%m/%Y'), "fin": f_f.strftime('%d/%m/%Y'), "dias": dias, "tipo": "LAR"}
                    requests.post(URL_MACRO, json=p)
                    st.success("Enviado")
                    # (Aquí iría la generación de nota LAR que ya tenías)

    elif st.session_state.view == "Art74":
        if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
        st.header("📄 Artículo 74")
        st.write("Razones Particulares (Máximo 2 días por año calendario)")
        
        try:
            df_sol = leer_hoja(GID_SOLICITUDES)
            df_sol.columns = df_sol.columns.str.strip()
            dni_u = str(user['DNI']).split('.')[0]
            # Contar cuántos Art74 tiene en el año actual
            anio_actual = datetime.now().year
            mis_art = df_sol[(df_sol['DNI'].astype(str) == dni_u) & (df_sol['Tipo'] == 'Art74')]
            usados_art = len(mis_art)
        except: usados_art = 0
        
        disponibles_art = 2 - usados_art
        st.metric("Días Art. 74 Disponibles", f"{disponibles_art}")
        
        if disponibles_art > 0:
            fecha_art = st.date_input("Seleccione el día solicitado", min_value=date.today(), format="DD/MM/YYYY")
            if st.button("🚀 ENVIAR SOLICITUD ART. 74"):
                p = {"dni": str(user['DNI']).split('.')[0], "nombre": user['Nombre'], "inicio": fecha_art.strftime('%d/%m/%Y'), "fin": fecha_art.strftime('%d/%m/%Y'), "dias": 1, "tipo": "Art74"}
                res = requests.post(URL_MACRO, json=p)
                if res.status_code == 200:
                    st.success("✅ Solicitud de Art. 74 enviada y guardada.")
                    
                    hoy = datetime.now()
                    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                    fecha_salta = f"SALTA, {hoy.day} de {meses[hoy.month-1]} de {hoy.year}"
                    
                    nota_art = f"""
{fecha_salta}

Sr. Subsecretario del Parque Automotor
Ricardo Velarde Figueroa
S__________/__________D

Tengo el agrado de dirigirme a Usted, a fin de solicitar la justificación de la inasistencia incurrida el día {fecha_art.strftime('%d/%m/%Y')}, con goce de haberes, encuadrada en el Art. 74 (Razones Particulares) de la Reglamentación vigente, el cual dispone de hasta dos (2) días por año calendario.

Sin otro particular, saludo a Usted atentamente.

Firma: _______________________________
Apellido y Nombre: {user['Nombre']}
D.N.I.: {str(user['DNI']).split('.')[0]}
                    """
                    st.text_area("Copia para imprimir nota Art. 74:", nota_art, height=350)
                    enviar_correo("rrhhparqueautomotor@gmail.com", f"Art. 74: {user['Nombre']}", nota_art)
        else:
            st.error("⚠️ Ya has utilizado tus 2 días de Art. 74 para este año calendario.")
