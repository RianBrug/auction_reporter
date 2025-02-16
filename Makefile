.PHONY: install run docker-run

install:
	python3.11 -m venv auctions_venv
	. auctions_venv/bin/activate && pip install -r requirements.txt

uninstall:
	source auctions_venv/bin/deactivate
	rm -rf auctions_venv

run:
	python src/local.py

docker-run:
	docker-compose up --build

docker-stop:
	docker-compose down
