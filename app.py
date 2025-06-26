import streamlit as st
from scheduler import start as start_scheduler

start_scheduler()  # запускает фоновые обновления при первом заходе на дашборд

st.title("Base / TON Dashboard")
# остальная логика Streamlit
