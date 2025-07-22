import streamlit as st
st.set_page_config(page_title="Image Tagging Interface", layout="wide")

pg = st.navigation([
    st.Page("home.py",title="Home"),
    # st.Page("image_tagger.py",title="Image Tagger",icon='💎'),
    st.Page("test_ab_tester.py", title="A or B?", icon = '💎'),
    st.Page("gallery.py", title = "Image Gallery"),
    st.Page("final_rating.py", title = "Final Rating", icon = '⭐')
])
pg.run()