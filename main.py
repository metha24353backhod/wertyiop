import streamlit as st 
file_upload=uploaded_file = st.file_uploader("Choose a pdf file")
key = st.text_input("enter key")
name=st.text_input("enter csv name")


tab1, tab2,tab3 = st.tabs(["Dashboard", "Analysis", "Raw Data"])
with tab1:
  if file_upload:
    from pdf2image import convert_from_path,convert_from_bytes
    import os

    pdf_path = file_upload
    pdf_bytes = file_upload.getvalue()

    folder_page1 = "page1"
    folder_images = "images"

    os.makedirs(folder_page1, exist_ok=True)
    os.makedirs(folder_images, exist_ok=True)

    pages =  convert_from_bytes(pdf_bytes, dpi=300)
    total = len(pages)

    st.write(total)

    for i, page in enumerate(pages, start=1):

    # ❌ Skip last page
      if i == total:
        print(f"[SKIPPED LAST PAGE] Page {i}")
        continue

    # Page 1 → separate folder
      if i == 1:
        out = f"{folder_page1}/page_1.png"
        page.save(out, "PNG")
        print(f"[PAGE 1 SAVED] {out}")
        continue

    # Pages 2 to n-1 → /content/images
      out = f"{folder_images}/page{i}.png"
      page.save(out, "PNG")
      st.write(os.listdir(folder_images))

