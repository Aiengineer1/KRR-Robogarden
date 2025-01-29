from machine import Pin, PWM
import ujson as json

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

    def move_servo(self, pin, angle, freq, current_angle_attr):
        pwm = PWM(pin, freq=freq)
        current_angle = getattr(self, current_angle_attr)
        steps = max(int(abs(angle - current_angle) / 5), 1)  # Increase step resolution for smoother movement
        step_angle = (angle - current_angle) / steps

        for _ in range(steps):
            current_angle += step_angle
            duty = self.angle_to_duty(current_angle)
            pwm.duty(int(duty))
            time.sleep(0.02)  # Adjust sleep time for smoother movement

        # Final position
        pwm.duty(self.angle_to_duty(angle))
        time.sleep(0.5)  # Give the servo some time to settle
        pwm.deinit()
        pin.init(Pin.IN)  # Reset pin to input to clear state
        print(f"Servo is at {angle} degrees")
        setattr(self, current_angle_attr, angle)

    def move_shoulder(self, angle):
        self.move_servo(self.pin_shoulder, angle, 60, 'current_angle_shoulder')

    def move_elbow(self, angle):
        self.move_servo(self.pin_elbow, angle, 70, 'current_angle_elbow')

    def move_gripper(self, angle):
        self.move_servo(self.pin_gripper, angle, 50, 'current_angle_gripper')

    def move_shoulder_up(self):
        self.move_shoulder(180)

    def move_shoulder_down(self):
        self.move_shoulder(40)

    def expand_elbow(self):
        self.move_elbow(180)

    def close_elbow(self):
        self.move_elbow(0)

    def open_gripper(self):
        self.move_gripper(35)

    def close_gripper(self):
        self.move_gripper(180)
        
    def expand_arm(self):
        self.move_shoulder_up()
        self.expand_elbow()
    
    def close_arm(self):
        self.close_elbow()
        self.move_shoulder_down()

    def get_current_state(self):
        return {
            "shoulder": self.current_angle_shoulder,
            "elbow": self.current_angle_elbow,
            "gripper": self.current_angle_gripper
        }


import usocket as socket
import ujson as json
import network
import time

ssid = "OPPO A54"
password = "11111111"
robotic_arm = RoboticArm(pin_shoulder=23, pin_elbow=22, pin_gripper=21)

# Function to handle HTTP client requests
def handle_client(client_sock):
    request = client_sock.recv(1024).decode()
    method, path, protocol = request.split('\r\n')[0].split()

    if method == 'GET' and path == '/move_shoulder_up':
        robotic_arm.move_shoulder_up()
        response = json.dumps({"message": "Shoulder moved up"})
    elif method == 'GET' and path == '/move_shoulder_down':
        robotic_arm.move_shoulder_down()
        response = json.dumps({"message": "Shoulder moved down"})
    elif method == 'GET' and path == '/expand_elbow':
        robotic_arm.expand_elbow()
        response = json.dumps({"message": "Elbow expanded"})
    elif method == 'GET' and path == '/close_elbow':
        robotic_arm.close_elbow()
        response = json.dumps({"message": "Elbow closed"})
    elif method == 'GET' and path == '/open_gripper':
        robotic_arm.open_gripper()
        response = json.dumps({"message": "Gripper opened"})
    elif method == 'GET' and path == '/close_gripper':
        robotic_arm.close_gripper()
        response = json.dumps({"message": "Gripper closed"})
    elif method == 'GET' and path == '/expand_arm':
        robotic_arm.expand_arm()
        response = json.dumps({"message": "Arm expanded"})
    elif method == 'GET' and path == '/close_arm':
        robotic_arm.close_arm()
        response = json.dumps({"message": "Arm closed"})
    else:
        response = "HTTP/1.1 404 Not Found\r\n\r\n"

    client_sock.send(response.encode())
    client_sock.close()

# Main function to handle Wi-Fi connection and start the HTTP server
def main():
    station = network.WLAN(network.STA_IF)
    station.active(True)
    station.connect(ssid, password)

    while not station.isconnected():
        time.sleep(1)

    print('Connection successful')
    print(station.ifconfig())

    server = socket.socket()
    server.bind(('0.0.0.0', 8080))
    server.listen(5)
    print('Server running on http://0.0.0.0:8080')

    try:
        while True:
            client_sock, addr = server.accept()
            handle_client(client_sock)
    except KeyboardInterrupt:
        print("Server stopped")

# Start the main function
main()
