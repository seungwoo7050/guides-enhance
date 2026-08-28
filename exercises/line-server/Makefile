CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic
CPPFLAGS := -Iinclude
SOURCES := src/main.cpp src/Poller_epoll.cpp src/Poller_kqueue.cpp

.PHONY: all test stress backpressure leak-check clean
all: line_server

line_server: $(SOURCES) include/Poller.hpp
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) $(SOURCES) -o $@

test: line_server
	python3 tests/test_server.py ./line_server

stress: line_server
	python3 tests/test_server.py ./line_server --stress

backpressure: line_server
	python3 tests/test_server.py ./line_server --backpressure

leak-check: line_server
	python3 tests/test_server.py ./line_server --leak-check

clean:
	rm -f line_server
