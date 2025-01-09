# app.py
from flask import Flask, render_template, request, send_file, jsonify, after_this_request
import os
import zipfile
from werkzeug.utils import secure_filename
import shutil
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['COMPRESSED_FOLDER'] = 'compressed'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure required folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['COMPRESSED_FOLDER'], exist_ok=True)

def get_file_size(filepath):
    """Get file size in bytes"""
    return os.path.getsize(filepath)

def compress_file(input_filepath, output_filepath):
    """
    Compress the input file using ZIP compression with maximum compression
    Returns: tuple of (original_size, compressed_size)
    """
    original_size = get_file_size(input_filepath)
    
    # Create a ZIP file with maximum compression
    with zipfile.ZipFile(output_filepath, 'w', compression=zipfile.ZIP_DEFLATED, 
                        compresslevel=9) as zipf:
        # Add the file to the ZIP archive with its original filename
        zipf.write(input_filepath, os.path.basename(input_filepath))
    
    compressed_size = get_file_size(output_filepath)
    return original_size, compressed_size

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

    try:
        # Generate a unique filename using timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        original_filename = secure_filename(file.filename)
        base_filename = os.path.splitext(original_filename)[0]
        
        # Create unique filenames for both original and compressed files
        unique_filename = f"{base_filename}_{timestamp}"
        input_filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        output_filepath = os.path.join(app.config['COMPRESSED_FOLDER'], 
                                     f"{unique_filename}.zip")
        
        # Save the uploaded file
        file.save(input_filepath)
        
        # Compress the file and get size information
        original_size, compressed_size = compress_file(input_filepath, output_filepath)
        
        # Calculate compression ratio and percentage saved
        compression_ratio = (original_size - compressed_size) / original_size * 100
        
        # Format sizes for display
        original_size_mb = original_size / (1024 * 1024)
        compressed_size_mb = compressed_size / (1024 * 1024)
        
        # Clean up the original file
        os.remove(input_filepath)
        
        # Generate download URL with original filename
        download_filename = f"{base_filename}.zip"
        
        return jsonify({
            'success': True,
            'original_size': f"{original_size_mb:.2f} MB",
            'compressed_size': f"{compressed_size_mb:.2f} MB",
            'compression_ratio': f"{compression_ratio:.1f}%",
            'download_url': f"/download/{unique_filename}.zip",
            'download_filename': download_filename
        })

    except Exception as e:
        # Clean up files in case of error
        if 'input_filepath' in locals() and os.path.exists(input_filepath):
            os.remove(input_filepath)
        if 'output_filepath' in locals() and os.path.exists(output_filepath):
            os.remove(output_filepath)
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download(filename):
    """Handle the download of the compressed file"""
    try:
        filepath = os.path.join(app.config['COMPRESSED_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404

        # Get original filename without timestamp
        original_filename = filename.split('_')[0] + '.zip'
        
        @after_this_request
        def cleanup(response):
            try:
                # Remove the file after it has been downloaded
                os.remove(filepath)
            except Exception as e:
                print(f"Error cleaning up file: {e}")
            return response

        return send_file(
            filepath,
            as_attachment=True,
            download_name=original_filename  # This ensures the user gets a clean filename
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
