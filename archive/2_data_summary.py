import streamlist as st
import pandas as pd
import plotly.graph_objects as go


st.title('Ski Resort Data Summary')
st.image('images/whistler.png'), use_column_width='always'

@st.cache_data
def load_data(path):
    data = pd.read_csv(path, index.col=0)
    return data

resort_data = load_data('data/modeling/final_content_df.csv')
user_data = load_data('data/modeling/collaborative_surprise_df.csv')
                        