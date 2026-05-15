# RP2040_Test-01

def show(self):
        # 1. Warten, bis ALLE 8 DMA-Kanäle fertig sind (Busy-Bit Check)
        # Wir prüfen alle Kanäle 0 bis 7
        for i in range(self.num_strips):
            ctrl_reg = self.DMA_BASE + (i * 0x40) + 0x0C
            while mem32[ctrl_reg] & (1 << 24): # Bit 24 ist das BUSY-Bit
                pass

        # 2. Kurze Reset-Pause für die WS2812 (wichtig!)
        time.sleep_us(300)

        # 3. Jetzt erst neue Daten triggern
        for i in range(self.num_strips):
            dma_chan = i
            base = self.DMA_BASE + (dma_chan * 0x40)
            mem32[base + 0x00] = uctypes.addressof(self.buffers[i])
            mem32[base + 0x08] = self.leds_per_strip
            mem32[base + 0x0c] = self.dma_configs[i]


# ----- Double Buffer

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

class WS2812DoubleBuffered:
    def __init__(self, start_pin, leds_per_strip):
        self.num_strips = 8
        self.leds_per_strip = leds_per_strip
        self.DMA_BASE = 0x50000000
        
        # Erzeuge ZWEI Sätze von Buffern (Double Buffering)
        # buffer_set[0] = Front-Buffer (wird gesendet)
        # buffer_set[1] = Back-Buffer (wird beschrieben)
        self.buffer_sets = [
            [array.array("I", [0] * leds_per_strip) for _ in range(8)],
            [array.array("I", [0] * leds_per_strip) for _ in range(8)]
        ]
        
        self.write_index = 0  # Welchen Buffer beschreibt die CPU gerade
        self.dma_configs = [0] * 8
        
        # Initialisierung der PIOs und DMA-Grundkonfiguration
        for i in range(8):
            pin = Pin(start_pin + i)
            sm = rp2.StateMachine(i, ws2812_parallel, freq=8_000_000, sideset_base=pin)
            sm.active(1)
            
            # DREQ Auswahl (PIO0 oder PIO1)
            dreq = i if i < 4 else 8 + (i - 4)
            self.dma_configs[i] = (dreq << 15) | (1 << 4) | (2 << 2) | 1
            
            # Ziel-Adresse (FIFO) festlegen
            dest_fifo = (0x50200010 + (i * 4)) if i < 4 else (0x50300010 + ((i - 4) * 4))
            mem32[self.DMA_BASE + (i * 0x40) + 0x04] = dest_fifo

    def set_pixel(self, strip, index, r, g, b):
        """ Schreibt immer in den aktuellen Back-Buffer """
        # WS2812: GRB Format
        self.buffer_sets[self.write_index][strip][index] = (g << 24) | (r << 16) | (b << 8)

    def is_sending(self):
        """ Prüft, ob einer der DMA Kanäle noch aktiv ist """
        for i in range(8):
            if mem32[self.DMA_BASE + (i * 0x40) + 0x0C] & (1 << 24):
                return True
        return False

    def show(self):
        # 1. Warten, bis der vorherige DMA-Transfer fertig ist
        while self.is_sending():
            pass
        
        # 2. Reset-Pause für die LEDs (Timing-Sicherheit)
        time.sleep_us(300)
        
        # 3. Den aktuellen Back-Buffer zum Senden (Front-Buffer) machen
        read_index = self.write_index
        
        # 4. Alle 8 DMA Kanäle mit dem gewählten Buffer-Set triggern
        for i in range(8):
            base = self.DMA_BASE + (i * 0x40)
            mem32[base + 0x00] = uctypes.addressof(self.buffer_sets[read_index][i])
            mem32[base + 0x08] = self.leds_per_strip
            mem32[base + 0x0C] = self.dma_configs[i]
            
        # 5. Den Back-Buffer umschalten (0 -> 1 oder 1 -> 0)
        # Die CPU schreibt ab jetzt in den jeweils anderen Buffer
        self.write_index = 1 - self.write_index

# --- Anwendung ---

# 8 Streifen à 250 LEDs, Start an GPIO 2 (um UART Konflikte zu vermeiden)
leds = WS2812DoubleBuffered(start_pin=2, leds_per_strip=250)

step = 0
try:
    while True:
        # Während der DMA im Hintergrund sendet, berechnet die CPU hier schon das nächste Bild
        for s in range(8):
            for i in range(250):
                # Schnelle Farbberechnung
                r = int((math.sin(i/5 + step/3) + 1) * 15)
                g = int((math.cos(i/10 - step/5) + 1) * 15)
                leds.set_pixel(s, i, r, g, 0)
        
        # Überträgt den fertigen Back-Buffer und wechselt sofort die Rollen
        leds.show()
        step += 1
        
except KeyboardInterrupt:
    pass