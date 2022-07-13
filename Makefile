.PHONY: test smalltest

default: test

test:
	rm -f cppdoc.db
	rm -rf site/global site/index.html
	./cppdoc --dir test -- test/test.cpp
	./gendoc --site site

smalltest:
	rm -f cppdoc.db
	rm -rf site/global site/index.html
	./cppdoc --dir test -- test/small.cpp -Wdocumentation --std=c++17
	./gendoc

