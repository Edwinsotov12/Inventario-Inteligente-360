import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO


st.set_page_config(
    page_title="Inventario Inteligente 360",
    page_icon="📦",
    layout="wide"
)


st.title("📦 INVENTARIO INTELIGENTE 360")
st.caption("Control de inventarios, compras y reducción de costos")


# Datos ficticios de demostración
demo = pd.DataFrame({
    "Producto": [
        "Arroz 500g", "Azúcar 1kg",
        "Aceite 900ml", "Leche 1L", "Papa kg"
    ],
    "Stock": [1200, 800, 150, 90, 100],
    "Venta_Diaria": [30, 25, 20, 15, 10],
    "Costo_Unitario": [2500, 3200, 8500, 3800, 4500]
})


st.sidebar.header("⚙️ Configuración")


archivo = st.sidebar.file_uploader(
    "Cargar inventario Excel",
    type=["xlsx"]
)


entrega = st.sidebar.slider(
    "Días de entrega", 1, 30, 5
)


seguridad = st.sidebar.slider(
    "Días de seguridad", 0, 20, 3
)


objetivo = st.sidebar.slider(
    "Cobertura objetivo", 1, 90, 30
)


costo_anual = st.sidebar.slider(
    "Costo anual de inventario (%)",
    5, 40, 20
)


if archivo:
    try:
        df = pd.read_excel(archivo)
    except Exception as e:
        st.error(f"No se pudo leer el Excel: {e}")
        st.stop()
else:
    df = demo.copy()
    st.info("Mostrando datos ficticios de demostración.")


# Validaciones
columnas = [
    "Producto", "Stock",
    "Venta_Diaria", "Costo_Unitario"
]


faltantes = [c for c in columnas if c not in df.columns]


if faltantes:
    st.error(f"Faltan columnas: {faltantes}")
    st.stop()


df = df[columnas].copy()


if df.empty:
    st.error("El archivo no contiene productos.")
    st.stop()


df["Producto"] = df["Producto"].astype("string").str.strip()


if df["Producto"].isna().any() or (df["Producto"] == "").any():
    st.error("Existen productos sin nombre.")
    st.stop()


if df["Producto"].duplicated().any():
    st.error("Hay productos duplicados. Revisa el Excel.")
    st.stop()


for col in ["Stock", "Venta_Diaria", "Costo_Unitario"]:
    try:
        df[col] = pd.to_numeric(df[col], errors="raise")
    except (ValueError, TypeError):
        st.error(f"La columna {col} contiene valores no numéricos.")
        st.stop()


    if df[col].isna().any() or (df[col] < 0).any():
        st.error(f"La columna {col} tiene datos vacíos o negativos.")
        st.stop()


# Análisis de inventarios
df["Valor_Inventario"] = (
    df["Stock"] * df["Costo_Unitario"]
)


df["Dias_Cobertura"] = (
    df["Stock"] /
    df["Venta_Diaria"].replace(0, float("nan"))
).round(1)


def diagnosticar(fila):
    if fila["Venta_Diaria"] == 0:
        return "SIN DEMANDA"
    if fila["Dias_Cobertura"] < 7:
        return "RIESGO"
    if fila["Dias_Cobertura"] > objetivo:
        return "EXCESO"
    return "NORMAL"


df["Estado"] = df.apply(diagnosticar, axis=1)


# Compras sugeridas
df["Punto_Pedido"] = (
    df["Venta_Diaria"] * (entrega + seguridad)
)


df["Stock_Objetivo"] = (
    df["Venta_Diaria"] * (entrega + objetivo)
)


df["Cantidad_Comprar"] = (
    df["Stock_Objetivo"] - df["Stock"]
).clip(lower=0)


df.loc[
    df["Stock"] > df["Punto_Pedido"],
    "Cantidad_Comprar"
] = 0


df["Inversion_Compra"] = (
    df["Cantidad_Comprar"] * df["Costo_Unitario"]
)


# Excesos y costos
df["Unidades_Exceso"] = (
    df["Stock"] - df["Venta_Diaria"] * objetivo
).clip(lower=0)


df["Capital_Exceso"] = (
    df["Unidades_Exceso"] * df["Costo_Unitario"]
)


df["Costo_Anual_Exceso"] = (
    df["Capital_Exceso"] * costo_anual / 100
)


# Indicadores
total = df["Valor_Inventario"].sum()
exceso = df["Capital_Exceso"].sum()
compras = df["Inversion_Compra"].sum()
costo = df["Costo_Anual_Exceso"].sum()


def pesos(valor):
    return f"${valor:,.0f}"


st.subheader("📊 Panel gerencial")


a, b, c, d = st.columns(4)


a.metric("Valor inventario", pesos(total))
b.metric("Capital en exceso", pesos(exceso))
c.metric("Compras sugeridas", pesos(compras))
d.metric("Costo anual del exceso", pesos(costo))


# Pestañas
tab1, tab2, tab3, tab4 = st.tabs([
    "📦 Inventarios",
    "🛒 Compras",
    "💰 Costos",
    "📈 Gerencia"
])


with tab1:
    st.subheader("Estado del inventario")
    st.dataframe(
        df[[
            "Producto", "Stock",
            "Valor_Inventario",
            "Dias_Cobertura", "Estado"
        ]],
        use_container_width=True,
        hide_index=True
    )


with tab2:
    st.subheader("Plan de compras")
    st.dataframe(
        df[[
            "Producto", "Stock",
            "Punto_Pedido",
            "Cantidad_Comprar",
            "Inversion_Compra"
        ]],
        use_container_width=True,
        hide_index=True
    )
    st.metric("Inversión sugerida", pesos(compras))


with tab3:
    st.subheader("Oportunidades de reducción de costos")
    st.dataframe(
        df[[
            "Producto", "Unidades_Exceso",
            "Capital_Exceso", "Costo_Anual_Exceso"
        ]],
        use_container_width=True,
        hide_index=True
    )


    st.warning(
        "El capital en exceso y su costo son estimaciones. "
        "No equivalen a ahorros realizados."
    )


with tab4:
    st.subheader("Análisis ejecutivo")


    fig = px.bar(
        df,
        x="Producto",
        y="Valor_Inventario",
        color="Estado",
        title="Valor del inventario por producto",
        color_discrete_map={
            "NORMAL": "#168653",
            "EXCESO": "#e4a33a",
            "RIESGO": "#d84a4a",
            "SIN DEMANDA": "#888888"
        }
    )
    st.plotly_chart(fig, use_container_width=True)


    fig2 = px.pie(
        df,
        names="Estado",
        title="Distribución del inventario por estado",
        hole=0.5
    )
    st.plotly_chart(fig2, use_container_width=True)


    st.subheader("Recomendaciones")


    for _, fila in df.iterrows():
        if fila["Estado"] == "EXCESO":
            st.warning(
                f"{fila['Producto']}: revisar exceso "
                f"de {fila['Unidades_Exceso']:,.0f} unidades."
            )
        elif fila["Estado"] == "RIESGO":
            st.error(
                f"{fila['Producto']}: revisar reposición."
            )
        elif fila["Estado"] == "SIN DEMANDA":
            st.info(
                f"{fila['Producto']}: verificar demanda "
                "y posible inventario sin movimiento."
            )


# Descargar informe Excel
buffer = BytesIO()


with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    df.to_excel(
        writer,
        sheet_name="Analisis_Inventario",
        index=False
    )


st.download_button(
    "📥 DESCARGAR INFORME EXCEL",
    data=buffer.getvalue(),
    file_name="Informe_Inventario_360.xlsx",
    mime=(
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    )
)


st.caption(
    "Inventario Inteligente 360 | "
    "Prototipo comercial con datos ficticios"
)
