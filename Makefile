include common.mk
NOTEBOOK_DIRS=$(wildcard notebooks/*)
NOTEBOOKS=$(NOTEBOOK_DIRS:%=%/notebook.ipynb)             # ipynb targets: "make notebooks/byod/notebook.ipynb"
PUBLISH=$(subst notebooks,publish,$(NOTEBOOK_DIRS))       # publish targets: "make publish/byod"
LINT=$(subst notebooks,lint,$(NOTEBOOK_DIRS))             # lint targts: "make lint/byod"
MYPY=$(subst notebooks,mypy,$(NOTEBOOK_DIRS))             # mypy targts: "make mypy/byod"
TESTS=$(subst notebooks,test,$(NOTEBOOK_DIRS))            # test targets: "make test/byod"
CICD_TESTS=$(subst notebooks,cicd_test,$(NOTEBOOK_DIRS))  # cicd_test targets: "make cicd_test/byod"

all: test

test: verify-gitlab-yml $(TESTS)

lint: $(LINT)

mypy: $(MYPY)

test-cicd: $(CICD_TESTS)

$(NOTEBOOK_DIRS): clean_notebooks
	$(MAKE) $(@:notebooks/%=test/%)

$(NOTEBOOKS):
	herzog $(@:%/notebook.ipynb=%/main.py) > $@

$(PUBLISH):
	$(MAKE) $(@:publish/%=notebooks/%/notebook.ipynb)
	scripts/publish.sh $(@:publish/%=notebooks/%/notebook.ipynb) $(@:publish/%=notebooks/%/publish.txt) 

$(TESTS):
	$(MAKE) $(@:test/%=lint/%)
	$(MAKE) $(@:test/%=mypy/%)
	scripts/run_leo_container.sh $(@:test/%=%)
	docker exec $(@:test/%=%) bash -c "$(LEO_PIP) install --upgrade -r $(LEO_REPO_DIR)/$(@:test/%=notebooks/%/requirements.txt)"
	docker exec $(@:test/%=%) $(LEO_PYTHON) $(LEO_REPO_DIR)/$(@:test/%=notebooks/%/main.py)
	$(MAKE) $(@:test/%=notebooks/%/notebook.ipynb)

$(CICD_TESTS):
	$(MAKE) $(@:cicd_test/%=lint/%)
	$(MAKE) $(@:cicd_test/%=mypy/%)
	${LEO_PIP} install --upgrade -r $(@:cicd_test/%=notebooks/%)/requirements.txt
	${LEO_PYTHON} $(@:cicd_test/%=notebooks/%)/main.py
	$(MAKE) $(@:cicd_test/%=notebooks/%/notebook.ipynb)

$(LINT):
	flake8 $(@:lint/%=notebooks/%)

$(MYPY):
	mypy --ignore-missing-imports --no-strict-optional $(@:mypy/%=notebooks/%)

.gitlab-ci.yml:
	scripts/generate_gitlab_yml.sh .gitlab-ci.yml

verify-gitlab-yml:
	scripts/generate_gitlab_yml.sh test_gitlab_yml
	diff .gitlab-ci.yml test_gitlab_yml

clean_notebooks:
	git clean -dfX notebooks

clean:
	git clean -dfx

.PHONY: .gitlab-ci.yml $(NOTEBOOK_DIRS) $(NOTEBOOKS) $(PUBLISH) $(TESTS) $(CICD_TESTS) clean clean_notebooks
