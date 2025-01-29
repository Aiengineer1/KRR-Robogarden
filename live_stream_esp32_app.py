from flask import Flask, render_template, redirect, url_for, request, flash, Response
from ultralytics import YOLO
import aiohttp
import aiofiles
import asyncio
import cv2

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'detect_live'  # Necessary for flash messages

# Load a model
model = YOLO("yolov8m.pt")  # load an official model

ESP32_CAM_IP = '192.168.69.212'  # Replace with your ESP32-CAM IP address
REQUEST_TIMEOUT = 5  # Timeout for HTTP requests in seconds
MAX_RETRIES = 3  # Maximum number of retries for failed requests

async def send_request(url):
    retries = 0
    async with aiohttp.ClientSession() as session:
        while retries < MAX_RETRIES:
            try:
                async with session.get(url, timeout=REQUEST_TIMEOUT) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        app.logger.warning(f'Unexpected status code: {response.status}')
            except aiohttp.ClientError as e:
                app.logger.error(f'RequestException occurred: {e}')
            retries += 1
            await asyncio.sleep(1)  # Wait before retrying
    return None

@app.route('/')
def index():
    return render_template('interface_esp32cam.html')

@app.route('/stream_on')
def stream_on():
    url = f'http://{ESP32_CAM_IP}/stream_on'
    response = asyncio.run(send_request(url))
    if response:
        flash('Stream started successfully', 'success')
    else:
        flash('Failed to start stream', 'danger')
    return redirect(url_for('index'))

@app.route('/stream_off')
def stream_off():
    url = f'http://{ESP32_CAM_IP}/stream_off'
    response = asyncio.run(send_request(url))
    if response:
        flash('Stream stopped successfully', 'success')
    else:
        flash('Failed to stop stream', 'danger')
    return redirect(url_for('index'))

@app.route('/snapshot')
def take_snapshot():
    url = f'http://{ESP32_CAM_IP}/snapshot'
    response = asyncio.run(send_request(url))
    if response:
        async def save_snapshot():
            async with aiofiles.open('static/snapshot.jpg', 'wb') as f:
                await f.write(response)
        asyncio.run(save_snapshot())
        image_url = url_for('static', filename='snapshot.jpg')
        return render_template('snapshot.html', image_url=image_url)
    else:
        flash('Failed to capture snapshot', 'danger')
        return redirect(url_for('index'))

def generate_frames():
    cap = cv2.VideoCapture(f'http://{ESP32_CAM_IP}/stream')
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        success, frame = loop.run_until_complete(loop.run_in_executor(None, cap.read))
        if not success:
            break
        else:
            # Apply YOLOv8 detection
            results = model(frame)
            annotated_frame = results[0].plot()

            ret, buffer = cv2.imencode('.jpg', annotated_frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/stream')
def live_stream():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True)
