.PHONY: test smalltest

default: test

test:
	rm -f cppinfo.db
	rm -rf site/global site/index.html
	./cppdoc --dir test -- test/test.cpp
	./gendoc

smalltest:
	rm -f cppinfo.db
	rm -rf site/global site/index.html
	./cppdoc --dir test -- -Wdocumentation --std=c++11 test/small.cpp
	./gendoc
