import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
import google.generativeai as genai
from PIL import Image
import io
import zipfile
import csv
import os

# --- Configuration and Session State Initialization ---
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

if "csv_name" not in st.session_state:
    st.session_state.csv_name = ""

if "processed_images" not in st.session_state:
    st.session_state.processed_images = []

if "gemini_csv_outputs" not in st.session_state:
    st.session_state.gemini_csv_outputs = []

# --- Gemini Prompt ---
prompt_text = """
Extract all voter table data from the contextually provided image/PDF text (or any specific page indicated, e.g., Page 2 of the uploaded file).

Output MUST consist of ONLY the CSV data block. DO NOT include any conversational text, explanations, verification lines, or code wrappers.

I. Header Row Rules (8 Columns)
Heading Row: The first row must contain the table column headings translated into English: "Voter Serial No.","House No.","Voter Name","Relationship Code","Relative Name","Gender","Age","Photo ID No.".

Indexing: Remove all numerical indices (e.g., (1), (2)) from these English headings.

Column Count: The header must have exactly 8 column headings (which means exactly 7 commas).

Quotation: Every single field in the heading row MUST be enclosed in double quotes (").

II. Data Rows and Formatting Rules (8 Columns per Row)
Field Quotation: Every single field in the data rows MUST be enclosed in double quotes (").

Translation: Voter names must be in English transliteration. Gender and relationship fields must be translated into English (e.g., "Male", "Wife").

ID Format: For the Photo ID field, replace backslashes with forward slashes (e.g., "xyz/se/d/rt/drf").

Nulls: Use two double quotes with nothing between them ("") to represent any null or missing values.

Column Count: Each data row must have exactly 8 columns (which means exactly 7 commas).

III. Crucial Continuity and Data Integrity Rules
S. No. Range Determination: The extraction process MUST autonomously determine the full sequential range of Voter Serial Numbers (S. No.) present on the target page/image, starting at the lowest S. No. (e.g., "1") and ending at the highest S. No. (e.g., "275"). The final output MUST contain every S. No. within this detected range.

Pre-Execution Check and Record Continuity (Mandatory): Before finalizing the data block, re-check the resulting sequence of S. No.'s and the column details for every single record. The Voter Serial Number (S. No.) is the primary determinant of a row's existence and position.

Missing S. No. Record Gaps (Rule for Missing Rows - Double-Check): If a Voter Serial Number (S. No.) is missing from the sequential run between the detected start and end points (a gap):

Check: Re-read the source data specifically for this missing S. No.

If found upon re-check: Proceed to Rule 4 for partial data.

If NOT found upon re-check: The row must still be created and included in the correct sequential place. The S. No. will be included (e.g., "240"), and all other 7 columns will be filled with the null placeholder ("").

Partial Data (Rule for Missing Columns - Double-Check): If an S. No. is present in the source data, but any of the other 7 column details (House No., Name, Relationship Code, Relative Name, Gender, Age, or Photo ID No.) cannot be read or are missing:

Check: Re-read the source data specifically for the missing column detail(s).

If found upon re-check: Use the corrected value.

If NOT found upon re-check: The row for that S. No. must be created, and the missing column(s) MUST be filled with the null placeholder ("") to maintain exactly 8 columns per row.

IV. Noise Reduction Rule
Ensure there are NO empty lines, NO leading/trailing spaces, and NO other characters before the first quote (") or after the final quote on any data line.
"""

# --- Tab Functions ---
def convert_files_tab():
    st.header("1. Convert PDF to Images")
    file_upload = st.file_uploader("Upload a PDF file", type="pdf")

    if file_upload:
        st.info("Converting PDF pages to images...")
        try:
            pdf_bytes = file_upload.getvalue()
            pages = convert_from_bytes(pdf_bytes, dpi=300)
            
            # Store processed images in session state
            st.session_state.processed_images = pages
            total = len(pages)
            st.success(f"PDF successfully processed. Total pages: {total}")
            
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED, False) as zip_file:
                for i, page in enumerate(pages, start=1):
                    if i == total: # Skip last page
                        continue
                    
                    img_buffer = io.BytesIO()
                    page.save(img_buffer, "PNG")
                    img_buffer.seek(0)
                    
                    if i == 1:
                        zip_file.writestr("super_img/image1.png", img_buffer.read())
                    else:
                        zip_file.writestr(f"super_img/images/page{i}.png", img_buffer.read())
            zip_buffer.seek(0)
            
            st.download_button(
                label="Download Images as ZIP",
                data=zip_buffer,
                file_name="super_img.zip",
                mime="application/zip"
            )
            
        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.error("Ensure 'poppler-utils' is installed via packages.txt.")

def process_files_tab():
    st.header("2. Process Images with Gemini")
    
    # User input for Gemini key and CSV name
    api_key_input = st.text_input("Enter your Gemini API key", type="password")
    csv_name_input = st.text_input("Enter final CSV name", value="final_voter_output")

    st.markdown("---")
    st.info("You can either use images from Tab 1 or upload a ZIP file containing images.")
    
    zip_file_upload = st.file_uploader("Upload images as a ZIP file", type="zip")
    
    images_to_process = []

    # Get images from ZIP file if uploaded
    if zip_file_upload:
        st.write("Reading images from uploaded ZIP file...")
        try:
            with zipfile.ZipFile(zip_file_upload, "r") as zip_ref:
                for file_info in zip_ref.infolist():
                    file_name = file_info.filename
                    if file_name.endswith(".png") and not file_name.startswith("super_img/image1.png"):
                        with zip_ref.open(file_name) as file:
                            image_bytes = file.read()
                            image = Image.open(io.BytesIO(image_bytes))
                            images_to_process.append(image)
        except Exception as e:
            st.error(f"Error reading images from ZIP file: {e}")
            return
    # Or, get images from session state if processed in Tab 1
    elif st.session_state.processed_images:
        images_to_process = [img for i, img in enumerate(st.session_state.processed_images) if i > 0]
        
    st.write(f"Found {len(images_to_process)} images to process.")

    if st.button("Process Images"):
        if not api_key_input:
            st.warning("Please enter your Gemini API key.")
            return
        if not images_to_process:
            st.warning("No images available for processing. Please upload a ZIP file or convert a PDF first.")
            return

        st.session_state.api_key = api_key_input
        st.session_state.csv_name = csv_name_input
        
        genai.configure(api_key=st.session_state.api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        with st.spinner("Sending images to Gemini..."):
            try:
                temp_csv_buffers = []
                for i, page in enumerate(images_to_process, start=1):
                    response = model.generate_content([prompt_text, page])
                    csv_text = response.text.strip()
                    temp_csv_buffers.append(io.StringIO(csv_text))
                    st.write(f"Processed image {i} with Gemini...")

                st.session_state.gemini_csv_outputs = temp_csv_buffers
                st.success("All images processed by Gemini!")
                
            except Exception as e:
                st.error(f"Gemini API error: {e}")
                return

        if st.session_state.gemini_csv_outputs:
            with st.spinner("Merging CSV data..."):
                try:
                    merged_df = None
                    expected_columns = 8

                    for i, csv_buffer in enumerate(st.session_state.gemini_csv_outputs):
                        csv_buffer.seek(0)
                        df = pd.read_csv(csv_buffer, encoding='utf-8', quoting=csv.QUOTE_ALL)
                        
                        if df.shape[1] != expected_columns:
                            st.warning(f"Skipping CSV from page {i+2} due to incorrect column count.")
                            continue
                        
                        if merged_df is None:
                            merged_df = df.copy()
                        else:
                            df_data_only = df.copy()
                            df_data_only.columns = merged_df.columns
                            merged_df = pd.concat([merged_df, df_data_only], ignore_index=True)

                    if merged_df is not None:
                        csv_buffer = merged_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download Final CSV",
                            data=csv_buffer,
                            file_name=f"{st.session_state.csv_name}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.error("No valid CSV data found to merge.")

                except Exception as e:
                    st.error(f"Error merging CSVs: {e}")

def merge_two_major_files_tab():
    st.header("3. Merge Two Major Files")
    st.warning("This feature is not yet implemented. Please refer to the previous example for merging CSVs.")

def chat_with_files_tab():
    st.header("4. Chat with Your Files")
    st.warning("This feature is not yet implemented. Please refer to the previous example for chatting with Gemini.")

# --- Main App Layout ---
st.set_page_config(layout="wide")

st.title("Document Processing App")

tab1, tab2, tab3, tab4 = st.tabs([
    "Convert Files", 
    "Process Files", 
    "Merge Two Major Files", 
    "Chat with Your Files"
])

with tab1:
    convert_files_tab()

with tab2:
    process_files_tab()

with tab3:
    merge_two_major_files_tab()

with tab4:
    chat_with_files_tab()
