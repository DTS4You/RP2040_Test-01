from machine import Pin, mem32      # type: ignore
import rp2                          # type: ignore
import array
import time

# --- DMA Basis ---
DMA_BASE = 0x50000000
DMA_CH_SIZE = 0x40

PIO0_TXF0 = 0x50200010  # TX FIFO SM0
DREQ_PIO0_TX0 = 0       # DREQ Index

class DMAChannel:
    def __init__(self, ch=0):
        self.base = DMA_BASE + ch * DMA_CH_SIZE

    def config(self, read_addr, write_addr, count, ctrl):
        mem32[self.base + 0x00] = read_addr
        mem32[self.base + 0x04] = write_addr
        mem32[self.base + 0x08] = count
        mem32[self.base + 0x0C] = ctrl

    def start(self):
        mem32[self.base + 0x0C] |= 1  # EN bit

    def busy(self):
        return (mem32[self.base + 0x0C] >> 24) & 1


# --- PIO Programm ---
@rp2.asm_pio(
    sideset_init=rp2.PIO.OUT_LOW,
    autopull=True,
    pull_thresh=24
)
def ws2812():
    T1 = 2
    T2 = 5
    T3 = 3
    wrap_target()
    label("bitloop")
    out(x, 1)               .side(0) [T3 - 1]
    jmp(not_x, "do_zero")   .side(1) [T1 - 1]
    jmp("bitloop")          .side(1) [T2 - 1]
    label("do_zero")
    nop()                   .side(0) [T2 - 1]
    wrap()


class WS2812_DMA:
    def __init__(self, pin, num_leds, dma_ch=0, sm_id=0):
        self.num_leds = num_leds

        # --- PIO ---
        self.sm = rp2.StateMachine(
            sm_id,
            ws2812,
            freq=8_000_000,
            sideset_base=Pin(pin)
        )
        self.sm.active(1)

        # --- Buffer ---
        self.buf = array.array("I", [0] * num_leds)

        # --- DMA ---
        self.dma = DMAChannel(dma_ch)

        self.ctrl = (
            (1 << 0) |        # EN
            (2 << 2) |        # DATA SIZE = 32bit
            (1 << 5) |        # INC READ
            (0 << 6) |        # NO INC WRITE
            (DREQ_PIO0_TX0 << 15)  # PIO TX FIFO pacing
        )

    def set_pixel(self, i, r, g, b):
        self.buf[i] = (g << 16) | (r << 8) | b

    def fill(self, r, g, b):
        val = (g << 16) | (r << 8) | b
        for i in range(self.num_leds):
            self.buf[i] = val

    def clear(self):
        self.fill(0, 0, 0)

    def show(self):
        addr = id(self.buf)

        self.dma.config(
            read_addr=addr,
            write_addr=PIO0_TXF0,
            count=self.num_leds,
            ctrl=self.ctrl
        )

        self.dma.start()

        # warten bis fertig
        while self.dma.busy():
            pass

        time.sleep_us(60)  # Reset WS2812

    # optional HSV
    def set_hsv(self, i, h, s, v):
        h %= 360
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c

        if h < 60:   r,g,b = c,x,0
        elif h < 120:r,g,b = x,c,0
        elif h < 180:r,g,b = 0,c,x
        elif h < 240:r,g,b = 0,x,c
        elif h < 300:r,g,b = x,0,c
        else:        r,g,b = c,0,x

        self.set_pixel(i,
            int((r+m)*255),
            int((g+m)*255),
            int((b+m)*255)
        )




leds = WS2812_DMA(pin=0, num_leds=30)

while True:
    for i in range(leds.num_leds):
        leds.set_pixel(i, 255, 0, 0)
    leds.show()
    time.sleep(0.5)

    leds.fill(0, 0, 255)
    leds.show()
    time.sleep(0.5)


