import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ==============================
# PROJECT CONFIGURATION
# ==============================

BASE_DIR = Path(__file__).resolve().parent

ATHLETE_FILE = BASE_DIR / "data" / "athletes.json"
SESSION_FILE = BASE_DIR / "data" / "sessions.csv"

OUTPUT_DIR = BASE_DIR / "output"
PLOT_DIR = OUTPUT_DIR / "plots"
REPORT_DIR = OUTPUT_DIR / "reports"

PLOT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_COLUMNS = [
    "session_date",
    "athlete_id",
    "event",
    "result",
    "unit"
]

EVENT_LIMITS = {
    "100m": (9.0, 30.0),
    "400m": (40.0, 120.0),
    "1500m": (180.0, 600.0),
    "long_jump": (1.0, 9.0)
}

# Lower result is better for running events.
# Higher result is better for long jump.
LOWER_IS_BETTER = ["100m", "400m", "1500m"]


# ==============================
# DATA LOADING
# ==============================

def load_data():
    """Load athlete information and performance records."""

    with open(ATHLETE_FILE, "r") as file:
        athletes = json.load(file)

    sessions = pd.read_csv(SESSION_FILE)

    print("\nData loaded successfully.")
    print(f"Number of athletes: {len(athletes)}")
    print(f"Number of records: {len(sessions)}")

    return athletes, sessions


# ==============================
# DATA VALIDATION
# ==============================

def validate_data(athletes, sessions):
    """Validate dataset structure and performance records."""

    errors = []
    warnings = []

    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in sessions.columns
    ]

    if missing_columns:
        errors.append(f"Missing columns: {missing_columns}")
        return errors, warnings

    missing_values = sessions[REQUIRED_COLUMNS].isnull().sum()

    for column, count in missing_values.items():
        if count > 0:
            errors.append(f"{column} contains {count} missing values")

    duplicates = sessions.duplicated(
        subset=["session_date", "athlete_id", "event"]
    )

    if duplicates.any():
        errors.append(
            f"{duplicates.sum()} duplicate performance records found"
        )

    valid_athlete_ids = set(athletes.keys())

    invalid_ids = sessions[
        ~sessions["athlete_id"].isin(valid_athlete_ids)
    ]

    if not invalid_ids.empty:
        errors.append("Records contain unknown athlete IDs")

    unknown_events = sessions[
        ~sessions["event"].isin(EVENT_LIMITS.keys())
    ]

    if not unknown_events.empty:
        errors.append("Unknown event names detected")

    sessions["result"] = pd.to_numeric(
        sessions["result"], errors="coerce"
    )

    if sessions["result"].isnull().any():
        errors.append("Non-numeric or missing performance values found")

    for event, (minimum, maximum) in EVENT_LIMITS.items():

        event_data = sessions[sessions["event"] == event]

        suspicious = event_data[
            (event_data["result"] < minimum) |
            (event_data["result"] > maximum)
        ]

        for _, row in suspicious.iterrows():
            warnings.append(
                f"Suspicious result: {row['athlete_id']} | "
                f"{event} | {row['result']} {row['unit']} | "
                f"Date: {row['session_date']}"
            )

    sessions["session_date"] = pd.to_datetime(
        sessions["session_date"], errors="coerce"
    )

    if sessions["session_date"].isnull().any():
        errors.append("Invalid dates detected")

    return errors, warnings


# ==============================
# ATHLETE NAME HELPER
# ==============================

def get_athlete_name(athletes, athlete_id):
    """Retrieve athlete name if available."""

    athlete = athletes.get(athlete_id)

    if isinstance(athlete, dict):
        return athlete.get("name", athlete_id)

    if isinstance(athlete, str):
        return athlete

    return athlete_id


# ==============================
# PERFORMANCE ANALYSIS
# ==============================

def analyze_event(sessions, event):
    """Calculate statistics for athletes in one event."""

    event_data = sessions[sessions["event"] == event].copy()

    results = []

    for athlete_id, athlete_data in event_data.groupby("athlete_id"):

        athlete_data = athlete_data.sort_values("session_date")

        values = athlete_data["result"].astype(float)

        first_result = values.iloc[0]
        last_result = values.iloc[-1]

        if event in LOWER_IS_BETTER:
            best_result = values.min()
            improvement = first_result - last_result
        else:
            best_result = values.max()
            improvement = last_result - first_result

        results.append({
            "athlete_id": athlete_id,
            "average": values.mean(),
            "best_result": best_result,
            "worst_result": values.max() if event in LOWER_IS_BETTER else values.min(),
            "std_dev": values.std(ddof=0),
            "first_result": first_result,
            "last_result": last_result,
            "improvement": improvement,
            "sessions": len(values),
            "unit": athlete_data["unit"].iloc[0]
        })

    analysis = pd.DataFrame(results)

    if analysis.empty:
        return analysis

    # Ranking is based on average performance across recorded sessions.
    analysis["rank"] = analysis["average"].rank(
        ascending=(event in LOWER_IS_BETTER),
        method="min"
    ).astype(int)

    analysis = analysis.sort_values("rank")

    return analysis


# ==============================
# DISPLAY RANKINGS
# ==============================

def display_rankings(athletes, event, analysis):

    print(f"\n{'=' * 65}")
    print(f"EVENT: {event.upper()}")
    print("=" * 65)

    if analysis.empty:
        print("No records available.")
        return

    print(
        f"{'Rank':<6}{'Athlete':<12}{'Average':<12}"
        f"{'Best':<12}{'Consistency':<14}{'Improvement'}"
    )

    print("-" * 65)

    for _, row in analysis.iterrows():

        athlete_name = get_athlete_name(
            athletes, row["athlete_id"]
        )

        print(
            f"{int(row['rank']):<6}"
            f"{athlete_name:<12}"
            f"{row['average']:<12.2f}"
            f"{row['best_result']:<12.2f}"
            f"{row['std_dev']:<14.3f}"
            f"{row['improvement']:+.2f}"
        )


# ==============================
# GRAPH GENERATION
# ==============================

def generate_event_graphs(sessions, athletes, event, analysis):
    """Generate performance trend and ranking graphs."""

    event_data = sessions[sessions["event"] == event].copy()

    if event_data.empty:
        return

    # --------------------------
    # Performance trend graph
    # --------------------------

    plt.figure(figsize=(10, 6))

    for athlete_id, athlete_data in event_data.groupby("athlete_id"):

        athlete_data = athlete_data.sort_values("session_date")

        plt.plot(
            athlete_data["session_date"],
            athlete_data["result"],
            marker="o",
            label=athlete_id
        )

    plt.title(f"{event} - Performance Trend")
    plt.xlabel("Training Date")
    plt.ylabel(event_data["unit"].iloc[0])
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    trend_path = PLOT_DIR / f"{event}_trend.png"
    plt.savefig(trend_path, dpi=300)
    plt.close()

    # --------------------------
    # Average performance graph
    # --------------------------

    if not analysis.empty:

        ranked = analysis.sort_values(
            "average",
            ascending=(event not in LOWER_IS_BETTER)
        )

        plt.figure(figsize=(9, 6))

        plt.bar(
            ranked["athlete_id"],
            ranked["average"]
        )

        plt.title(f"{event} - Average Performance Ranking")
        plt.xlabel("Athlete")
        plt.ylabel("Average (" + str(ranked["unit"].iloc[0]) + ")")
        plt.grid(axis="y")
        plt.tight_layout()

        ranking_path = PLOT_DIR / f"{event}_ranking.png"
        plt.savefig(ranking_path, dpi=300)
        plt.close()


# ==============================
# REPORT GENERATION
# ==============================

def save_reports(athletes, event, analysis):

    if analysis.empty:
        return

    report = analysis.copy()

    report.insert(
        1,
        "athlete_name",
        report["athlete_id"].apply(
            lambda athlete_id: get_athlete_name(
                athletes, athlete_id
            )
        )
    )

    report_path = REPORT_DIR / f"{event}_report.csv"

    report.to_csv(report_path, index=False)


def save_summary_report(all_analyses):

    summary_path = REPORT_DIR / "summary_report.txt"

    with open(summary_path, "w") as file:

        file.write("SPORTS PERFORMANCE STATISTICS EXPLORER\n")
        file.write("=" * 45 + "\n\n")

        for event, analysis in all_analyses.items():

            file.write(f"\nEVENT: {event.upper()}\n")
            file.write("-" * 35 + "\n")

            if analysis.empty:
                file.write("No records available.\n")
                continue

            winner = analysis.iloc[0]

            file.write(
                f"Top performer: {winner['athlete_id']}\n"
            )

            file.write(
                f"Average result: {winner['average']:.2f} "
                f"{winner['unit']}\n"
            )

            file.write(
                f"Best result: {winner['best_result']:.2f} "
                f"{winner['unit']}\n"
            )

            file.write(
                f"Consistency (standard deviation): "
                f"{winner['std_dev']:.3f}\n"
            )

            file.write(
                f"Improvement: {winner['improvement']:+.2f}\n"
            )


# ==============================
# MAIN EXECUTION
# ==============================

def main():

    print("=" * 55)
    print("SPORTS PERFORMANCE STATISTICS EXPLORER")
    print("=" * 55)

    athletes, sessions = load_data()

    errors, warnings = validate_data(athletes, sessions)

    # --------------------------
    # Validation
    # --------------------------

    print("\nDATA VALIDATION")
    print("-" * 30)

    if errors:
        print("\nErrors detected:")

        for error in errors:
            print(" [ERROR]", error)

    else:
        print("No structural or critical data errors detected.")

    if warnings:
        print("\nWarnings:")

        for warning in warnings:
            print(" [WARNING]", warning)

    print("\nValidation completed.")

    if errors:
        print("\nCritical validation errors exist.")
        print("Please correct the dataset before analysis.")
        return

    # --------------------------
    # Analysis
    # --------------------------

    all_analyses = {}

    print("\n\nPERFORMANCE ANALYSIS")
    print("=" * 55)

    for event in EVENT_LIMITS:

        analysis = analyze_event(sessions, event)

        all_analyses[event] = analysis

        display_rankings(athletes, event, analysis)

        generate_event_graphs(
            sessions, athletes, event, analysis
        )

        save_reports(athletes, event, analysis)

    # --------------------------
    # Save summary
    # --------------------------

    save_summary_report(all_analyses)

    print("\n" + "=" * 55)
    print("ANALYSIS COMPLETED SUCCESSFULLY")
    print("=" * 55)

    print(f"\nGraphs saved in: {PLOT_DIR}")
    print(f"Reports saved in: {REPORT_DIR}")

    print("\nGenerated files:")
    print("- Event performance trend graphs")
    print("- Event average ranking graphs")
    print("- Individual event CSV reports")
    print("- Summary text report")


if __name__ == "__main__":
    main()
