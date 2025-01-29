import uasyncio as asyncio
from machine import Pin, PWM, time_pulse_us
import network
import ujson as json
import time

# Robotic Arm class definition
class RoboticArm:
    def __init__(self, pin_shoulder, pin_elbow, pin_gripper):
        self.pin_shoulder = Pin(pin_shoulder, Pin.OUT)
        self.pin_elbow = Pin(pin_elbow, Pin.OUT)
        self.pin_gripper = Pin(pin_gripper, Pin.OUT)
        
        self.current_angle_shoulder = 0
        self.current_angle_elbow = 0
        self.current_angle_gripper = 0

    def angle_to_duty(self, angle, min_duty=40, max_duty=115):
        return int(min_duty + (angle / 180) * (max_duty - min_duty))

    async def move_servo(self, pin, angle, freq, current_angle_attr):
        pwm = PWM(pin, freq=freq)
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
        pin.init(Pin.IN)
        print(f"Servo is at {angle} degrees")
        setattr(self, current_angle_attr, angle)

    async def move_shoulder(self, angle):
        await self.move_servo(self.pin_shoulder, angle, 60, 'current_angle_shoulder')

    async def move_elbow(self, angle):
        await self.move_servo(self.pin_elbow, angle, 70, 'current_angle_elbow')

    async def move_gripper(self, angle):
        await self.move_servo(self.pin_gripper, angle, 70, 'current_angle_gripper')

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

# Car control functions
motor_right_in1 = Pin(15, Pin.OUT)
motor_right_in2 = Pin(2, Pin.OUT)
motor_right_ena = PWM(Pin(4), freq=1000)
motor_left_in1 = Pin(13, Pin.OUT)
motor_left_in2 = Pin(12, Pin.OUT)
motor_left_enb = PWM(Pin(14), freq=1000)
trigger = Pin(27, Pin.OUT)
echo = Pin(26, Pin.IN)
ir_sensor = Pin(25, Pin.IN)

def measure_distance():
    trigger.off()
    time.sleep_us(2)
    trigger.on()
    time.sleep_us(10)
    trigger.off()
    pulse_duration = time_pulse_us(echo, 1, 30000)

    if pulse_duration > 0:
        distance = (pulse_duration * 0.0343) / 2
    else:
        distance = float('inf')
    return distance

def set_speed(speed):
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

    set_speed(speed)

# Server handling
async def handle_arm_request(path):
    try:
        if path == '/move_shoulder_up':
            await robotic_arm.move_shoulder_up()
            response = json.dumps({"message": "Shoulder moved up"})
        elif path == '/move_shoulder_down':
            await robotic_arm.move_shoulder_down()
            response = json.dumps({"message": "Shoulder moved down"})
        elif path == '/expand_elbow':
            await robotic_arm.expand_elbow()
            response = json.dumps({"message": "Elbow expanded"})
        elif path == '/close_elbow':
            await robotic_arm.close_elbow()
            response = json.dumps({"message": "Elbow closed"})
        elif path == '/open_gripper':
            await robotic_arm.open_gripper()
            response = json.dumps({"message": "Gripper opened"})
        elif path == '/close_gripper':
            await robotic_arm.close_gripper()
            response = json.dumps({"message": "Gripper closed"})
        elif path == '/expand_arm':
            await robotic_arm.expand_arm()
            response = json.dumps({"message": "Arm expanded"})
        elif path == '/close_arm':
            await robotic_arm.close_arm()
            response = json.dumps({"message": "Arm closed"})
        else:
            response = 'HTTP/1.1 404 Not Found\r\n\r\n'
        return response
    except Exception as e:
        print(f"Error in handle_arm_request: {e}")
        return 'HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/plain\r\n\r\nInternal Server Error'

async def handle_car_request(params):
    try:
        direction = params.get('direction')
        speed = params.get('speed')

        if not direction or not speed:
            return 'HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\n\r\n{"status": "error", "message": "Invalid parameters"}'

        ir_value = ir_sensor.value()
        distance = measure_distance()

        print(f"IR Sensor Value: {ir_value}")
        if ir_value == 0 and direction == "backward":
            direction = "forward"

        if distance < 10:
            adjusted_speed = 0
        elif distance < 20:
            adjusted_speed = 50
        else:
            adjusted_speed = 100

        move(direction, adjusted_speed)

        response_data = {
            "distance": distance,
            "speed": adjusted_speed,
            "status": "running",
            "direction": direction
        }

        http_response = 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n'
        http_response += json.dumps(response_data)
        return http_response
    except Exception as e:
        print(f"Error in handle_car_request: {e}")
        return 'HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/plain\r\n\r\nInternal Server Error'

async def handle_client(reader, writer):
    try:
        request = await reader.read(1024)
        if not request:
            return
        request = request.decode('utf-8')
        print(f"Received request: {request}")

        request_line = request.split('\r\n')[0]
        method, path, _ = request_line.split()

        if method == 'GET' and path.startswith('/arm'):
            response = await handle_arm_request(path)
        elif method == 'GET' and path.startswith('/move'):
            query = path.split('?')[-1]
            params = {kv.split('=')[0]: kv.split('=')[1] for kv in query.split('&') if '=' in kv}
            response = await handle_car_request(params)
        else:
            response = 'HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\nNot Found'

        writer.write(response.encode('utf-8'))
        await writer.drain()

    except Exception as e:
        print(f"Error in handle_client: {e}")
        response = 'HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/plain\r\n\r\nInternal Server Error'
        writer.write(response.encode('utf-8'))
        await writer.drain()

    finally:
        writer.close()

async def main():
    try:
        robotic_arm = RoboticArm(pin_shoulder=23, pin_elbow=22, pin_gripper=21)

        ssid = "Mohi"
        password = "12345678"
        station = network.WLAN(network.STA_IF)
        station.active(True)
        station.connect(ssid, password)

        while not station.isconnected():
            await asyncio.sleep_ms(1000)

        print('Connection successful')
        print(station.ifconfig())

        server = await asyncio.start_server(handle_client, '0.0.0.0', 8080)
        print('Server running on http://0.0.0.0:8080')

        while True:
            await asyncio.sleep(1)  # Keep event loop running

    except KeyboardInterrupt:
        print("Server stopped")

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Server stopped")

