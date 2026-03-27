.PHONY: deploy-prod rebuild-db

deploy-prod:
	git pull
	docker compose -f docker-compose.yml -f docker-compose.prd.yml build
	docker compose -f docker-compose.yml -f docker-compose.prd.yml up -d

rebuild-db:
	docker compose -f docker-compose.yml -f docker-compose.prd.yml down -v
	docker compose -f docker-compose.yml -f docker-compose.prd.yml up -d
	@echo "✅ DB rebuilt — schema + seed data ใหม่"
