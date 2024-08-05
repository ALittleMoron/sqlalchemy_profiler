NAME := sqlalchemy_profiler
PDM := $(shell command -v pdm 2> /dev/null)

.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo -e "Please, use \033[0;33m'make <target>'\033[0m where <target> is one the following commands:"
	@echo ""
	@echo -e "  \033[0;33minstall\033[0m         run installation for all dependencies"
	@echo -e "  \033[0;33mshell\033[0m           run ipython shell"
	@echo -e "  \033[0;33mclean\033[0m           run delete all not needed files"
	@echo -e "  \033[0;33mlint\033[0m            run project code checking without formatting"
	@echo -e "  \033[0;33mformat\033[0m          run project code formatting"
	@echo -e "  \033[0;33mtest\033[0m            run all tests"
	@echo -e "  \033[0;33mtest_docker\033[0m     run all tests in docker"

	@echo ""
	@echo -e "Check \033[0;33mMakefile\033[0m to get full context of commands."


.PHONY: install
install:
	@if [ -z $(PDM) ]; then echo "PDM could not be found."; exit 2; fi
	$(PDM) install -G:all --no-self


.PHONY: shell
shell:
	@if [ -z $(PDM) ]; then echo "Poetry could not be found. See https://python-poetry.org/docs/"; exit 2; fi
	$(ENV_VARS_PREFIX) $(PDM) run ipython --no-confirm-exit --no-banner --quick \
	--InteractiveShellApp.extensions="autoreload" \
	--InteractiveShellApp.exec_lines="%autoreload 2"

.PHONY: clean
clean:
	find . -type d -name "__pycache__" | xargs rm -rf {};

.PHONY: lint
lint:
	@if [ -z $(PDM) ]; then echo "Poetry could not be found. See https://python-poetry.org/docs/"; exit 2; fi
	$(PDM) run pyright $(NAME)
	$(PDM) run isort --settings-path ./pyproject.toml --check-only $(NAME)
	$(PDM) run black --config ./pyproject.toml --check $(NAME) --diff
	$(PDM) run ruff check $(NAME)
	$(PDM) run vulture $(NAME) --min-confidence 100 --exclude "migration_numbering.py"
	$(PDM) run bandit --configfile ./pyproject.toml -r ./$(NAME)

.PHONY: format
format:
	@if [ -z $(PDM) ]; then echo "Poetry could not be found. See https://python-poetry.org/docs/"; exit 2; fi
	$(PDM) run isort --settings-path ./pyproject.toml $(NAME)
	$(PDM) run black --config ./pyproject.toml $(NAME)

.PHONY: test
test:
	@if [ -z $(PDM) ]; then echo "Poetry could not be found. See https://python-poetry.org/docs/"; exit 2; fi
	$(PDM) run pytest ./tests --cov-report xml --cov-fail-under 95 --cov ./$(NAME) -vv


.PHONY: test_docker
test_docker:
	@if [ -z $(PDM) ]; then echo "Poetry could not be found. See https://python-poetry.org/docs/"; exit 2; fi
	$(ENV_VARS_PREFIX) docker-compose -f docker/docker-compose-test.yaml up --build
	$(ENV_VARS_PREFIX) docker-compose -f docker/docker-compose-test.yaml down