CFLAGS ?= -Wall -O2

TARGET1 = legiond
SOURCE1 = $(TARGET1).c
TARGET2 = legiond-cli
SOURCE2 = $(TARGET2).c

all: $(TARGET1) $(TARGET2)

$(TARGET1): $(SOURCE1)
	$(CC) $(CFLAGS) -o $@ $^

$(TARGET2): $(SOURCE2)
	$(CC) $(CFLAGS) -o $@ $^

clean:
	rm -f $(TARGET1) $(TARGET2)
