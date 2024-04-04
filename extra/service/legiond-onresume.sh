#!/bin/bash
case $1/$2 in
post/*)
       /usr/bin/legiond-cli fanset 3
       ;;
esac
