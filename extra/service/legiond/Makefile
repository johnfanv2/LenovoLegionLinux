CC = gcc

CFLAGS = -O2 -std=gnu2x -Wall -Wextra
LDLIBS = -linih

SRC = $(wildcard modules/*.c)
OBJ = $(SRC:.c=.o)

TARGET = legiond legiond-ctl
all: $(TARGET)

legiond: $(OBJ) legiond.o
	$(CC) $(CFLAGS) $(OBJ) legiond.o $(LDLIBS) -o legiond

legiond-ctl: legiond-ctl.o
	$(CC) $(CFLAGS) legiond-ctl.o $(LDLIBS) -o legiond-ctl

%.o : %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJ) $(TARGET) legiond.o legiond-ctl.o

.PHONY: all clean
