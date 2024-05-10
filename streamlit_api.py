import requests
import streamlit as st
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as patches
from datetime import datetime
from main import extract_geometry, adjust_transparency, score_color, sort_list, read_config

config = read_config()

# Paths & Parameters
font_file = config.get('font_file')
figsize_w = config.get('figsize_w')
figsize_h = config.get('figsize_h')
fontsize_min = config.get('fontsize_min')
fontsize_max = config.get('fontsize_max')
fontsize_init = config.get('fontsize_init')
languages = config.get('languages')

# Flask API endpoint on Computer B
API_ENDPOINT = "http://140.109.161.10:8080/app"

def main():
    st.title("MapKurator Demo")
    selected_language = st.selectbox('選擇偵測語言 (Select a language)', languages)

    if selected_language is not None:
        uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png", "jp2"])

        if uploaded_file is not None:
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")
            filename = f"{timestamp}.{uploaded_file.name.split('.')[-1]}"
            
            # Send the image file to the Flask API
            files = {'file': (filename, uploaded_file.getvalue())}
            response = requests.post(API_ENDPOINT, files=files)

            if response.status_code == 200:

                image = Image.open(uploaded_file)

                # Get GeoJSON data from the response
                geojson_data = response.json()
                features = geojson_data['features']    

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
            else:
                st.error(f"Error: {response.text}")

if __name__ == "__main__":
    main()