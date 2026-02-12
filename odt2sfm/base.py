from datetime import datetime


def get_timestamp():
    return datetime.today().strftime("%Y-%m-%d")
