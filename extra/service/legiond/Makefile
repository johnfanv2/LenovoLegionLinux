CC ?= clang

CFLAGS ?= -O2
CFLAGS += -Wall -linih

TARGET1 = legiond
SOURCE1 = $(TARGET1).c modules/*.c
TARGET2 = legiond-ctl
SOURCE2 = $(TARGET2).c

all: $(TARGET1) $(TARGET2)

$(TARGET1): $(SOURCE1)
	$(CC) $(CFLAGS) -o $@ $^

$(TARGET2): $(SOURCE2)
	$(CC) $(CFLAGS) -o $@ $^

clean:
	rm -f $(TARGET1) $(TARGET2)
