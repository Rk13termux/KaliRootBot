VENV := venv
PY := $(VENV)/bin/python

.PHONY: setup start check run

setup:
	chmod +x dev_setup.sh || true
	./dev_setup.sh

start:
	@echo "Starting server using venv python. If the venv isn't present run 'make setup' first."
	@echo "To run on custom port: PORT=8001 make start"
	$(PY) main.py

check:
	$(PY) check_deps.py

run:
	@echo "Activate venv then run: python main.py"
	@echo "Example: source venv/bin/activate && python main.py"

poll:
	$(PY) run_polling.py
