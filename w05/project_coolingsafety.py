import time
import smbus2 as smbus
from gpiozero import OutputDevice, Button, DigitalInputDevice
import hiwonder.ros_robot_controller_sdk as rrc
import hiwonder.Sonar as Sonar

# Touch sensor toggles a safety mode: ARMED (alarm ON) / DISARMED (alarm OFF).
# When ARMED, the sonar checks distance. If something is too close, the robot beeps and shows red lights.
# If nothing is too close, it shows green lights. When DISARMED, it shows blue lights.
# Temperature controls the fan automatically: hot -> fan ON, cool -> fan OFF.
# The program prints sensor readings (temperature, humidity, distance, light) continuously.

DIST_ALARM_MM = 300
TEMP_FAN_ON = 30.0
TEMP_FAN_OFF = 28.0
BUZZ_HZ = 1900

fanPin1 = OutputDevice(8)
fanPin2 = OutputDevice(7)

def set_fan(on):
    if on:
        fanPin1.on()
        fanPin2.off()
    else:
        fanPin1.off()
        fanPin2.off()

class AHT10:
    MEASURE = [0x33, 0x00]

    def __init__(self, bus=1, addr=0x38):
        self.bus = smbus.SMBus(bus)
        self.addr = addr
        time.sleep(0.2)

    def read(self):
        self.bus.write_i2c_block_data(self.addr, 0xAC, self.MEASURE)
        time.sleep(0.5)
        data = self.bus.read_i2c_block_data(self.addr, 0x00, 6)

        temp_raw = ((data[3] & 0x0F) << 16) | (data[4] << 8) | data[5]
        temp_c = (temp_raw * 200 / 1048576) - 50

        hum_raw = (((data[1] << 16) | (data[2] << 8) | data[3]) >> 4)
        hum = hum_raw * 100 / 1048576

        return round(temp_c, 1), round(hum, 1)

def main():
    board = rrc.Board()
    touch = Button(22)
    light = DigitalInputDevice(24, pull_up=True)

    sonar = Sonar.Sonar()
    sonar.setRGBMode(0)

    aht10 = AHT10()

    armed = False
    fan_on = False
    last_touch = False

    try:
        while True:
            pressed = touch.is_pressed
            if pressed and not last_touch:
                armed = not armed
                board.set_buzzer(1200, 0.1, 0.0, 1)
            last_touch = pressed

            temp_c, hum = aht10.read()

            dist = sonar.getDistance()
            if dist == 99999:
                dist = None

            light_state = light.value

            if (not fan_on) and (temp_c >= TEMP_FAN_ON):
                fan_on = True
                set_fan(True)
            elif fan_on and (temp_c <= TEMP_FAN_OFF):
                fan_on = False
                set_fan(False)

            if armed and dist is not None and dist <= DIST_ALARM_MM:
                board.set_buzzer(BUZZ_HZ, 0.2, 0.1, 1)
                sonar.setRGB(0, (255, 0, 0))
                sonar.setRGB(1, (255, 0, 0))
            else:
                if armed:
                    sonar.setRGB(0, (0, 255, 0))
                    sonar.setRGB(1, (0, 255, 0))
                else:
                    sonar.setRGB(0, (0, 0, 255))
                    sonar.setRGB(1, (0, 0, 255))

            print(
                f"[armed={armed}] temp={temp_c}C hum={hum}% fan={fan_on} "
                f"dist={dist if dist is not None else 'NA'}mm light={light_state}"
            )

            time.sleep(0.3)

    except KeyboardInterrupt:
        pass
    finally:
        set_fan(False)
        board.set_buzzer(1000, 0.0, 0.0, 1)

if __name__ == "__main__":
    main()
