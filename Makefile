.PHONY: help install-dev test lint package deploy-terraform clean

help:
	@echo "Available commands:"
	@echo "  make install-dev    Install development dependencies"
	@echo "  make test           Run tests"
	@echo "  make lint           Run linting"
	@echo "  make package        Create Lambda deployment package"
	@echo "  make deploy-terraform  Deploy using Terraform"
	@echo "  make clean          Clean up build artifacts"

install-dev:
	pip install -r requirements-dev.txt

test:
	pytest src/test_lambda_function.py -v

lint:
	flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 src --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

package:
	cd src && zip -r ../function.zip lambda_function.py

deploy-terraform:
	cd terraform && terraform init && terraform apply

clean:
	rm -f function.zip
	rm -f terraform/function.zip
	find . -type d -name __pycache__ -exec rm -rf {} +