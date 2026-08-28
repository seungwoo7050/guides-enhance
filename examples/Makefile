SHELL := /bin/sh
CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -pedantic -O2
THREAD_FLAGS ?= -pthread
BUILD_DIR ?= build
PROGRAMS := syscall-boundary lost-update bounded-buffer

.PHONY: all check clean
all: $(PROGRAMS:%=$(BUILD_DIR)/%)

$(BUILD_DIR):
	mkdir -p $@

$(BUILD_DIR)/syscall-boundary: syscall-boundary.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< -o $@

$(BUILD_DIR)/lost-update: lost-update.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(THREAD_FLAGS) $< -o $@

$(BUILD_DIR)/bounded-buffer: bounded-buffer.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(THREAD_FLAGS) $< -o $@

check: all

clean:
	rm -rf $(BUILD_DIR)
