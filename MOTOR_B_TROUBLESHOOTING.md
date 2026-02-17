MOTOR B (RIGHT MOTOR) TROUBLESHOOTING GUIDE
=============================================

🔍 DIAGNOSTIC STEPS (Run on Raspberry Pi with sudo):

1. Test Motor B GPIO Pins:
   sudo python3 diagnose_motor_b.py
   
   Use a multimeter to check:
   - GPIO {GPIO_IN3_PIN} (IN3): Should show 3.3V when HIGH, 0V when LOW
   - GPIO {GPIO_IN4_PIN} (IN4): Should show 3.3V when HIGH, 0V when LOW
   - GPIO {GPIO_ENB_PIN} (ENB): Should show PWM signal

2. Test Motor B Only:
   sudo python3 test_motor_b_only.py
   
   Listen and feel for motor rotation:
   - Motor should spin forward for 3 seconds
   - Motor should spin backward for 3 seconds
   - Motor should respond to speed changes

=============================================
COMMON ISSUES & SOLUTIONS
=============================================

❌ ISSUE: Motor B GPIO pins show correct voltage but motor doesn't spin

SOLUTIONS:
1. Check L298N OUT3/OUT4 pins have 12V across them
2. Verify motor wires are connected to OUT3/OUT4
3. Try swapping motor wires (OUT3 ↔ OUT4)
4. Motor B may be defective
5. L298N Motor B section may be defective

❌ ISSUE: Motor B GPIO pins show NO voltage change

SOLUTIONS:
1. GPIO pin numbers may be WRONG in config.py
2. GPIO pins may not be configured correctly
3. Raspberry Pi GPIO may be damaged
4. Check /boot/config.txt for GPIO conflicts

❌ ISSUE: Motor B runs but wrong direction

SOLUTIONS:
1. Swap IN3 and IN4 in motor_b_forward() function
2. Or swap physical motor wire connections
3. Update config.py with correct pin mapping

❌ ISSUE: Motor B runs too slow or not at all

SOLUTIONS:
1. Check ENB PWM pin is connected to L298N
2. Verify power supply provides enough current
3. Try increasing PWM frequency in config.py
4. Check for loose connections

=============================================
GPIO PIN VERIFICATION
=============================================

Current config in config.py:
Motor B:
  IN3 = {GPIO_IN3_PIN}
  IN4 = {GPIO_IN4_PIN}
  ENB = {GPIO_ENB_PIN}

Expected L298N Connections:
  IN3 (GPIO {GPIO_IN3_PIN}) -> L298N IN3
  IN4 (GPIO {GPIO_IN4_PIN}) -> L298N IN4
  ENB (GPIO {GPIO_ENB_PIN}) -> L298N ENB
  GND -> L298N GND
  Power Supply -> L298N +5V/+12V

Motor B OUT pins:
  OUT3 -> Motor B Wire 1
  OUT4 -> Motor B Wire 2

=============================================
QUICK TEST CHECKLIST
=============================================

Before running:
□ Power supply connected to L298N (5V-12V)
□ Motor B wires connected to OUT3/OUT4
□ All GND connections secure
□ Running with sudo
□ config.py pin numbers match your wiring

During test:
□ Listen for motor sound
□ Feel for motor vibration
□ Check for smoke (short circuit!)
□ Verify direction changes

=============================================
IF STILL NOT WORKING
=============================================

1. Try Motor A with Motor B pins:
   - Swap motor connectors at L298N
   - If Motor A runs on OUT3/OUT4, then Motor B section is bad
   
2. Check L298N with different power supply:
   - Try 5V, then 12V
   - Check for burnt components
   
3. Use continuity tester:
   - Verify wires are connected end-to-end
   - Check for broken motor connections

Contact: Check L298N datasheet at Microchip website
