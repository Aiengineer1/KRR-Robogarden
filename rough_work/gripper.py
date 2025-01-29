import uasyncio as asyncio
from machine import Pin, PWM

# Function to map the angle (0 to 180) to duty cycle for gripper servo
def angle_to_duty_for_gripper(angle_gripper):
    min_duty_gripper = 40
    max_duty_gripper = 115
    return int(min_duty_gripper + (angle_gripper / 180) * (max_duty_gripper - min_duty_gripper))

# Initialize GPIO pin for gripper servo
pin_gripper = Pin(21, Pin.OUT)

# Function to move the gripper servo to a specified angle
async def move_gripper(angle_gripper):
    pwm_gripper = PWM(pin_gripper, freq=30)
    duty_gripper = angle_to_duty_for_gripper(angle_gripper)
    print(f"Setting gripper servo to {angle_gripper} degrees (duty cycle: {duty_gripper})")
    pwm_gripper.duty(duty_gripper)
    await asyncio.sleep(1)  # Give the servo some time to move
    pwm_gripper.deinit()
    pin_gripper.init(Pin.IN)  # Reset pin to input to clear state
    print(f"Gripper servo is at {angle_gripper} degrees")

# Function to open the gripper
async def open_gripper():
    await move_gripper(35)  # Open the gripper

# Function to close the gripper
async def close_gripper():
    await move_gripper(55)  # Close the gripper

# Main coroutine to run gripper control tasks
async def main_gripper():
    await open_gripper()  # Open the gripper
    await asyncio.sleep(1)  # Wait for 1 second
    await close_gripper()  # Close the gripper

# Run the main coroutine
try:
    asyncio.run(main_gripper())
except Exception as e:
    print(f"Exception: {e}")
