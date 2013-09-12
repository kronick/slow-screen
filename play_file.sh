#!/bin/sh

# Blank the screen. Have to run this as root. Use sudo to avoid 
#   running omxplayer as root.

sudo sh -c 'setterm -cursor off -clear > /dev/tty1'

# setterm -blank force

# Hide command line
#sudo sh -c 'export OLD_PS1=$PS1'
#sudo sh -c 'export PS1=""'

omxplayer "$@" # caller must silence output

sudo sh -c 'setterm -clear > /dev/tty1'
sudo setterm -clear
