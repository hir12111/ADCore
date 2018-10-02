#Makefile at top of application tree
x := $(shell locate boost)
$(info $$x is [${x}])

TOP = .
include $(TOP)/configure/CONFIG
DIRS := $(DIRS) $(filter-out $(DIRS), configure)
DIRS := $(DIRS) $(filter-out $(DIRS), $(wildcard *App))
DIRS := $(DIRS) $(filter-out $(DIRS), $(wildcard *app))

include $(TOP)/configure/RULES_TOP
