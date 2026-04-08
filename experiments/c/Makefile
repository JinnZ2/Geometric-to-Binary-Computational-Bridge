# Makefile — Geometric NFS C acceleration library
# ================================================
# Build a shared library (.so / .dylib) that the Python ctypes
# wrapper can load at runtime.
#
# Usage:
#   make            # build libgeometric_nfs.so
#   make test       # build and run the smoke test
#   make clean      # remove build artifacts

CC       ?= gcc
CFLAGS   := -O3 -Wall -Wextra -std=gnu11 -fPIC
LDFLAGS  := -lm
UNAME_S  := $(shell uname -s)

# Shared library extension
ifeq ($(UNAME_S),Darwin)
  SHARED_EXT := dylib
  SHARED_FLAG := -dynamiclib
else
  SHARED_EXT := so
  SHARED_FLAG := -shared
endif

LIB_NAME := libgeometric_nfs.$(SHARED_EXT)

.PHONY: all clean test

all: $(LIB_NAME)

$(LIB_NAME): geometric_nfs_core.c geometric_nfs_core.h
	$(CC) $(CFLAGS) $(SHARED_FLAG) -o $@ geometric_nfs_core.c $(LDFLAGS)

# Static library (for embedding)
libgeometric_nfs.a: geometric_nfs_core.o
	ar rcs $@ $<

geometric_nfs_core.o: geometric_nfs_core.c geometric_nfs_core.h
	$(CC) $(CFLAGS) -c -o $@ geometric_nfs_core.c

# Smoke test: factor a small semiprime via the C library
test: $(LIB_NAME) test_nfs.c
	$(CC) $(CFLAGS) -o test_nfs test_nfs.c -L. -lgeometric_nfs $(LDFLAGS) \
		-Wl,-rpath,'$$ORIGIN'
	./test_nfs

clean:
	rm -f $(LIB_NAME) libgeometric_nfs.a geometric_nfs_core.o test_nfs
