JAVA ?= java
JAVAC ?= javac
JAVA_RELEASE ?= 17
BUILD_DIR := build
MAIN_CLASSES := $(BUILD_DIR)/classes
TEST_CLASSES := $(BUILD_DIR)/test-classes
MAIN_SOURCES := $(shell find src/main/java -name '*.java' -print)
TEST_SOURCES := $(shell find src/test/java -name '*.java' -print)
TEST_CLASS := dev.guides.distributed.boundary.ServiceBoundaryTest

.PHONY: all build test clean

all: test

build:
	mkdir -p $(MAIN_CLASSES)
	$(JAVAC) --release $(JAVA_RELEASE) -d $(MAIN_CLASSES) $(MAIN_SOURCES)

test: build
	mkdir -p $(TEST_CLASSES)
	$(JAVAC) --release $(JAVA_RELEASE) -cp $(MAIN_CLASSES) -d $(TEST_CLASSES) $(TEST_SOURCES)
	$(JAVA) -cp $(MAIN_CLASSES):$(TEST_CLASSES) $(TEST_CLASS)

clean:
	rm -rf $(BUILD_DIR)
