from machine import Pin, mem32
import rp2
import array

DMA_BASE = 0x50000000
DMA_CH_SIZE = 0x40

PIO0_BASE = 0x50200000
PIO1_BASE = 0x50300000

def pio_txf(pio, sm):
    return (PIO0_BASE if pio == 0 else PIO1_BASE) + 0x10 + sm*4

def dreq(pio, sm):
    return (0 if pio == 0 else 8) + sm


class DMAChannel:
    def __init__(self, ch):
        self.base = DMA_BASE + ch * DMA_CH_SIZE

    def config(self, read, write, count, ctrl):
        mem32[self.base + 0x00] = read
        mem32[self.base + 0x04] = write
        mem32[self.base + 0x08] = count
        mem32[self.base + 0x0C] = ctrl

    def start(self):
        mem32[self.base + 0x0C] |= 1

    def busy(self):
        return (mem32[self.base + 0x0C] >> 24) & 1


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
    jmp(not_x, "zero")      .side(1) [T1 - 1]
    jmp("bitloop")          .side(1) [T2 - 1]
    label("zero")
    nop()                   .side(0) [T2 - 1]
    wrap()


class WS2812_8Strip_DMA:
    def __init__(self, pins, num_leds):
        assert len(pins) == 8
        self.n = num_leds

        self.buffers = [array.array("I", [0]*num_leds) for _ in range(8)]
        self.dmas = []
        self.sms = []

        # --- PIO0 (Strips 0-3) ---
        for i in range(4):
            sm = rp2.StateMachine(
                i, ws2812,
                freq=8_000_000,
                sideset_base=Pin(pins[i])
            )
            sm.active(1)
            self.sms.append(sm)

        # --- PIO1 (Strips 4-7) ---
        for i in range(4):
            sm = rp2.StateMachine(
                4+i, ws2812,
                freq=8_000_000,
                sideset_base=Pin(pins[4+i])
            )
            sm.active(1)
            self.sms.append(sm)

        # --- DMA Channels ---
        for ch in range(8):
            self.dmas.append(DMAChannel(ch))

    # -------- API --------
    def set_pixel(self, strip, i, r, g, b):
        self.buffers[strip][i] = (g << 16) | (r << 8) | b

    def fill(self, strip, r, g, b):
        val = (g << 16) | (r << 8) | b
        for i in range(self.n):
            self.buffers[strip][i] = val

    def show(self):
        # alle DMA konfigurieren
        for i in range(8):
            pio = 0 if i < 4 else 1
            sm  = i if i < 4 else i - 4

            ctrl = (
                (1 << 0) |
                (2 << 2) |
                (1 << 5) |
                (0 << 6) |
                (dreq(pio, sm) << 15)
            )

            self.dmas[i].config(
                read=id(self.buffers[i]),
                write=pio_txf(pio, sm),
                count=self.n,
                ctrl=ctrl
            )

        # alle gleichzeitig starten
        for dma in self.dmas:
            dma.start()

        # warten
        while any(dma.busy() for dma in self.dmas):
            pass

