import matplotlib.pyplot as plt
import csv

time_values_l = []
voltages_l = []
with open('throttle_data_l.csv', 'r') as file:
    reader = csv.reader(file)
    for row in reader:
        time_values_l.append(float(row[0]))
        voltages_l.append(float(row[1]))
plt.plot(time_values_l, voltages_l)
print(270*5/1023)
print(624*5/1023)

time_values_r = []
voltages_r = []
with open('throttle_data_r.csv', 'r') as file:
    reader = csv.reader(file)
    for row in reader:
        time_values_r.append(float(row[0]))
        voltages_r.append(float(row[1]))
plt.plot(time_values_r, voltages_r)
print(voltages_r)
print(273*5/1023)
print(621*5/1023)
plt.show()
