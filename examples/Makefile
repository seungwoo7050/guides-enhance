SHELL := /bin/sh
CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -pedantic -O2
THREAD_FLAGS ?= -pthread
BUILD_DIR ?= build
PROGRAMS := syscall-boundary

.PHONY: all check clean
all: $(PROGRAMS:%=$(BUILD_DIR)/%)

$(BUILD_DIR):
	mkdir -p $@

$(BUILD_DIR)/syscall-boundary: syscall-boundary.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< -o $@

check: all

clean:
	rm -rf $(BUILD_DIR)
