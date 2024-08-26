from flask import Flask, render_template, request, redirect, url_for
import os
import subprocess
import re
import shutil
import ffmpeg
from datetime import datetime

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    def move_image(src_path, dst_folder):
        if not os.path.exists(dst_folder):
            os.makedirs(dst_folder)
        
        if os.path.isfile(src_path):
            dst_path = os.path.join(dst_folder, os.path.basename(src_path))
            try:
                shutil.move(src_path, dst_path)
                print(f"Image moved to {dst_path}")
            except Exception as e:
                print(f"Error: {e}")
        else:
            print(f"The path: {src_path} ,is not a legal file.")

    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file:
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        print("filepath: ", filepath)

        command = ["python", "detect.py", "--weights", "runs/train/exp24/weights/best.pt", "--img", "640", "--conf", "0.25", "--source", filepath]
        #result = subprocess.run(command, stderr=subprocess.PIPE, text=True)
        #result = subprocess.run(command, stderr=subprocess.PIPE,capture_output=True, text=True)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        last_line = None
        with open('output.txt', 'w') as f:
            for line in process.stderr:
                last_line = line.strip()
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if "dophin" in last_line:
                    f.write(f'{timestamp} [INFO] dolphin - {last_line}\n')
                if "shark" in last_line:
                    f.write(f'{timestamp} [WARNING] shark - {last_line}\n')
            #process.wait()

        #last_line = result.stderr.strip().split('\n')[-1]
        match = re.search(r"Results saved to (.+)", last_line)

        if match:
            result_path = match.group(1)
           
        result_path = os.path.basename(result_path)
        result_name = os.path.basename(filepath)
        print(result_path, ' ', result_name)
        result_name_type = result_name.split(".")[1]
        file_path = f"runs/detect/{result_path}/{result_name}"
        destination_folder = "static"
        image_path_copy = f"static/{result_name}"

        print("result path: ", image_path_copy)
        if result_name_type == "mp4":
            output_file = f'static/{result_name[:-4]}.mp4'
            try:
                (
                    ffmpeg
                    .input(file_path)
                    .output(output_file, vcodec='h264')
                    .run(overwrite_output=True)
                )
            except ffmpeg.Error as e:
                print(f"FFmpeg Error: {e.stderr.decode('utf8')}")
                return "Error occurred during conversion", 500
            return redirect(url_for('result_video', image_path_copy=image_path_copy))
        else:
            move_image(file_path, destination_folder)
            return redirect(url_for('result_image', image_path_copy=image_path_copy))
        

@app.route('/result_image')
def result_image():
    image_path_copy = request.args.get('image_path_copy')
    return render_template('result_image.html', image_path_copy=image_path_copy)

@app.route('/result_video')
def result_video():
    image_path_copy = request.args.get('image_path_copy')

    return render_template('result_video.html', image_path_copy=image_path_copy)

if __name__ == '__main__':
    app.run(debug=True)
