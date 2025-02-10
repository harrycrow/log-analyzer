# Log Analyzer

A Python script for analyzing nginx access logs and generating HTML reports with URL statistics.

## Features

- Parses nginx access logs (plain text or gzipped)
- Generates HTML reports with URL statistics including:
  - Request count and percentage
  - Total request time and percentage
  - Average, maximum and median request times
- Configurable via YAML config file
- Structured JSON logging
- (*) Docker support
- (*) Log analyzer check if report already exists and skip it

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/otus-log-analyzer.git
   cd otus-log-analyzer
   ```

2. Install package:
   ```bash
   make install
   ```

3. Run tests:
   ```bash
   make test
   ```

4. Run docker container:
   ```bash
   make docker-run
   ```

5. Clean docker container:
   ```bash
   make docker-clean
   ```

6. Clean all:
   ```bash
   make clean
   ```

7. Uninstall package:
   ```bash
   make uninstall
   ```

## Configuration

The script uses a YAML config file (`config.yaml`) to configure the log directory, log file pattern, and other parameters.
