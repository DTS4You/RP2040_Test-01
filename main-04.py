from machine import UART, Pin
from umodbus.serial import Serial as ModbusRTUMaster
import time

# --- Hardware Setup ---
TX_PIN = 0
RX_PIN = 1
EN_PIN = 2
BAUDRATE = 9600

host = ModbusRTUMaster(
    uart_id=0,
    uart_pins=(Pin(TX_PIN), Pin(RX_PIN)),
    baudrate=BAUDRATE,
    ctrl_pin=Pin(EN_PIN, Pin.OUT)
)

SLAVE_ID = 1

def write_modbus_data():
    try:
        # --- 1. EINZELNES REGISTER SCHREIBEN (FC 06) ---
        # Schreibt den Wert 1234 in das Register mit der Adresse 50
        reg_addr = 50
        value = 1234
        print(f"Schreibe {value} in Register {reg_addr}...")
        host.write_single_register(SLAVE_ID, reg_addr, value)
        
        time.sleep(0.1)
        
        # --- 2. MEHRERE REGISTER SCHREIBEN (FC 16) ---
        # Schreibt die Werte [10, 20, 30] ab der Start-Adresse 100
        start_addr = 100
        values = [10, 20, 30]
        print(f"Schreibe Block {values} ab Adresse {start_addr}...")
        host.write_multiple_registers(SLAVE_ID, start_addr, values)
        
        print("Schreibvorgang erfolgreich.")

    except Exception as e:
        print(f"Fehler beim Schreiben: {e}")

# Ausführung
write_modbus_data()

