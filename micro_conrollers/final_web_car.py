import network
from machine import Pin, PWM
import ujson as json
import time
import ure as re
import usocket as socket
import _thread

# Motor controller pins for the robotic car
motor_right_in1 = Pin(15, Pin.OUT)
motor_right_in2 = Pin(2, Pin.OUT)
motor_right_ena = PWM(Pin(4), freq=1000)
motor_left_in1 = Pin(13, Pin.OUT)
motor_left_in2 = Pin(12, Pin.OUT)
motor_left_enb = PWM(Pin(14), freq=1000)

# Ultrasonic sensor pins
trigger = Pin(27, Pin.OUT)
echo = Pin(26, Pin.IN)

# IR sensor pin
ir_sensor = Pin(25, Pin.IN)

# Robotic arm servo control pins
pin_shoulder = Pin(23, Pin.OUT)
pin_elbow = Pin(22, Pin.OUT)
pin_gripper = Pin(21, Pin.OUT)

class RoboticArm:
    def __init__(self):
        self.current_angle_shoulder = 0
        self.current_angle_elbow = 0
        self.current_angle_gripper = 0

    def angle_to_duty(self, angle, min_duty=40, max_duty=115):
        return int(min_duty + (angle / 180) * (max_duty - min_duty))

    def move_servo(self, pin, angle, freq):
        pwm = PWM(pin, freq=freq)
        duty = self.angle_to_duty(angle)
        pwm.duty(duty)
        time.sleep(0.5)  # Adjust time as needed for servo to move
        pwm.deinit()
        pin.init(Pin.IN)  # Reset pin to input to clear state

    def move_shoulder(self, angle):
        self.move_servo(pin_shoulder, angle, 60)
        self.current_angle_shoulder = angle

    def move_elbow(self, angle):
        self.move_servo(pin_elbow, angle, 70)
        self.current_angle_elbow = angle

    def move_gripper(self, angle):
        self.move_servo(pin_gripper, angle, 30)
        self.current_angle_gripper = angle

def move_car(direction, speed):
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

def measure_distance():
    trigger.off()
    time.sleep_us(2)
    trigger.on()
    time.sleep_us(10)
    trigger.off()
    pulse_duration = machine.time_pulse_us(echo, 1, 30000)  # Timeout of 30ms (30,000 us)
    if pulse_duration > 0:
        distance = (pulse_duration * 0.0343) / 2
    else:
        distance = float('inf')  # No pulse received, set distance to infinity
    return distance

def handle_car_request(request):
    global robotic_arm
    # Parse request to get direction and speed
    # Example: GET /car?direction=forward&speed=50 HTTP/1.1
    direction = 'stop'
    speed = 0
    if request.find(b'direction=forward') != -1:
        direction = 'forward'
    elif request.find(b'direction=backward') != -1:
        direction = 'backward'
    elif request.find(b'direction=left') != -1:
        direction = 'left'
    elif request.find(b'direction=right') != -1:
        direction = 'right'
    elif request.find(b'direction=stop') != -1:
        direction = 'stop'
    if direction != 'stop':
        speed = int(re.findall(b'speed=(\d+)', request)[0])
    move_car(direction, speed)
    set_speed(speed)

def handle_arm_request(request, robotic_arm):
    # Parse request to determine which arm action to perform
    if request.find(b'/move_shoulder_up') != -1:
        robotic_arm.move_shoulder(180)
    elif request.find(b'/move_shoulder_down') != -1:
        robotic_arm.move_shoulder(40)
    elif request.find(b'/expand_elbow') != -1:
        robotic_arm.move_elbow(180)
    elif request.find(b'/close_elbow') != -1:
        robotic_arm.move_elbow(0)
    elif request.find(b'/open_gripper') != -1:
        robotic_arm.move_gripper(35)
    elif request.find(b'/close_gripper') != -1:
        robotic_arm.move_gripper(55)

def handle_http_client(client_sock, robotic_arm):
    try:
        request = client_sock.recv(1024)
        if request:
            if request.find(b'/car') != -1:
                handle_car_request(request)
            elif request.find(b'/arm') != -1:
                handle_arm_request(request, robotic_arm)
            else:
                response = b'HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n'
                client_sock.send(response)
                client_sock.close()
                return
            response = b'HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n'
            client_sock.send(response)
        client_sock.close()
    except Exception as e:
        print("Exception in handle_http_client:", e)
        client_sock.close()

def main():
    try:
        global robotic_arm
        robotic_arm = RoboticArm()
        # Setup Wi-Fi connection
        ssid = "OPPO A54"
        password = "11111111"
        station = network.WLAN(network.STA_IF)
        station.active(True)
        station.connect(ssid, password)
        while not station.isconnected():
            time.sleep_ms(1000)
        print('Connection successful')
        print(station.ifconfig())
        # Setup HTTP server
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind(('0.0.0.0', 80))
        server_sock.listen(5)
        print('HTTP server running on port 80')
        # Handle incoming client connections
        while True:
            client_sock, addr = server_sock.accept()
            _thread.start_new_thread(handle_http_client, (client_sock, robotic_arm))
    except Exception as e:
        print("Exception in main:", e)

if __name__ == '__main__':
    main()
