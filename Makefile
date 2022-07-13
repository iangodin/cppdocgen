.PHONY: test smalltest

default: test smalltest

test:
	rm -f test.db
	rm -rf test-site
	./cppdoc --dir test --db test.db -- test/test.cpp
	./gendoc --db test.db --site test-site

smalltest:
	rm -f small.db
	rm -rf small-site
	./cppdoc --dir test --db small.db -- -Wdocumentation --std=c++11 test/small.cpp
	./gendoc --db small.db --site small-site
