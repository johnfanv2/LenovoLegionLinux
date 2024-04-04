#!/bin/bash
case $1/$2 in
post/*)
      while true; do
        /usr/bin/legiond-ctl cpuset
        sleep 30
      done
      ;;
esac
