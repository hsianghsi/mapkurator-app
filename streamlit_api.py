import requests
import streamlit as st
import os
import yaml
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as patches
from datetime import datetime
import json
from main import extract_geometry, adjust_transparency, score_color, sort_list
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==== CONFIG ====
def read_config():
    config_file = 'config_api.yaml'
    # Construct the absolute path to the config file
    abs_config_file = os.path.join(os.path.dirname(__file__), config_file)
    try:
        with open(abs_config_file, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print(f"Error: Config file '{config_file}' not found.")
        return None

config = read_config()

# Paths & Parameters
font_file = config.get('font_file')
figsize_w = config.get('figsize_w')
figsize_h = config.get('figsize_h')
fontsize_min = config.get('fontsize_min')
fontsize_max = config.get('fontsize_max')
fontsize_init = config.get('fontsize_init')
languages = {list(lang.keys())[0]: list(lang.values())[0] for lang in config.get('languages')}

# Flask API endpoint on Computer B
API_ENDPOINT = ""
filename = ""

def handle_response(response, uploaded_file):
    image = Image.open(uploaded_file)    
    response_data = response.json()

    # Access the 'features' key directly from the parsed JSON data
    features = response_data['features']
    text_with_score_list = []

    alpha = st.slider('文字透明度 (Text Transparency)', min_value=0.0, max_value=1.0, value=1.0, step=0.1, key="alpha_slider")
    fontsize = st.slider('文字大小 (Font Size)', min_value=fontsize_min, max_value=fontsize_max, value=fontsize_init, step=1, key="fontsize_slider")
    text_version = st.selectbox("選擇初始偵測或OSM校正版 (Select a text version)", ['text', 'postocr_label'])

    fig, ax = plt.subplots(figsize=(figsize_w, figsize_h))
    ax.imshow(image)

    for feature in features:
        properties = feature.get('properties', {})
        text = properties.get(text_version, None)
        score = properties.get('score', None)
        if text:
            x, y = extract_geometry(feature)
            text_with_score = f"{text} ({score:.2f})" if score is not None else text
            poly_patch = patches.Polygon(xy=list(zip(x, y)), edgecolor=adjust_transparency(score_color(score), alpha), facecolor='none')
            ax.add_patch(poly_patch)
            ax.text(x[0], y[0], text, fontsize=fontsize, color=adjust_transparency(score_color(score), alpha), fontproperties=fm.FontProperties(fname=font_file), ha='center')
            text_with_score_list.append(text_with_score)

    st.pyplot(fig)
    st.write("文字偵測清單 (List of Spotted Text)")
    st.write(text_with_score_list)

    if st.button("Sort by Score"):
        sorted_list = sort_list(text_with_score_list)
        st.write(sorted_list)
    
    # Convert the dictionary to a JSON string
    response_json = json.dumps(response_data)

    # Encode the JSON string to bytes
    response_bytes = response_json.encode('utf-8')

    st.download_button(label="下載偵測檔(Download JSON)", data=response_bytes, file_name=f'{filename}.json', mime='application/json')

def upload_and_send_data():
    st.title("MapKurator Demo")
    selected_display_name = st.selectbox('選擇偵測語言 (Select a language)', list(languages.keys()))
    selected_language = languages.get(selected_display_name)
    if selected_language is not None:
        # st.write(selected_language)
        uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png", "jp2"])
    
    if uploaded_file is not None:
        global filename

        uploaded_filename = uploaded_file.name
        filename, file_extension = os.path.splitext(uploaded_filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        new_filename = f"{filename}-{timestamp}{file_extension}"
        logger.info(f"Uploaded file name: {new_filename}")

        # Read the content of the uploaded file
        file_content = uploaded_file.read()

        # Prepare data for the Flask API
        json_data = {'selected_language': selected_language}
        accepted_image_types = ['image/jpeg', 'image/jpg', 'image/jp2', 'image/png']
        files = {
            'file': (new_filename, file_content, accepted_image_types[0]),
            'json_data': ('data.json', json.dumps(json_data), 'application/json')
        }

        # Set the Content-Type header explicitly
        headers = None

        # Send the image file and JSON data to the Flask API
        response = requests.post(API_ENDPOINT, files=files, headers=headers, timeout=1000)

        if response.status_code == 200:
            # Call the function to handle the response and visualization
            handle_response(response, uploaded_file)
        else:
            st.error(f"Error: {response.text}")

if __name__ == "__main__":
    upload_and_send_data()