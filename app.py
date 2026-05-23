import streamlit as st
import pandas as pd
from datetime import datetime, date
import smtplib
from email.mime.text import MIMEText
from streamlit_gsheets import GSheetsConnection
import numpy as np

# Configuración de la página para celulares
st.set_page_config(page_title="RRHH - Parque Automotor", layout="centered")

# Conexión a Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("Error de conexión. Verifica los 'Secrets' en Streamlit.")

def enviar_correo(destinatario, asunto, cuerpo):
    remitente = "rrhhparqueautomotor@gmail.com"
    # IMPORTANTE: Aquí pondrás tu clave de 16 letras de Google
    password = "uwqiaqcuovcjejuk" 
    
    msg = MIMEText(cuerpo)
    msg['Subject'] = asunto
    msg['From'] = remitente
    msg['To'] = destinatario

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(remitente, password)
        server.sendmail(remitente, destinatario, msg.as_string())
        server.quit()
    except Exception as e:
        st.error(f"No se pudo enviar el correo: {e}")

# --- LOGIN ---
if 'auth' not in st.session_state:
    st.title("🔐 Control de Ingresos")
    dni = st.text_input("DNI")
    pin = st.text_input("Clave de 4 dígitos", type="password")
    
    if st.button("Ingresar"):
        try:
            df_emp = conn.read(worksheet="Empleados")
            user_row = df_emp[(df_emp['DNI'].astype(str) == str(dni)) & (df_emp['PIN'].astype(str) == str(pin))]
            
            if not user_row.empty:
                st.session_state.auth = True
                st.session_state.user = user_row.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("DNI o Clave incorrectos.")
        except:
            st.error("No se pudo leer la base de datos de Google Sheets.")

# --- PANEL PRINCIPAL ---
else:
    user = st.session_state.user
    st.sidebar.title(f"Hola, {user['Nombre']}")
    opcion = st.sidebar.radio("Menú", ["Mis Marcas", "Solicitar Vacaciones"])

    if opcion == "Mis Marcas":
        st.header("📋 Mis Registros")
        try:
            df_marcas = conn.read(worksheet="Marcas")
            # Filtrar por el ID Biométrico del usuario
            mis_marcas = df_marcas[df_marcas['ID'].astype(str) == str(user['ID_Biometrico'])]
            if not mis_marcas.empty:
                st.dataframe(mis_marcas[['Fecha', 'Hora', 'Evento']], use_container_width=True)
            else:
                st.info("No tienes marcas registradas todavía.")
        except:
            st.info("Sube el archivo de marcas al Google Sheets para ver los datos.")

    elif opcion == "Solicitar Vacaciones":
        st.header("🏖️ Solicitud de Licencia (L.A.R.)")
        
        try:
            df_sol = conn.read(worksheet="Solicitudes")
            mis_sol = df_sol[df_sol['DNI'].astype(str) == str(user['DNI'])]
            dias_usados = mis_sol['Dias_Habiles'].sum()
        except:
            dias_usados = 0
            mis_sol = pd.DataFrame()
        
        remanente = user['Dias_Totales'] - dias_usados
        partes_pedidas = len(mis_sol)

        col1, col2 = st.columns(2)
        col1.metric("Días Disponibles", f"{remanente}")
        col2.metric("Partes Usadas", f"{partes_pedidas} / 2")

        if partes_pedidas < 2 and remanente > 0:
            with st.form("form_vac"):
                f_inicio = st.date_input("Fecha de Inicio", min_value=date(2025, 12, 1), max_value=date(2026, 11, 30))
                f_fin = st.date_input("Fecha de Fin", min_value=f_inicio, max_value=date(2026, 11, 30))
                
                if st.form_submit_button("Generar Solicitud"):
                    # Cálculo de días hábiles
                    rango = pd.bdate_range(start=f_inicio, end=f_fin)
                    dias_pedidos = len(rango)

                    if dias_pedidos <= remanente:
                        fecha_hoy = datetime.now().strftime("%d de %B")
                        # (Opcional) Traducción de meses aquí...
                        
                        nota = f"""
SALTA, {fecha_hoy} de 2026

Sr. Subsecretario del Parque Automotor
Ricardo Velarde Figueroa
S__________/__________D

Tengo el agrado de dirigirme a Usted, a fin de solicitar autorización para hacer uso de mi Licencia Anual Reglamentaria — L.A.R., correspondiente al período 2025-2026, por la cantidad de {dias_pedidos} días hábiles, a partir del día {f_inicio.strftime('%d/%m/%Y')} y hasta el día {f_fin.strftime('%d/%m/%Y')}, inclusive.

Firma: _______________________________
Apellido y Nombre: {user['Nombre']}
D.N.I.: {user['DNI']}
Teléfono: {user['Telefono']}
                        """
                        st.success("✅ Solicitud lista.")
                        st.text_area("Copia y pega este texto para imprimir:", nota, height=350)
                        
                        # Notificar por mail
                        enviar_correo("rrhhparqueautomotor@gmail.com", 
                                      f"Pedido de LAR: {user['Nombre']}", 
                                      f"El empleado {user['Nombre']} solicita {dias_pedidos} días.")
                    else:
                        st.error(f"Solo te quedan {remanente} días.")
        else:
            st.warning("No puedes solicitar más días por ahora.")

    if st.sidebar.button("Salir"):
        del st.session_state.auth
        st.rerun()
