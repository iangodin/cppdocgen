.PHONY: test smalltest

default: smalltest

test:
	rm -f cppinfo.db
	rm -rf site/global site/index.html
	./cppdoc --dir test -- test/test.cpp
	./gendoc

smalltest:
	rm -f cppinfo.db
	rm -rf site/global site/index.html
	./cppdoc --dir test -- test/small.cpp
	./gendoc
