-include .env

MONGODB_URI ?= mongodb://localhost:27017
MONGODB_DATABASE ?= movie_analytics
DATASET_DIR ?= dataset
ETL_BATCH_SIZE ?= 5000
USER_SEED ?= 2026
PERSON_NAME ?= Christopher Nolan
LIMIT ?= 10
MIN_RATINGS ?= 20
GENRE_NAME ?= Action

MONGODB_URL := $(MONGODB_URI)/$(MONGODB_DATABASE)
PYTHON := .venv/bin/python

export MONGODB_URI MONGODB_DATABASE DATASET_DIR ETL_BATCH_SIZE USER_SEED

.PHONY: help inspect setup import rebuild init query-1 query-2 query-3 query-4 query-5 query-6 query-test benchmark

help:
	@printf '%s\n' \
		'make init                         Setup, import, and rebuild derived data' \
		'make query-1                      Top Action movies' \
		'make query-2 PERSON_NAME="..."    Career of an actor or director' \
		'make query-3 LIMIT=10             Most active actors and directors' \
		'make query-4 MIN_RATINGS=20       Top genre by demographic' \
		'make query-5 GENRE_NAME="Action" Country and age report' \
		'make query-6                      Company investment analysis' \
		'make query-test                   Test query' \
		'make benchmark                    Benchmark all queries'

inspect:
	$(PYTHON) scripts/validation/inspect_dataset.py

setup:
	$(PYTHON) scripts/setup/setup_database.py

import:
	$(PYTHON) scripts/etl/import_data.py

rebuild:
	mongosh "$(MONGODB_URL)" scripts/aggregate/rebuild_derived.js

init: setup import rebuild

query-1:
	mongosh "$(MONGODB_URL)" scripts/queries/query_01_top_action_movies.mongodb.js

query-2:
	PERSON_NAME="$(PERSON_NAME)" mongosh "$(MONGODB_URL)" scripts/queries/query_02_person_career.mongodb.js

query-3:
	LIMIT="$(LIMIT)" mongosh "$(MONGODB_URL)" scripts/queries/query_03_most_active_people.mongodb.js

query-4:
	MIN_RATINGS="$(MIN_RATINGS)" mongosh "$(MONGODB_URL)" scripts/queries/query_04_top_genre_by_demographic.mongodb.js

query-5:
	GENRE_NAME="$(GENRE_NAME)" mongosh "$(MONGODB_URL)" scripts/queries/query_05_country_age_report.mongodb.js

query-6:
	mongosh "$(MONGODB_URL)" scripts/queries/query_06_company_investment.mongodb.js

query-test:
	mongosh "$(MONGODB_URL)" scripts/queries/query_test.mongodb.js

benchmark:
	mongosh "$(MONGODB_URL)" --quiet scripts/validation/benchmark_queries.js
