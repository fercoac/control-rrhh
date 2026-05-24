import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import smtplib
from email.mime.text import MIMEText
import requests
import time

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="RRHH - Parque Automotor", layout="centered")

# --- CÓDIGO PARA OCULTAR EL MENÚ Y EL GATO DE GITHUB ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# Datos de conexión (Tus GIDs confirmados)
URL_MACRO = "https://script.google.com/macros/s/AKfycby42PKm1KqL0IaqAKfumxB_9_856yueCpJOWx1ersgmb218g6R3sU0Y0SKRQ-ZIQ4Fj/exec"
SHEET_ID = "1JwTFaSjcYLDLG6knoxXBkjPTZb2L9CGEWVCwXdswjpI"
GID_EMPLEADOS = "1680284558"
GID_MARCAS = "598259224"
GID_SOLICITUDES = "0"
GID_FERIADOS = "320254015" 

# Función de lectura con auto-reintento
def leer_hoja(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    intentos = 0
    while intentos < 3:
        try:
            return pd.read_csv(url)
        except:
            intentos += 1
            time.sleep(1)
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
    except:
        return False

# --- LOGIN ---
if 'auth' not in st.session_state:
    st.title("🔐 Control de Ingresos")
    dni_input = st.text_input("DNI")
    pin_input = st.text_input("Clave de 4 dígitos", type="password")
    
    if st.button("Ingresar"):
        with st.spinner('Verificando...'):
            try:
                df_emp = leer_hoja(GID_EMPLEADOS)
                df_emp.columns = df_emp.columns.str.strip()
                df_emp['DNI'] = df_emp['DNI'].astype(str).str.strip().str.replace('.0', '', regex=False)
                df_emp['PIN'] = df_emp['PIN'].astype(str).str.strip().str.replace('.0', '', regex=False).str.zfill(4)
                
                user_row = df_emp[(df_emp['DNI'] == str(dni_input).strip()) & (df_emp['PIN'] == str(pin_input).strip())]
                
                if not user_row.empty:
                    st.session_state.auth = True
                    st.session_state.user = user_row.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("DNI o Clave incorrectos.")
            except:
                st.error("Error de conexión. Intente de nuevo.")

# --- PANEL PRINCIPAL ---
else:
    user = st.session_state.user
    st.sidebar.title(f"Hola, {user['Nombre']}")
    opcion = st.sidebar.radio("Menú:", ["Mis Marcas", "Solicitar Vacaciones"])

    if opcion == "Mis Marcas":
        st.header("📋 Mis Registros")
        with st.spinner('Cargando...'):
            try:
                df_marcas = leer_hoja(GID_MARCAS)
                df_marcas.columns = df_marcas.columns.str.strip()
                mi_id = str(int(float(user['ID_Biometrico'])))
                col_id = df_marcas.columns[0]
                df_marcas[col_id] = df_marcas[col_id].astype(str).str.strip().str.replace('.0', '', regex=False)
                mis_marcas = df_marcas[df_marcas[col_id] == mi_id]
                if not mis_marcas.empty:
                    st.dataframe(mis_marcas, use_container_width=True, hide_index=True)
                else:
                    st.info(f"No hay registros para el ID {mi_id}")
            except:
                st.error("Error al cargar.")

    elif opcion == "Solicitar Vacaciones":
        st.header("🏖️ Solicitud de Licencia (L.A.R.)")
        with st.spinner('Consultando saldo...'):
            try:
                url_fer = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_FERIADOS}"
                df_fer = pd.read_csv(url_fer)
                fechas_s = pd.to_datetime(df_fer['Fecha'], dayfirst=True, errors='coerce')
                lista_feriados = set(fechas_s.dropna().dt.date.tolist())
            except:
                lista_feriados = set()

            try:
                df_sol = leer_hoja(GID_SOLICITUDES)
                df_sol.columns = df_sol.columns.str.strip()
                df_sol['DNI'] = df_sol['DNI'].astype(str).str.strip().str.replace('.0', '', regex=False)
                dni_u = str(user['DNI']).split('.')[0]
                mis_sol = df_sol[df_sol['DNI'] == dni_u]
                dias_u = mis_sol['Dias_Habiles'].sum()
            except:
                dias_u = 0

        remanente = float(user['Dias_Totales']) - dias_u
        st.metric("Días Disponibles Hoy", f"{int(remanente)}")

        f_ini = st.date_input("Fecha Inicio", min_value=date(2025, 12, 1), format="DD/MM/YYYY")
        f_fin = st.date_input("Fecha Fin", min_value=f_ini, format="DD/MM/YYYY")
        
        cant_dias = (f_fin - f_ini).days + 1
        dias_h = [f_ini + timedelta(days=i) for i in range(cant_dias) if (f_ini + timedelta(days=i)).weekday() < 5 and (f_ini + timedelta(days=i)) not in lista_feriados]
        pedidos = len(dias_h)
        nuevo_rem = remanente - pedidos

        if pedidos > 0:
            st.info(f"🧾 Días a solicitar: **{pedidos}** | Saldo restante: **{int(nuevo_rem)}**")
            if nuevo_rem >= 0:
                if st.checkbox("Confirmo fechas."):
                    if st.button("🚀 ENVIAR"):
                        dni_l = str(user['DNI']).split('.')[0]
                        payload = {"dni": dni_l, "nombre": user['Nombre'], "inicio": f_ini.strftime('%d/%m/%Y'), "fin": f_fin.strftime('%d/%m/%Y'), "dias": pedidos}
                        try:
                            res = requests.post(URL_MACRO, json=payload)
                            if res.status_code == 200:
                                st.success("✅ ¡Registrado!")
                                h = datetime.now()
                                n = f"SALTA, {h.day}/{h.month}/{h.year}\n\nSr. Ricardo Velarde Figueroa:\n\nYo {user['Nombre']}, DNI {dni_l}, solicito {pedidos} días hábiles de LAR de {f_ini.strftime('%d/%m/%Y')} a {f_fin.strftime('%d/%m/%Y')}.\n\nFirma: _________________________"
                                st.text_area("Copia para imprimir:", n, height=300)
                                enviar_correo("rrhhparqueautomotor@gmail.com", f"LAR: {user['Nombre']}", n)
                        except:
                            st.error("Error al guardar.")

    if st.sidebar.button("Cerrar Sesión"):
        del st.session_state.auth
        st.rerun()
