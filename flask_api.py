from flask import Flask, request, jsonify
import os
import subprocess
import shutil
import json
import logging
import glob

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

def save_uploaded_file(upload_dir, uploaded_file):
    filename = uploaded_file.filename
    uploaded_file_path = os.path.join(upload_dir, filename)
    os.makedirs(upload_dir, exist_ok=True)
    uploaded_file.save(uploaded_file_path)
    logger.info("File saved successfully at %s", uploaded_file_path)
    return uploaded_file_path, os.path.splitext(filename)[0]

def run_command(command, timeout=None):
    try:
        logger.info("Running command: %s", command)
        completed_process = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        logger.info("Command output: %s", completed_process.stdout)
        return completed_process.stdout
    except subprocess.TimeoutExpired:
        logger.error("Command timed out after %d seconds", timeout)
        raise
    except subprocess.CalledProcessError as e:
        logger.error("Error running command: %s", e.stderr)
        raise

def handle_timeout_or_error(expt_name, spotter_expt_name, filename):
    input_file = f"/ssd/luhsianghsi/mapkurator-output/{expt_name}/stitch/{spotter_expt_name}/{filename}.geojson"
    output_file = f"/ssd/luhsianghsi/mapkurator-output/post_ocr/{filename}.geojson"
    shutil.copy(input_file, output_file)

def read_geojson(output_dir, filename):
    with open(f"{output_dir}/{filename}.geojson", "r") as geojson_file:
        geojson_data = geojson_file.read()
        return json.loads(geojson_data)

def process_geojson_with_tile_info(expt_name, spotter_expt_name, filename, tile_info):
    
    tile_info_json = json.dumps(tile_info)
    tile_info_json_escaped = tile_info_json.replace('"', '\\"')

    convert_command = f"python /ssd/luhsianghsi/mapkurator-system/m5_geocoordinate_converter/convert_tile_coord.py --tile_info \"{tile_info_json_escaped}\" --in_geojson_file /ssd/luhsianghsi/mapkurator-output/{expt_name}/stitch/{spotter_expt_name}/{filename}.geojson --out_geojson_dir /ssd/luhsianghsi/mapkurator-output/{expt_name}/geocoord/{spotter_expt_name}"
    post_ocr_command = f"python /ssd/luhsianghsi/mapkurator-system/m4_post_ocr/post_ocr_main.py --in_geojson_file /ssd/luhsianghsi/mapkurator-output/{expt_name}/geocoord/{spotter_expt_name}/{filename}.geojson --out_geojson_dir /ssd/luhsianghsi/mapkurator-output/post_ocr"

    try:
        run_command(convert_command)
        run_command(post_ocr_command, timeout=60)
    except subprocess.TimeoutExpired:
        handle_timeout_or_error(expt_name, spotter_expt_name, filename)
    except subprocess.CalledProcessError:
        handle_timeout_or_error(expt_name, spotter_expt_name, filename)
        raise

    return read_geojson("/ssd/luhsianghsi/mapkurator-output/post_ocr", filename)

def process_geojson_without_tile_info(expt_name, spotter_expt_name, filename):
    post_ocr_command = f"python /ssd/luhsianghsi/mapkurator-system/m4_post_ocr/post_ocr_main.py --in_geojson_file /ssd/luhsianghsi/mapkurator-output/{expt_name}/stitch/{spotter_expt_name}/{filename}.geojson --out_geojson_dir /ssd/luhsianghsi/mapkurator-output/post_ocr"

    try:
        run_command(post_ocr_command, timeout=60)
    except subprocess.TimeoutExpired:
        handle_timeout_or_error(expt_name, spotter_expt_name, filename)
    except subprocess.CalledProcessError:
        handle_timeout_or_error(expt_name, spotter_expt_name, filename)
        raise

    return read_geojson("/ssd/luhsianghsi/mapkurator-output/post_ocr", filename)

@app.route('/app', methods=['POST'])
def main():
    logger.info("Request received")
    logger.info(f"Request headers: {request.headers}")
    logger.info(f"Request files data: {request.files}")

    uploaded_file = request.files['file']
    uploaded_file_path, filename = save_uploaded_file("/ssd/luhsianghsi/mapkurator-input/", uploaded_file)

    json_data = request.files.get('json_data')
    selected_language = None
    tile_info = None

    if json_data:
        json_content = json.loads(json_data.read().decode())
        selected_language = json_content.get('selected_language')
        tile_info = json_content.get('tile_info')
        logger.info(f"Selected language: {selected_language}")
        logger.info(f"Tile Info: {tile_info}")
    else:
        logger.info("Unable to find Selected language.")

    if selected_language and uploaded_file:
        expt_name = "mapkurator_processed_file"
        spotter_expt_name = filename

        main_cmd = (
            f"python /ssd/luhsianghsi/mapkurator-system/run_img.py --map_kurator_system_dir /ssd/luhsianghsi/mapkurator-system/ "
            f"--input_dir_path /ssd/luhsianghsi/mapkurator-input --expt_name {expt_name} --module_cropping --module_get_dimension "
            f"--module_text_spotting --text_spotting_model_dir /ssd/luhsianghsi/mapkurator-spotter/spotter-v2/ --spotter_model spotter-v2 "
            f"--spotter_config {selected_language} --spotter_expt_name {spotter_expt_name} --module_img_geojson "
            f"--output_folder /ssd/luhsianghsi/mapkurator-output/ --gpu_id 0"
        )

        try:
            run_command(main_cmd)
        except subprocess.CalledProcessError as e:
            return jsonify({"error": str(e)}), 500

        if tile_info is not None:
            try:
                parsed_geojson_data = process_geojson_with_tile_info(expt_name, spotter_expt_name, filename, tile_info)
            except subprocess.CalledProcessError as e:
                return jsonify({"error": str(e)}), 500
        else:
            try:
                parsed_geojson_data = process_geojson_without_tile_info(expt_name, spotter_expt_name, filename)
            except subprocess.CalledProcessError as e:
                return jsonify({"error": str(e)}), 500

        return jsonify(parsed_geojson_data)
    else:
        return jsonify({"error": "Missing selected language or uploaded file"}), 400

@app.route('/remove', methods=['POST'])
def remove_files():
    directories = [
        '/ssd/luhsianghsi/mapkurator-input',
        '/ssd/luhsianghsi/mapkurator-output'
    ]
    
    for directory in directories:
        # Get all files and directories inside the given directory
        items = glob.glob(os.path.join(directory, '*'))
        
        for item in items:
            try:
                if os.path.isfile(item):
                    os.remove(item)
                    print(f"Removed file: {item}")
                elif os.path.isdir(item):
                    shutil.rmtree(item)
                    print(f"Removed directory and its contents: {item}")
            except Exception as e:
                print(f"Error removing {item}: {e}")
    
    return jsonify({"status": "success", "message": "Files removed successfully"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
