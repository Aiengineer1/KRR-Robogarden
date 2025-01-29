import network
import machine
import uasyncio as asyncio
import time
import ujson

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

async def handle_client(reader, writer):
    try:
        params = {}

        async def control_movement():
            try:
                while True:
                    direction = params.get('direction')

                    if not direction:
                        response = 'HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\n\r\n{"status": "error", "message": "Invalid parameters"}'
                        writer.write(response.encode('utf-8'))
                        await writer.drain()
                        await writer.aclose()
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
                                # wait 300 ms
                                await asyncio.sleep_ms(50)
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

                    # Prepare JSON response with distance, speed, status, and direction
                    response_data = {
                        "distance": distance,
                        "speed": speed,
                        "status": "running",
                        "direction": direction  # Assuming forward direction for now
                    }

                    # Prepare HTTP response with JSON data
                    http_response = 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n'
                    http_response += ujson.dumps(response_data)

                    # Send response
                    writer.write(http_response.encode('utf-8'))
                    await writer.drain()

                    # Adjust speed every 100 ms
                    await asyncio.sleep_ms(100)

            except Exception as e:
                print(f"Error in control_movement: {e}")
                response = 'HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/plain\r\n\r\nInternal Server Error'
                writer.write(response.encode('utf-8'))
                await writer.drain()
            finally:
                writer.close()  # Close the writer when control_movement ends

        async def update_request_variables():
            nonlocal params
            try:
                request = await reader.read(1024)
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
                    await control_movement()
                else:
                    response = 'HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\nNot Found'
                    writer.write(response.encode('utf-8'))
                    await writer.drain()
            except Exception as e:
                response = f"Error in update_request_variables: {e}"
            finally:
                writer.close()  # Close the writer when update_request_variables ends

        await update_request_variables()

    except asyncio.CancelledError:
        response = "Client connection cancelled"
    except Exception as e:
        response = f"Error in handle_client: {e}"
    finally:
        writer.close()  # Close the writer in the outermost try block

async def main():
    ssid = "OPPO A54"
    password = "11111111"
    station = network.WLAN(network.STA_IF)
    station.active(True)
    station.connect(ssid, password)

    while not station.isconnected():
        await asyncio.sleep_ms(1000)

    print('Connection successful')
    print(station.ifconfig())

    server = await asyncio.start_server(handle_client, '0.0.0.0', 8080)  # Use port 8080 instead of 80
    print('Server running on http://0.0.0.0:8080')

    try:
        while True:
            await asyncio.sleep_ms(1000)  # Keep the server running
    except KeyboardInterrupt:
        print("Server stopped")

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Server stopped")




