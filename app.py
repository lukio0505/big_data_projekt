import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import numpy as np

# Konfiguracja strony
st.set_page_config(page_title="Dashboard Pogodowy", layout="wide", page_icon="🌤️")

# Nagłówek aplikacji
st.title("🌤️ Analiza Pogody w Polskich Miastach (2023)")
st.markdown("""
<style>
    .st-emotion-cache-1v0mbdj > img {
        border-radius: 10px;
    }
</style>
Aplikacja pobiera rzeczywiste dane z darmowego API Open-Meteo, czyści je i wizualizuje. 
Skorzystaj z panelu bocznego, aby dostosować analizę.
""", unsafe_allow_html=True)


# --- 1. POZYSKANIE DANYCH (Z PAMIĘCIĄ PODRĘCZNĄ) ---
@st.cache_data
def load_weather_data():
    cities = {
        "Warszawa": {"lat": 52.2297, "lon": 21.0122},
        "Kraków": {"lat": 50.0614, "lon": 19.9366},
        "Gdańsk": {"lat": 54.3520, "lon": 18.6466},
        "Wrocław": {"lat": 51.1079, "lon": 17.0385},
        "Poznań": {"lat": 52.4064, "lon": 16.9252}
    }

    all_data = []
    for city, coords in cities.items():
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={coords['lat']}&longitude={coords['lon']}&start_date=2023-01-01&end_date=2023-12-31&daily=temperature_2m_mean,precipitation_sum,wind_speed_10m_max&timezone=Europe%2FWarsaw"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data['daily'])
            df['Miasto'] = city
            df['Szerokość'] = coords['lat']
            df['Długość'] = coords['lon']
            all_data.append(df)

    return pd.concat(all_data, ignore_index=True)


# --- 2. CZYSZCZENIE I PRZYGOTOWANIE DANYCH ---
def clean_data(df):
    df = df.rename(columns={
        "time": "Data",
        "temperature_2m_mean": "Średnia_Temp_C",
        "precipitation_sum": "Suma_Opadów_mm",
        "wind_speed_10m_max": "Max_Wiatr_kmh"
    })

    df['Data'] = pd.to_datetime(df['Data'])
    df['Średnia_Temp_C'] = df['Średnia_Temp_C'].fillna(df['Średnia_Temp_C'].median())
    df['Suma_Opadów_mm'] = df['Suma_Opadów_mm'].fillna(0.0)

    # Mapowanie numerów miesięcy na polskie nazwy
    miesiace = {
        1: 'Styczeń', 2: 'Luty', 3: 'Marzec', 4: 'Kwiecień',
        5: 'Maj', 6: 'Czerwiec', 7: 'Lipiec', 8: 'Sierpień',
        9: 'Wrzesień', 10: 'Październik', 11: 'Listopad', 12: 'Grudzień'
    }
    df['Miesiąc_Liczba'] = df['Data'].dt.month
    df['Miesiąc'] = df['Miesiąc_Liczba'].map(miesiace)

    df['Typ_Dnia'] = np.where(df['Suma_Opadów_mm'] > 0, '🌧️ Deszczowy', '☀️ Suchy')
    return df


raw_data = load_weather_data()
df = clean_data(raw_data)

# --- 3. WIDGETY I FILTRY (SIDEBAR) ---
# --- 3. WIDGETY I FILTRY (SIDEBAR) ---
st.sidebar.header("⚙️ Ustawienia filtrów")

# 1. Kalendarz na samej górze (żeby miał miejsce rozwinąć się w dół)
min_date = df['Data'].min().date()
max_date = df['Data'].max().date()
date_range = st.sidebar.date_input(
    "📅 Wybierz zakres dat:",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# 2. Wybór miast (Multiselect)
selected_cities = st.sidebar.multiselect(
    "📍 Wybierz miasta:",
    options=df['Miasto'].unique(),
    default=["Warszawa", "Kraków", "Gdańsk"]
)

# 3. Zmieniony trzeci widget (Selectbox zamiast bezsensownego slidera)
weather_type = st.sidebar.selectbox(
    "🌤️ Rodzaj pogody:",
    options=["Wszystkie dni", "Tylko deszczowe (🌧️)", "Tylko suche (☀️)"]
)

# Aplikacja filtrów na DataFrame
if len(date_range) == 2:
    start_date, end_date = date_range

    # Krok 1: Filtrowanie po datach i miastach
    filtered_df = df[
        (df['Miasto'].isin(selected_cities)) &
        (df['Data'].dt.date >= start_date) &
        (df['Data'].dt.date <= end_date)
        ]

    # Krok 2: Filtrowanie po rodzaju pogody
    if weather_type == "Tylko deszczowe (🌧️)":
        filtered_df = filtered_df[filtered_df['Suma_Opadów_mm'] > 0]
    elif weather_type == "Tylko suche (☀️)":
        filtered_df = filtered_df[filtered_df['Suma_Opadów_mm'] == 0]

else:
    filtered_df = df.copy()

# Zabezpieczenie przed pustym DataFrame
if filtered_df.empty:
    st.warning("⚠️ Brak danych dla wybranych filtrów. Zmień parametry w panelu bocznym.")
    st.stop()
# --- 4. KPI (METRYKI) ---
st.subheader("📊 Podsumowanie statystyk")
col1, col2, col3 = st.columns(3)

with col1:
    avg_temp = filtered_df['Średnia_Temp_C'].mean()
    st.metric("🌡️ Średnia Temperatura", f"{avg_temp:.1f} °C")

with col2:
    total_rain = filtered_df['Suma_Opadów_mm'].sum()
    st.metric("🌧️ Całkowity Opad", f"{total_rain:.1f} mm")

with col3:
    max_wind = filtered_df['Max_Wiatr_kmh'].max()
    st.metric("💨 Najsilniejszy Wiatr", f"{max_wind:.1f} km/h")

st.markdown("---")

# --- 5. WIZUALIZACJE ---
tab1, tab2, tab3 = st.tabs(["📈 Trendy w Czasie", "🔍 Zależności i Rozkłady", "🗺️ Mapa Stacji"])

with tab1:
    st.subheader("Zmiana temperatury w czasie")
    fig_line = px.line(
        filtered_df, x="Data", y="Średnia_Temp_C", color="Miasto",
        labels={"Średnia_Temp_C": "Średnia Temp. (°C)", "Data": "Data pomiaru"}
    )
    # Ładniejszy hover dla wykresu liniowego
    fig_line.update_traces(mode="lines",
                           hovertemplate="<b>%{fullData.name}</b><br>Data: %{x}<br>Temperatura: %{y:.1f} °C<extra></extra>")
    fig_line.update_layout(hovermode="x unified", legend_title_text="Miasto")
    st.plotly_chart(fig_line, use_container_width=True)

    st.subheader("Suma opadów według miesięcy")
    # Grupowanie (wymaga sortowania, żeby miesiące nie pomieszały się alfabetycznie)
    monthly_rain = filtered_df.groupby(['Miesiąc_Liczba', 'Miesiąc', 'Miasto'])['Suma_Opadów_mm'].sum().reset_index()
    monthly_rain = monthly_rain.sort_values(by="Miesiąc_Liczba")

    fig_bar = px.bar(
        monthly_rain, x="Miesiąc", y="Suma_Opadów_mm", color="Miasto",
        barmode="group",
        labels={"Suma_Opadów_mm": "Suma opadów (mm)", "Miesiąc": "Miesiąc"}
    )
    # Ładniejszy hover dla wykresu słupkowego (rozwiązuje problem ze zdjęcia!)
    fig_bar.update_traces(hovertemplate="<b>%{fullData.name}</b><br>Miesiąc: %{x}<br>Opad: %{y:.1f} mm<extra></extra>")
    fig_bar.update_layout(legend_title_text="Miasto", xaxis_title="")
    st.plotly_chart(fig_bar, use_container_width=True)

with tab2:
    st.subheader("Zależność między wiatrem a temperaturą")
    fig_scatter = px.scatter(
        filtered_df, x="Średnia_Temp_C", y="Max_Wiatr_kmh",
        color="Typ_Dnia", hover_data={"Data": True, "Miasto": True, "Typ_Dnia": False},
        labels={"Średnia_Temp_C": "Temperatura (°C)", "Max_Wiatr_kmh": "Max Wiatr (km/h)", "Typ_Dnia": "Rodzaj pogody"}
    )
    # Formatowanie dymka
    fig_scatter.update_traces(
        hovertemplate="<b>%{customdata[1]}</b><br>Data: %{customdata[0]|%Y-%m-%d}<br>Temp: %{x:.1f} °C<br>Wiatr: %{y:.1f} km/h<extra></extra>")
    fig_scatter.update_layout(legend_title_text="Pogoda")
    st.plotly_chart(fig_scatter, use_container_width=True)

    st.subheader("Rozkład temperatur w wybranym okresie")
    fig_hist = px.histogram(
        filtered_df, x="Średnia_Temp_C", nbins=30, color="Miasto",
        opacity=0.7, barmode="overlay",
        labels={"Średnia_Temp_C": "Temperatura (°C)", "count": "Liczba dni"}
    )
    fig_hist.update_traces(hovertemplate="Temperatura: %{x} °C<br>Liczba dni: %{y}<extra></extra>")
    fig_hist.update_layout(yaxis_title="Liczba dni", legend_title_text="Miasto")
    st.plotly_chart(fig_hist, use_container_width=True)

with tab3:
    st.subheader("Lokalizacja analizowanych miast")
    map_data = filtered_df[['Szerokość', 'Długość', 'Miasto']].drop_duplicates()
    map_data = map_data.rename(columns={"Szerokość": "lat", "Długość": "lon"})

    # Dodajemy proste markery na mapie z podpisami miast
    st.map(map_data, size=5000, color="#0044ff")
    st.caption("Powyższa mapa wskazuje współrzędne stacji pomiarowych dla wybranych miast.")