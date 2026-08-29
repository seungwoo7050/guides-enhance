PYTHON ?= python3

.PHONY: install check migrations migrate test sample run deploy-check

install:
	$(PYTHON) -m pip install .

check:
	$(PYTHON) manage.py check

migrations:
	$(PYTHON) manage.py makemigrations --check

migrate:
	$(PYTHON) manage.py migrate

test:
	$(PYTHON) manage.py test

sample:
	$(PYTHON) manage.py loaddata catalog/sample_catalog

run:
	$(PYTHON) manage.py runserver

deploy-check:
	DJANGO_SETTINGS_MODULE=config.settings.production \
	DJANGO_SECRET_KEY='development-deploy-check-only-change-me-1234567890' \
	DJANGO_ALLOWED_HOSTS='example.com' \
	$(PYTHON) manage.py check --deploy
