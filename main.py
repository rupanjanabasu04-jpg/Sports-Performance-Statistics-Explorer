import json
import csv
import statistics
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
PLOT_DIR = OUTPUT_DIR / "plots"
REPORT_DIR = OUTPUT_DIR / "reports"

ATHLETE_FILE = DATA_DIR / "athletes.json"
SESSION_FILE = DATA_DIR / "sessions.csv"

EVENT_LIMITS = {
    "100m": (9.0, 30.0),
    "400m": (40.0, 120.0),
    "1500m": (180.0, 600.0),
    "long_jump": (1.0, 9.0),
}

LOWER_IS_BETTER = {"100m", "400m", "1500m"}
HIGHER_IS_BETTER = {"long_jump"}


def setup_directories():
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def load_data():
    with open(ATHLETE_FILE, "r", encoding="utf-8") as f:
        athletes = json.load(f)

    with open(SESSION_FILE, "r", encoding="utf-8") as f:
        sessions = list(csv.DictReader(f))

    for row in sessions:
        row["result"] = float(row["result"])
    return athletes, sessions


def validate_data(athletes, sessions):
    print("\\nDATA VALIDATION")
    print("-" * 40)

    athlete_ids = set(athletes.keys()) if isinstance(athletes, dict) else {
        str(a.get("athlete_id", a.get("id", ""))) for a in athletes
    }

    valid = []
    excluded = []
    seen = set()

    for row in sessions:
        event = row.get("event", "").strip()
        athlete = row.get("athlete_id", "").strip()
        date = row.get("session_date", "").strip()
        result = row.get("result")

        key = (athlete, event, date)
        reason = None

        if event not in EVENT_LIMITS:
            reason = "Unknown event"
        elif athlete not in athlete_ids:
            reason = "Unknown athlete"
        elif key in seen:
            reason = "Duplicate record"
        else:
            low, high = EVENT_LIMITS[event]
            if not low <= result <= high:
                reason = f"Suspicious result: {result} (allowed {low}-{high})"

        seen.add(key)

        if reason:
            excluded.append((row, reason))
        else:
            valid.append(row)

    print(f"Total records: {len(sessions)}")
    print(f"Valid records: {len(valid)}")
    print(f"Excluded records: {len(excluded)}")

    if excluded:
        print("\\nWarnings / Excluded Records:")
        for row, reason in excluded:
            print(
                f"  {row.get('athlete_id')} | {row.get('event')} | "
                f"{row.get('session_date')} | {row.get('result')} -> {reason}"
            )
    else:
        print("No structural or critical data errors detected.")

    return valid, excluded

def get_athlete_name(athletes, athlete_id):
    if isinstance(athletes, dict):
        value = athletes.get(athlete_id, athlete_id)
        if isinstance(value, dict):
            return value.get("name", athlete_id)
        return value
    for athlete in athletes:
        if athlete.get("athlete_id", athlete.get("id")) == athlete_id:
            return athlete.get("name", athlete_id)
    return athlete_id


def calculate_athlete_statistics(records):
    stats = {}

    for athlete in sorted(set(r["athlete_id"] for r in records)):
        values = [r["result"] for r in records if r["athlete_id"] == athlete]
        if not values:
            continue

        stats[athlete] = {
            "average": statistics.mean(values),
            "best": min(values) if records[0]["event"] in LOWER_IS_BETTER else max(values),
            "worst": max(values) if records[0]["event"] in LOWER_IS_BETTER else min(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "count": len(values),
        }

    return stats


def calculate_rankings(records):
    event = records[0]["event"]
    stats = calculate_athlete_statistics(records)

    reverse = event in HIGHER_IS_BETTER

    rankings = sorted(
        stats.items(),
        key=lambda item: item[1]["average"],
        reverse=reverse
    )

    return rankings


def calculate_event_statistics(records):
    values = [r["result"] for r in records]

    return {
        "average": statistics.mean(values),
        "best": max(values) if records[0]["event"] in HIGHER_IS_BETTER else min(values),
        "worst": min(values) if records[0]["event"] in HIGHER_IS_BETTER else max(values),
        "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
        "count": len(values),
    }


def calculate_improvement(records):
    improvements = {}

    athletes = sorted(set(r["athlete_id"] for r in records))

    for athlete in athletes:
        athlete_records = sorted(
            [r for r in records if r["athlete_id"] == athlete],
            key=lambda r: r["session_date"]
        )

        if len(athlete_records) < 2:
            continue

        first = athlete_records[0]["result"]
        last = athlete_records[-1]["result"]

        event = athlete_records[0]["event"]

        if event in LOWER_IS_BETTER:
            change = first - last
        else:
            change = last - first

        improvements[athlete] = {
            "first": first,
            "last": last,
            "change": change,
            "improved": change > 0,
        }

    return improvements


def save_reports(event, records, excluded, athletes):
    rankings = calculate_rankings(records)
    event_stats = calculate_event_statistics(records)
    improvements = calculate_improvement(records)

    csv_path = REPORT_DIR / f"{event}_report.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow([
            "Rank", "Athlete ID", "Athlete Name", "Average",
            "Best", "Worst", "Standard Deviation",
            "Sessions", "Improvement", "Improved"
        ])

        for rank, (athlete, stat) in enumerate(rankings, start=1):
            imp = improvements.get(athlete, {})
            writer.writerow([
                rank,
                athlete,
                get_athlete_name(athletes, athlete),
                round(stat["average"], 3),
                round(stat["best"], 3),
                round(stat["worst"], 3),
                round(stat["std_dev"], 3),
                stat["count"],
                round(imp.get("change", 0), 3),
                imp.get("improved", False)
            ])

    print(f"\n{event.upper()} REPORT")
    print("-" * 55)
    print(f"Event average: {event_stats['average']:.3f}")
    print(f"Best result: {event_stats['best']:.3f}")
    print(f"Worst result: {event_stats['worst']:.3f}")
    print(f"Standard deviation: {event_stats['std_dev']:.3f}")

    print("\nRANKINGS")
    for rank, (athlete, stat) in enumerate(rankings, start=1):
        print(
            f"{rank}. {athlete} | Average: {stat['average']:.3f} | "
            f"Best: {stat['best']:.3f} | Consistency SD: {stat['std_dev']:.3f}"
        )

    print("\nIMPROVEMENT")
    for athlete, imp in improvements.items():
        status = "Improved" if imp["improved"] else "No improvement"
        print(f"{athlete}: {imp['first']} -> {imp['last']} | {imp['change']:.3f} | {status}")

    return rankings, event_stats, improvements


def save_plots(event, records, rankings, improvements):
    # Ranking chart
    athletes = [a for a, _ in rankings]
    averages = [s["average"] for _, s in rankings]

    plt.figure(figsize=(9, 5))
    plt.bar(athletes, averages)
    plt.title(f"{event} Athlete Rankings")
    plt.xlabel("Athlete")
    plt.ylabel("Average Result")
    plt.tight_layout()
    plt.savefig(PLOT_DIR / f"{event}_ranking.png", dpi=150)
    plt.close()

    # Performance trend
    plt.figure(figsize=(9, 5))

    for athlete in sorted(set(r["athlete_id"] for r in records)):
        data = sorted(
            [r for r in records if r["athlete_id"] == athlete],
            key=lambda r: r["session_date"]
        )
        plt.plot(
            [r["session_date"] for r in data],
            [r["result"] for r in data],
            marker="o",
            label=athlete
        )

    plt.title(f"{event} Performance Trend")
    plt.xlabel("Date")
    plt.ylabel("Result")
    plt.xticks(rotation=30)
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOT_DIR / f"{event}_trend.png", dpi=150)
    plt.close()


def save_summary(all_results, excluded):
    path = REPORT_DIR / "summary_report.txt"

    with open(path, "w", encoding="utf-8") as f:
        f.write("SPORTS PERFORMANCE STATISTICS EXPLORER\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write(f"Excluded suspicious records: {len(excluded)}\n\n")

        for event, stats in all_results.items():
            f.write(f"\nEVENT: {event}\n")
            f.write("-" * 30 + "\n")
            f.write(f"Average: {stats['average']:.3f}\n")
            f.write(f"Best: {stats['best']:.3f}\n")
            f.write(f"Worst: {stats['worst']:.3f}\n")
            f.write(f"Standard Deviation: {stats['std_dev']:.3f}\n")

        if excluded:
            f.write("\nEXCLUDED RECORDS\n")
            for row, reason in excluded:
                f.write(f"{row} | {reason}\n")


def main():
    setup_directories()

    print("=" * 55)
    print("SPORTS PERFORMANCE STATISTICS EXPLORER")
    print("=" * 55)

    athletes, sessions = load_data()

    print("\nData loaded successfully.")
    print(f"Number of athletes: {len(athletes)}")
    print(f"Number of records: {len(sessions)}")

    valid_records, excluded = validate_data(athletes, sessions)

    all_event_stats = {}

    events = sorted(set(r["event"] for r in valid_records))

    for event in events:
        event_records = [r for r in valid_records if r["event"] == event]

        rankings, stats, improvements = save_reports(
            event, event_records, excluded, athletes
        )

        save_plots(event, event_records, rankings, improvements)
        all_event_stats[event] = stats

    save_summary(all_event_stats, excluded)

    print("\n" + "=" * 55)
    print("ANALYSIS COMPLETED SUCCESSFULLY")
    print("=" * 55)
    print(f"Reports saved in: {REPORT_DIR}")
    print(f"Graphs saved in: {PLOT_DIR}")


if __name__ == "__main__":
    main()
