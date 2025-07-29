.DEFAULT_GOAL := help
.PHONY = help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'


changelog:  ## compile changelog
	git cliff --output CHANGELOG.md $(if $(bump),--tag $(bump))

deploy-docs:  ## build and publish documentation
	mkdocs gh-deploy

test-server:  ## start server for frontend testing
	yes | ckan -c test.ini db clean
	ckan -c test.ini db upgrade
	yes | ckan -ctest.ini sysadmin add admin password=password123 email=admin@test.net
	ckan -c test.ini run -t
