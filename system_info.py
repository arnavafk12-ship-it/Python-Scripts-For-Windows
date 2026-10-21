import datetime
import os
import platform
import time
from plyer import notification
import psutil

# --- CONFIGURATION THRESHOLDS ---
CPU_THRESHOLD = 80.0  # Alert if CPU exceeds 80%
RAM_THRESHOLD = 85.0  # Alert if RAM exceeds 85%
DISK_THRESHOLD = 90.0  # Alert if C: Drive exceeds 90%
CHECK_INTERVAL = 5  # Check resources every 5 seconds
ALERT_COOLDOWN = 300  # 5-minute alert cooldown

LOG_FILE = os.path.join(os.path.expanduser("~"), "Desktop", "system_monitor_log.txt")


def log_message(message):
    """Logs to Desktop file AND prints to terminal so you see it working!"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] {message}"
    print(formatted_msg)  # <-- This keeps your terminal informative!
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted_msg + "\n")


def get_top_processes(metric="cpu", limit=3):
    """Finds the top 3 apps eating up your resources."""
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            # Fetch process data safely
            if metric == "cpu":
                proc_val = proc.info["cpu_percent"]
            else:
                proc_val = proc.info["memory_percent"]
            processes.append((proc.info["name"], proc_val))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # Sort processes by highest usage
    processes.sort(key=lambda x: x[1], reverse=True)
    return ", ".join([f"{name} ({val:.1f}%)" for name, val in processes[:limit]])


def initialize_system_profile():
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")

    startup_text = (
        f"\n=========================================\n"
        f"    SYSTEM MONITOR STARTED\n"
        f"=========================================\n"
        f"OS: {platform.system()} {platform.release()}\n"
        f"Processor: {platform.processor()}\n"
        f"CPU Cores: {psutil.cpu_count(logical=False)} Physical / {psutil.cpu_count(logical=True)} Logical\n"
        f"Total RAM: {ram.total / (1024**3):.2f} GB\n"
        f"Total Disk Space (C:): {disk.total / (1024**3):.2f} GB\n"
        f"=========================================\n"
    )
    print(startup_text)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(startup_text)


def main():
    initialize_system_profile()
    last_alerts = {"cpu": 0, "ram": 0, "disk": 0}

    # Prime CPU counter
    psutil.cpu_percent(interval=None)
    time.sleep(1)

    log_message("Monitoring active. Waiting silently for threshold violations...")

    try:
        while True:
            current_time = time.time()

            # 1. High CPU Track + Top Apps
            cpu_usage = psutil.cpu_percent(interval=None)
            if cpu_usage > CPU_THRESHOLD:
                if current_time - last_alerts["cpu"] > ALERT_COOLDOWN:
                    top_apps = get_top_processes(metric="cpu")
                    msg = f"CPU load is spiking at {cpu_usage}%! Top culprits: {top_apps}"
                    log_message(f"ALERT: ⚠️ High CPU Usage - {msg}")
                    notification.notify(
                        title="⚠️ High CPU Usage",
                        message=msg[:120],
                        timeout=5,
                    )
                    last_alerts["cpu"] = current_time

            # 2. RAM Track + Top Apps
            ram = psutil.virtual_memory()
            if ram.percent > RAM_THRESHOLD:
                if current_time - last_alerts["ram"] > ALERT_COOLDOWN:
                    top_apps = get_top_processes(metric="ram")
                    msg = f"RAM is at {ram.percent}%. Top culprits: {top_apps}"
                    log_message(f"ALERT: ⚠️ High RAM Usage - {msg}")
                    notification.notify(
                        title="⚠️ High RAM Usage",
                        message=msg[:120],
                        timeout=5,
                    )
                    last_alerts["ram"] = current_time

            # 3. Disk Space Track
            disk = psutil.disk_usage("C:\\")
            if disk.percent > DISK_THRESHOLD:
                if current_time - last_alerts["disk"] > ALERT_COOLDOWN:
                    msg = f"C: Drive is {disk.percent}% full! Only {disk.free / (1024**3):.1f} GB free."
                    log_message(f"ALERT: 🚨 Low Disk - {msg}")
                    notification.notify(
                        title="🚨 Critical Storage Alert", message=msg, timeout=5
                    )
                    last_alerts["disk"] = current_time

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        log_message("Monitoring gracefully stopped by user.")


if __name__ == "__main__":
    main()
