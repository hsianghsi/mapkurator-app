import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
import os
import matplotlib.font_manager as fm
import yaml
import tempfile

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
geojson_folder = config.get('geojson_folder')
font_file = config.get('font_file')
figsize_w = config.get('figsize_w')
figsize_h = config.get('figsize_h')
fontsize_min = config.get('fontsize_min')
fontsize_max = config.get('fontsize_max')
fontsize_init = config.get('fontsize_init')
score_colors = config.get('score_colors')

# ==== FUNCTIONS ====

# Get geojson file from other folder 
def get_geojson_path(image_filename):
    
    # Construct the path to the GeoJSON file using the image file name
    geojson_filename = os.path.splitext(image_filename)[0] + ".geojson"
    geojson_path = os.path.join(geojson_folder, geojson_filename)
    print("GeoJSON path:", geojson_path)
    
    return geojson_path

# Function to save uploaded file to a temporary location
def save_uploaded_file(uploaded_file):
    # Create a temporary directory to store the uploaded file
    temp_dir = tempfile.TemporaryDirectory()
    temp_file_path = os.path.join(temp_dir.name, uploaded_file.name)
    
    # Save the uploaded file to the temporary location
    with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return temp_file_path

# Colorway based on score
def score_color(score):
    if score is None:
        return tuple(score_colors['none']) + (1.0,)  # Black 
    elif score < 0.5:
        return tuple(score_colors['red']) + (1.0,)  # Red
    elif 0.8 > score >= 0.5:
        return tuple(score_colors['orange']) + (1.0,)  # Orange
    elif 0.9 > score >= 0.8:
        return tuple(score_colors['green']) + (1.0,)  # Green
    else:
        return tuple(score_colors['dark_green']) + (1.0,)  # Dark green

# Extract geojson features
def extract_json_features(uploaded_file):
    # Read the image
    image_filename = uploaded_file.name
    geojson_path = get_geojson_path(image_filename)

    # Read the GeoJSON file
    with open(geojson_path, 'r') as f:
        geo_data = json.load(f)

    # Extract polygon coordinates and text
    features = geo_data['features']    
    return features

# Extract geomtry
def extract_geometry(feature):
    geometry = feature['geometry']
    coordinates = geometry['coordinates'][0]  # Assuming the first set of coordinates represents the polygon
    x = [coord[0] for coord in coordinates]
    y = [-coord[1] for coord in coordinates]
    return x, y

# Adjust transparency of the color based on the slider value
def adjust_transparency(color, alpha):
    r, g, b = color[:3]  # Extract RGB values
    return (r, g, b, alpha)

# Adjust font size
def adjust_fontsize(fontsize):
    # Ensure value is within the range
    fontsize = max(fontsize_min, min(fontsize, fontsize_max))
    # If the value is not provided, use the initial size
    if fontsize is None:
        return fontsize_init
    return fontsize

# Function to sort the list based on the score
def sort_list(list):
    sorted_list = sorted(list, key=lambda x: float(x.split('(')[-1].split(')')[0]), reverse=False)
    return sorted_list

# Visualize text on map
def vis_text_with_score(uploaded_file):
    # Read the image
    image = Image.open(uploaded_file)
    features = extract_json_features(uploaded_file)

    # Plot the image
    plt.figure(figsize=(figsize_w, figsize_h))
    plt.imshow(image)

    for feature in features:
        properties = feature.get('properties', {})
        text = properties.get('text', None)
        score = properties.get('score', None)
        if text:
            x, y = extract_geometry(feature)

            # Create polygon patch
            poly_patch = patches.Polygon(xy=list(zip(x, y)), edgecolor=score_color(score), facecolor='none')

            # Concatenate 'text' and 'score' into a single string
            text_with_score = f"{text} ({score:.2f})" if score is not None else text

            # Add polygon patch to plot
            plt.gca().add_patch(poly_patch)

            # Add text annotation
            plt.text(x[0], y[0], text_with_score, fontsize=7, color=score_color(score), fontproperties=fm.FontProperties(fname=font_file))

    plt.show()

def reduce_image_size(uploaded_file):
    max_width=3000
    max_height=3000
    max_pixels=80000000
    # Open the uploaded image
    image = Image.open(uploaded_file)
    
    # Calculate the total number of pixels in the image
    total_pixels = image.width * image.height
    
    # Check if the image exceeds the maximum number of pixels
    if total_pixels > max_pixels:
        # Resize the image to fit within the specified maximum dimensions
        aspect_ratio = image.width / image.height
        new_width = min(image.width, max_width)
        new_height = min(image.height, max_height)
        if aspect_ratio > 1:
            new_height = int(new_width / aspect_ratio)
        else:
            new_width = int(new_height * aspect_ratio)
        image = image.resize((new_width, new_height), Image.ANTIALIAS)
    
    # Return the image object
    return image
