setup:
	python tor/cli/poetry2setup.py > setup.py

build: setup shiv

clean:
	rm setup.py

shiv:
	mkdir -p build
	shiv -c tor -o build/tor.pyz . --compressed
