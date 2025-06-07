import streamlit as st

st.title("🎈 My new app")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)
pg = st.navigation([
    st.Page("image_tagger.py",title="Image Tagger",icon='💎')
])
pg.run()