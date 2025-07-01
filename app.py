import streamlit as st
from utils.storage import init_db
from scheduler import start as start_scheduler


init_db()
start_scheduler()  # запускает фоновые обновления при первом заходе на дашборд

st.title("Base / TON Dashboard")
# остальная логика Streamlit
