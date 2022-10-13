CC = gcc
CFLAGS := -Wall -fpic

MKDIR_P = mkdir -p
OUT_DIR = target

OBJS = $(OUT_DIR)/wrapper.o

SRCS = src/native/wrapper.c

TARGET = $(OUT_DIR)/libwrapper.a

wrapper: $(TARGET)

run:
	make
	cargo run

install:
	make
	cargo install --path .

$(TARGET): $(OBJS)
	rm -f $@
	ar rcs $@ $(OBJS)
	rm -f $(OBJS)

$(OBJS) : $(SRCS)
	$(MKDIR_P) $(OUT_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -rf $(OUT_DIR) $(OBJS)
	rm -rf $(CARGO_BUILD_DIR)
	cargo clean

.PHONY: clean all run

build-img: clean wrapper
	cargo install --path .
	docker build -t caribouf/helloworld-rust .
	docker push caribouf/helloworld-rust
