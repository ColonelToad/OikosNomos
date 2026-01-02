import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")

def on_publish(client, userdata, mid, reason_code, properties):
    print(f"Message {mid} published")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="test_pub")
client.on_connect = on_connect
client.on_publish = on_publish

print("Connecting...")
client.connect("localhost", 1883, 60)
client.loop_start()

time.sleep(2)  # Wait for connection

print("Publishing test message...")
payload = {
    "timestamp": datetime.now().isoformat() + "Z",
    "device_category": "base_load",
    "power_w": 150.5,
    "energy_wh": 12.5
}

result = client.publish("home/home_001/device/base_load/power", json.dumps(payload), qos=1)
result.wait_for_publish()
print(f"Publish result: rc={result.rc}, mid={result.mid}")

time.sleep(1)  # Allow delivery

client.loop_stop()
client.disconnect()
print("Done")
