testall: lint test

lint:
	flake8 .

test:
	python3 -m unittest discover

run:
	./test_demodhcpd.py

.PHONY: lint test testall run