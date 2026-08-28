CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic
CPPFLAGS := -Iinclude

.PHONY: all test clean
all: demo

demo: examples/demo.cpp include/MiniVector.hpp
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) $< -o $@

tests/mini_vector_tests: tests/mini_vector_tests.cpp tests/ThrowOnCopy.hpp include/MiniVector.hpp
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) $< -o $@

test: tests/mini_vector_tests
	./tests/mini_vector_tests

clean:
	rm -f demo tests/mini_vector_tests
