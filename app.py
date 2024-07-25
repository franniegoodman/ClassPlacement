import os
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
from ClassPlacement import makeClasses 

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DOWNLOAD_FOLDER'] = 'downloads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part'
        file = request.files['file']
        if file.filename == '':
            return 'No selected file'
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # user input
            user_input = request.form['user_input']
            
            # process CSV
            output_filename = 'output_' + filename
            output_filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], output_filename)
            makeClasses(filepath, output_filepath, int(user_input))
            
            return send_file(output_filepath, as_attachment=True)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=8080)