from flask import Flask, request, jsonify
from datetime import datetime
import subprocess
import logging
import os
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, World!'

@app.route('/app', methods=['POST'])
def main():
    logging.info("Request received")
    logging.info(f"Request headers: {request.headers}")
    logging.info(f"Request files data: {request.files}")

    uploaded_file = request.files['file'] # Retrieve the file from the request
    file = uploaded_file.filename
    filename = os.path.splitext(file)[0]

    # Log file and language details
    logging.info(f"Uploaded file: {file}")
 
    # Retrieve the JSON data from the request
    json_data = request.files.get('json_data')

    if json_data:
        # Decode the JSON data
        selected_language = json.loads(json_data.read().decode())['selected_language']
        logging.info(f"Selected language: {selected_language}")
    else:
        logging.info("Unable to find Selected language.")

    if selected_language and uploaded_file is not None:
    
        # Save the uploaded file on Computer B
        upload_dir = "/ssd/luhsianghsi/mapkurator-input/"
        uploaded_file_path = os.path.join(upload_dir, file)

        # Create the directory if it doesn't exist
        os.makedirs(upload_dir, exist_ok=True)

        uploaded_file.save(uploaded_file_path)
        logger.info("File saved successfully.")

        # Run the Python script
        expt_name = f"mapkurator_{datetime.now().strftime('%Y-%m-%d')}"
        spotter_expt_name = datetime.now().strftime('%Y-%m-%d')
                    
        cmd = f"python /ssd/luhsianghsi/mapkurator-system/run_img.py --map_kurator_system_dir /ssd/luhsianghsi/mapkurator-system/ --input_dir_path /ssd/luhsianghsi/mapkurator-input --expt_name {expt_name} --module_cropping --module_get_dimension --module_text_spotting --text_spotting_model_dir /ssd/luhsianghsi/mapkurator-spotter/spotter-v2/ --spotter_model spotter-v2 --spotter_config {selected_language} --spotter_expt_name {spotter_expt_name} --module_img_geojson --output_folder /ssd/luhsianghsi/mapkurator-output/ --gpu_id 0"
        try:
            logger.info("Running command: %s", cmd)
            completed_process = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            logger.info("Command output: %s", completed_process.stdout)
        except subprocess.CalledProcessError as e:
            logger.error("Error running command: %s", e.stderr)
            raise

        run_post_ocr = f"python /ssd/luhsianghsi/mapkurator-system/m4_post_ocr/post_ocr_main.py --in_geojson_file /ssd/luhsianghsi/mapkurator-output/{expt_name}/stitch/{spotter_expt_name}/{filename}.geojson --out_geojson_dir /ssd/luhsianghsi/mapkurator-output/post_ocr"
        try:
            logger.info("Running command: %s", run_post_ocr)
            completed_process = subprocess.run(run_post_ocr, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            logger.info("Command output: %s", completed_process.stdout)
        except subprocess.CalledProcessError as e:
            logger.error("Error running command: %s", e.stderr)
            raise

        with open(f"/ssd/luhsianghsi/mapkurator-output/post_ocr/{filename}.geojson", "r") as geojson_file:
            geojson_data = geojson_file.read()
            parsed_geojson_data = json.loads(geojson_data)

        # Return the parsed GeoJSON data as JSON response
        return parsed_geojson_data

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
