import machine
import time
import ujson
import network 
import socket

# Motor controller pins
motor_right_in1 = machine.Pin(15, machine.Pin.OUT)
motor_right_in2 = machine.Pin(2, machine.Pin.OUT)
motor_right_ena = machine.PWM(machine.Pin(4), freq=1000)  # Use PWM for speed control
motor_left_in1 = machine.Pin(13, machine.Pin.OUT)
motor_left_in2 = machine.Pin(12, machine.Pin.OUT)
motor_left_enb = machine.PWM(machine.Pin(14), freq=1000)  # Use PWM for speed control

# Ultrasonic sensor pins
trigger = machine.Pin(27, machine.Pin.OUT)
echo = machine.Pin(26, machine.Pin.IN)

# IR sensor pin
ir_sensor = machine.Pin(25, machine.Pin.IN)

def measure_distance():
    # Ensure trigger is low
    trigger.off()
    time.sleep_us(2)

    # Send a 10us pulse to trigger
    trigger.on()
    time.sleep_us(10)
    trigger.off()

    # Measure the duration of the pulse on echo pin
    pulse_duration = machine.time_pulse_us(echo, 1, 30000)  # Timeout of 30ms (30,000 us)

    if pulse_duration > 0:
        # Calculate the distance (duration * speed of sound / 2)
        distance = (pulse_duration * 0.0343) / 2
    else:
        distance = float('inf')  # No pulse received, set distance to infinity

    return distance

def set_speed(speed):
    # Set PWM duty cycle for motor enable pins
    motor_right_ena.duty(int(speed * 1023 / 100))
    motor_left_enb.duty(int(speed * 1023 / 100))

def move(direction, speed):
    if direction == "backward":
        motor_right_in1.on()
        motor_right_in2.off()
        motor_left_in1.on()
        motor_left_in2.off()
    elif direction == "forward":
        motor_right_in1.off()
        motor_right_in2.on()
        motor_left_in1.off()
        motor_left_in2.on()
    elif direction == "left":
        motor_right_in1.off()
        motor_right_in2.on()
        motor_left_in1.on()
        motor_left_in2.off()
    elif direction == "right":
        motor_right_in1.on()
        motor_right_in2.off()
        motor_left_in1.off()
        motor_left_in2.on()
    elif direction == "stop":
        motor_right_in1.off()
        motor_right_in2.off()
        motor_left_in1.off()
        motor_left_in2.off()

def control_movement(params):
    try:
        while True:
            direction = params.get('direction')

            if not direction:
                print('Invalid parameters: Missing direction')
                return

            # Read IR sensor value
            ir_value = ir_sensor.value()

            # Measure distance
            distance = measure_distance()

            if direction != "stop":
                if ir_value == 0 and direction == "backward":
                    direction = "forward"
                    params['direction'] = "forward"
                
                # Adjust speed based on distance
                if direction != "backward":
                    if distance < 50:
                        speed = 0   # Slow down if obstacle is close
                        time.sleep_ms(50)
                        direction = "backward"
                        params['direction'] = "backward"
                    elif distance < 100:
                        speed = 50  # Moderate speed if obstacle is moderately close
                    else:
                        speed = 100  # Full speed if no obstacle nearby
                else:
                    speed = 50
            else:
                speed = 0

            # Move with adjusted speed and direction
            move(direction, speed)
            set_speed(speed)

            # Print status (for debugging)
            print(f"Direction: {direction}, Distance: {distance}, Speed: {speed}, IR Value: {ir_value}")

            # Small delay before next iteration
            time.sleep_ms(100)

    except Exception as e:
        print(f"Error in control_movement: {e}")

def handle_client(client_sock, client_addr):
    try:
        params = {}

        def update_request_variables():
            nonlocal params
            try:
                request = client_sock.recv(1024)
                if not request:
                    return
                request = request.decode('utf-8')

                request_line = request.split('\r\n')[0]
                method, path, _ = request_line.split()

                if method == 'GET' and path.startswith('/move'):
                    query = path.split('?')[-1]
                    params = {kv.split('=')[0]: kv.split('=')[1] for kv in query.split('&') if '=' in kv}
                    if not params.get('direction'):
                        raise ValueError("Missing direction parameter")
                else:
                    response = 'HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\nNot Found'
                    client_sock.send(response.encode('utf-8'))
            except Exception as e:
                response = f"Error in update_request_variables: {e}"
            finally:
                client_sock.close()

        update_request_variables()

    except Exception as e:
        response = f"Error in handle_client: {e}"
    finally:
        client_sock.close()

def main():
    ssid = "OPPO A54"
    password = "11111111"
    station = network.WLAN(network.STA_IF)
    station.active(True)
    station.connect(ssid, password)

    while not station.isconnected():
        time.sleep_ms(1000)

    print('Connection successful')
    print(station.ifconfig())

    server = socket.socket()
    server.bind(('0.0.0.0', 8080))  # Use port 8080 instead of 80
    server.listen(5)
    print('Server running on http://0.0.0.0:8080')

    try:
        params = {}  # Initialize params dictionary for direction control
        client_sock = None

        # Start the control movement loop in a separate thread or coroutine
        control_movement_thread = machine.Thread(target=control_movement, args=(params,))
        control_movement_thread.start()

        while True:
            client_sock, client_addr = server.accept()
            handle_client(client_sock, client_addr)
    except KeyboardInterrupt:
        print("Server stopped")
    finally:
        if client_sock:
            client_sock.close()

try:
    main()
except KeyboardInterrupt:
    print("Server stopped")
