CC ?= cc
CPPFLAGS ?= -Iinclude
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -O2
LDFLAGS ?=
AR ?= ar
ARFLAGS ?= rcs

BUILD_DIR := build
LIB := $(BUILD_DIR)/libint_vector.a
OBJ := $(BUILD_DIR)/int_vector.o
TEST_BIN := $(BUILD_DIR)/test-int-vector

.PHONY: all test sanitize clean fclean re

all: $(LIB)

$(BUILD_DIR):
	mkdir -p $@

$(OBJ): src/int_vector.c include/int_vector.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(LIB): $(OBJ)
	$(AR) $(ARFLAGS) $@ $^

$(TEST_BIN): tests/test_int_vector.c $(LIB) include/int_vector.h
	$(CC) $(CPPFLAGS) $(CFLAGS) tests/test_int_vector.c $(LIB) $(LDFLAGS) -o $@

test: $(TEST_BIN)
	./$(TEST_BIN)

sanitize:
	$(MAKE) clean
	$(MAKE) CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='-fsanitize=address,undefined' test

clean:
	rm -rf $(BUILD_DIR)

fclean: clean

re: fclean all
