CXX := c++
CXXFLAGS := -std=c++98 -Wall -Wextra -Werror -pedantic -Iinclude
TARGET := command_service
SOURCES := \
	src/main.cpp \
	src/TextBuffer.cpp \
	src/RequestParser.cpp \
	src/Store.cpp \
	src/ResponseFormatter.cpp \
	src/Handler.cpp \
	src/Router.cpp
LIB_SOURCES := $(filter-out src/main.cpp,$(SOURCES))
UNIT_TARGET := tests/unit_tests

.PHONY: all test clean

all: $(TARGET)

$(TARGET): $(SOURCES)
	$(CXX) $(CXXFLAGS) $(SOURCES) -o $@

$(UNIT_TARGET): tests/unit_tests.cpp $(LIB_SOURCES)
	$(CXX) $(CXXFLAGS) tests/unit_tests.cpp $(LIB_SOURCES) -o $@

test: $(TARGET) $(UNIT_TARGET)
	./$(UNIT_TARGET)
	./tests/test_cli.sh ./$(TARGET)

clean:
	rm -f $(TARGET) $(UNIT_TARGET)
