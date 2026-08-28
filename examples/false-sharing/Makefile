SHELL := /bin/sh
CC ?= cc
CFLAGS ?= -O2 -std=c11 -Wall -Wextra -Werror -pedantic
CPPFLAGS ?= -D_POSIX_C_SOURCE=200809L
TARGET := build/false_sharing

.PHONY: check benchmark clean

# [Implementation 5] 동일한 pthread 빌드 조건
# 검사와 측정 모두 같은 컴파일·링크 옵션을 사용합니다.
$(TARGET): false_sharing.c
	@mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) $< -pthread -o $@

check: $(TARGET)
	@./$(TARGET) 2 100000

benchmark: $(TARGET)
	@./$(TARGET) 2 10000000

clean:
	@rm -rf build
