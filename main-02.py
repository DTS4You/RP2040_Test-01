import machine
import rp2
import array
import time
import uctypes

# Register-Adressen für den RP2040
DMA_BASE = 0x50000000
PIO0_BASE = 0x50200000
PIO0_TXF0 = PIO0_BASE + 0x10  # TX FIFO 0 Adress

# DMA Channel Register Offsets (für Channel 0)
CH0_READ_ADDR  = DMA_BASE + 0x00
CH0_WRITE_ADDR = DMA_BASE + 0x04
CH0_TRANS_COUNT = DMA_BASE + 0x08
CH0_CTRL_TRIG  = DMA_BASE + 0x0C

@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_LEFT, autopull=True, pull_thresh=24)
def ws2812_pio():
    wrap_target()
    label("bitloop")
    out(x, 1)               .side(0)    [2] 
    jmp(not_x, "do_zero")   .side(1)    [2] 
    jmp("bitloop")          .side(1)    [5] 
    label("do_zero")
    nop()                   .side(0)    [5] 
    wrap()

class WS2812_DMA:
    def __init__(self, pin_num, num_leds):
        self.num_leds = num_leds
        self.buffer = array.array("I", [0] * num_leds)
        
        # 1. PIO State Machine initialisieren (PIO 0, SM 0)
        self.sm = rp2.StateMachine(0, ws2812_pio, freq=8_000_000, sideset_base=machine.Pin(pin_num))
        self.sm.active(1)
        
        # 2. DMA Konfiguration vorbereiten
        # DREQ_PIO0_TX0 = 0 (Data Request Index für PIO0 TX FIFO 0)
        # Treib-Wert berechnen: 
        # Quiet=0, DREQ=0, ChainTo=0, RingSel=0, RingSize=0, IncrWrite=0, IncrRead=1, Size=2 (32-bit), En=1
        self.dma_config = (0 << 15) | (0 << 11) | (0 << 6) | (1 << 4) | (2 << 2) | 1

    def is_busy(self):
        # Prüft, ob das BUSY-Bit (Bit 24) im Control-Register noch gesetzt ist
        return (machine.mem32[CH0_CTRL_TRIG] & (1 << 24)) != 0

    def show(self):
        """Startet den DMA-Transfer und kehrt sofort zurück"""
        if self.is_busy():
            return False # Vorheriger Transfer läuft noch
            
        # DMA Register direkt beschreiben
        machine.mem32[CH0_READ_ADDR] = uctypes.addressof(self.buffer)
        machine.mem32[CH0_WRITE_ADDR] = PIO0_TXF0
        machine.mem32[CH0_TRANS_COUNT] = self.num_leds
        machine.mem32[CH0_CTRL_TRIG] = self.dma_config # Dieser Schreibvorgang startet den DMA
        return True

    def set_pixel(self, i, r, g, b, brightness=0.2):
        # WS2812 nutzt GRB
        g_val = int(g * brightness)
        r_val = int(r * brightness)
        b_val = int(b * brightness)
        self.buffer[i] = (g_val << 16) | (r_val << 8) | b_val

# --- Test-Programm ---
LEDS = 1000
strip = WS2812_DMA(15, LEDS)

# Puffer füllen
for i in range(LEDS):
    strip.set_pixel(i, 255, 0, 100) # Pink

print("Starte non-blocking Transfer...")
start_time = time.ticks_us()

strip.show() # Schickt 1000 LEDs los

# HIER IST DER BEWEIS:
end_time = time.ticks_us()
print(f"show() hat nur {time.ticks_diff(end_time, start_time)} Mikrosekunden blockiert!")
print("Während die LEDs im Hintergrund geladen werden, kann ich weiterrechnen.")

# Wir warten hier nur, um zu sehen, wann die Hardware fertig ist
while strip.is_busy():
    pass

print("Hardware-Transfer abgeschlossen.")
