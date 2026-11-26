# make: builds every C search tool (live*, ls*, mincirc, allmin, pm/lsdnf) next to its source.
CFLAGS ?= -O3 -march=native -fopenmp -pthread
LDLIBS = -lm
BINS = $(patsubst %.c,%,$(wildcard *.c pm/*.c))
all: $(BINS)
clean: ; rm -f $(BINS)
