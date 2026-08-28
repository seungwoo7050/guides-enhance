CC ?= cc
CPPFLAGS ?= -D_POSIX_C_SOURCE=200809L -Iinclude
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -O2
LDFLAGS ?=
AR ?= ar
ARFLAGS ?= rcs

BUILD_DIR := build
LIB := $(BUILD_DIR)/libcommand_pipeline.a
OBJ := $(BUILD_DIR)/command_pipeline.o
TEST_BIN := $(BUILD_DIR)/test-command-pipeline
HELPERS := \
	$(BUILD_DIR)/emit-bytes \
	$(BUILD_DIR)/expect-bytes \
	$(BUILD_DIR)/exit-with \
	$(BUILD_DIR)/terminate-with

.PHONY: all test sanitize clean fclean re

all: $(LIB)

$(BUILD_DIR):
	mkdir -p $@

$(OBJ): src/command_pipeline.c include/command_pipeline.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(LIB): $(OBJ)
	$(AR) $(ARFLAGS) $@ $^

$(TEST_BIN): tests/test_command_pipeline.c $(LIB) include/command_pipeline.h
	$(CC) $(CPPFLAGS) $(CFLAGS) tests/test_command_pipeline.c $(LIB) $(LDFLAGS) -o $@

$(BUILD_DIR)/emit-bytes: tests/helpers/emit_bytes.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(LDFLAGS) -o $@

$(BUILD_DIR)/expect-bytes: tests/helpers/expect_bytes.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(LDFLAGS) -o $@

$(BUILD_DIR)/exit-with: tests/helpers/exit_with.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(LDFLAGS) -o $@

$(BUILD_DIR)/terminate-with: tests/helpers/terminate_with.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(LDFLAGS) -o $@

test: $(TEST_BIN) $(HELPERS)
	./$(TEST_BIN) ./$(BUILD_DIR)/emit-bytes ./$(BUILD_DIR)/expect-bytes ./$(BUILD_DIR)/exit-with ./$(BUILD_DIR)/terminate-with

sanitize:
	$(MAKE) clean
	$(MAKE) CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='-fsanitize=address,undefined' test

clean:
	rm -rf $(BUILD_DIR)

fclean: clean

re: fclean all
