import json
import sqlite3
import os
import subprocess
import pipes

import logging


# Set up logging
logfile = logging.FileHandler("download_manager.log", "a", encoding = "UTF-8")
logformat = logging.Formatter(fmt = '%(asctime)s %(message)s',
                                      datefmt = '%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger()
logfile.setFormatter(logformat)
logger.addHandler(logfile)
logger.setLevel(logging.INFO)

# Open up the nextplaylist from the config database

db = sqlite3.connect('slow-screen.db')
c = db.cursor()
c.execute("SELECT value FROM config WHERE key='nextplaylist'")
next_playlist = c.fetchone()[0]

c.execute("SELECT value FROM config WHERE key='playlist'")
current_playlist = c.fetchone()[0]

if next_playlist == current_playlist:
    logging.debug("No playlist in waiting...")
    exit()

# Get video directory
c.execute("SELECT value FROM config WHERE key='videodirectory'")
video_directory = c.fetchone()[0]


def getFileStatus(f):
    '''
    Returns status of file download.
    Possible values are:
      "complete" - filesize and md5 hash of local file match playlist entry
      "downloading" - curl is currently retrieving this file
      "incomplete" - filesize is less than playlist entry. Need to start curl
      "bad" - filesize >= playlist entry but md5 doesn't match
    '''

    logging.info("Checking file '{0}...'".format(f["name"]))

    # First check if curl is already running for this file
    returncode = subprocess.call(['pgrep', '-f', 'curl .*{0}'.format(f["URL"])])
    if returncode == 0:
        logging.debug("File '{0}' is currently downloading with curl.".format(f["URL"]))
        return "downloading"

    path_to_file = video_directory + os.sep + f["name"]

    # If curl isn't running, check to see if filesize matches
    try:
        local_filesize = os.path.getsize(path_to_file)
    except OSError:
        logging.debug("File does not exist yet.")
        local_filesize = 0

    try: actual_filesize = long(f["size"])
    except: return "bad" # can't check if filesize isn't a number
    
    if local_filesize < actual_filesize:
        logging.debug("File is not done downloading. Need to start curl.")
        return "incomplete"

    if local_filesize > actual_filesize:
        logging.info("File is too large. There must be an error.")
        return "bad"

    # Filesize matches, check md5sum
    returncode = subprocess.call( \
        'echo "{0}  {1}" | md5sum -c --status -'.format( \
            pipes.quote(f["md5"]), pipes.quote(path_to_file)), shell=True)
    # 0 if success, 1 if failure
    if returncode == 0:
        logging.debug("Filesize and MD5 match! Download is complete.")
        return "complete"
    else:
        logging.info("Filesize is correct but MD5 is incorrect. Uh-oh!")
        return "bad"


# Process json in playlist

logging.debug("Opening playlist...")
with open(next_playlist) as f:
    json_contents = json.load(f)
    files = json_contents["playlist"]["files"]

    complete_count = 0

    for video in files:
        status = getFileStatus(video)
        logging.info("Status is: " + status)
        if status == "complete" or status == "bad": # Bad files are just ignored
            complete_count += 1
        elif status == "incomplete":
            # Start curl for this file
            logging.info("Starting download with curl...")
            path_to_file = video_directory + os.sep + video["name"]
            with open(os.devnull, 'w') as silence:
                subprocess.Popen(["curl", "-C", "-", "-o",
                                  path_to_file, video["URL"]],
                                 stdout=silence, stderr=silence)

        logging.info("")

    logging.info("{0}/{1} file downloads are complete.".format(complete_count, 
                                                               len(files)))
    if len(files) > 0 and complete_count == len(files):
        # Move nextplaylist -> playlist when all files are complete
        logging.info("Downloads complete. Updating current playlist...")
        c.execute("UPDATE config SET value=? WHERE key='playlist'", (next_playlist, ))
    else:
        logging.info("Downloads still in progress...")

db.commit()
db.close()

# (OPTIONAL) delete all files not in playlist or nextplaylist

# Find all files that are not at the proper file size
# Check to see if they are already wget-ing. Start (with -c) if not.

# If all files seem to be downloaded, compare md5sums to make sure
# If that check succeeds, move nextplaylist to playlist
