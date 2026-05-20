import streamlit as st
import pandas as pd
import time
from influxdb_client import InfluxDBClient

# --- 1. CONFIGURACIÓN ESTÉTICA DE LA INTERFAZ ---
st.set_page_config(page_title="Vibration Monitor IoT", page_icon="🏭", layout="wide")

st.title("🏭Sistema de Monitoreo de Vibración y Temperatura Industrial")
st.markdown("Plataforma analítica para la prevención de fallas mecánicas y sobrecalentamiento de motores en tiempo real.")
st.write("---")

# --- 2. PARÁMETROS DE CONEXIÓN DE INFLUXDB (PROVISTOS) ---
URL = "https://us-east-1-1.aws.cloud2.influxdata.com"
TOKEN = "JoKdx3OFaBCFPmYQgiVWE8hjrtJ0lDkjwWZzT9djWJlvg98rtTgF9iRgKhQtAkKIA2UQsU6zsrJlv1BH6lfsVw=="
ORG = "miguelcmo"
BUCKET = "iot_telemetry_data"

# Inicializar cliente oficial de InfluxDB
client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
query_api = client.query_api()

# --- 3. FUNCIONES DE EXTRACCIÓN MEDIANTE CONSULTAS FLUX ---
def obtener_datos_clima():
    """Consulta datos de temperatura y humedad ambientales del DHT22"""
    query = f'''
    from(bucket: "{BUCKET}")
      |> range(start: -1h)
      |> filter(fn: (r) => r._measurement == "environment")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    try:
        df = query_api.query_data_frame(query)
        if isinstance(df, list):
            df = pd.concat(df)
        return df
    except Exception:
        return pd.DataFrame()

def obtener_datos_movimiento():
    """Consulta datos de vibración y aceleración del MPU6050"""
    query = f'''
    from(bucket: "{BUCKET}")
      |> range(start: -30m)
      |> filter(fn: (r) => r._measurement == "mpu6050")
      |> filter(fn: (r) => r._field == "accel_x" or r._field == "accel_y" or r._field == "accel_z")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    try:
        df = query_api.query_data_frame(query)
        if isinstance(df, list):
            df = pd.concat(df)
        return df
    except Exception:
        return pd.DataFrame()

# --- 4. CONTENEDOR DINÁMICO Y CICLO DE REFRESCO ---
dashboard_placeholder = st.empty()

while True:
    df_clima = obtener_datos_clima()
    df_mov = obtener_datos_movimiento()
    
    with dashboard_placeholder.container():
        if not df_clima.empty and not df_mov.empty:
            
            # Normalización y orden cronológico (DHT22)
            df_clima['_time'] = pd.to_datetime(df_clima['_time'])
            df_clima = df_clima.sort_values('_time')
            ultimo_clima = df_clima.iloc[-1]
            
            temp = ultimo_clima.get('temperature', 0.0)
            hum = ultimo_clima.get('humidity', 0.0)
            
            # Normalización y orden cronológico (MPU6050)
            df_mov['_time'] = pd.to_datetime(df_mov['_time'])
            df_mov = df_mov.sort_values('_time')
            ultimo_mov = df_mov.iloc[-1]
            
            ax = ultimo_mov.get('accel_x', 0.0)
            ay = ultimo_mov.get('accel_y', 0.0)
            az = ultimo_mov.get('accel_z', 1.0)
            
            # --- INDICADORES: ALERTA LÓGICA ---
            st.subheader("⚠️ Estado Operacional de la Maquinaria")
            col_a1, col_a2 = st.columns(2)
            
            with col_a1:
                if temp > 28.0: 
                    st.error(f"🚨 CRÍTICO: ¡Sobrecalentamiento del motor! ({temp:.1f}°C)")
                else:
                    st.success("✅ Temperatura térmica estable.")
                    
            with col_a2:
                if abs(ax) > 1.5 or abs(ay) > 1.5:
                    st.error("🚨 ALERTA MECÁNICA: Vibración fuera de límites seguros.")
                else:
                    st.success("✅ Patrón de vibración correcto.")
            
            st.write("---")
            
            # --- TARJETAS MÉTRICAS (KPIs ACTUALES) ---
            st.subheader("📊 Telemetría Actual")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric(label="Temperatura Chasis", value=f"{temp:.1f} °C")
            kpi2.metric(label="Humedad Planta", value=f"{hum:.1f} %")
            kpi3.metric(label="Aceleración X", value=f"{ax:.2f} g")
            kpi4.metric(label="Aceleración Y", value=f"{ay:.2f} g")
            
            st.write("---")
            
            # ==============================================================
            # ESTA SECCIÓN CONTIENE EXACTAMENTE LAS 4 GRÁFICAS REQUERIDAS
            # ==============================================================
            st.subheader("📈 Paneles de Análisis Continuo (Series de Tiempo)")
            
            # FILA 1: Climatología de la Planta (Gráficos 1 y 2)
            fila1_col1, fila1_col2 = st.columns(2)
            
            with fila1_col1:
                st.markdown("**Gráfica 1: Historial de Temperatura del Motor (°C)**")
                chart_temp = df_clima.set_index('_time')[['temperature']]
                st.line_chart(chart_temp, color="#e53e3e") # Línea Roja para temperatura
                
            with fila1_col2:
                st.markdown("**Gráfica 2: Historial de Humedad Relativa (%)**")
                chart_hum = df_clima.set_index('_time')[['humidity']]
                st.line_chart(chart_hum, color="#3182ce") # Línea Azul para humedad
                
            # FILA 2: Dinámica Mecánica de Vibración (Gráficos 3 y 4)
            fila2_col1, fila2_col2 = st.columns(2)
            
            with fila2_col1:
                st.markdown("**Gráfica 3: Desplazamiento Transversal (Ejes X / Y)**")
                chart_planos = df_mov.set_index('_time')[['accel_x', 'accel_y']]
                st.line_chart(chart_planos)
                
            with fila2_col2:
                st.markdown("**Gráfica 4: Impacto Vertical de Fuerza G (Eje Z)**")
                chart_z = df_mov.set_index('_time')[['accel_z']]
                st.line_chart(chart_z, color="#319795") # Línea verde/teal para el eje Z
                
        else:
            st.warning("Enlazando con el nodo central de InfluxDB en AWS... Cargando datos industriales.")
            
    # Tiempo de refresco del dashboard
    time.sleep(3)
