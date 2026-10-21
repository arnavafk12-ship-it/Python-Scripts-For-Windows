import psutil

def get_processes():
    processes = []

    for process in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = process.info
            processes.append({
                "pid": info["pid"],
                "name": info["name"] or "Unknown",
                "cpu": info["cpu_percent"],
                "memory": info["memory_percent"]
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return processes


def show_processes():
    processes = get_processes()
    processes.sort(key=lambda x: x["memory"], reverse=True)

    print("\n" + "=" * 70)
    print("                    APEX PROCESS MANAGER")
    print("=" * 70)
    print(f"{'PID':<10}{'PROCESS':<30}{'CPU %':<12}{'RAM %':<10}")
    print("-" * 70)

    for process in processes[:30]:
        print(
            f"{process['pid']:<10}"
            f"{process['name'][:28]:<30}"
            f"{process['cpu']:<12.1f}"
            f"{process['memory']:<10.2f}"
        )

    print("=" * 70)
    print(f"Showing top {min(30, len(processes))} processes by RAM usage")


if __name__ == "__main__":
    show_processes()