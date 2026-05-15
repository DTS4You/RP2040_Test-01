import array
import time
import math
from machine import Pin, mem32
import rp2
import uctypes

@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_LEFT, 
             autopull=True, pull_thresh=24)
def ws2812_parallel():
    wrap_target()
    label("bitloop")
    out(x, 1)               .side(0) [2]
    jmp(not_x, "do_zero")   .side(1) [1]
    jmp("bitloop")          .side(1) [4]
    label("do_zero")
    nop()                   .side(0) [4]
    wrap()

class WS2812Parallel:
    def __init__(self, start_pin, num_leds_per_strip):
        self.num_strips = 8
        self.leds_per_strip = num_leds_per_strip
        
        # Buffer: 8 separate Arrays
        self.buffers = [array.array("I", [0] * self.leds_per_strip) for _ in range(self.num_strips)]
        # Separate Liste für die DMA-Konfigurations-Words
        self.dma_configs = [0] * self.num_strips
        
        self.DMA_BASE = 0x50000000
        
        for i in range(self.num_strips):
            pin = Pin(start_pin + i)
            # Verteile State Machines: 0-3 auf PIO0, 4-7 auf PIO1
            sm_id = i 
            state_m = rp2.StateMachine(sm_id, ws2812_parallel, freq=8_000_000, 
                                       sideset_base=pin)
            state_m.active(1)
            
            # DMA Config berechnen
            # DREQ_PIO0_TX0 ist 0, DREQ_PIO1_TX0 ist 8
            if i < 4:
                dreq = i 
            else:
                dreq = 8 + (i - 4)
            
            # Config: Incremental Read, 32-bit, DREQ enabled, Start
            self.dma_configs[i] = (dreq << 15) | (1 << 4) | (2 << 2) | 1
            
            # Einmalige Initialisierung der Ziel-Adresse (PIO FIFO)
            dma_chan = i
            write_addr_reg = self.DMA_BASE + (dma_chan * 0x40) + 0x04
            if i < 4:
                dest_fifo = 0x50200010 + (i * 4)
            else:
                dest_fifo = 0x50300010 + ((i - 4) * 4)
            mem32[write_addr_reg] = dest_fifo

    def set_pixel(self, strip, index, r, g, b):
        # WS2812: GRB Format in den oberen 24 Bit
        self.buffers[strip][index] = (g << 24) | (r << 16) | (b << 8)

    def show(self):
        # 1. Sicherstellen, dass die LEDs den letzten Frame verarbeitet haben
        # WS2812 Reset-Zeit (min 80us, wir nehmen 300us für Sicherheit bei 2000 LEDs)
        time.sleep_us(300)

        for i in range(self.num_strips):
            dma_chan = i
            base = self.DMA_BASE + (dma_chan * 0x40)
            
            # Adressen und Zähler setzen
            mem32[base + 0x00] = uctypes.addressof(self.buffers[i])
            mem32[base + 0x08] = self.leds_per_strip
            # Trigger durch Schreiben des Config-Words
            mem32[base + 0x0c] = self.dma_configs[i]

# --- Anwendung ---
leds = WS2812Parallel(start_pin=2, num_leds_per_strip=200)

step = 0
try:
    while True:
        for s in range(8):
            for i in range(20):
                leds.set_pixel(s, i, 0, 0, 0)
            leds.set_pixel(s, step, 0, 0, 30)
        
        if step < 19:
            step += 1
        else:
            step = 0
        leds.show()
        time.sleep(0.3)
except KeyboardInterrupt:
    # Clear all
    for s in range(8):
        for i in range(20): leds.set_pixel(s, i, 0, 0, 0)
    leds.show()

