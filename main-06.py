import uasyncio as asyncio

# Beispiel für einen gemeinsamen Status
# 0: Modus, 1: Helligkeit, 2: Geschwindigkeit
led_settings = {'mode': 0, 'brightness': 255, 'speed': 50}

async def modbus_update_task():
    """Liest Modbus-Register aus und aktualisiert die Einstellungen"""
    while True:
        try:
            # Beispiel: Register 0 = Modus, 1 = Helligkeit
            data = host.read_holding_registers(SLAVE_ID, 0, 2)
            if data:
                led_settings['mode'] = data[0]
                led_settings['brightness'] = data[1]
                print(f"Update: Modus={data[0]}, Helligkeit={data[1]}")
        except Exception as e:
            print("Modbus Lesefehler:", e)
        
        await asyncio.sleep(0.5) # Modbus-Update-Rate

async def led_animation_task():
    """Nutzt die Werte aus led_settings für die PIO/DMA Animation"""
    while True:
        # Hier greifst du auf die aktuellen Werte zu
        current_brightness = led_settings['brightness']
        
        # Deine existierende PIO/DMA Logik hier...
        # update_led_strip(brightness=current_brightness)
        
        await asyncio.sleep(0.01) # Animations-Framerate (sehr schnell)

async def main():
    await asyncio.gather(modbus_update_task(), led_animation_task())

asyncio.run(main())
