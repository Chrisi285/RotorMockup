import threading
import time
import re
import serial

status = "000000"
azimuth = 10.0
elevation = 15.0
lock = threading.Lock()
is_homeing = False


def go_home():
    global azimuth, elevation, is_homeing
    with lock:
        is_homeing = True
    while azimuth != 0 and elevation != 0:
        if azimuth >= 0.1:
            with lock:
                azimuth = azimuth - 0.1
        if elevation >= 0.1:
            with lock:
                elevation = elevation - 0.1
        time.sleep(0.2)
    with lock:
        is_homeing = False


def handle_status(ser):
    response = status
    ser.write(response.encode('utf-8'))
    print(f'Sent: {response}')


def handle_azimuth(ser):
    response = f"AZ={azimuth:06.2f}"
    ser.write(response.encode('utf-8'))


def handle_elevation(ser):
    response = f"EL={elevation:06.2f}"
    ser.write(response.encode('utf-8'))


def handle_org_request(ser):
    threading.Thread(daemon=True, target=go_home).start()


def drive_azimuth(target_azimuth):
    global azimuth, status
    print("Driving azimuth")
    print(target_azimuth)
    with lock:
        status = "000002"
    print(status)
    if target_azimuth > azimuth:
        while target_azimuth > azimuth:
            with lock:
                azimuth = azimuth + 0.05
            time.sleep(0.01)
    elif target_azimuth < azimuth:
        while target_azimuth < azimuth:
            with lock:
                azimuth = azimuth - 0.05
            time.sleep(0.01)
    with lock:
        status = "000000"


def drive_elevation(target_elevation):
    global elevation, status
    print("Driving elevation")
    with lock:
        status = "000002"
    if target_elevation > elevation:
        while target_elevation > elevation:
            with lock:
                elevation = elevation + 0.1
            time.sleep(0.01)
    elif target_elevation < elevation:
        while target_elevation < elevation:
            with lock:
                elevation = elevation - 0.1
            time.sleep(0.01)
    with lock:
        status = "000000"


def handle_numeric_message(ser, command, value):
    global azimuth, elevation
    try:
        value = float(value)
        if command == 'AZ':
            threading.Thread(daemon=True, target=drive_azimuth, args=(value,)).start()
        elif command == 'EL':
            threading.Thread(daemon=True, target=drive_elevation, args=(value,)).start()
        else:
            response = f"Unknown command: {command}"
    except ValueError:
        print(f'Invalid numeric value: {value}')


def default_handler(ser, message):
    print(f'Unknown message: {message}')


def read_from_serial(port, baudrate):
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f'Opened port {port} with baudrate {baudrate}')

        buffer = ''
        handlers = {
            '&*STATUS=?': handle_status,
            '&* AZ=?': handle_azimuth,
            '&* EL=?': handle_elevation,
            "&* ORG": handle_org_request
        }

        while True:
            char = ser.read().decode('utf-8')
            if char:
                if char == '\r':
                    message = buffer.strip()
                    if message in handlers:
                        handlers[message](ser)
                    else:
                        match = re.match(r'&\* (\w+)=([\d.]+)', message)
                        if match:
                            command, value = match.groups()
                            handle_numeric_message(ser, command, value)
                        else:
                            default_handler(ser, message)
                    buffer = ''
                else:
                    buffer += char
    except serial.SerialException as e:
        print(f'Error opening or reading from serial port: {e}')
    except KeyboardInterrupt:
        print('Exiting...')
    finally:
        ser.close()
        print(f'Closed port {port}')


if __name__ == '__main__':
    port_name = 'COM7'  # Beispiel für Windows
    # port_name = '/dev/ttyUSB0'  # Beispiel für Linux
    baudrate = 9600

    read_from_serial(port_name, baudrate)
