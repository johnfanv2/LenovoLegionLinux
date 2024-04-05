#!/bin/bash
case $1/$2 in
post/*)
       /usr/bin/legiond-ctl fanset 3
       ;;
esac
