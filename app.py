from flask import Flask, request, jsonify
from flask_cors import CORS
import io
import os
import re
import json
from google.cloud import vision

# Set the environment variable to the path of your service account key file
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')  # Update path

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

# Function to extract text from image using GCP Vision API
def detect_document_text_from_gcp(image_file):
    client = vision.ImageAnnotatorClient()

    content = image_file.read()
    image = vision.Image(content=content)

    response = client.document_text_detection(image=image)

    # Extracted full text from the image
    full_text_annotation = response.full_text_annotation
    return full_text_annotation.text


# Function to clean extracted text, remove noise and standardize format
def clean_text(text):
    # Remove unnecessary characters, fix common OCR errors, and standardize
    text = text.replace('\n', ' ')  # Remove newlines
    text = text.replace('  ', ' ')  # Remove double spaces
    text = text.lower()  # Convert to lowercase for easier matching
    text = re.sub(r'[^\x00-\x7F]+', '', text)  # Remove non-ASCII characters (optional)
    text = re.sub(r'[^a-z0-9%.,() ]+', '', text)  # Remove unwanted symbols
    return text

# Function to extract nutrient data using regex patterns
def extract_nutrient_data(text, nutrient_pattern_dict):
    extracted_data = {}
    for nutrient, pattern in nutrient_pattern_dict.items():
        matches = re.findall(pattern, text)
        if matches:
            # Only take the first match value (i.e., the first occurrence of the nutrient)
            extracted_data[nutrient] = matches[0]
    return extracted_data

# Define the regex patterns for common nutrients
def get_nutrient_patterns():
    return {
        'Calories': r'calories\s+(\d+)',  # Match calories
        'Total Fat': r'total\s+fat\s+(\d+)g',  # Match total fat in grams
        'Saturated Fat': r'saturated\s+fat\s+(\d+)g',  # Match saturated fat
        'Trans Fat': r'trans\s+fat\s+(\d+)g',  # Match trans fat
        'Polyunsaturated Fat': r'polyunsaturated\s+fat\s+(\d+\.\d+)g',  # Match polyunsaturated fat
        'Monounsaturated Fat': r'monounsaturated\s+fat\s+(\d+\.\d+)g',  # Match monounsaturated fat
        'Cholesterol': r'cholesterol\s+(\d+)mg',  # Match cholesterol in mg
        'Sodium': r'sodium\s+(\d+)mg',  # Match sodium in mg
        'Potassium': r'potassium\s+(\d+)mg',  # Match potassium in mg
        'Total Carbohydrate': r'total\s+carbohydrate\s+(\d+)g',  # Match total carbohydrate in grams
        'Dietary Fiber': r'dietary\s+fiber\s+(\d+)g',  # Match dietary fiber
        'Sugars': r'sugars\s+(\d+)g',  # Match sugars in grams
        'Protein': r'protein\s+(\d+)g',  # Match protein in grams
        'Vitamin A': r'vitamin\s+a\s+(\d*)',  # Match Vitamin A (if present)
        'Vitamin C': r'vitamin\s+c\s+(\d*)',  # Match Vitamin C (if present)
        'Calcium': r'calcium\s+(\d+)mg',  # Match Calcium in mg
        'Iron': r'iron\s+(\d+)mg',  # Match Iron in mg
        'Vitamin D': r'vitamin\s+d\s+(\d*)',  # Match Vitamin D (if present)
        'Thiamin': r'thiamin\s+(\d*)',  # Match Thiamin (if present)
        'Riboflavin': r'riboflavin\s+(\d*)',  # Match Riboflavin (if present)
        'Niacin': r'niacin\s+(\d*)',  # Match Niacin (if present)
        'Vitamin B6': r'vitamin\s+b6\s+(\d*)',  # Match Vitamin B6 (if present)
        'Folic Acid': r'folic\s+acid\s+(\d*)',  # Match Folic Acid (if present)
        'Vitamin B12': r'vitamin\s+b12\s+(\d*)',  # Match Vitamin B12 (if present)
        'Pantothenic Acid': r'pantothenic\s+acid\s+(\d*)',  # Match Pantothenic Acid (if present)
    }

# Function to parse and extract nutritional facts to JSON
def parse_nutrition_facts_to_json(text):
    # Clean the extracted text
    cleaned_text = clean_text(text)

    # Get the regex patterns for nutrients
    nutrient_patterns = get_nutrient_patterns()

    # Extract data using the common function
    extracted_data = extract_nutrient_data(cleaned_text, nutrient_patterns)

    # Look for "Daily Value" percentages and add them if found
    daily_value_match = re.findall(r'(\d+)%', cleaned_text)
    if len(daily_value_match) >= 2:
        extracted_data['Daily Value'] = {
            'Total Fat %': int(daily_value_match[0]),
            'Total Carbohydrate %': int(daily_value_match[1])
        }

    return extracted_data

@app.route("/process-image", methods=["POST"])
def process_image():
    # Log the request files
    print(f"Files received: {request.files}")

    # Check if the 'File' file is in the request
    if "File" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    image_file = request.files["File"]

    # Print the filename to ensure the image is being received
    print(f"Received image: {image_file.filename}")

    # Continue with processing
    extracted_text = detect_document_text_from_gcp(image_file)
    parsed_data = parse_nutrition_facts_to_json(extracted_text)

    return jsonify(parsed_data)


if __name__ == "__main__":
    app.run(debug=True)
