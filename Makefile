##########################################################################
#  CONFIGURATION

# Path to python binary
PYTHON ?= $(shell which python3)

COMMIT ?= $(shell git rev-parse HEAD)

PWD = $(shell pwd)

# Path to virtual environment(s)
VIRTUAL_ENV ?= .venv
NODE_ENV ?= .nodeenv

TP_SRC_PATH ?= typed_python

TP_BUILD_PATH ?= build/temp.linux-x86_64-3.6/typed_python
TP_LIB_PATH ?= build/lib.linux-x86_64-3.6/typed_python

CPP_FLAGS = -std=c++14  -O2  -Wall  -pthread  -DNDEBUG  -g  -fwrapv         \
            -fstack-protector-strong  -D_FORTIFY_SOURCE=2  -fPIC            \
            -Wno-terminate -Wno-bool-compare \
            -Wno-cpp \
            -Wformat  -Werror=format-security  -Wdate-time -Wno-reorder     \
            -Wno-sign-compare  -Wno-narrowing  -Wno-int-in-bool-context     \
            -I$(VIRTUAL_ENV)/include/python3.6m                             \
            -I$(VIRTUAL_ENV)/lib/python3.6/site-packages/numpy/core/include \
            -I/usr/include/python3.6m                                       \
            -I/usr/local/lib/python3.6/dist-packages/numpy/core/include

LINKER_FLAGS = -Wl,-O1 \
               -Wl,-Bsymbolic-functions \
               -Wl,-z,relro

SHAREDLIB_FLAGS = -pthread -shared -g -fstack-protector-strong \
                  -Wformat -Werror=format-security -Wdate-time \
                  -D_FORTIFY_SOURCE=2

UNICODEPROPS = $(TP_SRC_PATH)/UnicodeProps.hpp
TP_O_FILES = $(TP_BUILD_PATH)/all.o
DT_SRC_PATH = $(TP_SRC_PATH)/direct_types
TESTTYPES = $(DT_SRC_PATH)/GeneratedTypes1.hpp
TESTTYPES2 = $(DT_SRC_PATH)/ClientToServer0.hpp

##########################################################################
#  MAIN RULES
.PHONY: install
install: install-dependencies install-pre-commit


.PHONY: install-dependencies
install-dependencies: $(VIRTUAL_ENV)
	. $(VIRTUAL_ENV)/bin/activate; \
		pip install pipenv==2018.11.26; \
		pipenv install --dev --deploy;


.PHONY: install-pre-commit
install-pre-commit:install-dependencies
	. $(VIRTUAL_ENV)/bin/activate; \
		pre-commit install


.PHONY: test
test: js-test
	. $(VIRTUAL_ENV)/bin/activate; pytest

.PHONY: lint
lint:
	flake8 --show-source

.PHONY: vlint
vlint: $(VIRTUAL_ENV)
	. $(VIRTUAL_ENV)/bin/activate; \
		make lint

.PHONY: lib
lib: typed_python/_types.cpython-36m-x86_64-linux-gnu.so

.PHONY: unicodeprops
unicodeprops: ./unicodeprops.py
	$(PYTHON) ./unicodeprops.py > $(UNICODEPROPS)

.PHONY: generatetesttypes
generatetesttypes: $(DT_SRC_PATH)/generate_types.py
	. $(VIRTUAL_ENV)/bin/activate; \
	python3 $(DT_SRC_PATH)/generate_types.py --testTypes3 $(TESTTYPES)
	. $(VIRTUAL_ENV)/bin/activate; \
	python3 $(DT_SRC_PATH)/generate_types.py --testTypes2 $(TESTTYPES2)

.PHONY: clean
clean:
	rm -rf build/
	rm -rf typed_python.egg-info/
	rm -f nose.*.log
	rm -f typed_python/_types.cpython-*.so
	rm -rf $(VIRTUAL_ENV) .env
	rm -f .coverage*
	rm -f dist/


##########################################################################
#  HELPER RULES

.env:
	echo "NOTICE: File Auto-generated by Makefile" > $@
	echo "export COVERAGE_PROCESS_START=$(PWD)/tox.ini" >> $@
	echo "export PYTHONPATH=$(PWD)" >> $@

$(VIRTUAL_ENV): $(PYTHON) .env
	virtualenv $(VIRTUAL_ENV) --python=$(PYTHON)

$(TP_BUILD_PATH)/all.o: $(TP_SRC_PATH)/*.hpp $(TP_SRC_PATH)/*.cpp
	$(CC) $(CPP_FLAGS) -c $(TP_SRC_PATH)/all.cpp $ -o $@

typed_python/_types.cpython-36m-x86_64-linux-gnu.so: $(TP_LIB_PATH)/_types.cpython-36m-x86_64-linux-gnu.so
	cp $(TP_LIB_PATH)/_types.cpython-36m-x86_64-linux-gnu.so  typed_python

$(TP_LIB_PATH)/_types.cpython-36m-x86_64-linux-gnu.so: $(TP_LIB_PATH) $(TP_BUILD_PATH) $(TP_O_FILES)
	$(CXX) $(SHAREDLIB_FLAGS) $(LINKER_FLAGS) \
		$(TP_O_FILES) \
		-o $(TP_LIB_PATH)/_types.cpython-36m-x86_64-linux-gnu.so

$(TP_BUILD_PATH):
	mkdir -p $(TP_BUILD_PATH)

$(TP_LIB_PATH):
	mkdir -p $(TP_LIB_PATH)

.PHONY: testpypi-upload
testpypi-upload: $(VIRTUAL_ENV)
	. $(VIRTUAL_ENV)/bin/activate; \
	rm -rf dist
	python setup.py sdist
	twine upload --repository-url https://test.pypi.org/legacy/  dist/*

.PHONY: pypi-upload
pypi-upload: $(VIRTUAL_ENV)
	. $(VIRTUAL_ENV)/bin/activate; \
	rm -rf dist
	python setup.py sdist
	twine upload dist/*
