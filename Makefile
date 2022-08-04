setup:
	poetry2setup > setup.py

build: setup shiv

clean:
	rm setup.py

shiv:
	mkdir -p build
	shiv -c tor -o build/tor.pyz . --compressed
