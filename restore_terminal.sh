#!/bin/sh

# Restore the cursor
sudo sh -c 'setterm -cursor on > /dev/tty1'
sudo sh -c 'setterm -default > /dev/tty1'
sudo sh -c 'setterm -blank poke > /dev/tty1'
sudo sh -c 'export PS1=$OLD_PS1'
