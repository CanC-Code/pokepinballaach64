.PHONY: all tools compare clean tidy

.SUFFIXES:
.SECONDEXPANSION:
.PRECIOUS:
.SECONDARY:

ROM := pokepinball.gbc
OBJS := main.o wram.o sram.o hram.o

ifeq (,$(shell which sha1sum))
SHA1 := shasum
else
SHA1 := sha1sum
endif

RGBDS ?=
RGBASM  ?= $(RGBDS)rgbasm
RGBLINK ?= $(RGBDS)rgblink
RGBFIX  ?= $(RGBDS)rgbfix
RGBGFX  ?= $(RGBDS)rgbgfx

RGBASMFLAGS  ?= -Weverything -Wtruncation=1
RGBLINKFLAGS ?= -Weverything -Wtruncation=1
RGBFIXFLAGS  ?= -Weverything
RGBGFXFLAGS  ?= 

all: $(ROM) compare

ifeq (,$(filter tools clean tidy,$(MAKECMDGOALS)))
Makefile: tools
endif

%.o: dep = $(shell tools/scan_includes $(@D)/$*.asm)
%.o: %.asm $$(dep)
	$(RGBASM) $(RGBASMFLAGS) -o $@ $<

$(ROM): RGBLINKFLAGS += -l contents/contents.link -n $(ROM:.gbc=.sym) -m $(ROM:.gbc=.map)
$(ROM): RGBFIXFLAGS += -jsvc -k 01 -l 0x33 -m 0x1e -p 0 -r 02 -t "POKEPINBALL" -i VPHE
$(ROM): $(OBJS) contents/contents.link
	$(RGBLINK) $(RGBLINKFLAGS) -o $@ $(OBJS)
	$(RGBFIX) $(RGBFIXFLAGS) $@

compare: $(ROM)
	@$(SHA1) -c rom.sha1

tools:
	$(MAKE) -C tools

tidy:
	rm -f $(ROM) $(OBJS) $(ROM:.gbc=.sym) $(ROM:.gbc=.map)
	$(MAKE) -C tools clean

clean: tidy
	find . \( -iname '*.1bpp' -o -iname '*.2bpp' -o -iname '*.pcm' \) -exec rm {} +

# Corrected Interleave Rule using temporary file staging
%.interleave.2bpp: %.interleave.png
	$(RGBGFX) -p -o temp_$@ $<
	tools/gfx --interleave --png $< -o temp_$@
	mv temp_$@ $@

%.2bpp: %.png
	$(RGBGFX) -p -o $@ $<

%.1bpp: %.png
	$(RGBGFX) -p -d1 -o $@ $<

%.pcm: %.wav
	tools/pcm -o $@ $<
