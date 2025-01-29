import uasyncio as asyncio
from machine import Pin, PWM

# Function to map the angle (0 to 180) to duty cycle for elbow servo
def angle_to_duty_for_elbow(angle_elbow):
    min_duty_elbow = 40
    max_duty_elbow = 115
    return int(min_duty_elbow + (angle_elbow / 180) * (max_duty_elbow - min_duty_elbow))

# Initialize GPIO pin for elbow servo
pin_elbow = Pin(22, Pin.OUT)

# Function to move the elbow servo to a specified angle
async def move_elbow(angle_elbow):
    pwm_elbow = PWM(pin_elbow, freq=60)
    duty_elbow = angle_to_duty_for_elbow(angle_elbow)
    print(f"Setting elbow servo to {angle_elbow} degrees (duty cycle: {duty_elbow})")
    pwm_elbow.duty(duty_elbow)
    await asyncio.sleep(1)  # Give the servo some time to move
    pwm_elbow.deinit()
    pin_elbow.init(Pin.IN)  # Reset pin to input to clear state
    print(f"Elbow servo is at {angle_elbow} degrees")

# Function to open the elbow
async def open_elbow():
    await move_elbow(160)  # Open the elbow

# Function to close the elbow
async def close_elbow():
    await move_elbow(45)  # Close the elbow

# Main coroutine to run elbow control tasks
async def main_elbow():
    await open_elbow()  # Open the elbow
    await asyncio.sleep(1)  # Wait for 1 second
    await close_elbow()  # Close the elbow

# Run the main coroutine
try:
    asyncio.run(main_elbow())
except Exception as e:
    print(f"Exception: {e}")
