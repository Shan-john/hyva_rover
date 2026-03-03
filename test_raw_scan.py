import serial
import time
import binascii

def test_raw_scan_data():
    port = "/dev/ttyUSB0"
    baud = 115200
    print(f"Reading raw scan data from {port}...")
    try:
        ser = serial.Serial(port, baud, timeout=2)
        
        # Start motor (may need DTR/RTS manipulation depending on adapter)
        print("Starting motor (DTR=False)...")
        ser.dtr = False # Usually starts motor on RPLidar A1 adapters
        time.sleep(1)
        
        # Start Scan command
        print("Sending Start Scan (A5 20)...")
        ser.write(b'\xA5\x20')
        time.sleep(0.5)
        
        # Read descriptor
        desc = ser.read(7)
        print(f"Descriptor: {binascii.hexlify(desc)}")
        
        # Read measurements for 2 seconds
        print("Reading measurements for 2s...")
        start = time.time()
        while time.time() - start < 2:
            if ser.in_waiting:
                data = ser.read(ser.in_waiting)
                print(f"Read {len(data)} bytes")
                # Print a bit of the data
                if len(data) >= 5:
                    print(f"  Sample: {binascii.hexlify(data[:5])}")
            time.sleep(0.1)
            
        # Stop Scan
        print("Sending Stop Scan (A5 25)...")
        ser.write(b'\xA5\x25')
        time.sleep(0.5)
        ser.close()
    except Exception as e:
        print(f"Serial error: {e}")

if __name__ == "__main__":
    test_raw_scan_data()
