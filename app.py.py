# app.py
from flask import Flask, render_template, request, send_file
import os
import gzip
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def compress_file(input_file):
    """Compress the input file using gzip compression"""
    output_filename = input_file + '.gz'
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
        return 'No file uploaded', 400
    
    file = request.files['file']
    if file.filename == '':
        return 'No file selected', 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # Save the uploaded file
    file.save(filepath)
    
    # Compress the file
    compressed_filepath = compress_file(filepath)
    
    # Clean up the original file
    os.remove(filepath)
    
    # Send the compressed file
    return send_file(compressed_filepath, 
                    as_attachment=True,
                    download_name=os.path.basename(compressed_filepath))

if __name__ == '__main__':
    app.run(debug=True)
