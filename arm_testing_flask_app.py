from flask import Flask, render_template, redirect, url_for, flash
import requests

app = Flask(__name__)
app.secret_key = 'robotic_arm_control'  # Necessary for flash messages

ESP32_SERVER_IP = '192.168.43.79'  # Replace with your ESP32 server IP address

def send_command_to_esp32(command):
    url = f'http://{ESP32_SERVER_IP}:8080/{command}'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            return {"message": "Failed to execute command"}
    except requests.exceptions.RequestException as e:
        return {"message": str(e)}

@app.route('/')
def index():
    return render_template('arm_interface.html')

@app.route('/move_shoulder_up')
def move_shoulder_up():
    result = send_command_to_esp32('move_shoulder_up')
    flash(result['message'], 'success' if 'moved' in result['message'] else 'danger')
    return redirect(url_for('index'))

@app.route('/move_shoulder_down')
def move_shoulder_down():
    result = send_command_to_esp32('move_shoulder_down')
    flash(result['message'], 'success' if 'moved' in result['message'] else 'danger')
    return redirect(url_for('index'))

@app.route('/expand_elbow')
def expand_elbow():
    result = send_command_to_esp32('expand_elbow')
    flash(result['message'], 'success' if 'expanded' in result['message'] else 'danger')
    return redirect(url_for('index'))

@app.route('/close_elbow')
def close_elbow():
    result = send_command_to_esp32('close_elbow')
    flash(result['message'], 'success' if 'closed' in result['message'] else 'danger')
    return redirect(url_for('index'))

@app.route('/open_gripper')
def open_gripper():
    result = send_command_to_esp32('open_gripper')
    flash(result['message'], 'success' if 'opened' in result['message'] else 'danger')
    return redirect(url_for('index'))

@app.route('/close_gripper')
def close_gripper():
    result = send_command_to_esp32('close_gripper')
    flash(result['message'], 'success' if 'closed' in result['message'] else 'danger')
    return redirect(url_for('index'))

@app.route('/expand_arm')
def expand_arm():
    result = send_command_to_esp32('expand_arm')
    flash(result['message'], 'success' if 'expanded' in result['message'] else 'danger')
    return redirect(url_for('index'))

@app.route('/close_arm')
def close_arm():
    result = send_command_to_esp32('close_arm')
    flash(result['message'], 'success' if 'closed' in result['message'] else 'danger')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
