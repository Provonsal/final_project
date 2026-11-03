from utils.config import DatabaseConfig


def check_db_config(): 
    configs = DatabaseConfig()
    try:
        for value in configs:
            assert value
    except AssertionError as e:
        e.add_note("Database config not setted up completely.")
        raise e
