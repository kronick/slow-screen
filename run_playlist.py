import urllib2, json
import sqlite3
import os, sys
import subprocess
from subprocess import Popen, PIPE
import time

import logging

from UserDict import UserDict

logfile = logging.FileHandler("run_playlist.log", "a", encoding = "UTF-8")
logformat = logging.Formatter(fmt = '%(asctime)s %(message)s',
                              datefmt = '%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger()
logfile.setFormatter(logformat)
logger.addHandler(logfile)
logger.setLevel(logging.INFO)

# Route stdout to a file
#reload(sys).setdefaultencoding('utf8')
#logfile = open("run_playlist.log", 'a')
#sys.stdout = logfile
#sys.stderr = logfile

class Playlist(UserDict):
    "Stores a list of files and provides methods to play them back in sequence"
    def __init__(self, file=None):
        UserDict.__init__(self)
        self["config"] = updateConfig()

        self["filename"] = file
        self["files"] = []
        self.loadFileList()             # Populate file list
        
        self["stillvalid"] = True       # Set to false to stop

        self["current_index"] = 0

    def loadFileList(self, filename=None):
        if filename is not None:        # Load new playlist file
            self["filename"] = filename

        # Process json in playlist
        with open(self["filename"]) as f:
            json_contents = json.load(f)
            self["files"] = json_contents["playlist"]["files"]

        if len(self["files"]) == 0:
            logging.warning("No video files specified in playlist.")
        else: self.__getFileData()
        
    def __getFileData(self):
        '''Get additional info about files'''
        for f in self["files"]:
            # Make sure file exists
            path_to_file = self["config"]["video_directory"] + \
                           os.sep + f["name"]
            f["path"] = path_to_file
            f["exists"] = os.path.isfile(path_to_file)

            logging.info("%s  %s" % (u'\u25A7' if f["exists"] else u'\u25A2',
                               path_to_file))

            try: f["loop"] = int(f["loop"])
            except: f["loop"] = 1

            # Calculate lengths of files that will loop more than once
            if f["exists"] and f["loop"] > 1:
                logging.debug("Calculating length of looping file '%s'..." % f["URL"])
                try:
                    length = subprocess.check_output(["./get_duration.sh",
                                                      path_to_file])
                    f["duration"] = int(length)
                    logging.debug(f["duration"])
                except (subprocess.CalledProcessError, ValueError) as e:
                    logging.error(e)
                    logging.error(length)
                    f["exists"] = False
                    f["duration"] = 0

    def __playFile(self, index):
        ''' Plays a file at specified index. Blocks until complete.'''
        try:
            f = self["files"][index]
            if not f["exists"]:
                logging.warning("Skipping %s because it can't be found..." % f["path"])
                return

            logging.info("Playing file '%s' (Loops %i times)" %  \
                    (f["path"], f["loop"]))
            if f["loop"] > 1:
                # Looping case. Run omxplayer and sleep for
                # n_loops * duration before killing process
                proc = Popen(["./play_file.sh", "-s", "--loop", f["path"]],
                             stdin  = subprocess.PIPE,
                             stdout = subprocess.PIPE
                             #stdout = open("/dev/null", 'w')) # mute output
                             )

                started = False
                finished = False
                start_time = 0
                runtime = f["loop"] * f["duration"]
                logging.info("Total runtime is %d ms" % runtime)

                while not finished:
                    if proc.poll() is not None:
                        finished = True
                        logging.warning("Looping file closed on its own!??")
                    elif not started:
                        # Wait for the file to start
                        logging.debug("Waiting for file to start...")
                        i = 0
                        while "\rV" not in proc.stdout.read(10) and \
                                i < 2000:
                            time.sleep(0.001)
                            i = i+1

                        logging.debug("File started.")
                        proc.stdout.close() # don't need output anymore

                        started = True
                        start_time = time.time() * 1000
                    elif (time.time() * 1000) - start_time > runtime:
                        proc.stdin.write('q') # Quit player
                        logging.debug("Looping file complete.")
                        finished = True
                    else:
                        #print "%d / %i\r" % ((time.time()*1000) - start_time, int(runtime)),
                        time.sleep(0.001) # Just wait until player is done

            else:
                # Single play case. Run omxplayer and wait until it
                # finishes as indicated by p.poll() is not None
                
                proc = Popen(["./play_file.sh", f["path"]],
                             stdin  = subprocess.PIPE,
                             stdout = open("/dev/null", 'w'))

                while proc.poll() is None:
                    time.sleep(0.01)

        except IndexError:
            logging.error("Tried playing file out of bounds!")
            return -1

    def play(self):
        ''' Start playing the playlist. '''
        if len(self["files"]) <= 0: return False

        # First kill any instances of omxplayer.bin that might linger
        subprocess.call(["killall", "omxplayer.bin"])
        
        while True:
            self.__playFile(self["current_index"])
            
            # After each file, check to make sure this playlist is still valid
            config = updateConfig()
            if config["playlist_filename"] != self["filename"]:
                logging.info("A newer playlist is available. Loading now.")
                return True

            self["current_index"] += 1
            self["current_index"] %= len(self["files"])


    def stop(self):
        pass

def updateConfig():
    '''
    Update configuration from database. If playlist file has changed
    it will be reflected here.
    '''
    
    # Connect to database to get current state
    db = sqlite3.connect('slow-screen.db')
    c = db.cursor()

    # Load current playlist 
    c.execute("SELECT value FROM config WHERE key='playlist'")
    playlist_filename = c.fetchone()[0]

    c.execute("SELECT value FROM config WHERE key='videodirectory'")
    video_directory = c.fetchone()[0]

    db.commit()
    db.close()
    return {"playlist_filename" : playlist_filename,
            "video_directory"   : video_directory}


while True:
    # Automatically loop
    config = updateConfig()
    pl = Playlist(config["playlist_filename"])
    pl.play()
    
