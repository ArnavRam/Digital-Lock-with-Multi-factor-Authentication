"""
ESP32 Multi-Factor Smart Lock System
-------------------------------------
Author: Arnav

Description:
    Secure access control system with:
        1. RFID authentication
        2. PIN entry (4x4 Keypad)
        3. OTP verification (Telegram)
        4. Smart LED indicators for Wi-Fi and Lock Status

Hardware:
    - ESP32 (MicroPython)
    - RC522 RFID Module (SPI)
    - 4x4 Matrix Keypad
    - Red + Green LEDs (Lock status)
    - Blue/Onboard LED for Wi-Fi indicator
"""

import network
import time
import urequests
import urandom
import machine
from machine import Pin
from mfrc522 import MFRC522
from keypad import Keypad

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Wi-Fi
WIFI_SSID = "Arnav's Android"
WIFI_PASS = "cmfphone1"

# Telegram
BOT_TOKEN = "8412858567:AAGOhM89r01IXHAtolz3Bg6FsiloI29ledM"
CHAT_ID = "1327556061"
AUTHORIZED_USER_ID = 1327556061

# Authentication
AUTHORIZED_UIDS = ["11 B5 F9 03", "71 DC B9 89"]
PIN_CODE = "0000"

# GPIO Pins
RED_LED_PIN = 15      # Red LED - Lock / Denied
GREEN_LED_PIN = 5     # Green LED - Access granted
WIFI_LED_PIN = 2      # Onboard LED (Wi-Fi status)

RFID_RST_PIN = 22
RFID_CS_PIN = 21
RFID_SCK_PIN = 18
RFID_MOSI_PIN = 23
RFID_MISO_PIN = 19
KEYPAD_PINS = [32, 33, 25, 26, 27, 14, 12, 13]

KEY_MAP = [
    ['1','2','3','A'],
    ['4','5','6','B'],
    ['7','8','9','C'],
    ['*','0','#','D']
]

# States
LOCKED = "LOCKED"
WAITING_FOR_PIN = "WAITING_FOR_PIN"
WAITING_FOR_OTP = "WAITING_FOR_OTP"
UNLOCKED = "UNLOCKED"

# ---------------------------------------------------------------------------
# Hardware Initialization
# ---------------------------------------------------------------------------

red_led = Pin(RED_LED_PIN, Pin.OUT)
green_led = Pin(GREEN_LED_PIN, Pin.OUT)
wifi_led = Pin(WIFI_LED_PIN, Pin.OUT)

rfid = MFRC522(sck=RFID_SCK_PIN, mosi=RFID_MOSI_PIN, miso=RFID_MISO_PIN, rst=RFID_RST_PIN, cs=RFID_CS_PIN)
keypad = Keypad(KEYPAD_PINS, KEY_MAP)

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------

current_state = LOCKED
entered_pin = ""
generated_otp = ""
last_activity_time = 0
last_telegram_check = 0
last_led_toggle = 0

telegram_check_interval = 5000  # ms
wifi_led_interval_connected = 2000  # slow blink
wifi_led_interval_disconnected = 300  # fast blink
timeout_seconds = 30
last_update_id = 0

# ---------------------------------------------------------------------------
# Wi-Fi & Telegram
# ---------------------------------------------------------------------------

def connect_wifi():
    sta = network.WLAN(network.STA_IF)
    if sta.isconnected():
        return True

    print("Connecting to Wi-Fi...")
    sta.active(True)
    sta.connect(WIFI_SSID, WIFI_PASS)

    for _ in range(20):
        if sta.isconnected():
            print("Wi-Fi Connected.")
            return True
        time.sleep(1)
    print("Wi-Fi connection failed.")
    return False


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message.replace(' ', '%20')}"
    try:
        res = urequests.get(url)
        res.close()
    except Exception as e:
        print(f"Telegram send error: {e}")


def check_telegram_commands(execute=True):
    global last_update_id, current_state
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update_id + 1}&limit=1"
    try:
        res = urequests.get(url)
        data = res.json()
        res.close()
        if data['ok'] and data['result']:
            update = data['result'][0]
            last_update_id = update['update_id']
            if execute:
                msg = update.get('message', {})
                sender = msg.get('from', {}).get('id')
                text = msg.get('text', '').strip()
                if sender == AUTHORIZED_USER_ID:
                    handle_telegram_command(text)
    except Exception as e:
        print(f"Telegram check error: {e}")


def handle_telegram_command(text):
    global current_state
    if text == '/status':
        send_telegram_message(f"STATUS: {current_state}")
    elif text == '/lock':
        if current_state == UNLOCKED:
            reset_to_locked_state()
            send_telegram_message("Lock secured.")
        else:
            send_telegram_message("Lock already secured.")
    elif text == '/reboot':
        send_telegram_message("Rebooting device.")
        time.sleep(1)
        machine.reset()

# ---------------------------------------------------------------------------
# Core Functions
# ---------------------------------------------------------------------------

def reset_to_locked_state():
    global current_state, entered_pin, generated_otp
    red_led.on()
    green_led.off()
    wifi_led.off()
    current_state = LOCKED
    entered_pin = ""
    generated_otp = ""
    print("System locked. Awaiting RFID scan.")


def generate_otp():
    return str(urandom.randint(100000, 999999))


def read_rfid():
    (status, _) = rfid.request(rfid.REQIDL)
    if status == rfid.OK:
        (status, raw_uid) = rfid.anticoll(rfid.PICC_ANTICOLL1)
        if status == rfid.OK:
            return "%02X %02X %02X %02X" % tuple(raw_uid[:4])
    return None


def update_wifi_led(sta):
    global last_led_toggle
    now = time.ticks_ms()

    if current_state == UNLOCKED:
        wifi_led.on()
        return

    if not sta.isconnected():
        if time.ticks_diff(now, last_led_toggle) > wifi_led_interval_disconnected:
            wifi_led.value(not wifi_led.value())
            last_led_toggle = now
    else:
        if time.ticks_diff(now, last_led_toggle) > wifi_led_interval_connected:
            wifi_led.value(not wifi_led.value())
            last_led_toggle = now

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

sta_if = network.WLAN(network.STA_IF)
connect_wifi()
send_telegram_message("Smart Lock System Online.")
check_telegram_commands(execute=False)
reset_to_locked_state()

# ---------------------------------------------------------------------------
# Main Loop
# ---------------------------------------------------------------------------

while True:
    update_wifi_led(sta_if)

    # Telegram check
    if time.ticks_diff(time.ticks_ms(), last_telegram_check) > telegram_check_interval:
        check_telegram_commands()
        last_telegram_check = time.ticks_ms()

    # Timeout
    if current_state != LOCKED and time.ticks_diff(time.ticks_ms(), last_activity_time) > (timeout_seconds * 1000):
        print("Timeout: Returning to locked state.")
        reset_to_locked_state()

    # RFID authentication
    if current_state == LOCKED:
        uid = read_rfid()
        if uid:
            print(f"Card scanned: {uid}")
            if uid in AUTHORIZED_UIDS:
                send_telegram_message(f"Authorized card detected: {uid}")
                current_state = WAITING_FOR_PIN
                last_activity_time = time.ticks_ms()
                print("RFID verified. Enter PIN and press #.")
            else:
                print("Unauthorized card.")
                send_telegram_message(f"ALERT: Unauthorized card detected! UID: {uid}")
                red_led.on()
                green_led.off()
                time.sleep(1)

    # PIN input
    elif current_state == WAITING_FOR_PIN:
        key = keypad.get_key()
        if key:
            print(key, end="")
            last_activity_time = time.ticks_ms()
            if key == '#':
                if entered_pin == PIN_CODE:
                    generated_otp = generate_otp()
                    send_telegram_message(f"Your OTP is: {generated_otp}")
                    current_state = WAITING_FOR_OTP
                    print("\nPIN verified. OTP sent.")
                else:
                    print("\nInvalid PIN.")
                    reset_to_locked_state()
                entered_pin = ""
            elif key == '*':  # Clear input for typos
                print("\nInput cleared. Enter again:")
                entered_pin = ""
            else:
                entered_pin += key

    # OTP input
    elif current_state == WAITING_FOR_OTP:
        key = keypad.get_key()
        if key:
            print(key, end="")
            last_activity_time = time.ticks_ms()
            if key == '#':
                if entered_pin == generated_otp:
                    print("\nAccess granted.")
                    red_led.off()
                    green_led.on()
                    wifi_led.on()
                    current_state = UNLOCKED
                    last_activity_time = time.ticks_ms()
                else:
                    print("\nInvalid OTP.")
                    reset_to_locked_state()
                entered_pin = ""
            elif key == '*':  # Clear OTP input
                print("\nInput cleared. Enter again:")
                entered_pin = ""
            else:
                entered_pin += key

    # Unlocked state
    elif current_state == UNLOCKED:
        if time.ticks_diff(time.ticks_ms(), last_activity_time) > 30000:
            print("Auto-locking.")
            reset_to_locked_state()

    time.sleep_ms(20)

