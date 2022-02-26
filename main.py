import os
import tkinter as tk
import logging
from connectors.binance_futures import BinanceFuturesClient
from interface.root_component import Root

public_api_key = os.environ.get("PUBLIC_API_KEY")
secret_api_key = os.environ.get("SECRET_API_KEY")

# creating an instance of the logging object
logger = logging.getLogger()
# This sets the minimum logging level that will show up in the terminal
# We will not see the debugging message since we are setting the minimum logging
# level to INFO
logger.setLevel(logging.DEBUG)
# For logging messages to show up in the python terminal we need to initialize a
# stream handler
stream_handler = logging.StreamHandler()
# now for this stream handler we need to provide a format for the message
# the message needs to display a time code the level of the message and the message itself
# so we need to create a formatter object
formatter = logging.Formatter('%(asctime)s %(levelname)s :: %(message)s')
# Here we are adding the formatter to the stream handler. So we take the stream_handler
# object and set the formatter to the formatter instance we created above
stream_handler.setFormatter(formatter)
# now we set the level for the stream handler itself
stream_handler.setLevel(logging.INFO)

# unlike the stream handler that its non persistent we are now going to add a file handler
# to log everything to a stand alone file
file_handler = logging.FileHandler('info.log')
# now we are going to perform some of the same steps for that we did for the stream_handler
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
# now we add the stream handler to the logging instance
logger.addHandler(stream_handler)

# Log messages to display
# logger.debug("This message is important only when debugging the program.")
# logger.info("This message just shows basic information.")
# logger.warning("This message is about something you should pay attention to.")
# logger.error("This messgae helps to debug an error that occurred in your program.")

if __name__ == '__main__':

    binance = BinanceFuturesClient(public_api_key, secret_api_key, True)

    # instantiate a tkinter (GUI) root window
    root = Root(binance)
    # the next line creates the mainloop which makes the window for the application available
    root.mainloop()