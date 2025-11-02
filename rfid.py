from machine import Pin
from mfrc522 import MFRC522
import time

# RC522 wiring (ESP32)
sck = 18
mosi = 23
miso = 19
rst = 22
cs = 21  # SDA

# Initialize reader (this library uses 6 positional arguments)
rdr = MFRC522(sck, mosi, miso, rst, cs)

print("Place card near the reader...")

while True:
    (stat, tag_type) = rdr.request(rdr.REQIDL)
    if stat == rdr.OK:
        (stat, raw_uid) = rdr.anticoll(rdr.PICC_ANTICOLL1)
        if stat == rdr.OK:
            uid = "".join(["%02X" % x for x in raw_uid])
            print("Card detected! UID:", uid)
            time.sleep(1)

