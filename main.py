import streamlit as st 
uploaded_file = st.file_uploader("Choose a pdf file")
key = st.text_input("enter key")
name=st.text_input("enter csv name")


tab1, tab2,tab3 = st.tabs(["Dashboard", "Analysis", "Raw Data"])

