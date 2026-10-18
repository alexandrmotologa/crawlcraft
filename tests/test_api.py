"""Tests for FastAPI endpoints and server routes."""

import pytest
from fastapi.testclient import TestClient
from crawlcraft.server.app import app

client = TestClient(app)


def test_health_check():
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_extract_endpoint_raw_html():
    raw_html = """
    <html>
      <head><title>API Extract Test</title></head>
      <body>
        <main>
          <h1>API Extraction</h1>
          <p>This is a test of synchronous HTML extraction via REST API.</p>
        </main>
      </body>
    </html>
    """
    response = client.post("/v1/extract", json={"html": raw_html})
    assert response.status_code == 200
    data = response.json()
    assert "# API Extraction" in data["markdown"]
    assert data["metadata"]["title"] == "API Extract Test"
    assert data["metadata"]["token_stats"]["token_count"] > 0


def test_crawl_launch_endpoint():
    payload = {
        "urls": ["https://example.com"],
        "max_depth": 1,
        "max_pages": 2,
        "concurrency": 2,
        "requests_per_second": 10.0,
        "same_domain_only": True,
        "allow_spa_fallback": False,
    }
    response = client.post("/v1/crawl", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"

    job_id = data["job_id"]
    status_response = client.get(f"/v1/crawl/{job_id}/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["job_id"] == job_id
