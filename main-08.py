import uasyncio as asyncio
from machine import UART, Pin
from umodbus.serial import Serial as ModbusRTUSlave

# --- Hardware Setup ---
# Nur TX und RX Pins, kein EN_PIN
TX_PIN = 0
RX_PIN = 1
BAUDRATE = 9600

# Slave Initialisierung ohne ctrl_pin
slave = ModbusRTUSlave(
    uart_id=0,
    uart_pins=(Pin(TX_PIN), Pin(RX_PIN)),
    baudrate=BAUDRATE,
    slave_address=10  # Deine Slave-ID
)

# Shared Memory für Register
holding_registers = {0: 0, 1: 0, 2: 0}

async def slave_task():
    """Wartet permanent auf Anfragen vom Master"""
    print("Modbus Slave (ohne EN-Pin) läuft auf ID 10...")
    while True:
        # Verarbeitet eingehende Anfragen
        slave.process(
            holding_registers=holding_registers
        )
        # Sehr kurzes Sleep, um den Event-Loop nicht zu blockieren
        await asyncio.sleep_ms(5)

async def logic_task():
    """Deine LED-Logik oder andere Prozesse"""
    while True:
        val = holding_registers.get(0, 0)
        # Beispiel: print(f"Wert in Register 0: {val}")
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

