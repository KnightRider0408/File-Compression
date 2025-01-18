from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import gzip
from werkzeug.utils import secure_filename
from flask_cors import CORS  # Import CORS

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['COMPRESSED_FOLDER'] = 'compressed'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['COMPRESSED_FOLDER'], exist_ok=True)

# Enable CORS for all routes
CORS(app)

def compress_file(input_file, output_folder):
    """Compress the input file using gzip compression"""
    output_filename = os.path.join(output_folder, os.path.basename(input_file) + '.gz')
    with open(input_file, 'rb') as f_in:
        with gzip.open(output_filename, 'wb') as f_out:
            f_out.writelines(f_in)
    return output_filename

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/compress', methods=['POST'])
def compress():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # Save the uploaded file
    file.save(filepath)
    
    try:
        # Compress the file
        compressed_filepath = compress_file(filepath, app.config['COMPRESSED_FOLDER'])
        
        # Calculate sizes
        original_size = os.path.getsize(filepath)
        compressed_size = os.path.getsize(compressed_filepath)
        compression_ratio = round((1 - compressed_size / original_size) * 100, 2)
        
        # Clean up the original file
        os.remove(filepath)
        
        # Provide details and download link for the compressed file
        return jsonify({
            'original_size': original_size,
            'compressed_size': compressed_size,
            'compression_ratio': compression_ratio,
            'download_url': f'/download/{os.path.basename(compressed_filepath)}',  # Serve through /download route
            'filename': os.path.basename(compressed_filepath)
        })
    
    except Exception as e:
        # In case of an error, return a JSON error response
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """Serve the compressed file for download"""
    return send_from_directory(app.config['COMPRESSED_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
