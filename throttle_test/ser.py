import csv
from time import time
import serial

ser = serial.Serial('/dev/ttyACM0', timeout=1)
ser.baudrate = 9600

f = open('throttle_data.csv', 'w+')
writer = csv.writer(f, delimiter=',')

init = time()
while True:
    s = ser.readline().decode().strip()
    if s != '':
        rows = [float(x) for x in s.split(',')]
        rows.insert(0, time()-init)
        print(rows)
        writer.writerow(rows)
        f.flush()
