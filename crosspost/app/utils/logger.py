from datetime import datetime


class Logger:
    @staticmethod
    def log(message: str, level: str = "INFO") -> dict:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
        }
        print(f"[{entry['timestamp']}] {level}: {message}", flush=True)
        return entry

    @staticmethod
    def info(message: str) -> dict:
        return Logger.log(message, "INFO")

    @staticmethod
    def success(message: str) -> dict:
        return Logger.log(message, "SUCCESS")

    @staticmethod
    def warning(message: str) -> dict:
        return Logger.log(message, "WARNING")

    @staticmethod
    def error(message: str) -> dict:
        return Logger.log(message, "ERROR")
