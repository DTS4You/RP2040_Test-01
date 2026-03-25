import rp2
from machine import Pin, mem32
import uctypes
import time
import array

# PIO-Programm für WS2812 (NeoPixel) Protokoll
@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_LEFT, autopull=True, pull_thresh=24)
def ws2812_program():
    T1 = 2
    T2 = 5
    T3 = 3
    wrap_target()
    label("bit_loop")
    out(x, 1)               .side(0)    [T3 - 1] 
    jmp(not_x, "do_zero")   .side(1)    [T1 - 1] 
    jmp("bit_loop")         .side(1)    [T2 - 1] 
    label("do_zero")
    nop()                   .side(1)    [T1 - 1] 
    wrap()

# DMA Register Adressen (RP2040)
DMA_BASE = 0x50000000
CH0_READ_ADDR  = DMA_BASE + 0x00
CH0_WRITE_ADDR = DMA_BASE + 0x04
CH0_TRANS_COUNT = DMA_BASE + 0x08
CH0_CTRL_TRIG  = DMA_BASE + 0x0c

CH1_READ_ADDR  = DMA_BASE + 0x40
CH1_WRITE_ADDR = DMA_BASE + 0x44
CH1_TRANS_COUNT = DMA_BASE + 0x48
CH1_CTRL_TRIG  = DMA_BASE + 0x4c

# PIO Register
PIO0_BASE = 0x50200000
PIO0_TXF0 = PIO0_BASE + 0x10

class WS2812_DMA:
    def __init__(self, pin_num, num_leds, brightness=0.2):
        self.num_leds = num_leds
        self.brightness = brightness
        
        # State Machine initialisieren
        self.sm = rp2.StateMachine(0, ws2812_program, freq=8_000_000, sideset_base=Pin(pin_num))
        self.sm.active(1)
        
        # Pixel-Datenpuffer als Byte-Array (fest im Speicher für DMA)
        # Wir nutzen 'I' für 32-Bit Unsigned Integers
        self.buffer = array.array('I', [0] * self.num_leds)
        self.buffer_ptr = uctypes.addressof(self.buffer)
        
        # Hilfsvariable für den Autoload (enthält die Adresse des Puffers)
        self.ptr_array = array.array('I', [self.buffer_ptr])
        self.ptr_array_ptr = uctypes.addressof(self.ptr_array)

        self._setup_dma()

    def _setup_dma(self):
        # Kanal 0: Daten -> PIO TX FIFO
        # TREQ_SEL für PIO0 TX0 ist 0
        # CHAIN_TO Kanal 1 (Bit 11:14)
        dreq_pio0_tx0 = 0
        chain_to_ch1 = 1
        
        ctrl0 = (dreq_pio0_tx0 << 15) | (chain_to_ch1 << 11) | (2 << 2) | 1 # 32-bit, Incremental Read, Enable
        
        mem32[CH0_READ_ADDR] = self.buffer_ptr
        mem32[CH0_WRITE_ADDR] = PIO0_TXF0
        mem32[CH0_TRANS_COUNT] = self.num_leds
        mem32[CH0_CTRL_TRIG] = ctrl0

        # Kanal 1: Puffer-Adresse -> CH0_READ_ADDR (Autoload)
        # Dieser Kanal schreibt die Adresse des Datenpuffers zurück in Kanal 0
        # CHAIN_TO Kanal 0 (Bit 11:14)
        chain_to_ch0 = 0
        ctrl1 = (chain_to_ch0 << 11) | (2 << 2) | 1 # 32-bit, No DREQ, Enable
        
        mem32[CH1_READ_ADDR] = self.ptr_array_ptr
        mem32[CH1_WRITE_ADDR] = CH0_READ_ADDR
        mem32[CH1_TRANS_COUNT] = 1
        mem32[CH1_CTRL_TRIG] = ctrl1

    def set_pixel(self, i, color):
        r, g, b = color
        # Da DMA aktiv ist, schreiben wir direkt in den RAM-Puffer
        # Die Hardware übernimmt den Rest automatisch
        self.buffer[i] = (int(g * self.brightness) << 16) | \
                         (int(r * self.brightness) << 8) | \
                         int(b * self.brightness)

    def fill(self, color):
        for i in range(self.num_leds):
            self.set_pixel(i, color)

# --- Beispielanwendung ---

def wheel(pos):
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)

def main():
    NUM_LEDS = 16
    # Pin 0, 16 LEDs, 10% Helligkeit
    leds = WS2812_DMA(0, NUM_LEDS, brightness=0.1)

    print("DMA Autoload aktiv. CPU ist nun frei für andere Aufgaben.")
    
    try:
        offset = 0
        while True:
            # Wir müssen kein .show() mehr aufrufen!
            # Die CPU schreibt nur in den Speicher, der DMA-Controller
            # liest diesen permanent im Hintergrund aus.
            for i in range(NUM_LEDS):
                idx = (i * 256 // NUM_LEDS) + offset
                leds.set_pixel(i, wheel(idx & 255))
            
            offset += 3
            time.sleep(0.01) # Hier kann beliebiger anderer Code stehen
            
    except KeyboardInterrupt:
        leds.fill((0, 0, 0))
        print("Demo beendet.")

if __name__ == "__main__":
    main()
