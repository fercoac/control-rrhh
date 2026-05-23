import streamlit as st
import pandas as pd
from datetime import datetime, date
import smtplib
from email.mime.text import MIMEText
from streamlit_gsheets import GSheetsConnection
import numpy as np

# Configuración de la página
st.set_page_config(page_title="RRHH - Parque Automotor", layout="centered")

# Conexión mejorada a Google Sheets
try:
    # Usamos ttl=0 para que no guarde datos viejos y lea siempre lo último
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error técnico de conexión: {e}")

def enviar_correo(destinatario, asunto, cuerpo):
    remitente = "rrhhparqueautomotor@gmail.com"
    # Recuerda poner aquí tu clave de 16 letras de Gmail
    password = "TU_CONTRASEÑA_DE_APLICACION" 
    
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
        st.warning(f"La solicitud se guardó pero no se pudo enviar el mail: {e}")

# --- LOGIN ---
if 'auth' not in st.session_state:
    st.title("🔐 Control de Ingresos")
    dni_input = st.text_input("DNI")
    pin_input = st.text_input("Clave de 4 dígitos", type="password")
    
    if st.button("Ingresar"):
        try:
            # Leemos la pestaña Empleados
            df_emp = conn.read(worksheet="Empleados", ttl=0)
            
            # Limpiamos los datos por si hay espacios en blanco
            df_emp['DNI'] = df_emp['DNI'].astype(str).str.strip()
            df_emp['PIN'] = df_emp['PIN'].astype(str).str.strip()
            
            # Buscamos al usuario
            user_row = df_emp[(df_emp['DNI'] == str(dni_input).strip()) & (df_emp['PIN'] == str(pin_input).strip())]
            
            if not user_row.empty:
                st.session_state.auth = True
                st.session_state.user = user_row.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("DNI o Clave incorrectos. Revisa tu PIN en el Excel.")
        except Exception as e:
            # ESTO NOS DIRÁ EL ERROR REAL EN PANTALLA
            st.error(f"Error al leer Google Sheets: {e}")

# --- PANEL PRINCIPAL ---
else:
    user = st.session_state.user
    st.sidebar.title(f"Hola, {user['Nombre']}")
    opcion = st.sidebar.radio("Menú", ["Mis Marcas", "Solicitar Vacaciones"])

    # SECCIÓN MARCAS
    if opcion == "Mis Marcas":
        st.header("📋 Mis Registros")
        try:
            df_marcas = conn.read(worksheet="Marcas", ttl=0)
            # Filtrar por ID de reloj
            id_usuario = str(user['ID_Biometrico']).split('.')[0] # Por si viene como 10.0
            mis_marcas = df_marcas[df_marcas['ID'].astype(str).str.contains(id_usuario)]
            
            if not mis_marcas.empty:
                st.dataframe(mis_marcas[['Fecha', 'Hora', 'Evento']], use_container_width=True)
            else:
                st.info("No se encontraron marcas para tu ID.")
        except Exception as e:
            st.info(f"Todavía no hay datos en la pestaña Marcas o el formato es incorrecto.")

    # SECCIÓN VACACIONES
    elif opcion == "Solicitar Vacaciones":
        st.header("🏖️ Solicitud de Licencia (L.A.R.)")
        
        try:
            df_sol = conn.read(worksheet="Solicitudes", ttl=0)
            mis_sol = df_sol[df_sol['DNI'].astype(str) == str(user['DNI'])]
            dias_usados = mis_sol['Dias_Habiles'].sum()
        except:
            dias_usados = 0
            mis_sol = pd.DataFrame()
        
        remanente = float(user['Dias_Totales']) - dias_usados
        partes_pedidas = len(mis_sol)

        col1, col2 = st.columns(2)
        col1.metric("Días Disponibles", f"{remanente}")
        col2.metric("Partes Usadas", f"{partes_pedidas} / 2")

        if partes_pedidas < 2 and remanente > 0:
            with st.form("form_vac"):
                f_inicio = st.date_input("Fecha de Inicio", min_value=date(2025, 12, 1))
                f_fin = st.date_input("Fecha de Fin", min_value=f_inicio)
                
                if st.form_submit_button("Generar Solicitud"):
                    rango = pd.bdate_range(start=f_inicio, end=f_fin)
                    dias_pedidos = len(rango)

                    if dias_pedidos <= remanente:
                        # Nota formal
                        fecha_hoy = datetime.now().strftime("%d/%m/%Y")
                        nota = f"""
SALTA, {fecha_hoy}

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
                        st.text_area("Copia este texto para imprimir:", nota, height=350)
                        enviar_correo("rrhhparqueautomotor@gmail.com", f"Pedido LAR: {user['Nombre']}", f"Solicitud de {dias_pedidos} días.")
                    else:
                        st.error(f"No tienes días suficientes (te quedan {remanente}).")
        else:
            st.warning("No puedes solicitar más días o ya completaste las 2 partes.")

    if st.sidebar.button("Cerrar Sesión"):
        del st.session_state.auth
        st.rerun()
