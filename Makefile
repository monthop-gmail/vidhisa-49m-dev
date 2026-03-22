.PHONY: deploy-prod

deploy-prod:
	docker compose -f docker-compose.yml -f docker-compose.prd.yml build --no-cache
	docker compose -f docker-compose.yml -f docker-compose.prd.yml up -d
