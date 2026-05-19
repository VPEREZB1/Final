import streamlit as st
import pandas as pd
import time
from influxdb_client import InfluxDBClient

# --- CONFIGURACIÓN ESTÉTICA DE LA INTERFAZ ---
st.set_page_config(page_title="CargoGuard IoT", page_icon="📦", layout="wide")

st.title("📦 CargoGuard: Monitoreo Activo de Carga Crítica")
st.markdown("Plataforma interactiva para el control de la cadena de frío, orientación y picos de vibración.")
st.write("---")

# --- PARÁMETROS DE CONEXIÓN PROVISTOS ---
URL = "https://us-east-1-1.aws.cloud2.influxdata.com"
TOKEN = "JoKdx3OFaBCFPmYQgiVWE8hjrtJ0lDkjwWZzT9djWJlvg98rtTgF9iRgKhQtAkKIA2UQsU6zsrJlv1BH6lfsVw=="
ORG = "miguelcmo"
BUCKET = "iot_telemetry_data"

# Inicializar cliente de InfluxDB
client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
query_api = client.query_api()

# --- FUNCIONES DE CONSULTA (FLUX) ---
def obtener_datos_clima():
    """Trae datos de temperatura y humedad de la última hora"""
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
    """Trae datos de acelerómetro de los últimos 30 minutos"""
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

# --- CONTENEDOR DINÁMICO ---
dashboard_placeholder = st.empty()

# Ciclo infinito para simular refresco en tiempo real
while True:
    df_clima = obtener_datos_clima()
    df_mov = obtener_datos_movimiento()
    
    with dashboard_placeholder.container():
        # Validar que tengamos datos en ambas mediciones
        if not df_clima.empty and not df_mov.empty:
            
            # Procesar datos de clima
            df_clima['_time'] = pd.to_datetime(df_clima['_time'])
            df_clima = df_clima.sort_values('_time')
            ultimo_clima = df_clima.iloc[-1]
            
            temp = ultimo_clima.get('temperature', 0.0)
            hum = ultimo_clima.get('humidity', 0.0)
            
            # Procesar datos de movimiento
            df_mov['_time'] = pd.to_datetime(df_mov['_time'])
            df_mov = df_mov.sort_values('_time')
            ultimo_mov = df_mov.iloc[-1]
            
            ax = ultimo_mov.get('accel_x', 0.0)
            ay = ultimo_mov.get('accel_y', 0.0)
            az = ultimo_mov.get('accel_z', 1.0)
            
            # --- SECCIÓN 1: ALERTAS EN TIEMPO REAL ---
            st.subheader("⚠️ Centro de Notificaciones y Alertas")
            col_a1, col_a2 = st.columns(2)
            
            with col_a1:
                # Alerta lógica para cadena de frío (Ejemplo: Alimentos o vacunas)
                if temp > 24.0 or temp < 15.0: 
                    st.error(f"🚨 CRÍTICO: Temperatura fuera de rango operacional ({temp:.1f}°C)")
                else:
                    st.success("✅ Ambiente óptimo controlado.")
                    
            with col_a2:
                # Detección de picos de vibración o inclinación severa
                if abs(ax) > 1.5 or abs(ay) > 1.5:
                    st.error("🚨 ALERTA: Movimiento brusco o posible vuelco detectado.")
                else:
                    st.success("✅ Estabilidad de carga correcta.")
            
            st.write("---")
            
            # --- SECCIÓN 2: TARJETAS DE INDICADORES (KPIs) ---
            st.subheader("📊 Variables Actuales")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric(label="Temperatura", value=f"{temp:.1f} °C")
            kpi2.metric(label="Humedad Relativa", value=f"{hum:.1f} %")
            kpi3.metric(label="Aceleración X", value=f"{ax:.2f} g")
            kpi4.metric(label="Aceleración Y", value=f"{ay:.2f} g")
            
            st.write("---")
            
            # --- SECCIÓN 3: GRÁFICAS DE TENDENCIAS ---
            st.subheader("📈 Análisis de Series de Tiempo")
            graf1, graf2 = st.columns(2)
            
            with graf1:
                st.markdown("**Historial Climatológico (Última Hora)**")
                chart_clima = df_clima.set_index('_time')[['temperature', 'humidity']]
                st.line_chart(chart_clima)
                
            with graf2:
                st.markdown("**Dinámica de Impactos y Movimiento (Últimos 30m)**")
                chart_mov = df_mov.set_index('_time')[['accel_x', 'accel_y', 'accel_z']]
                st.line_chart(chart_mov)
                
        else:
            st.warning("Conectando con el clúster de AWS InfluxDB... Verificando flujo de datos.")
            
    # Intervalo de actualización del dashboard
    time.sleep(3)
