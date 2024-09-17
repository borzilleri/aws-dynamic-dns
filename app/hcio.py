import time
from enum import Enum
from urllib import request

__retries = 5
__action = Enum("Format", ["start", "fail", "log"])

def __uri(id: str, action: str | None) -> str:
    uri = f"https://hc-ping.com/{id}"
    if action:
        uri += f"/{action}"
    return uri

class HealthCheck:
    def __init__(self, id: str) -> None:
        self.id = id

    def __ping(self, action: str | None):
        success = False
        wait = 1
        i = 0
        while(not success and i < __retries):
            try:
                with request.urlopen(__uri(self.id, action), timeout=10) as r:
                    if r.status == 200:
                        success = True
            except Exception as e:
                print(f"Ping ({action or 'success'}) failed: {e}")
            time.sleep(wait)
            i += 1
            wait *= 2
            

    def success(self):
        self.__ping()

    def start(self):
        self.__ping(__action.start)

    def fail(self):
        self.__ping(__action.fail)

    def log(self):
        self.__ping(__action.log)