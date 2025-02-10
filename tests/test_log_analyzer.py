from src.log_analyzer import main


def test_log_analyzer():
    main(config="./tests/test_config.yaml")
