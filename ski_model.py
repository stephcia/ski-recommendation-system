import streamlit as st
import pandas as pd
import numpy as np
import joblib
import seaborn as sns

from PIL import Image

st.title('Avant Ski')
st.header('Shred faster with Avant Ski')

st.sidebar.title('Sidebar')
side_button = st.sidebar.button('Press Me!')
if side_button:
    st.sidebar.write('Sidebar button was pressed')