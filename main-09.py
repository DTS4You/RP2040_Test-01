import asyncio
import machine
import utime
import micropython

# Aktiviert den Notfall-Buffer, damit wir ISR-Fehlermeldungen in der Konsole sehen
micropython.alloc_emergency_exception_buf(100)

# 1. Ringpuffer vorab anlegen (Größe muss eine Potenz von 2 sein oder modulo genutzt werden)
BUFFER_SIZE = 8
data_buffer = [0] * BUFFER_SIZE  # Speicher wird JETZT reserviert, nicht in der ISR
write_index = 0
read_index = 0

# Das Flag weckt die Async-Task auf
data_flag = asyncio.ThreadSafeFlag()

# Sensor-Pin (z. B. Lichtschranke oder Taster)
sensor_pin = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_UP)

def isr_handler(pin):
    """Die ISR: Schreibt Daten absolut speichersicher in den Puffer."""
    global write_index
    
    # Daten generieren/auslesen (hier: aktueller Zeitstempel in Mikrosekunden)
    aktueller_wert = utime.ticks_us()
    
    # Nächste Schreibposition berechnen
    next_write = (write_index + 1) % BUFFER_SIZE
    
    # Prüfen, ob der Puffer voll ist (Schreib-Zähler darf Lesefluss nicht überholen)
    if next_write != read_index:
        data_buffer[write_index] = aktueller_wert
        write_index = next_write
        data_flag.set()  # Async-Welt benachrichtigen
    else:
        # Puffer voll! Daten mussten verworfen werden (Überlauf)
        pass

# Interrupt an Pin koppeln
sensor_pin.irq(trigger=machine.Pin.IRQ_FALLING, handler=isr_handler)

async def data_consumer_task():
    """Diese Task läuft in der Async-Loop und verarbeitet die Daten."""
    global read_index
    while True:
        # Warten, bis die ISR uns signalisiert, dass Daten da sind
        await data_flag.wait()
        
        # Puffer komplett leer lesen (falls in der Zwischenzeit mehrere Werte kamen)
        while read_index != write_index:
            wert_aus_isr = data_buffer[read_index]
            read_index = (read_index + 1) % BUFFER_SIZE
            
            # AB HIER sind wir sicher in der Async-Welt:
            # Wir dürfen Strings bauen, printen, rechnen oder ins WLAN senden.
            print(f"Daten empfangen! Zeitstempel: {wert_aus_isr} µs")
            
        # Dem Event-Loop ganz kurz Zeit für andere Tasks geben
        await asyncio.sleep(0.01)

async def main():
    print("System bereit. Warte auf Signale an GP14...")
    await asyncio.gather(data_consumer_task())

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Programm beendet")

