import json
import sys

def process_temperature_data(config_file="config.json"):
    try:
        with open(config_file, "r") as f:
            data = json.load(f)

        temperatures = data.get("temperatures", [])
        if not temperatures:
            print("No temperature data found.")
            return

        avg_temp = sum(temperatures) / len(temperatures)
        print(f"Average Temperature: {avg_temp:.2f}°C")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    process_temperature_data()
