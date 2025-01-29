import machine
import utime
import time

# Motor controller pins
motor_right_in1 = machine.Pin(15, machine.Pin.OUT)
motor_right_in2 = machine.Pin(2, machine.Pin.OUT)
motor_right_ena = machine.PWM(machine.Pin(4))  # Use PWM for speed control
motor_left_in1 = machine.Pin(13, machine.Pin.OUT)
motor_left_in2 = machine.Pin(12, machine.Pin.OUT)
motor_left_enb = machine.PWM(machine.Pin(14))  # Use PWM for speed control

# Set PWM frequency
motor_right_ena.freq(1000)  # 1 kHz
motor_left_enb.freq(1000)  # 1 kHz

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

    # Wait for the echo pin to go high (start of the pulse)
    while echo.value() == 0:
        pass
    start = time.ticks_us()

    # Wait for the echo pin to go low (end of the pulse)
    while echo.value() == 1:
        pass
    end = time.ticks_us()

    # Calculate the duration of the pulse
    duration = time.ticks_diff(end, start)

    # Calculate the distance (duration * speed of sound / 2)
    distance = (duration * 0.0343) / 2

    return distance

def set_speed(speed):
    # Set PWM duty cycle for motor enable pins
    motor_right_ena.duty_u16(int(speed * 65535 / 100))
    motor_left_enb.duty_u16(int(speed * 65535 / 100))

def move(direction, speed):
    
    if direction == "backward":
        motor_right_in1.value(1)
        motor_right_in2.value(0)
        motor_left_in1.value(1)
        motor_left_in2.value(0)
    elif direction == "forward":
        motor_right_in1.value(0)
        motor_right_in2.value(1)
        motor_left_in1.value(0)
        motor_left_in2.value(1)            
    elif direction == "left":
        motor_right_in1.value(0)
        motor_right_in2.value(1)
        motor_left_in1.value(1)
        motor_left_in2.value(0)
    elif direction == "right":
        motor_right_in1.value(1)
        motor_right_in2.value(0)
        motor_left_in1.value(0)
        motor_left_in2.value(1)
    elif direction == "stop":
        motor_right_in1.value(0)
        motor_right_in2.value(0)
        motor_left_in1.value(0)
        motor_left_in2.value(0)
    
    set_speed(speed)

while True:
    move_direction = input("Enter direction (forward/backward/left/right/stop): ")
    if move_direction == "stop":
        move(move_direction, 0)  # Stop the car
        print("Car stopped.")
        break  # Exit the loop
    
    distance = measure_distance()
    print(distance)
    if distance < 20:
        speed = 20
    elif distance < 50:
        speed = 50
    else:
        speed = 100
            
    move(move_direction, speed)
    print(f"Moving {move_direction}.")

    if move_direction == "backward":
        while True:
            distance = measure_distance()
            print(ir_sensor.value(),distance)
            # Check IR sensor value
            if ir_sensor.value() == 0:
                print(ir_sensor.value())
                if distance < 5 or move_direction == "stop":
                    move("stop", 0)
                    print("Object detected! Car stopped.")
                elif distance < 20 or move_direction == "right":
                    move("right", speed)
                    print("Object detected! Moving right.")
                elif distance < 50 or move_direction == "left":
                    move("left", speed)
                    print("Object detected! Moving left.")
                else:
                    move("forward", speed)
                    print("Object detected! Moving forward.")
            else:
                move("backward", speed)
                print("Moving backward.")
                
            utime.sleep(0.1)  # Small delay to avoid excessive CPU usage
            move_direction = input("Enter direction (forward/backward/left/right/stop): ")
