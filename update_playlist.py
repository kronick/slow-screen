import urllib2
import sqlite3
import json
import os

import logging

# Set up logging
logfile = logging.FileHandler("update_playlist.log", "a", encoding = "UTF-8")
logformat = logging.Formatter(fmt = '%(asctime)s %(message)s',
                                      datefmt = '%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger()
logfile.setFormatter(logformat)
logger.addHandler(logfile)
logger.setLevel(logging.INFO)

db = sqlite3.connect('slow-screen.db')
c = db.cursor()

# Get stream URL
c.execute("SELECT value FROM config WHERE key='stream'")
stream_url = c.fetchone()[0]

# Get last update time
c.execute("SELECT value FROM config WHERE key='lastupdate'")
try:
    last_update = long(c.fetchone()[0])
except:
    last_update = 0

logging.info("Last update time: {0}".format(last_update))

try:
    stream = urllib2.urlopen(stream_url)
    response_string = stream.read()
    response = json.loads(response_string)
    logging.debug("Response API version: " + response["playlist"]["version"])

    timestamp = long(response["playlist"]["timestamp"])
    if timestamp > last_update:
        # Save this playlist to disk
        playlist_filename = 'playlist-%s.json' % timestamp
        local_playlist = open(playlist_filename, 'w')
        playlist_filename = os.path.realpath(playlist_filename)
        local_playlist.write(response_string)
        local_playlist.close()
       
        logging.info("Wrote new playlist to " + playlist_filename)
        
        # Update the configuration
        timestamp_string = str(timestamp)
        logging.debug(timestamp_string)
        c.execute("UPDATE config SET value=? WHERE key='lastupdate'" , (timestamp_string, ))
        c.execute("UPDATE config SET value=? WHERE key='nextplaylist'", (playlist_filename, ))

        # Video files are actually downloaded by download_manager.py
        # When all videos are downloaded, playlist is set to nextplaylist

    else:
        logging.info("No new playlist from stream.")

except urllib2.HTTPError as e:
    logging.error("Could not open stream URL ({0})".format(e))
except ValueError as e:
    logging.error("Badly formed response: ")
    logging.error(e)

db.commit()
db.close()
