import _thread
import time
from dma_pio_ws2812 import WS2812DMADoubleBuffer

leds = WS2812DMADoubleBuffer(pin=0, num_leds=60)

def animation_core():
    hue = 0
    while True:
        for i in range(leds.num_leds):
            leds.set_hsv(i, (hue + i*8) % 360, 1.0, 0.3)
        leds.swap()   # <<<< Frame fertig
        hue = (hue + 2) % 360
        time.sleep(0.02)

_thread.start_new_thread(animation_core, ())

while True:
    leds.show()
    time.sleep(0.01)