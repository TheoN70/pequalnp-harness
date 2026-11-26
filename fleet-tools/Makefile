# make: builds every C search tool (live*, ls*, mincirc, allmin, pm/lsdnf) next to its source.
# make cirbo: installs Cirbo (exact circuit synthesis by SAT, SPbSAT/cirbo, MIT) pinned to CIRBO_REV, in CIRBO_DIR
#   (default $PENP/work/tools: cirbo-src + cirbo-venv). Its wheel does not build, so the venv reads the source
#   through a .pth file; the C extensions (abc, mockturtle) are not needed for CircuitFinderSat. Needs network once.
CFLAGS ?= -O3 -march=native -fopenmp -pthread
LDLIBS = -lm
BINS = $(patsubst %.c,%,$(wildcard *.c pm/*.c))
CIRBO_REV = ca19a9f29691459563a8a0a90d8f5b6cdc4e5006
CIRBO_DIR ?= $(abspath $(CURDIR)/../../work/tools)
all: $(BINS)

# make test: the self-checks (--demo) of the Python tools and slots; circsat/promise_batch need sat-venv
test: bfcirc
	python3 -I circuit2lean.py --demo
	sat-venv/bin/python -I circsat.py --demo
	sat-venv/bin/python -I promise_batch.py --demo
	./slots --demo
	python3 -I cube.py --demo
	./bfcirc 3 3 0xe8 | grep -q NONE && ./bfcirc 3 4 0xe8 | grep -q FOUND && ./bfcirc --two-lit 5 203 6 | grep -q NONE && ./bfcirc --two-lit 5 203 7 | grep -q FOUND && echo "bfcirc ok"

cirbo: $(CIRBO_DIR)/cirbo-venv/.ok-$(CIRBO_REV)
$(CIRBO_DIR)/cirbo-venv/.ok-$(CIRBO_REV): cirbo-requirements.txt cirbo_check.py
	mkdir -p $(CIRBO_DIR)
	test -d $(CIRBO_DIR)/cirbo-src || git clone -q https://github.com/SPbSAT/cirbo $(CIRBO_DIR)/cirbo-src
	git -C $(CIRBO_DIR)/cirbo-src checkout -q --detach $(CIRBO_REV) || { git -C $(CIRBO_DIR)/cirbo-src fetch -q origin && git -C $(CIRBO_DIR)/cirbo-src checkout -q --detach $(CIRBO_REV); }
	test -x $(CIRBO_DIR)/cirbo-venv/bin/python || python3 -m venv $(CIRBO_DIR)/cirbo-venv
	$(CIRBO_DIR)/cirbo-venv/bin/pip install -q -r cirbo-requirements.txt
	echo $(CIRBO_DIR)/cirbo-src > "$$($(CIRBO_DIR)/cirbo-venv/bin/python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')/cirbo-src.pth"
	$(CIRBO_DIR)/cirbo-venv/bin/python -I cirbo_check.py
	touch $@
.PHONY: test all clean cirbo
clean: ; rm -f $(BINS)
