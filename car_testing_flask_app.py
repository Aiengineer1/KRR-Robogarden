from flask import Flask, request, render_template
import requests

app = Flask(__name__)

ESP32_SERVER_URL = 'http://192.168.43.79:8080/move'

@app.route('/')
def index():
    return render_template('car_interface.html')

@app.route('/move', methods=['GET'])
def control_car():
    direction = request.args.get('direction')
    speed = request.args.get('speed')

    if not direction or not speed:
        return render_template('car_interface.html', error="Missing parameters")

    try:
        response = requests.get(f'{ESP32_SERVER_URL}?direction={direction}&speed={speed}')
        response_data = response.json()

        # Print the response received from the ESP32 server
        print(f"Response from ESP32: {response_data}")

        return render_template('car_interface.html', response=response_data)
    except Exception as e:
        return render_template('car_interface.html', error=str(e))

if __name__ == '__main__':
    app.run(debug=True)
