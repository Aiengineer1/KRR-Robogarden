import machine
import network
import uasyncio as asyncio
import ujson as json

# Motor controller pins for the robotic car
motor_right_in1 = machine.Pin(15, machine.Pin.OUT)
motor_right_in2 = machine.Pin(2, machine.Pin.OUT)
motor_right_ena = machine.PWM(machine.Pin(4), freq=1000)
motor_left_in1 = machine.Pin(13, machine.Pin.OUT)
motor_left_in2 = machine.Pin(12, machine.Pin.OUT)
motor_left_enb = machine.PWM(machine.Pin(14), freq=1000)

# Ultrasonic sensor pins
trigger = machine.Pin(27, machine.Pin.OUT)
echo = machine.Pin(26, machine.Pin.IN)

# IR sensor pin
ir_sensor = machine.Pin(25, machine.Pin.IN)

# Robotic arm pins and classes
class RoboticArm:
    def __init__(self, pin_shoulder, pin_elbow, pin_gripper):
        self.pin_shoulder = machine.Pin(pin_shoulder, machine.Pin.OUT)
        self.pin_elbow = machine.Pin(pin_elbow, machine.Pin.OUT)
        self.pin_gripper = machine.Pin(pin_gripper, machine.Pin.OUT)
        
        self.current_angle_shoulder = 0
        self.current_angle_elbow = 0
        self.current_angle_gripper = 0

    def angle_to_duty(self, angle, min_duty=40, max_duty=115):
        return int(min_duty + (angle / 180) * (max_duty - min_duty))

    async def move_servo(self, pin, angle, freq, current_angle_attr):
        pwm = machine.PWM(pin, freq=freq)
        current_angle = getattr(self, current_angle_attr)
        steps = max(int(abs(angle - current_angle) / 5), 1)
        step_angle = (angle - current_angle) / steps

        for _ in range(steps):
            current_angle += step_angle
            duty = self.angle_to_duty(current_angle)
            pwm.duty(int(duty))
            await asyncio.sleep_ms(20)

        pwm.duty(self.angle_to_duty(angle))
        await asyncio.sleep(0.5)
        pwm.deinit()
        pin.init(machine.Pin.IN)
        print(f"Servo is at {angle} degrees")
        setattr(self, current_angle_attr, angle)

    async def move_shoulder(self, angle):
        await self.move_servo(self.pin_shoulder, angle, 60, 'current_angle_shoulder')

    async def move_elbow(self, angle):
        await self.move_servo(self.pin_elbow, angle, 70, 'current_angle_elbow')

    async def move_gripper(self, angle):
        await self.move_servo(self.pin_gripper, angle, 30, 'current_angle_gripper')

    async def move_shoulder_up(self):
        await self.move_shoulder(180)

    async def move_shoulder_down(self):
        await self.move_shoulder(40)

    async def expand_elbow(self):
        await self.move_elbow(180)

    async def close_elbow(self):
        await self.move_elbow(0)

    async def open_gripper(self):
        await self.move_gripper(35)

    async def close_gripper(self):
        await self.move_gripper(55)
    
    async def expand_arm(self):
        await self.move_shoulder_up()
        await self.expand_elbow()
    
    async def close_arm(self):
        await self.close_elbow()
        await self.move_shoulder_down()

    def get_current_state(self):
        return {
            "shoulder": self.current_angle_shoulder,
            "elbow": self.current_angle_elbow,
            "gripper": self.current_angle_gripper
        }

async def handle_client_car(reader, writer):
    try:
        while True:
            request = await reader.read(1024)
            if not request:
                break

            request_line = request.decode().split('\r\n')[0]
            method, path, _ = request_line.split()

            if method == 'GET' and path.startswith('/move'):
                query = path.split('?')[-1]
                params = {kv.split('=')[0]: kv.split('=')[1] for kv in query.split('&') if '=' in kv}
                await control_movement(params, writer)
            else:
                response = 'HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\nNot Found'
                writer.write(response.encode('utf-8'))
                await writer.drain()

    except asyncio.CancelledError:
        print("Client connection cancelled")
    except Exception as e:
        print(f"Error in handle_client_car: {e}")
    finally:
        writer.close()

async def handle_client_arm(reader, writer):
    request_line = await reader.readline()
    method, path, protocol = request_line.decode().strip().split()

    try:
        if method == 'GET' and path == '/move_shoulder_up':
            await robotic_arm.move_shoulder_up()
            response = json.dumps({"message": "Shoulder moved up"})
        elif method == 'GET' and path == '/move_shoulder_down':
            await robotic_arm.move_shoulder_down()
            response = json.dumps({"message": "Shoulder moved down"})
        elif method == 'GET' and path == '/expand_elbow':
            await robotic_arm.expand_elbow()
            response = json.dumps({"message": "Elbow expanded"})
        elif method == 'GET' and path == '/close_elbow':
            await robotic_arm.close_elbow()
            response = json.dumps({"message": "Elbow closed"})
        elif method == 'GET' and path == '/open_gripper':
            await robotic_arm.open_gripper()
            response = json.dumps({"message": "Gripper opened"})
        elif method == 'GET' and path == '/close_gripper':
            await robotic_arm.close_gripper()
            response = json.dumps({"message": "Gripper closed"})
        elif method == 'GET' and path == '/expand_arm':
            await robotic_arm.expand_arm()
            response = json.dumps({"message": "Arm expanded"})
        elif method == 'GET' and path == '/close_arm':
            await robotic_arm.close_arm()
            response = json.dumps({"message": "Arm closed"})
        else:
            response = "HTTP/1.1 404 Not Found\r\n\r\n"

        writer.write(response.encode())
        await writer.drain()

    except Exception as e:
        print(f"Error in handle_client_arm: {e}")
        response = "HTTP/1.1 500 Internal Server Error\r\n\r\nInternal Server Error"
        writer.write(response.encode())
        await writer.drain()

    finally:
        writer.close()

async def control_movement(params, writer):
    try:
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
                    await asyncio.sleep_ms(50)  # Wait for 50 milliseconds
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

# Utility functions
def measure_distance():
    # Ensure trigger is low
    trigger.off()
    await asyncio.sleep_us(2)

    # Send a 10us pulse to trigger
    trigger.on()
    await asyncio.sleep_us(10)
    trigger.off()

    # Measure the duration of the pulse on echo pin
    pulse_duration = machine.time_pulse_us(echo, 1, 30000)  # Timeout of 30ms (30,000 us)

    if pulse_duration > 0:
        # Calculate distance in cm
        distance = pulse_duration / 58  # 58 us per cm (speed of sound)
    else:
        distance = 999  # Out of range

    return distance

def move(direction, speed):
    if direction == "forward":
        motor_left_in1.on()
        motor_left_in2.off()
        motor_right_in1.on()
        motor_right_in2.off()
    elif direction == "backward":
        motor_left_in1.off()
        motor_left_in2.on()
        motor_right_in1.off()
        motor_right_in2.on()
    elif direction == "left":
        motor_left_in1.off()
        motor_left_in2.on()
        motor_right_in1.on()
        motor_right_in2.off()
    elif direction == "right":
        motor_left_in1.on()
        motor_left_in2.off()
        motor_right_in1.off()
        motor_right_in2.on()
    elif direction == "stop":
        motor_left_in1.off()
        motor_left_in2.off()
        motor_right_in1.off()
        motor_right_in2.off()

    motor_left_enb.duty(speed)
    motor_right_ena.duty(speed)

def set_speed(speed):
    motor_left_enb.duty(speed)
    motor_right_ena.duty(speed)

# Create instances
robotic_arm = RoboticArm(pin_shoulder=21, pin_elbow=22, pin_gripper=23)

# Set up WiFi
ssid = 'OPPO A54'
password = '11111111'

station = network.WLAN(network.STA_IF)
station.active(True)
station.connect(ssid, password)

while not station.isconnected():
    pass

print('WiFi Connected')
print('IP address:', station.ifconfig()[0])

# Start the HTTP servers
async def start_servers():
    car_server = await asyncio.start_server(handle_client_car, "0.0.0.0", 8080)
    arm_server = await asyncio.start_server(handle_client_arm, "0.0.0.0", 8081)

    print(f'Car Server running on {car_server.sockets[0].getsockname()}')
    print(f'Arm Server running on {arm_server.sockets[0].getsockname()}')

try:
    asyncio.run(start_servers())
except KeyboardInterrupt:
    print('Interrupted')
finally:
    station.disconnect()
    station.active(False)
    print('WiFi Disconnected')
