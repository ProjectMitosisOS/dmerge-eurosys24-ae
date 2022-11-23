CC = gcc
CFLAGS := -Wall -fpic -shared
IMG_TAG = latest
MKDIR_P = mkdir -p
OUT_DIR = build

OBJS = $(OUT_DIR)/wrapper.so

SRCS = native/wrapper.cc

TARGET = $(OUT_DIR)/libwrapper.a

wrapper: $(TARGET)


$(TARGET): $(OBJS)
	rm -f $@
	ar rcs $@ $(OBJS)
	#rm -f $(OBJS)

$(OBJS) : $(SRCS)
	$(MKDIR_P) $(OUT_DIR)
	$(CC) $(CFLAGS) -fPIC $< -o $@

clean:
	rm -rf $(OUT_DIR) $(OBJS)
	rm -rf $(CARGO_BUILD_DIR)


sample:
	gcc -Wall -fpic -shared -fPIC native/wrapper.cc -o wrapper.so