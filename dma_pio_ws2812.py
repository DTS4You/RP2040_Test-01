from machine import Pin     # type: ignore
import rp2                  # type: ignore
import array
import time
import _thread

class WS2812DMADoubleBuffer:
    def __init__(self, pin, num_leds, sm_id=0, freq=8_000_000):
        self.num_leds = num_leds
        self.lock = _thread.allocate_lock()

        # --- PIO Programm ---
        @rp2.asm_pio(
            sideset_init=rp2.PIO.OUT_LOW,
            out_shift_dir=rp2.PIO.SHIFT_LEFT,
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

        self.sm = rp2.StateMachine(
            sm_id,
            ws2812,
            freq=freq,
            sideset_base=Pin(pin)
        )
        self.sm.active(1)

        # --- Double Buffer ---
        self.front_buf = array.array("I", [0] * num_leds)
        self.back_buf  = array.array("I", [0] * num_leds)

        # --- DMA ---
        self.dma = rp2.DMA()
        self.dma.config(
            read=self.front_buf,
            write=self.sm,
            count=num_leds,
            ctrl=rp2.DMA.CTRL(
                inc_read=True,
                inc_write=False,
                treq_sel=rp2.DREQ_PIO0_TX0
            )
        )

    # --------- Zeichnen in BACK buffer ---------
    def set_pixel(self, i, r, g, b):
        self.back_buf[i] = (g << 16) | (r << 8) | b

    def fill(self, r, g, b):
        val = (g << 16) | (r << 8) | b
        for i in range(self.num_leds):
            self.back_buf[i] = val

    def clear(self):
        self.fill(0, 0, 0)

    # --------- Buffer tauschen ---------
    def swap(self):
        self.lock.acquire()
        self.front_buf, self.back_buf = self.back_buf, self.front_buf
        self.dma.config(read=self.front_buf)  # DMA auf neuen Buffer zeigen
        self.lock.release()

    # --------- Ausgabe ---------
    def show(self):
        self.lock.acquire()
        self.dma.start()
        self.dma.wait()
        self.lock.release()
        time.sleep_us(60)

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
