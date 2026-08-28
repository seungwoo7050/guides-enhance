CC ?= cc
CPPFLAGS ?= -D_POSIX_C_SOURCE=200809L -Iinclude
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -O2
LDFLAGS ?=
AR ?= ar
ARFLAGS ?= rcs

BUILD_DIR := build
LIB := $(BUILD_DIR)/librecord_stream.a
OBJ := $(BUILD_DIR)/record_stream.o
TEST_BIN := $(BUILD_DIR)/test-record-stream

.PHONY: all test sanitize clean fclean re

all: $(LIB)

$(BUILD_DIR):
	mkdir -p $@

$(OBJ): src/record_stream.c include/record_stream.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(LIB): $(OBJ)
	$(AR) $(ARFLAGS) $@ $^

$(TEST_BIN): tests/test_record_stream.c $(LIB) include/record_stream.h
	$(CC) $(CPPFLAGS) $(CFLAGS) tests/test_record_stream.c $(LIB) $(LDFLAGS) -o $@

test: $(TEST_BIN)
	./$(TEST_BIN)

sanitize:
	$(MAKE) clean
	$(MAKE) CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='-fsanitize=address,undefined' test

clean:
	rm -rf $(BUILD_DIR)

fclean: clean

re: fclean all
