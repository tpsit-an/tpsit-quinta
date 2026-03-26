

import threading
from time import sleep

def thread_1():
    while True:
        print("Dentro il thread")
        sleep(1)

t1 = threading.Thread(target=thread_1)
t1.start()

while True:
    print("Dentro il main thread....")
    sleep(1)