CC ?= cc
CPPFLAGS ?= -D_POSIX_C_SOURCE=200809L
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -O2
LDFLAGS ?=
PYTHON ?= python3

BUILD_DIR := build
BIN := $(BUILD_DIR)/command-runner
HELPERS := \
	$(BUILD_DIR)/print-args \
	$(BUILD_DIR)/emit-bytes \
	$(BUILD_DIR)/expect-bytes \
	$(BUILD_DIR)/exit-with \
	$(BUILD_DIR)/terminate-with \
	$(BUILD_DIR)/mark-file

.PHONY: all test sanitize clean fclean re

all: $(BIN)

$(BUILD_DIR):
	mkdir -p $@

$(BIN): src/command_runner.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(LDFLAGS) -o $@

$(BUILD_DIR)/print-args: tests/helpers/print_args.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(LDFLAGS) -o $@

$(BUILD_DIR)/emit-bytes: tests/helpers/emit_bytes.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(LDFLAGS) -o $@

$(BUILD_DIR)/expect-bytes: tests/helpers/expect_bytes.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(LDFLAGS) -o $@

$(BUILD_DIR)/exit-with: tests/helpers/exit_with.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(LDFLAGS) -o $@

$(BUILD_DIR)/terminate-with: tests/helpers/terminate_with.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(LDFLAGS) -o $@

$(BUILD_DIR)/mark-file: tests/helpers/mark_file.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(LDFLAGS) -o $@

test: $(BIN) $(HELPERS)
	$(PYTHON) tests/check.py ./$(BIN) ./$(BUILD_DIR)/print-args ./$(BUILD_DIR)/emit-bytes ./$(BUILD_DIR)/expect-bytes ./$(BUILD_DIR)/exit-with ./$(BUILD_DIR)/terminate-with ./$(BUILD_DIR)/mark-file

sanitize:
	$(MAKE) clean
	$(MAKE) CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='-fsanitize=address,undefined' test

clean:
	rm -rf $(BUILD_DIR)

fclean: clean

re: fclean all
