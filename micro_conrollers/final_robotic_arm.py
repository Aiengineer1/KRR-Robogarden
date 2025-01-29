import uasyncio as asyncio
from machine import Pin, PWM
import network
import ujson as json  # Import ujson for JSON serialization

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
        steps = max(int(abs(angle - current_angle) / 5), 1)  # Increase step resolution for smoother movement
        step_angle = (angle - current_angle) / steps

        for _ in range(steps):
            current_angle += step_angle
            duty = self.angle_to_duty(current_angle)
            pwm.duty(int(duty))
            await asyncio.sleep_ms(20)  # Adjust sleep time for smoother movement

        # Final position
        pwm.duty(self.angle_to_duty(angle))
        await asyncio.sleep(0.5)  # Give the servo some time to settle
        pwm.deinit()
        pin.init(Pin.IN)  # Reset pin to input to clear state
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

async def handle_client(reader, writer):
    request_line = await reader.readline()
    method, path, protocol = request_line.decode().strip().split()

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
    writer.close()

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
    robotic_arm = RoboticArm(pin_shoulder=23, pin_elbow=22, pin_gripper=21)
    asyncio.run(main())
except KeyboardInterrupt:
    print("Server stopped")
