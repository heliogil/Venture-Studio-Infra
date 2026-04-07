"""
automation-runner/runner.py
BOT 05 — Automation Runner.
Jobs: health check horário, relatório de custo diário.
Extensível: adicionar @dramatiq.actor + scheduler.add_job.
"""
import dramatiq
from dramatiq.brokers.redis import RedisBroker
from apscheduler.schedulers.blocking import BlockingScheduler
import httpx
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://vs_redis:6379/1")
LITELLM_URL = os.environ.get("LITELLM_URL", "http://vs_litellm:4000")
LITELLM_KEY = os.environ.get("LITELLM_KEY", "")
KNOWLEDGE_API_URL = os.environ.get("KNOWLEDGE_API_URL", "http://vs_knowledge_api:8000")

broker = RedisBroker(url=REDIS_URL)
dramatiq.set_broker(broker)


@dramatiq.actor
def health_check():
    """Verifica saúde dos serviços core."""
    services = {
        "litellm": (
            f"{LITELLM_URL}/health/liveliness",
            {"Authorization": f"Bearer {LITELLM_KEY}"},
        ),
        "knowledge_api": (f"{KNOWLEDGE_API_URL}/health", {}),
    }
    with httpx.Client(timeout=10) as http:
        for name, (url, headers) in services.items():
            try:
                resp = http.get(url, headers=headers)
                status = "OK" if resp.status_code == 200 else f"HTTP {resp.status_code}"
            except Exception as e:
                status = f"ERROR: {e}"
            logger.info(f"Health {name}: {status}")


@dramatiq.actor
def daily_cost_report():
    """Relatório diário de custo de tokens via LiteLLM spend logs."""
    with httpx.Client(timeout=15) as http:
        try:
            resp = http.get(
                f"{LITELLM_URL}/spend/logs",
                headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            )
            data = resp.json()
            entries = data.get("data", [])
            total = sum(float(e.get("spend", 0)) for e in entries)
            logger.info(f"Daily spend: US${total:.4f} ({len(entries)} requests)")
        except Exception as e:
            logger.error(f"Cost report error: {e}")


def main():
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(health_check.send, "interval", hours=1, id="health_check")
    scheduler.add_job(
        daily_cost_report.send, "cron",
        hour=8, minute=0, id="daily_cost_report",
    )
    logger.info("BOT 05 — Automation Runner iniciado")
    scheduler.start()


if __name__ == "__main__":
    main()
