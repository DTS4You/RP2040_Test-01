import uasyncio as asyncio
from machine import UART, Pin
from umodbus.serial import Serial as ModbusRTUSlave

# --- Hardware Setup ---
TX_PIN = 0
RX_PIN = 1
EN_PIN = 2
BAUDRATE = 9600

# Slave Initialisierung
# Der 'slave_address' Parameter legt fest, auf welche ID dieses Gerät reagiert
slave = ModbusRTUSlave(
    uart_id=0,
    uart_pins=(Pin(TX_PIN), Pin(RX_PIN)),
    baudrate=BAUDRATE,
    ctrl_pin=Pin(EN_PIN, Pin.OUT),
    slave_address=10  # Deine Slave-ID
)

# --- Register-Speicher (Shared Data) ---
# Hier halten wir die Daten, die der Master lesen oder schreiben kann
holding_registers = {0: 0, 1: 0, 2: 0}

async def slave_task():
    """Wartet permanent auf Anfragen vom Master"""
    print("Modbus Slave läuft auf ID 10...")
    while True:
        # Modbus-Anfragen verarbeiten
        # Die Library prüft intern, ob Daten im Puffer sind
        slave.process(
            holding_registers=holding_registers
        )
        # Kurze Pause für den Event-Loop
        await asyncio.sleep_ms(10)

async def logic_task():
    """Beispiel: Deine eigene Logik, die die Modbus-Daten nutzt"""
    while True:
        # Zugriff auf die Register, z.B. für LED-Helligkeit
        val = holding_registers.get(0, 0)
        # Hier könnte deine LED-Steuerlogik auf 'val' reagieren
        # print(f"Aktueller Wert in Register 0: {val}")
        
        await asyncio.sleep(1)

async def main():
    await asyncio.gather(
        slave_task(),
        logic_task()
    )

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Slave gestoppt")

