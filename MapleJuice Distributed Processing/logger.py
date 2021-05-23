import os
import logging

class Logger:
    def __init__(self, name = '__name__', file_dir = 'log', file_name = 'logs.log'):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        if not os.path.exists(file_dir):
            os.mkdir(file_dir)

        file_handler = logging.FileHandler(os.path.join(file_dir, file_name))
        file_handler.setLevel(logging.DEBUG)
        f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(f_format)
        
        self.logger.addHandler(file_handler)