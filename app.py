import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import smtplib
from email.mime.text import MIMEText
import requests
import time # Importamos para poder esperar entre reintentos

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="RRHH - Parque Automotor", layout="centered")

# Datos de conexión
URL_MACRO = "https://script.google.com/macros/s/AKfycby42PKm1KqL0IaqAKfumxB_9_856yueCpJOWx1ersgmb218g6R3sU0Y0SKRQ-ZIQ4Fj/exec"
SHEET_ID = "1JwTFaSjcYLDLG6knoxXBkjPTZb2L9CGEWVCwXdswjpI"
GID_EMPLEADOS = "1680284558"
GID_MARCAS = "598259224"
GID_SOLICITUDES = "0"
GID_FERIADOS = "320254015" 

# --- FUNCIÓN DE LECTURA CON AUTO-REINTENTO ---
def leer_hoja(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    intentos = 0
    while intentos < 3: # Intentará hasta 3 veces si falla
        try:
            return pd.read_csv(url)
        except:
            intentos += 1
            time.sleep(1) # Espera 1 segundo antes de reintentar
    return pd.read_csv(url) # Último intento antes de lanzar error

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
        with st.spinner('Verificando credenciales...'):
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
            except Exception as e:
                st.error("La base de datos está tardando en responder. Por favor, intenta presionar 'Ingresar' nuevamente.")

# --- PANEL PRINCIPAL ---
else:
    user = st.session_state.user
    st.sidebar.title(f"Hola, {user['Nombre']}")
    opcion = st.sidebar.radio("Menú:", ["Mis Marcas", "Solicitar Vacaciones"])

    if opcion == "Mis Marcas":
        st.header("📋 Mis Registros")
        with st.spinner('Cargando registros...'):
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
                st.error("Error al cargar registros. Intenta refrescar la página.")

    elif opcion == "Solicitar Vacaciones":
        st.header("🏖️ Solicitud de Licencia (L.A.R.)")
        
        with st.spinner('Consultando días disponibles...'):
            try:
                url_feriados = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_FERIADOS}"
                df_feriados = pd.read_csv(url_feriados)
                df_feriados.columns = df_feriados.columns.str.strip()
                fechas_sucias = pd.to_datetime(df_feriados['Fecha'], dayfirst=True, errors='coerce')
                lista_feriados = set(fechas_sucias.dropna().dt.date.tolist())
            except:
                lista_feriados = set()

            try:
                df_sol = leer_hoja(GID_SOLICITUDES)
                df_sol.columns = df_sol.columns.str.strip()
                df_sol['DNI'] = df_sol['DNI'].astype(str).str.strip().str.replace('.0', '', regex=False)
                dni_usuario = str(user['DNI']).split('.')[0]
                mis_sol = df_sol[df_sol['DNI'] == dni_usuario]
                dias_usados = mis_sol['Dias_Habiles'].sum()
            except:
                dias_usados = 0

        remanente_actual = float(user['Dias_Totales']) - dias_usados
        st.metric("Días Disponibles Hoy", f"{int(remanente_actual)}")

        f_inicio = st.date_input("Fecha Inicio", min_value=date(2025, 12, 1), format="DD/MM/YYYY")
        f_fin = st.date_input("Fecha Fin", min_value=f_inicio, format="DD/MM/YYYY")
        
        cantidad_dias_total = (f_fin - f_inicio).days + 1
        dias_habiles_lista = [f_inicio + timedelta(days=i) for i in range(cantidad_dias_total) if (f_inicio + timedelta(days=i)).weekday() < 5 and (f_inicio + timedelta(days=i)) not in lista_feriados]
        dias_pedidos = len(dias_habiles_lista)
        nuevo_remanente = remanente_actual - dias_pedidos

        if dias_pedidos > 0:
            st.info(f"🧾 Días a solicitar: **{dias_pedidos}** | Saldo restante: **{int(nuevo_remanente)}**")
            
            if nuevo_remanente >= 0:
                confirmar = st.checkbox("Confirmo que las fechas son correctas.")
                if confirmar:
                    if st.button("🚀 ENVIAR SOLICITUD Y GUARDAR"):
                        dni_limpio = str(user['DNI']).split('.')[0]
                        payload = {
                            "dni": dni_limpio,
                            "nombre": user['Nombre'],
                            "inicio": f_inicio.strftime('%d/%m/%Y'),
                            "fin": f_fin.strftime('%d/%m/%Y'),
                            "dias": dias_pedidos
                        }
                        
                        with st.spinner('Guardando en base de datos y enviando mail...'):
                            try:
                                response = requests.post(URL_MACRO, json=payload)
                                if response.status_code == 200:
                                    st.success("✅ ¡Registrado en el Excel con éxito!")
                                    hoy = datetime.now()
                                    nota = f"SALTA, {hoy.day}/{hoy.month}/{hoy.year}\n\nSr. Subsecretario del Parque Automotor\nRicardo Velarde Figueroa\nS__________/__________D\n\nTengo el agrado de dirigirme a Usted, a fin de solicitar autorización para hacer uso de mi Licencia Anual Reglamentaria — L.A.R., correspondiente al período 2025-2026, por la cantidad de {dias_pedidos} días hábiles, a partir del día {f_inicio.strftime('%d/%m/%Y')} y hasta el día {f_fin.strftime('%d/%m/%Y')}, inclusive.\n\nFirma: _______________________________\nApellido y Nombre: {user['Nombre']}\nD.N.I.: {dni_limpio}"
                                    st.text_area("Copia para imprimir:", nota, height=400)
                                    enviar_correo("rrhhparqueautomotor@gmail.com", f"SOLICITUD LAR: {user['Nombre']}", nota)
                                else:
                                    st.error("Error al guardar en el servidor de Google.")
                            except:
                                st.error("Error de conexión al guardar.")

    if st.sidebar.button("Cerrar Sesión"):
        del st.session_state.auth
        st.rerun()
