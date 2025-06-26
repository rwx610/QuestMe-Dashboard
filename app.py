import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Пример данных
data = {
    "2025-06-18": 20,
    "2025-06-19": 40,
    "2025-06-20": 70,
}
df = pd.DataFrame(data.items(), columns=["Date", "Mint Volume"])

# Заголовок
st.title("📊 TON Mint Dashboard")

# График
st.bar_chart(df.set_index("Date"))