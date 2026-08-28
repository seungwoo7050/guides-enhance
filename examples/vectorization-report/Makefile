SHELL := /bin/sh
CC ?= cc
CFLAGS ?= -O3 -std=c11 -Wall -Wextra -Werror -pedantic
TARGET := build/vector_sum

.PHONY: check report assembly clean

# [Implementation 5] 동일한 최적화 조건
# 실행·진단·어셈블리 생성에 같은 최적화 옵션을 사용합니다.
$(TARGET): vector_sum.c
	@mkdir -p build
	$(CC) $(CFLAGS) $< -lm -o $@

check: $(TARGET)
	@./$(TARGET)

report:
	@CC="$(CC)" ./report.sh

assembly:
	@mkdir -p build
	$(CC) $(CFLAGS) -S vector_sum.c -o build/vector_sum.s
	@printf '어셈블리 파일: build/vector_sum.s\n'

clean:
	@rm -rf build
