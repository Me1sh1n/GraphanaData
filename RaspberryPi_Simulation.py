import paho.mqtt.client as mqtt
import random
import time
import json
from datetime import datetime

# ----------------------------
# MQTT SETTINGS
# ----------------------------
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "factory/machine/vibration"
PUBLISH_INTERVAL = 10  # seconds

# ----------------------------
# DAY CYCLE SETTINGS
# ----------------------------
DAY_CYCLE_SECONDS = 2880  # full simulated day length
DAY_START = 0.25
DAY_END = 0.75

# ----------------------------
# VALUE LIMITS
# ----------------------------
SOLAR_MIN = 0.0
SOLAR_MAX = 100.0

BATTERY_MIN = 22.0
BATTERY_MAX = 26.0

TEMP_MIN = 16.0
TEMP_MAX = 24.0

BASE_CURRENT_MIN = 2.3
BASE_CURRENT_MAX = 2.7

HIGH_CURRENT_MIN = 3.5
HIGH_CURRENT_MAX = 4.0

VIBRATION_MIN = 1.0
VIBRATION_MAX = 100.0

# ----------------------------
# INITIAL VALUES
# ----------------------------
solar_power = 0.0
battery_voltage = 23.5
temperature = 18.0
current_draw = 2.5
alarm = 0
vibration = 1.0

simulation_start = time.time()

# ----------------------------
# HIGH-LOAD EVENT STATE
# ----------------------------
high_load_active = False
high_load_end_time = 0
high_load_start_time = 0

hour_start_time = time.time()
scheduled_spike_time = None
scheduled_spike_duration = 0

# ----------------------------
# HELPER FUNCTIONS
# ----------------------------
def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def get_cycle_fraction():
    elapsed = time.time() - simulation_start
    return (elapsed % DAY_CYCLE_SECONDS) / DAY_CYCLE_SECONDS


def is_daytime(cycle_fraction):
    return DAY_START <= cycle_fraction <= DAY_END


def get_day_progress(cycle_fraction):
    if not is_daytime(cycle_fraction):
        return None
    return (cycle_fraction - DAY_START) / (DAY_END - DAY_START)


def schedule_next_hour_spike():
    """
    Schedule exactly one random spike inside the next 1-hour window.
    Spike starts at a random second in the hour and lasts 5-10 minutes.
    """
    global hour_start_time, scheduled_spike_time, scheduled_spike_duration

    hour_start_time = time.time()
    scheduled_spike_duration = random.uniform(5 * 60, 10 * 60)
    latest_start = max(0, 3600 - scheduled_spike_duration)
    random_offset = random.uniform(0, latest_start)

    scheduled_spike_time = hour_start_time + random_offset


def simulate_solar(previous, cycle_fraction):
    if not is_daytime(cycle_fraction):
        drop = random.uniform(2.0, 6.0)
        new_value = previous - drop
        return round(clamp(new_value, SOLAR_MIN, SOLAR_MAX), 1)

    day_progress = get_day_progress(cycle_fraction)

    if day_progress < 0.15:
        target_min, target_max = 5, 35
    elif day_progress < 0.35:
        target_min, target_max = 30, 70
    elif day_progress < 0.65:
        target_min, target_max = 75, 100
    elif day_progress < 0.85:
        target_min, target_max = 30, 70
    else:
        target_min, target_max = 5, 30

    target = random.uniform(target_min, target_max)

    if previous < target:
        step = random.uniform(1.0, 6.0)
        new_value = previous + step
    else:
        step = random.uniform(1.0, 6.0)
        new_value = previous - step

    new_value += random.uniform(-1.5, 1.5)

    return round(clamp(new_value, SOLAR_MIN, SOLAR_MAX), 1)


def simulate_battery(previous, solar_power, alarm_active):
    if solar_power >= 80:
        delta = random.uniform(0.01, 0.05)
    elif solar_power >= 40:
        delta = random.uniform(-0.01, 0.03)
    elif solar_power > 5:
        delta = random.uniform(-0.04, 0.01)
    else:
        delta = random.uniform(-0.08, -0.03)

    if alarm_active:
        delta -= random.uniform(0.01, 0.03)

    new_value = previous + delta
    return round(clamp(new_value, BATTERY_MIN, BATTERY_MAX), 2)


def simulate_temperature(previous, solar_power, cycle_fraction):
    if not is_daytime(cycle_fraction):
        target = random.uniform(16.0, 17.5)
    else:
        target = TEMP_MIN + (solar_power / SOLAR_MAX) * (TEMP_MAX - TEMP_MIN)
        target += random.uniform(-0.5, 0.5)

    if previous < target:
        step = random.uniform(0.05, 0.25)
        new_value = previous + step
    else:
        step = random.uniform(0.05, 0.25)
        new_value = previous - step

    return round(clamp(new_value, TEMP_MIN, TEMP_MAX), 2)


def update_high_load_state():
    """
    One spike is scheduled at a random time within each hour.
    """
    global high_load_active, high_load_end_time, high_load_start_time
    global hour_start_time, scheduled_spike_time, scheduled_spike_duration

    now = time.time()

    # Start a new hourly window if needed
    if now >= hour_start_time + 3600:
        schedule_next_hour_spike()

    # Start the spike when its scheduled time arrives
    if (not high_load_active) and scheduled_spike_time is not None and now >= scheduled_spike_time:
        high_load_active = True
        high_load_start_time = scheduled_spike_time
        high_load_end_time = scheduled_spike_time + scheduled_spike_duration

        # Prevent re-triggering inside same hour
        scheduled_spike_time = None

    # End active spike
    if high_load_active and now >= high_load_end_time:
        high_load_active = False


def simulate_current():
    if high_load_active:
        return round(random.uniform(HIGH_CURRENT_MIN, HIGH_CURRENT_MAX), 2), 1
    else:
        return round(random.uniform(BASE_CURRENT_MIN, BASE_CURRENT_MAX), 2), 0


def simulate_vibration():
    """
    Normal state:
    - low vibration near 1 with tiny noise

    During high-load spike:
    - vibration rises erratically from ~1 toward 100
    - reaches its highest zone around the middle of the spike
    - then falls erratically back toward ~1
    - includes random sharp peaks like the graph
    """
    if not high_load_active:
        return round(random.uniform(1.0, 3.0), 2)

    now = time.time()
    duration = high_load_end_time - high_load_start_time

    if duration <= 0:
        return round(random.uniform(1.0, 3.0), 2)

    progress = (now - high_load_start_time) / duration
    progress = clamp(progress, 0.0, 1.0)

    # Triangle-shaped envelope:
    # 0 at start, 1 at middle, 0 at end
    if progress <= 0.5:
        envelope = progress / 0.5
    else:
        envelope = (1.0 - progress) / 0.5

    # Base trend from 1 -> 100 -> 1
    trend = VIBRATION_MIN + envelope * (VIBRATION_MAX - VIBRATION_MIN)

    # Make it erratic:
    # more randomness near the middle
    noise_strength = 5 + envelope * 30
    noise = random.uniform(-noise_strength, noise_strength)

    # Add occasional upward bursts/spikes, especially near the middle
    burst = 0
    burst_chance = 0.10 + envelope * 0.35
    if random.random() < burst_chance:
        burst = random.uniform(5, 35) * envelope

    value = trend + noise + burst

    return round(clamp(value, VIBRATION_MIN, VIBRATION_MAX), 2)


# ----------------------------
# MQTT CALLBACKS
# ----------------------------
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")


def on_publish(client, userdata, mid):
    print(f"Message {mid} published")


# ----------------------------
# MQTT SETUP
# ----------------------------
client = mqtt.Client()
client.on_connect = on_connect
client.on_publish = on_publish

client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

# Schedule the first random spike
schedule_next_hour_spike()

# ----------------------------
# MAIN LOOP
# ----------------------------
try:
    while True:
        cycle_fraction = get_cycle_fraction()

        update_high_load_state()
        current_draw, alarm = simulate_current()

        solar_power = simulate_solar(solar_power, cycle_fraction)
        battery_voltage = simulate_battery(battery_voltage, solar_power, alarm == 1)
        temperature = simulate_temperature(temperature, solar_power, cycle_fraction)
        vibration = simulate_vibration()

        payload = {
            "timestamp": int(time.time()),
            "datetime": datetime.now().isoformat(),
            "day_cycle_position": round(cycle_fraction, 3),
            "is_daytime": 1 if is_daytime(cycle_fraction) else 0,
            "solar_power_w": solar_power,
            "battery_voltage_v": battery_voltage,
            "temperature_c": temperature,
            "current_draw_a": current_draw,
            "alarm": alarm,
            "vibration": vibration
        }

        message = json.dumps(payload)

        client.publish(MQTT_TOPIC, message)
        print(f"Published to {MQTT_TOPIC}: {message}")

        time.sleep(PUBLISH_INTERVAL)

except KeyboardInterrupt:
    print("Simulation stopped by user")

finally:
    client.loop_stop()
    client.disconnect()
    print("MQTT disconnected cleanly")