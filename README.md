# Sports Performance Statistics Explorer

A Python-based sports analytics project that analyzes athlete performance across multiple training sessions.

## Features

- CSV data loading
- Data validation
- Detection of suspicious performance records
- Athlete rankings
- Average, best and worst performance calculations
- Standard deviation and consistency analysis
- Performance improvement tracking
- Event-wise statistical analysis
- Report generation
- Graph generation

## Events

- 100m Sprint
- 400m Sprint
- 1500m Run
- Long Jump

## Ranking Logic

For running events, lower times are better.

For long jump, greater distances are better.

## Statistical Analysis

The program calculates:

- Average performance
- Best performance
- Worst performance
- Standard deviation
- Athlete consistency
- Performance improvement

## Data Validation

Suspicious and invalid performance records are detected and excluded from calculations to prevent inaccurate analysis.

## Technologies

- Python
- CSV
- Matplotlib
- Statistics
- Data analysis
- Data visualization

## Installation

Clone the repository:

    git clone YOUR_REPOSITORY_URL

Navigate into the project:

    cd Sports-Performance-Statistics-Explorer

Create a virtual environment:

    python3 -m venv .venv

Activate it:

    source .venv/bin/activate

Install dependencies:

    pip install -r requirements.txt

## Execution

Run the application:

    python main.py

## Output

Reports are generated in:

    output/reports/

Graphs are generated in:

    output/plots/

## Purpose

This project demonstrates the application of Python programming and statistical analysis to sports data, helping compare athlete performance, identify consistency, rank participants, and track improvement.

## Disclaimer

This project is intended for educational purposes and is based on the provided dataset.
