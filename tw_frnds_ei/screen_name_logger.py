class ScreenNameLogger:
    def __init__(self, logger, screen_name):
        self.logger = logger
        self.screen_name = screen_name
        self.msg_prefix = f"[{self.screen_name}] - "

    def debug(self, msg):
        self.logger.debug(f"{self.msg_prefix}{msg}")

    def info(self, msg):
        self.logger.info(f"{self.msg_prefix}{msg}")

    def warn(self, msg):
        self.logger.warning(f"{self.msg_prefix}{msg}")

    def error(self, msg):
        self.logger.error(f"{self.msg_prefix}{msg}")
