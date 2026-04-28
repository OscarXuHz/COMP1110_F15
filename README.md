# COMP1110 Group Project | Interactive Visualization System

This repository provides a lightweight, Flask-based visualization interface for the Restaurant Queue Simulator project. It is designed to demonstrate the simulation logic through an intuitive web UI without modifying the core algorithmic files.

---

## Key Features

- **Non-Invasive Integration**: Fully compatible with the original `main.py`. The UI functions as a separate layer, allowing you to run simulations via a web interface while keeping the underlying logic intact.
- **Dynamic Environment Configuration**: 
    - Real-time adjustment of table layouts (seating capacity and quantities).
    - Quick presets for Small, Default, and Large restaurant configurations.
- **Flexible Data Input**:
    - **Manual Entry**: Configure detailed customer attributes including VIP status, table-sharing preferences, reservations, and no-show handling.
    - **Batch Import**: Support for dragging and dropping CSV files for large-scale stress testing.
- **Automated Test Cases**: Automatically detects and loads `request1.csv` through `request10.csv` from the project directory for one-click testing.
- **Comprehensive Analytics**: Built-in visualization dashboard for key metrics like average wait times, table utilization rates, and SLA (Service Level Agreement) compliance.

---

## Quick Start

### 1. Prerequisites
Ensure you have Python 3 installed. Install the required web dependencies via pip:
```bash
pip install flask flask-cors
```

### 2. Launching the System
Place `app.py` and `ui.html` in your project root directory (same folder as `main.py`). Run the following command:
```bash
python app.py
```

### 3. Accessing the UI
Open your web browser and navigate to:
`http://localhost:5000`

---

## System Modules

### Table & Request Management
* **Live Configuration**: Add or remove table types dynamically and instantly view the total restaurant capacity.
* **Request Queue**: Edit customer details inline, including arrival timestamps with second-level precision.

### Simulation Engine
* The UI triggers the core `simulate()` function in `main.py` via a backend API and retrieves the processed results for display.

### Results & Visualization
* **Statistics Summary**: High-level overview of peak queue length, groups served, and total simulation duration.
* **Visual Charts**: Distribution bar charts for wait times and donut charts for table occupancy rates.
* **Data Export**: Download the simulation results as a CSV report for further analysis.

---

## Technical Stack

* **Backend**: Python 3, Flask
* **Frontend**: HTML5, CSS3, JavaScript (Chart.js for data visualization)
* **Recommended Browsers**: Google Chrome, Microsoft Edge, or Safari

---

## Developer Notes

To ensure compatibility, maintain the standard interface functions within `main.py`. The UI layer communicates with the backend using JSON, making it easy to extend or adapt to different scheduling algorithms.

---

## File Format Reference

### Request files (`requests.csv`, `request1–10.csv`)
Plain CSV, **no header row**, 9 comma-separated columns:
```
index, people, arrival(YYYYMMDDHHMMSS), duration(min), share(0/1), miss(0/1), comeback(0/1), vip(0/1), reserved(0/1)
```

### Restaurant/table config files (`restaurant.csv`, `restaurant1–10.csv`)
Plain CSV, **no header row**, 2 columns:
```
count, capacity
```
Each row defines `count` tables each with `capacity` seats.

### Output reference files (`output1–10.csv`)
These are **plain-text simulation reports** (not CSV data), stored with a `.csv` extension for convenience. Each file contains 9 lines in the following fixed format:
```
Simulation Result:
------------------
Average Wait Time: X.X min
Max Wait Time: X min
Peak Queue Length: X
Groups Served: X
Table Utilization: X.X%
Service Level (seated within 10 min): X.X%
Total Time: X min
```
These files serve as the expected reference output for each paired test case and can be reproduced by running the CLI (option 3 → option 5).