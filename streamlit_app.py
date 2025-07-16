import streamlit as st
st.set_page_config(page_title="Image Tagging Interface", layout="wide")

pg = st.navigation([
    st.Page("home.py",title="Home"),
    # st.Page("image_tagger.py",title="Image Tagger",icon='💎'),
    st.Page("ab_tester.py", title="Hot or Not?", icon = '🔥')
])
pg.run()