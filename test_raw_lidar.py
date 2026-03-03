import serial
import time
import binascii

def test_raw_serial():
    port = "/dev/ttyUSB0"
    baud = 115200
    print(f"Reading raw bytes from {port} at {baud}...")
    try:
        ser = serial.Serial(port, baud, timeout=2)
        
        # Send Get Info command manually
        # Command: 0xA5 0x50
        print("Sending Get Info command (A5 50)...")
        ser.write(b'\xA5\x50')
        time.sleep(0.5)
        
        if ser.in_waiting:
            data = ser.read(ser.in_waiting)
            print(f"Received ({len(data)} bytes): {binascii.hexlify(data)}")
        else:
            print("No response to Get Info")
            
        # Send Start Scan command manually
        # Command: 0xA5 0x20
        print("\nSending Start Scan command (A5 20)...")
        ser.write(b'\xA5\x20')
        time.sleep(1)
        
        if ser.in_waiting:
            data = ser.read(30) # Read first 30 bytes
            print(f"Received ({len(data)} bytes): {binascii.hexlify(data)}")
        else:
            print("No response to Start Scan")
            
        ser.close()
    except Exception as e:
        print(f"Serial error: {e}")

if __name__ == "__main__":
    test_raw_serial()
