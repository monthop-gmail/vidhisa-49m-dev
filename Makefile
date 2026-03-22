.PHONY: deploy-prod

deploy-prod:
	git pull
	docker compose -f docker-compose.yml -f docker-compose.prd.yml build
	docker compose -f docker-compose.yml -f docker-compose.prd.yml up -d
