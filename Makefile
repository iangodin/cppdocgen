.PHONY: test smalltest cpp17

default: grim

test:
	rm -f cppdoc.db
	rm -rf site/global site/index.html
	./cppdoc --dir test -- test/test.cpp
	./gendoc --site site

grim:
	rm -f cppdoc.db
	rm -rf site/global site/index.html
	./cppdoc --dir ../grim/lib -- lib
	./gendoc

smalltest:
	rm -f cppdoc.db
	rm -rf site/global site/index.html
	./cppdoc --dir test -- test/small.cpp -Wdocumentation --std=c++17
	./gendoc

pds:
	rm -f cppdoc.db
	rm -rf site/global site/index.html
	./cppdoc --dir ../pds -- ../pds/doc.cpp -I cpp17 --std=c++17
	./gendoc

gui:
	rm -f cppdoc.db
	rm -rf site/global site/index.html
	./cppdoc --dir /mnt/c/Users/Ian/Projects/gui -- /mnt/c/Users/Ian/Projects/gui/doc.cpp -I /mnt/c/Users/Ian/Projects/gui -I/usr/include/SDL2 --std=c++17
	./gendoc
