from machine import UART, Pin
from umodbus.serial import Serial as ModbusRTUMaster
import time

# --- RP2040 Pin-Konfiguration ---
# Wir nutzen UART 0
# TX: GP0 (Pin 1)
# RX: GP1 (Pin 2)
# RE/DE (RS485 Control): GP2 (Pin 4)
TX_PIN = 0
RX_PIN = 1
EN_PIN_NUM = 2
BAUDRATE = 9600

# GPIO für die Sende-/Empfangsumschaltung des RS485-Transceivers
en_pin = Pin(EN_PIN_NUM, Pin.OUT)

# --- Modbus Initialisierung ---
# Beim RP2040 wird die uart_id (0 oder 1) direkt angesprochen
host = ModbusRTUMaster(
    uart_id=0,
    uart_pins=(Pin(TX_PIN), Pin(RX_PIN)),
    baudrate=BAUDRATE,
    ctrl_pin=en_pin
)

# Ziel-Konfiguration
SLAVE_ADDR = 10

def modbus_logic():
    try:
        # Beispiel: Wert 500 an Holding Register 10 schreiben
        register = 10
        value = [500]
        
        print(f"Schreibe {value} an Register {register}...")
        host.write_multiple_registers(SLAVE_ADDR, register, value)
        
        time.sleep(0.2) # Kurze Pause für den Bus
        
        # Beispiel: 2 Register ab Adresse 0 lesen
        print("Lese Eingangsregister...")
        data = host.read_input_registers(SLAVE_ADDR, 0, 2)
        print(f"Empfangene Daten: {data}")

    except Exception as e:
        print(f"Kommunikationsfehler: {e}")

# Main Loop
while True:
    modbus_logic()
    time.sleep(2)
