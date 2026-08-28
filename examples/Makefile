SHELL := /bin/sh
CC ?= cc
PYTHON ?= python3
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -pedantic -O2
THREAD_FLAGS ?= -pthread
BUILD_DIR ?= build
PROGRAMS := syscall-boundary lost-update bounded-buffer dining-cycle cow-observer page-fault-observer
SANITIZER_FLAGS := -std=c11 -Wall -Wextra -Werror -pedantic -O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined

.PHONY: all check verify sanitizer-check clean

all: $(PROGRAMS:%=$(BUILD_DIR)/%)

$(BUILD_DIR):
	mkdir -p $@

$(BUILD_DIR)/syscall-boundary: syscall-boundary.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< -o $@

$(BUILD_DIR)/lost-update: lost-update.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(THREAD_FLAGS) $< -o $@

$(BUILD_DIR)/bounded-buffer: bounded-buffer.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(THREAD_FLAGS) $< -o $@

$(BUILD_DIR)/dining-cycle: dining-cycle.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(THREAD_FLAGS) $< -o $@

$(BUILD_DIR)/cow-observer: cow-observer.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< -o $@

$(BUILD_DIR)/page-fault-observer: page-fault-observer.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< -o $@

check: all

verify: all
	$(PYTHON) ../scripts/test-examples.py --build-dir $(BUILD_DIR)

sanitizer-check:
	$(MAKE) BUILD_DIR=build-sanitize CFLAGS='$(SANITIZER_FLAGS)' all
	ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
		$(PYTHON) ../scripts/test-examples.py --build-dir build-sanitize

clean:
	rm -rf build build-sanitize
