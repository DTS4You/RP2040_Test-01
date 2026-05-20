import uasyncio as asyncio
from machine import UART, Pin
from umodbus.serial import Serial as ModbusRTUMaster

# --- Hardware Setup ---
TX_PIN = 0
RX_PIN = 1
EN_PIN = 2
BAUDRATE = 9600

# Modbus Master Setup
host = ModbusRTUMaster(
    uart_id=0,
    uart_pins=(Pin(TX_PIN), Pin(RX_PIN)),
    baudrate=BAUDRATE,
    ctrl_pin=Pin(EN_PIN, Pin.OUT)
)

SLAVE_ID = 1

async def modbus_task():
    """Asynchrone Modbus-Aufgabe"""
    while True:
        try:
            # Beispiel: Wert schreiben
            print("Schreibe Daten...")
            # Wir nutzen run_in_executor oder direkte Aufrufe, 
            # da modbus-IO-Operationen in MicroPython kurz blockieren können.
            host.write_single_register(SLAVE_ID, 50, 1234)
            
            await asyncio.sleep(0.1) # Nicht-blockierendes Warten
            
            # Beispiel: Daten lesen
            result = host.read_holding_registers(SLAVE_ID, 50, 1)
            print(f"Gelesener Wert: {result}")
            
        except Exception as e:
            print(f"Fehler: {e}")
            
        # Warte 2 Sekunden, ohne andere Tasks zu blockieren
        await asyncio.sleep(2)

async def other_task():
    """Zusätzliche Aufgabe, z.B. LED-Blinken oder Sensor-Abfrage"""
    while True:
        print("--- Andere System-Task läuft ---")
        await asyncio.sleep(1)

async def main():
    """Haupt-Loop zum Starten der Tasks"""
    # Tasks gleichzeitig starten
    await asyncio.gather(
        modbus_task(),
        other_task()
    )

# Event-Loop starten
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Programm beendet")

