import streamlit as st
from pdf2image import convert_from_bytes
from PIL import Image
import io
import zipfile
import os

# App title
st.title("PDF to Images (in ZIP file)")

# Tabs for app organization
tab1, tab2, tab3 = st.tabs(["Dashboard", "Analysis", "Raw Data"])

with tab1:
    st.header("Upload and Process PDF")
    
    # File uploader is now inside tab1
    file_upload = st.file_uploader("Choose a pdf file", type="pdf")

    if file_upload:
        st.info("Converting PDF to images...")
        try:
            # Read the uploaded file as bytes
            pdf_bytes = file_upload.getvalue()

            # Convert PDF pages to PIL Image objects in memory
            pages = convert_from_bytes(pdf_bytes, dpi=300)
            total = len(pages)
            st.write(f"Total pages converted: {total}")

            # Create an in-memory byte buffer for the zip file
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED, False) as zip_file:
                for i, page in enumerate(pages, start=1):
                    # Skip the last page as requested
                    if i == total:
                        st.write(f"Skipping last page: {i}")
                        continue

                    # Create an in-memory buffer for the current image
                    img_buffer = io.BytesIO()
                    page.save(img_buffer, "PNG")
                    img_buffer.seek(0)

                    # Add the image to the zip file with the correct path
                    if i == 1:
                        # Page 1 goes into the 'super_img' folder as 'image1.png'
                        zip_file.writestr(f"super_img/image1.png", img_buffer.read())
                    else:
                        # Other pages go into the 'super_img/images' folder
                        zip_file.writestr(f"super_img/images/page{i}.png", img_buffer.read())

            # Seek back to the start of the buffer for reading
            zip_buffer.seek(0)

            # Provide a single download button for the generated zip file
            st.success("Images have been processed into a ZIP file.")
            st.download_button(
                label="Download all images as ZIP",
                data=zip_buffer,
                file_name="super_img.zip",
                mime="application/zip"
            )
            
        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.error("Make sure you have `poppler-utils` installed in your deployment environment via `packages.txt`.")

with tab2:
    st.header("Analysis (Placeholder)")
    st.info("The logic for analysis will go here.")

with tab3:
    st.header("Raw Data (Placeholder)")
    st.info("Displaying raw data will go here.")
