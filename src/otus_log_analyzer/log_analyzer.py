# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

import gzip
import re
import click
import yaml
import structlog
import json
import sys
import os
from datetime import datetime
from collections import namedtuple
from typing import Generator, Optional, Union, Any, Dict, List, TypedDict
from string import Template

Log = namedtuple("Log", ["path", "date", "extension"])


# Define TypedDict for report entries
class ReportEntry(TypedDict):
    count: int
    count_perc: float
    time_sum: float
    time_perc: float
    time_avg: float
    time_max: float
    time_med: float
    url: str


class ReportDict(TypedDict):
    count: int
    request_time: List[float]


default_config: Dict[str, Union[int, str]] = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
}


def find_latest_log(config: Dict[str, Any]) -> Optional[Log]:
    latest_date: str = ""
    latest_log: Optional[str] = None
    latest_extension: Optional[str] = None
    for log_name in os.listdir(config["LOG_DIR"]):
        if re.search(r"log-\d{8}(\.gz)?$", log_name):
            date = log_name.split("log-")[-1]
            if date.endswith(".gz"):
                date, extension = date.split(".")
            else:
                extension = "log"
            if latest_date is None or date > latest_date:
                latest_date = date
                latest_log = log_name
                latest_extension = extension
    if latest_log is not None:
        return Log(
            path=os.path.join(config["LOG_DIR"], latest_log),
            date=datetime.strptime(latest_date, "%Y%m%d"),
            extension=latest_extension,
        )
    return None


def parse_log(
    logger: structlog.BoundLogger, log: Log
) -> Generator[Dict[str, str], None, float]:
    open_func = gzip.open if log.extension == "gz" else open
    keys: List[str] = [
        "remote_addr",
        "remote_user",
        "http_x_real_ip",
        "time_local",
        "request",
        "status",
        "body_bytes_sent",
        "http_referer",
        "http_user_agent",
        "http_x_forwarded_for",
        "http_X_REQUEST_ID",
        "http_X_RB_USER",
        "request_time",
    ]

    n_errors: int = 0
    n_lines: int = 0
    try:
        with open_func(log.path, "rt") as f:
            for line in f:
                try:
                    fields = [
                        f for f in re.findall(r'\[([^]]*)\]|"([^"]*)"|(\S+)', line) if f
                    ]
                    fields = ["".join(group) for group in fields]
                    parsed_line: Dict[str, str] = {}
                    for i, key in enumerate(keys):
                        if fields[i] != "-":
                            parsed_line[key] = fields[i]
                    logger.info("Parsed line", line=parsed_line)
                    yield parsed_line
                except IndexError:
                    logger.error("Failed to parse line", line=line)
                    n_errors += 1
                n_lines += 1
    except FileNotFoundError as e:
        logger.error("File not found", file=log.path)
        raise e
    return float(n_errors) / max(1, float(n_lines))


def parse_request(request: Optional[str]) -> Optional[str]:
    if request is None:
        return None
    request_parts = request.split()
    for request_part in request_parts:
        request_part = request_part.strip()
        if request_part.startswith("/"):
            return request_part
    return None


def compute_report(
    config: Dict[str, Any],
    logger: structlog.BoundLogger,
    stream: Generator[Dict[str, str], None, float],
    log: Log,
) -> Optional[str]:
    report_path = os.path.join(
        config["REPORT_DIR"], f"report-{log.date.strftime('%Y.%m.%d')}.html"
    )
    if os.path.exists(report_path):
        return report_path

    overall_count: int = 0
    overall_time_sum = 0.0
    report: Dict[str, ReportDict] = {}

    try:
        for parsed_line in stream:
            url = parse_request(parsed_line.get("request"))  # type: ignore
            if url is not None:
                if url not in report:
                    report[url] = {"count": 0, "request_time": []}
                report[url]["count"] += 1
                request_time = float(parsed_line["request_time"])
                report[url]["request_time"].append(request_time)
                overall_count += 1
                overall_time_sum += request_time
    except StopIteration as e:
        error_ratio = float(e.value)
        if "ERROR_THRESHOLD" in config and error_ratio >= config["ERROR_THRESHOLD"]:
            logger.error("Error ratio is too high", error_ratio=error_ratio)
            return None

    final_report: List[ReportEntry] = []
    for url in report:
        times: List[float] = report[url]["request_time"]
        times.sort()

        time_sum = sum(times)
        count = report[url]["count"]

        final_report.append(
            {
                "url": url,
                "count": count,
                "count_perc": (count / overall_count * 100),
                "time_sum": time_sum,
                "time_perc": (time_sum / overall_time_sum * 100),
                "time_avg": time_sum / len(times),
                "time_max": times[-1],
                "time_med": (times[len(times) // 2 - 1] + times[len(times) // 2]) / 2
                if len(times) % 2 == 0
                else times[len(times) // 2],
            }
        )

    final_report.sort(key=lambda x: x["time_sum"], reverse=True)
    final_report = final_report[: config["REPORT_SIZE"]]
    template_path = config.get(
        "TEMPLATE_PATH", os.path.join(config["REPORT_DIR"], "report.html")
    )
    with open(report_path, "w") as f_report:
        with open(template_path, "r") as f_template:
            for line in f_template:
                f_report.write(
                    Template(line).safe_substitute(table_json=json.dumps(final_report))
                )
    return report_path


def log_analyzer(
    config: Dict[str, Any], logger: structlog.BoundLogger
) -> Optional[str]:
    log = find_latest_log(config)
    if log is not None:
        report_path = compute_report(config, logger, parse_log(logger, log), log)
        if report_path is not None:
            logger.info("Report computed", report=report_path)
            return report_path
    else:
        logger.info("No log file found")
        return config["LOG_DIR"]
    return None


@click.command()
@click.option(
    "--config", default="./tests/test_config.yaml", help="Path to config file"
)
def main(config: str) -> None:
    try:
        with open(config, "r") as f:
            new_config: Dict[str, Any] = yaml.safe_load(f)
        merged_config = {**default_config, **new_config}
        log_file = merged_config.get("LOG_FILE")
        if log_file is not None:
            log_file = open(log_file, "w")
        structlog.configure(
            processors=[structlog.processors.JSONRenderer()],
            logger_factory=structlog.WriteLoggerFactory(file=log_file),
        )
        logger = structlog.get_logger()
    except FileNotFoundError:
        sys.exit(1)

    try:
        log_analyzer(merged_config, logger)
    except BaseException as e:
        logger.error("Failed to compute report", error=str(e))
        sys.exit(1)
    return None


if __name__ == "__main__":
    main()
