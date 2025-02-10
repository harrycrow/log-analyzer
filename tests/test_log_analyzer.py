from otus_log_analyzer.log_analyzer import log_analyzer  # type: ignore
import yaml
import structlog
import os


def test_log_analyzer():
    config = yaml.safe_load(open("./tests/test_config.yaml", mode="r"))
    log_file = config.get("LOG_FILE")
    if log_file is not None:
        log_file = open(log_file, "w")
    structlog.configure(
        processors=[structlog.processors.JSONRenderer()],
        logger_factory=structlog.WriteLoggerFactory(file=log_file),
    )
    logger = structlog.get_logger()
    report_path = log_analyzer(config=config, logger=logger)
    assert report_path is not None
    assert os.path.exists(report_path)
