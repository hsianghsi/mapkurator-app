import requests
import streamlit as st
import streamlit.components.v1 as components
import os
import yaml
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as patches
from datetime import datetime
import json
from main import extract_geometry, adjust_transparency, score_color, sort_list, reduce_image_size, add_polygons_and_labels
import logging
from io import BytesIO
import time
import folium
from streamlit_folium import st_folium
from streamlit_folium import folium_static


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

# Flask API endpoint
API_ENDPOINT = st.secrets["API_ENDPOINT"]
REMOVE_ENDPOINT = st.secrets["REMOVE_ENDPOINT"]

# ==== FUNCTIONS ====

# Function to download a tile
def download_tile(url):
    response = requests.get(url)
    if response.status_code == 200:
        return Image.open(BytesIO(response.content))
    else:
        return None

def get_leaflet_map():
    # Embed the HTML file in the Streamlit app
    html_file = 'leaflet_map.html'
    with open(html_file, 'r') as f:
        html_content = f.read()

    # JavaScript to handle receiving messages from the iframe
    receive_message_js = """
    <script>
        window.addEventListener('message', function(event) {
            const data = event.data;
            console.log('Received message from iframe:', data);
            if (data && data.z !== undefined) {
                // Send data to Streamlit via query parameters
                const params = new URLSearchParams();
                params.set('z', data.z);
                params.set('x', JSON.stringify(data.x));
                params.set('y', JSON.stringify(data.y));
                window.parent.history.replaceState(null, '', `?${params.toString()}`);
            }
        });
    </script>
    """

    # Display the HTML content with JavaScript code
    components.html(html_content + receive_message_js, width=700, height=450)

    if st.button("Get Map"):

        # Function to get tile information
        def get_tile_info():
            params = st.experimental_get_query_params()
            # st.write(f"Query Params: {params}")  # Log the query params
            if 'z' in params and 'x' in params and 'y' in params:
                zoom = int(params['z'][0])
                x = json.loads(params['x'][0])
                y = json.loads(params['y'][0])

                # Sort the x and y lists
                x_tiles = sorted(set(x))
                y_tiles = sorted(set(y))

                tile_info = {
                    'zoom': zoom,
                    'x_tiles': x_tiles,
                    'y_tiles': y_tiles
                }
                return tile_info
            else:
                return None

        # Retrieve tile information
        tile_info = get_tile_info()

        zoom = tile_info['zoom']
        x_tiles = tile_info['x_tiles']
        y_tiles = tile_info['y_tiles']

        # Display tile information or waiting message
        if tile_info is not None:
            col1, col2, col3 = st.columns(3)
            col1.metric("Zoom Level", zoom)
            col2.info(f"X: {x_tiles}")
            col3.info(f"Y: {y_tiles}")
            
            tile_size = 256

            # Create a new blank image with appropriate size
            width = tile_size * len(x_tiles)
            height = tile_size * len(y_tiles)
            stitched_image = Image.new('RGB', (width, height))

            # Base URL
            base_url = "https://gis.sinica.edu.tw/tileserver/file-exists.php?img=TM50K_1954-png-{}-{}-{}"

            # Loop through tile coordinates, download, and paste them into the big image
            for i, x in enumerate(x_tiles):
                for j, y in enumerate(y_tiles):
                    url = base_url.format(zoom, x, y)
                    tile = download_tile(url)
                    if tile:
                        stitched_image.paste(tile, (i * tile_size, j * tile_size))

            # Create a file-like object for the image
            stitched_image_io = BytesIO()
            stitched_image.save(stitched_image_io, format='JPEG')
            stitched_image_io.seek(0)

        else:
            st.write("Waiting for tile information...")
            st.write("<div id='zoom-tiles' style='white-space: pre-wrap;'></div>", unsafe_allow_html=True)

        return stitched_image_io, tile_info


@st.cache_data
def upload_and_send_data(selected_language, uploaded_file, tile_info=None):

    # Check if the uploaded_file has a name attribute
    if hasattr(uploaded_file, 'name'):
        uploaded_filename = uploaded_file.name
        filename, file_extension = os.path.splitext(uploaded_filename)
    else:
        filename = "image"
        file_extension = ".jpeg"

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    new_filename = f"{filename}-{timestamp}{file_extension}"
    logger.info(f"Uploaded file name: {new_filename}")

    # Read the content of the uploaded file
    file_content = uploaded_file.read()

    # Prepare data for the Flask API
    json_data = {'selected_language': selected_language}
    if tile_info is not None:
        json_data['tile_info'] = tile_info
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
        response_data = response.json()
        return response_data, uploaded_file, filename

    else:
        st.error(f"Error: {response.text}")
    
    return None, None, None

def remove_data():
    try:
        response = requests.post(REMOVE_ENDPOINT, timeout=1000)
        print("Response from /remove-files endpoint:")
        print(response.json())
        st.session_state.remove_files_called = True
    except requests.exceptions.RequestException as e:
        print(f"Error sending request to {REMOVE_ENDPOINT}: {e}")

# @st.cache_data(experimental_allow_widgets=True)
def handle_response(response_data, uploaded_file, filename):
    # Access the 'features' key directly from the parsed JSON data
    features = response_data['features']
    image = reduce_image_size(uploaded_file)    
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

    # Initialize map centered at the first feature's center
    if 'latlon' in features[0]['geometry']:
        first_feature_coords = features[0]["geometry"]["latlon"][0]
        center_lat = sum([coord[1] for coord in first_feature_coords]) / len(first_feature_coords)
        center_lon = sum([coord[0] for coord in first_feature_coords]) / len(first_feature_coords)
        m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="CartoDB positron")
        add_polygons_and_labels(m, features)
        
        # Display the map in Streamlit
        folium_static(m, width=725)

    st.write("文字偵測清單 (List of Spotted Text)")
    st.write(text_with_score_list)

    if st.button("Sort by Score"):
        sorted_list = sort_list(text_with_score_list)
        st.write(sorted_list)

    # st.write(response_data)
    
    # Convert the dictionary to a JSON string
    response_json = json.dumps(response_data, sort_keys=False)

    # Encode the JSON string to bytes
    response_bytes = response_json.encode('utf-8')

    st.download_button(label="下載偵測檔(Download JSON)", data=response_bytes, file_name=f'{filename}.geojson', mime='application/json')


if __name__ == "__main__":
    st.title("MapKurator Demo")

    selected_display_name = st.selectbox('選擇偵測語言 (Select a Language)', list(languages.keys()))
    selected_language = languages.get(selected_display_name)
    
    option = st.selectbox(
    "選擇偵測模組 (Select a Module)",
    ("中研院百年歷史地圖", "自行上傳地圖"),
    index=None,
    placeholder="Select a module...",
    )

    st.write("You selected:", option)

    response_data = None

    if option == "自行上傳地圖":
        uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png", "jp2"])
        if uploaded_file is not None:
            response_data, uploaded_file, filename = upload_and_send_data(selected_language, uploaded_file)
            remove_data()
    
    elif option == "中研院百年歷史地圖":
        result = get_leaflet_map()
        if result is not None:
            stitched_image_io, tile_info = result
            response_data, uploaded_file, filename = upload_and_send_data(selected_language, stitched_image_io, tile_info)
            remove_data()

    if response_data:
        handle_response(response_data, uploaded_file, filename)

