SHELL:=/usr/bin/env bash -O globstar

# units
temp:
	mkdir temp

# ci / cd
install:
	poetry install

clean:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	rm -rf temp storage

clean-all: clean
	rm -rf .venv poetry.lock

black:
	 poetry run black ./src/

isort:
	poetry run isort ./src/

fix: isort black

fix-lint: fix lint

# scripts
scripts-create-big-file:
	PYTHONPATH=. poetry run python src/scripts/create_big_file.py

# testing
scripts-tc-disable:
	sudo tc qdisc del dev lo root netem

scripts-tc-10:
	sudo tc qdisc add dev lo root netem loss 10%

scripts-tc-15:
	sudo tc qdisc add dev lo root netem loss 15%

scripts-tc-20:
	sudo tc qdisc add dev lo root netem loss 20%

# start applications
start-app:
	PYTHONPATH=. poetry run python src/app/main.py

start-dhcp:
	PYTHONPATH=. poetry run python src/dhcp/main.py

start-dns:
	PYTHONPATH=. poetry run python src/dns/main.py

# testing
test-client-help:
	PYTHONPATH=. poetry run python src/client/main.py --help

test-client-upload:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/A.md

test-client-upload-100:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/100.txt

test-client-upload-1000:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/1K.txt

test-client-upload-10000:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/10K.txt

test-client-upload-child:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/B.txt --dest child-dir/B.txt

test-client-upload-child-100:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/100.txt --dest child-dir/100.txt

test-client-upload-child-1000:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/1K.txt --dest child-dir/1K.txt

test-client-upload-child-10000:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/10K.txt --dest child-dir/10K.txt

test-client-upload-multi:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/100.txt --dest a/100.txt
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/100.txt --dest b/100.txt
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/100.txt --dest a/c/100.txt
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/100.txt --dest b/c/100.txt

test-client-upload-range:
			PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/100.txt --dest b/c/100.txt
	for i in {1..10..2}; do \
		PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/100.txt --dest range/$$i-$$i/$$i.txt ;\
		for j in {1..10..1}; do \
			PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/100.txt --dest range/$$i-$$j.txt ;\
		done; \
	done;

test-client-upload-all:
	make test-client-upload
	make test-client-upload-child
	make test-client-upload-100
	make test-client-upload-child-100
	make test-client-upload-1000
	make test-client-upload-child-1000
	make test-client-upload-10000
	make test-client-upload-child-10000
	make test-client-upload-multi

test-client-upload-not-found:
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/other/100.txt --dest ../100.txt
	PYTHONPATH=. poetry run python src/client/main.py upload uploads/abdasda

test-client-download: temp
	PYTHONPATH=. poetry run python src/client/main.py download A.md ./temp/A.md

test-client-download-100: temp
	PYTHONPATH=. poetry run python src/client/main.py download 100.txt ./temp/100.txt

test-client-download-1000: temp
	PYTHONPATH=. poetry run python src/client/main.py download 1K.txt ./temp/1K.txt

test-client-download-10000: temp
	PYTHONPATH=. poetry run python src/client/main.py download 10K.txt ./temp/10K.txt

test-client-download-child: temp
	PYTHONPATH=. poetry run python src/client/main.py download child-dir/A.txt ./temp/child/A.txt

test-client-download-child-100: temp
	PYTHONPATH=. poetry run python src/client/main.py download child-dir/100.txt ./temp/child/100.txt

test-client-download-child-1000: temp
	PYTHONPATH=. poetry run python src/client/main.py download child-dir/1K.txt ./temp/child/1K.txt

test-client-download-child-10000: temp
	PYTHONPATH=. poetry run python src/client/main.py download child-dir/10K.txt ./temp/child/10K.txt

test-client-download-multi:
	PYTHONPATH=. poetry run python src/client/main.py download child-dir/100.txt ./temp/a/100.txt
	PYTHONPATH=. poetry run python src/client/main.py download child-dir/100.txt ./temp/b/100.txt
	PYTHONPATH=. poetry run python src/client/main.py download child-dir/100.txt ./temp/a/c/100.txt
	PYTHONPATH=. poetry run python src/client/main.py download child-dir/100.txt ./temp/b/c/100.txt

test-client-download-all:
	make test-client-download
	make test-client-download-child
	make test-client-download-100
	make test-client-download-child-100
	make test-client-download-1000
	make test-client-download-child-1000
	make test-client-download-10000
	make test-client-download-child-10000
	make test-client-download-multi

test-client-download-not-found:
	PYTHONPATH=. poetry run python src/client/main.py download ../.env ./temp/.enve
	PYTHONPATH=. poetry run python src/client/main.py download abdasda ./temp/abdasda

test-client-list:
	PYTHONPATH=. poetry run python src/client/main.py list

test-client-list-child:
	PYTHONPATH=. poetry run python src/client/main.py list child-dir

test-client-list-a:
	PYTHONPATH=. poetry run python src/client/main.py list a

test-client-list-b:
	PYTHONPATH=. poetry run python src/client/main.py list b

test-client-list-a-c:
	PYTHONPATH=. poetry run python src/client/main.py list a/c

test-client-list-range:
	PYTHONPATH=. poetry run python src/client/main.py list range

test-client-list-not-found:
	PYTHONPATH=. poetry run python src/client/main.py list ..
	PYTHONPATH=. poetry run python src/client/main.py list abdasda

test-client-not-found: test-client-upload-not-found test-client-download-not-found test-client-list-not-found
