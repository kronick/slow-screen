#!/bin/sh

# Returns duration from mediainfo in milliseconds
mediainfo --Inform="Video;%Duration%" $1

