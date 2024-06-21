from shapely.geometry import Polygon, mapping
from geojson import Feature

# Function to check if a polygon is near the edge of multiples of 1000
def is_near_edge(coords, edge_threshold=5):
    """Check if any vertex of the polygon is near the edge of the dynamic shift sizes."""
    for x, y in coords:
        if any(abs(x % size) < edge_threshold or abs(size - (x % size)) < edge_threshold for size in range(1000, int(max(coords, key=lambda c: c[0])[0]) + 1000, 1000)):
            return True
    return False

# Function to check if two polygons are adjacent
def are_polygons_adjacent(polygon1, polygon2, threshold=5):
    poly1 = Polygon(polygon1)
    poly2 = Polygon(polygon2)
    
    # Get the bounding boxes of both polygons
    minx1, miny1, maxx1, maxy1 = poly1.bounds
    minx2, miny2, maxx2, maxy2 = poly2.bounds
    
    # Check if x-axis ranges are adjacent
    x_adjacent = (abs(minx1 - maxx2) < threshold or abs(minx2 - maxx1) < threshold)
    
    return x_adjacent

# Function to merge two polygons into one
def merge_polygons(polygon1, polygon2):
    poly1 = Polygon(polygon1)
    poly2 = Polygon(polygon2)
    
    # Ensure polygons are valid
    if not poly1.is_valid:
        poly1 = poly1.buffer(0)
    if not poly2.is_valid:
        poly2 = poly2.buffer(0)
    
    merged_poly = poly1.union(poly2)
    
    if not merged_poly.is_valid:
        raise ValueError(f"Invalid merged polygon: {explain_validity(merged_poly)}")
    
    return list(mapping(merged_poly)['coordinates'][0])

def filter_top_bottom_points(coordinates):
    # Find the extreme x and y coordinates
    min_x = min(coordinates, key=lambda c: c[0])[0]
    max_x = max(coordinates, key=lambda c: c[0])[0]
    min_y = min(coordinates, key=lambda c: c[1])[1]
    max_y = max(coordinates, key=lambda c: c[1])[1]

    # Filter coordinates based on extreme values
    top_left = [min_x, max_y]
    top_right = [max_x, max_y]
    bottom_left = [min_x, min_y]
    bottom_right = [max_x, min_y]

    # Return filtered coordinates
    filtered_coordinates = [top_left, top_right, bottom_right, bottom_left, top_left]
    return filtered_coordinates

def merge_adjacent_polygons(features, edge_threshold=5):
    merged_features = []
    processed_indices = set()
    
    for i, feature in enumerate(features):
        if i in processed_indices:
            continue
        
        polygon_coords = feature['geometry']['coordinates']
        if is_near_edge(polygon_coords[0], edge_threshold):
            adjacent_found = False
            merged_text = feature['properties']['text']
            merged_score = feature['properties'].get('score', 0)
            num_merged = 1
            
            for j, other_feature in enumerate(features[i+1:], start=i+1):
                if j in processed_indices:
                    continue
                
                other_polygon_coords = other_feature['geometry']['coordinates']
                
                if is_near_edge(other_polygon_coords[0], edge_threshold) and are_polygons_adjacent(polygon_coords[0], other_polygon_coords[0], edge_threshold):
                    # Print pre-merged features
                    print("Pre-merged features:")
                    print(f"Feature {i}: {feature}")
                    print(f"Feature {j}: {other_feature}")

                    # Merge the polygons
                    try:
                        merged_coords = polygon_coords[0] + other_polygon_coords[0][1:]  # Concatenate the coordinates, excluding the duplicate first coordinate of the second polygon
                        merged_coords = filter_top_bottom_points(merged_coords)
                    except ValueError as e:
                        print(f"Error merging polygons at indices {i} and {j}: {e}")
                        continue
                    
                    # Update the merged text and score
                    merged_text += other_feature['properties']['text']
                    merged_score += other_feature['properties'].get('score', 0)
                    num_merged += 1

                    # Print after-merged features
                    print("After-merged features:")
                    print(f"Merged coordinates: {merged_coords}")
                    print(f"Merged text: {merged_text}")
                    print(f"Merged score: {merged_score / num_merged}")
                    
                    adjacent_found = True
                    processed_indices.add(j)
                    break
            
            if adjacent_found:
                # Append the merged feature
                merged_features.append(Feature(geometry={"type": "Polygon", "coordinates": [merged_coords]}, 
                                               properties={"text": merged_text, "score": merged_score / num_merged}))
                
            else:
                # If no adjacent polygon found, keep the original feature
                merged_features.append(feature)
        else:
            # If not near edge, keep the original feature
            merged_features.append(feature)
    
    return merged_features