import uasyncio as asyncio
from machine import Pin, PWM

# Function to map the angle (0 to 180) to duty cycle for shoulder servo
def angle_to_duty_for_shoulder(angle_shoulder):
    min_duty_shoulder = 40
    max_duty_shoulder = 115
    return int(min_duty_shoulder + (angle_shoulder / 180) * (max_duty_shoulder - min_duty_shoulder))

# Initialize GPIO pin for shoulder servo
pin_shoulder = Pin(23, Pin.OUT)

# Function to move the shoulder servo to a specified angle
async def move_shoulder(angle_shoulder):
    pwm_shoulder = PWM(pin_shoulder, freq=60)
    duty_shoulder = angle_to_duty_for_shoulder(angle_shoulder)
    print(f"Setting shoulder servo to {angle_shoulder} degrees (duty cycle: {duty_shoulder})")
    pwm_shoulder.duty(duty_shoulder)
    await asyncio.sleep(1)  # Give the servo some time to move
    pwm_shoulder.deinit()
    pin_shoulder.init(Pin.IN)  # Reset pin to input to clear state
    print(f"Shoulder servo is at {angle_shoulder} degrees")

# Function to open the shoulder
async def open_shoulder():
    await move_shoulder(180)  # Open the shoulder

# Function to close the shoulder
async def close_shoulder():
    await move_shoulder(40)  # Close the shoulder

# Main coroutine to run shoulder control tasks
async def main_shoulder():
    await open_shoulder()  # Open the shoulder
    await asyncio.sleep(1)  # Wait for 1 second
    await close_shoulder()  # Close the shoulder

# Run the main coroutine
try:
    asyncio.run(main_shoulder())
except Exception as e:
    print(f"Exception: {e}")
