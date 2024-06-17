import streamlit as st
import os
import yaml
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
from main import extract_json_features, extract_geometry, adjust_transparency, score_color, sort_list

# ==== CONFIG ====
def read_config():
    config_file = 'config.yaml'
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
languages = config.get('languages')

# ==== ST FUNCTIONS ====
# Function to display selectbox options
# def display_selectbox():
#     # Options for the selectbox
#     languages = ['Chinese', 'English', 'Russian']
#     selected_language = st.selectbox('選擇偵測語言 (Select a language)', languages)
#     return selected_language

# ==== APP ====
def main():
    st.title("MapKurator Demo")

    # Button to trigger selectbox display
    selected_language = st.selectbox('選擇偵測語言 (Select a language)', languages)

    if selected_language is not None:
        # Upload Window
        uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png"])

        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            features = extract_json_features(uploaded_file)

            # List to store text_with_score values
            text_with_score_list = []

            # St Sliders
            alpha = st.slider('文字透明度 (Text Transparency)', min_value=0.0, max_value=1.0, value=1.0, step=0.1, key="alpha_slider")
            fontsize = st.slider('文字大小 (Font Size)', min_value=fontsize_min, max_value=fontsize_max, value=fontsize_init, step=1, key="fontsize_slider")
            text_version = st.selectbox("選擇初始偵測或OSM校正版 (Select a text version)", ['text', 'postocr_label'])
            
            # Plot the image
            fig, ax = plt.subplots(figsize=(figsize_w, figsize_h))
            ax.imshow(image)

            for feature in features:
                properties = feature.get('properties', {})
                text = properties.get(text_version, None)
                score = properties.get('score', None)

                if text:
                    # Extract geometry coordinates
                    x, y = extract_geometry(feature)
                    text_with_score = f"{text} ({score:.2f})" if score is not None else text
                    poly_patch = patches.Polygon(xy=list(zip(x, y)), edgecolor=adjust_transparency(score_color(score), alpha), facecolor='none')
                    ax.add_patch(poly_patch)
                    
                    # Extract and plot start/end point
                    start_end_point = (x[0], y[0])
                    ax.plot(start_end_point[0], start_end_point[1], 'ro')
                        
                    # Add text and patch to fig
                    ax.text(x[0], y[0], text, fontsize=fontsize, color=adjust_transparency(score_color(score), alpha), fontproperties=fm.FontProperties(fname=font_file), ha='center')

                    # Append text_with_score to the list
                    text_with_score_list.append(text_with_score)

            # Display the processed image
            st.pyplot(fig)

            # Display the list of text_with_score values
            st.write("文字偵測清單 (List of Spotted Text)")
            st.write(text_with_score_list)

            # Button to trigger sorting
            if st.button("Sort by Score"):
                sorted_list = sort_list(text_with_score_list)
                st.write(sorted_list)
       
if __name__ == "__main__":
    main()

