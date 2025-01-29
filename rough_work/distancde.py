import machine
import time

# Define the pins
trigger = machine.Pin(27, machine.Pin.OUT)
echo = machine.Pin(26, machine.Pin.IN)

def get_distance():
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

while True:
    distance = get_distance()
    print("Distance: {:.2f} cm".format(distance))
    time.sleep(1)
