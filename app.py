# app.py
from flask import Flask, render_template, request, send_file, jsonify, after_this_request, make_response
import os
import zipfile
from werkzeug.utils import secure_filename
from datetime import datetime
from PIL import Image
import io
import mimetypes

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['COMPRESSED_FOLDER'] = 'compressed'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'pdf', 'doc', 'docx', 'txt'}

# Ensure required folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['COMPRESSED_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def compress_image(input_path, output_path, quality=60):
    """Compress image using PIL"""
    try:
        img = Image.open(input_path)
        # Convert RGBA to RGB if needed
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        # Save with reduced quality
        img.save(output_path, 'JPEG', quality=quality, optimize=True)
        return True
    except Exception as e:
        print(f"Image compression error: {e}")
        return False

def handle_file_compression(input_path, output_path, file_type):
    """Handle compression based on file type"""
    original_size = os.path.getsize(input_path)
    
    if file_type in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
        # For images, use PIL compression
        success = compress_image(input_path, output_path)
        if not success:
            # Fallback to ZIP if image compression fails
            with zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
                zipf.write(input_path, os.path.basename(input_path))
    else:
        # For other files, use ZIP compression
        with zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
            zipf.write(input_path, os.path.basename(input_path))
    
    compressed_size = os.path.getsize(output_path)
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

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    try:
        # Create unique filename
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        original_filename = secure_filename(file.filename)
        file_type = original_filename.rsplit('.', 1)[1].lower()
        base_filename = original_filename.rsplit('.', 1)[0]
        
        # Setup paths
        input_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{base_filename}_{timestamp}.{file_type}")
        output_filepath = os.path.join(app.config['COMPRESSED_FOLDER'], 
                                     f"{base_filename}_{timestamp}_compressed.{file_type}")
        
        # Save uploaded file
        file.save(input_filepath)
        
        # Compress based on file type
        original_size, compressed_size = handle_file_compression(input_filepath, output_filepath, file_type)
        
        # Calculate compression ratio
        compression_ratio = ((original_size - compressed_size) / original_size) * 100
        
        # Format sizes for display
        original_size_mb = original_size / (1024 * 1024)
        compressed_size_mb = compressed_size / (1024 * 1024)
        
        # Clean up original file
        os.remove(input_filepath)
        
        return jsonify({
            'success': True,
            'original_size': f"{original_size_mb:.2f} MB",
            'compressed_size': f"{compressed_size_mb:.2f} MB",
            'compression_ratio': f"{compression_ratio:.1f}%",
            'download_url': f"/download/{os.path.basename(output_filepath)}",
            'filename': original_filename
        })

    except Exception as e:
        # Clean up files in case of error
        for filepath in [input_filepath, output_filepath]:
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download(filename):
    """Handle file download with proper headers"""
    try:
        filepath = os.path.join(app.config['COMPRESSED_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404

        # Get the original filename without timestamp
        original_filename = filename.split('_')[0] + '.' + filename.rsplit('.', 1)[1]

        # Get proper MIME type
        mime_type, _ = mimetypes.guess_type(filepath)
        if mime_type is None:
            mime_type = 'application/octet-stream'

        # Send file with proper headers
        response = make_response(send_file(
            filepath,
            mimetype=mime_type,
            as_attachment=True,
            download_name=original_filename
        ))

        # Add headers to help with download
        response.headers['Content-Disposition'] = f'attachment; filename="{original_filename}"'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Cache-Control'] = 'no-cache'

        @after_this_request
        def cleanup(response):
            try:
                os.remove(filepath)
            except Exception as e:
                print(f"Error cleaning up file: {e}")
            return response

        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
