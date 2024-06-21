import math
import json
import argparse
import os

# For leaflet tiles only

def tile_to_latlon(zoom, x, y):
    n = 2.0 ** zoom
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg

def tiles_to_corner_coordinates(zoom, x_tiles, y_tiles):
    corners = {}

    # Top-left corner of the top-left tile
    lat, lon = tile_to_latlon(zoom, x_tiles.start, y_tiles.start)
    corners['top_left'] = (lon, lat)
    
    # Top-right corner of the top-right tile
    lat, lon = tile_to_latlon(zoom, x_tiles.stop, y_tiles.start)
    corners['top_right'] = (lon, lat)
    
    # Bottom-left corner of the bottom-left tile
    lat, lon = tile_to_latlon(zoom, x_tiles.start, y_tiles.stop)
    corners['bottom_left'] = (lon, lat)
    
    # Bottom-right corner of the bottom-right tile
    lat, lon = tile_to_latlon(zoom, x_tiles.stop, y_tiles.stop)
    corners['bottom_right'] = (lon, lat)

    return corners

def tiles_xy_to_img_xy(x_tiles, y_tiles, tile_size=256):
    img_xy = {}

    x_tiles_range = abs(x_tiles.stop - x_tiles.start)
    y_tiles_range = abs(y_tiles.stop - y_tiles.start)
    
    # Top-left corner
    img_xy['top_left'] = (0, 0)
    
    # Top-right corner
    img_xy['top_right'] = (x_tiles_range * tile_size, 0)
    
    # Bottom-left corner
    img_xy['bottom_left'] = (0, -y_tiles_range * tile_size)
    
    # Bottom-right corner
    img_xy['bottom_right'] = (x_tiles_range * tile_size, -y_tiles_range * tile_size)
    
    return img_xy

def img_xy_to_tiles_xy(img_x, img_y, x_tile_start, y_tile_start, tile_size=256):
    x_tile = x_tile_start + abs(img_x / tile_size)
    y_tile = y_tile_start + abs(img_y / tile_size)
    return x_tile, y_tile

# Convert
def convert_geojson_coord(args):

    input_geojson = args.in_geojson_file
    filename = os.path.basename(input_geojson)
    tile_info = json.loads(args.tile_info)

    zoom = int(tile_info['zoom'])
    x_tiles = tile_info['x_tiles']
    y_tiles = tile_info['y_tiles']

    x_tile_start = min(x_tiles)
    y_tile_start = min(y_tiles)
    
    with open(input_geojson, 'r') as f:
        geojson_data = json.load(f)

    feature_collection = {
        "type": "FeatureCollection",
        "features": []
    }

    if geojson_data['type'] == 'FeatureCollection':
        for feature in geojson_data['features']:
            if feature['geometry']['type'] == 'Polygon':
                coordinates = feature['geometry']['coordinates'][0]  # Assuming it's a simple Polygon
                latlon_coordinates = []

                for coord in coordinates:
                    x, y = coord
                    x_tile, y_tile = img_xy_to_tiles_xy(x, y, x_tile_start, y_tile_start)
                    lat, lon = tile_to_latlon(zoom, x_tile, y_tile)
                    latlon_coordinates.append([lon, lat])  # Ensure lon, lat order for GeoJSON

                new_feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [coordinates],  # Keep the original coordinates as a list of lists
                        "latlon": [latlon_coordinates]  # Add the converted latlon coordinates as a list of lists
                    },
                    "properties": feature['properties']
                }

                feature_collection['features'].append(new_feature)

    # Write the modified GeoJSON to a new file or use it as needed
    output_geojson = json.dumps(feature_collection)
    output_path = os.path.join(args.out_geojson_dir, {filename})
    with open(output_path, 'w') as f:
        f.write(output_geojson)

    return output_geojson

# Main function to handle argument parsing and execution
def main():
    parser = argparse.ArgumentParser(description='Process GeoJSON and add latlon coordinates.')
    parser.add_argument('--in_geojson_file', type=str, help='Path to the input GeoJSON file')
    parser.add_argument('--out_geojson_dir', type=str, help='Path to the output GeoJSON file')
    parser.add_argument('--tile_info', type=str, help='Tile info as JSON string')
    args = parser.parse_args()

    print(args)
    convert_geojson_coord(args)

if __name__ == '__main__':
    main()