"""Tests for FastAPI backend endpoints."""

import tempfile
import pytest
from fastapi.testclient import TestClient
from src.api.app import create_app


class TestAPI:
    @pytest.fixture
    def client(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(store_dir=tmpdir)
            yield TestClient(app)

    def test_health_endpoint(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "provider" in data

    def test_end_to_end_project_workflow(self, client):
        # 1. Create project from seed
        create_res = client.post(
            "/api/projects",
            json={
                "seed_prompt": "Two rival art dealers confront each other over a forged masterpiece in an exclusive gallery.",
                "title": "The Forged Masterpiece",
            },
        )
        assert create_res.status_code == 200
        proj_meta = create_res.json()
        pid = proj_meta["id"]
        assert proj_meta["title"] == "The Forged Masterpiece"

        # 2. List projects
        list_res = client.get("/api/projects")
        assert list_res.status_code == 200
        projects = list_res.json()
        assert len(projects) >= 1
        assert any(p["id"] == pid for p in projects)

        # 3. Inspect world state
        world_res = client.get(f"/api/projects/{pid}/world")
        assert world_res.status_code == 200
        world = world_res.json()
        assert len(world["characters"]) >= 2
        assert len(world["locations"]) >= 1

        # 4. Step simulation
        step_res = client.post(f"/api/projects/{pid}/step", json={"ticks": 1})
        assert step_res.status_code == 200
        step_data = step_res.json()
        assert step_data["current_tick"] == 1

        # 5. Run simulation for multiple ticks
        run_res = client.post(f"/api/projects/{pid}/run", json={"num_ticks": 3})
        assert run_res.status_code == 200
        run_data = run_res.json()
        assert run_data["current_tick"] >= 2

        # 6. Retrieve events
        events_res = client.get(f"/api/projects/{pid}/events")
        assert events_res.status_code == 200
        events = events_res.json()
        assert len(events) >= 1

        # 7. Generate screenplay
        screenplay_res = client.post(f"/api/projects/{pid}/generate-screenplay")
        assert screenplay_res.status_code == 200
        sc_data = screenplay_res.json()
        assert "fountain_text" in sc_data
        assert sc_data["total_scenes"] >= 1
        assert "Title: The Forged Masterpiece" in sc_data["fountain_text"]

        # 8. Download screenplay
        dl_res = client.get(f"/api/projects/{pid}/screenplay/download")
        assert dl_res.status_code == 200
        assert "attachment" in dl_res.headers["content-disposition"]
        assert len(dl_res.text) > 0

        # 8b. Storyboard generation
        story_res = client.get(f"/api/projects/{pid}/storyboard")
        assert story_res.status_code == 200
        story_data = story_res.json()
        assert story_data["shot_plan"]["total_panels"] >= 1
        assert len(story_data["rendered_panels"]) >= 1

        # 9. Delete project
        del_res = client.delete(f"/api/projects/{pid}")
        assert del_res.status_code == 200

        # Verify not found after deletion
        get_res = client.get(f"/api/projects/{pid}")
        assert get_res.status_code == 404
