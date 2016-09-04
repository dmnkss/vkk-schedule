import threading
from parse import *
from bot import *
import logging

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    a = MainParser()
    b = BotThread()

    p1 = threading.Thread(target=a)
    p2 = threading.Thread(target=b)
    p1.start()
    p2.start()

    p1.join()
    p2.join() 