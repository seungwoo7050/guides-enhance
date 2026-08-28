CC ?= cc
CPPFLAGS ?= -D_POSIX_C_SOURCE=200809L -Iinclude
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -O2 -pthread
LDFLAGS ?= -pthread
AR ?= ar
ARFLAGS ?= rcs

BUILD_DIR := build
LIB := $(BUILD_DIR)/libaccount.a
OBJ := $(BUILD_DIR)/account.o
TEST_BIN := $(BUILD_DIR)/test-account
TSAN_DIR := build-tsan
TSAN_BIN := $(TSAN_DIR)/test-account

.PHONY: all test sanitize thread-sanitize clean fclean re

all: $(LIB)

$(BUILD_DIR):
	mkdir -p $@

$(OBJ): src/account.c include/account.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(LIB): $(OBJ)
	$(AR) $(ARFLAGS) $@ $^

$(TEST_BIN): tests/test_account.c $(LIB) include/account.h
	$(CC) $(CPPFLAGS) $(CFLAGS) tests/test_account.c $(LIB) $(LDFLAGS) -o $@

test: $(TEST_BIN)
	./$(TEST_BIN)

sanitize:
	$(MAKE) clean
	$(MAKE) CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -O1 -g -pthread -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='-pthread -fsanitize=address,undefined' test

thread-sanitize:
	rm -rf $(TSAN_DIR)
	mkdir -p $(TSAN_DIR)
	$(CC) $(CPPFLAGS) -std=c11 -Wall -Wextra -Wpedantic -Werror -O1 -g -pthread -fsanitize=thread src/account.c tests/test_account.c -fsanitize=thread -pthread -o $(TSAN_BIN)
	./$(TSAN_BIN)

clean:
	rm -rf $(BUILD_DIR) $(TSAN_DIR)

fclean: clean

re: fclean all
