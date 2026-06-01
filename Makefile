AWS_PROFILE ?= context-engine-admin
AWS_REGION ?= us-east-1
ENVIRONMENT ?= prod
PROJECT ?= context-engine

ECS_CLUSTER := $(PROJECT)-$(ENVIRONMENT)-ecs-cluster
ECS_SERVICE := $(PROJECT)-$(ENVIRONMENT)-api
RDS_INSTANCE := $(PROJECT)-$(ENVIRONMENT)-rds
ALB_NAME := $(PROJECT)-$(ENVIRONMENT)-alb

.PHONY: demo-local demo-on demo-off local-down local-logs local-migrate local-test local-up status

demo-on:
	-aws rds start-db-instance --db-instance-identifier $(RDS_INSTANCE) --profile $(AWS_PROFILE) --region $(AWS_REGION)
	aws rds wait db-instance-available --db-instance-identifier $(RDS_INSTANCE) --profile $(AWS_PROFILE) --region $(AWS_REGION)
	aws ecs update-service --cluster $(ECS_CLUSTER) --service $(ECS_SERVICE) --desired-count 1 --profile $(AWS_PROFILE) --region $(AWS_REGION) --no-cli-pager
	aws ecs wait services-stable --cluster $(ECS_CLUSTER) --services $(ECS_SERVICE) --profile $(AWS_PROFILE) --region $(AWS_REGION)
	@powershell.exe -NoProfile -Command "$$alb = aws elbv2 describe-load-balancers --names '$(ALB_NAME)' --query 'LoadBalancers[0].DNSName' --output text --profile '$(AWS_PROFILE)' --region '$(AWS_REGION)'; for ($$i = 1; $$i -le 30; $$i++) { try { Invoke-WebRequest -UseBasicParsing ""http://$$alb/health"" -TimeoutSec 5 | Out-Null; Write-Host ""ContextEngine healthy at http://$$alb/health""; exit 0 } catch { Start-Sleep -Seconds 10 } }; Write-Error ""Health check did not pass within 5 minutes""; exit 1"

demo-off:
	aws ecs update-service --cluster $(ECS_CLUSTER) --service $(ECS_SERVICE) --desired-count 0 --profile $(AWS_PROFILE) --region $(AWS_REGION) --no-cli-pager
	aws ecs wait services-stable --cluster $(ECS_CLUSTER) --services $(ECS_SERVICE) --profile $(AWS_PROFILE) --region $(AWS_REGION)
	-aws rds stop-db-instance --db-instance-identifier $(RDS_INSTANCE) --profile $(AWS_PROFILE) --region $(AWS_REGION)

status:
	aws rds describe-db-instances --db-instance-identifier $(RDS_INSTANCE) --query "DBInstances[0].DBInstanceStatus" --output text --profile $(AWS_PROFILE) --region $(AWS_REGION)
	aws ecs describe-services --cluster $(ECS_CLUSTER) --services $(ECS_SERVICE) --query "services[0].{status:status,desired:desiredCount,running:runningCount,pending:pendingCount}" --output table --profile $(AWS_PROFILE) --region $(AWS_REGION)

local-up:
	docker compose up --build -d --wait postgres backend

local-down:
	docker compose down

local-logs:
	docker compose logs -f postgres backend

local-migrate:
	docker compose up -d --wait postgres
	docker compose run --rm backend alembic upgrade head

demo-local:
	docker compose up -d --wait postgres backend
	docker compose exec backend alembic upgrade head
	docker compose exec backend python -m app.scripts.demo_local

local-test:
	cd backend && .\.venv\Scripts\python.exe -m ruff format .
	cd backend && .\.venv\Scripts\python.exe -m ruff check .
	cd backend && .\.venv\Scripts\python.exe -m mypy app
	cd backend && .\.venv\Scripts\python.exe -m pytest
