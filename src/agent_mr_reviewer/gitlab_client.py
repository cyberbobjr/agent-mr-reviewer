from __future__ import annotations

from typing import Any, Dict
import requests


class GitLabClient:
    def __init__(self, base_url: str, token: str, token_type: str = "job") -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if token_type == "job":
            self.session.headers.update({"JOB-TOKEN": token})
        else:
            self.session.headers.update({"PRIVATE-TOKEN": token})
        self.session.headers.update({"Content-Type": "application/json"})

    def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v4{path}"
        response = self.session.request(method, url, **kwargs)
        if not response.ok:
            raise RuntimeError(
                f"GitLab API error {response.status_code}: {response.text}"
            )
        return response.json()

    def get_merge_request(self, project_id: str, mr_iid: str) -> Dict[str, Any]:
        return self._request("GET", f"/projects/{project_id}/merge_requests/{mr_iid}")

    def get_changes(self, project_id: str, mr_iid: str) -> Dict[str, Any]:
        return self._request(
            "GET", f"/projects/{project_id}/merge_requests/{mr_iid}/changes"
        )

    def get_commits(self, project_id: str, mr_iid: str) -> Dict[str, Any]:
        return self._request(
            "GET", f"/projects/{project_id}/merge_requests/{mr_iid}/commits"
        )

    def post_discussion(
        self,
        project_id: str,
        mr_iid: str,
        body: str,
        position: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = {"body": body, "position": position}
        return self._request(
            "POST", f"/projects/{project_id}/merge_requests/{mr_iid}/discussions", json=payload
        )

    def post_note(self, project_id: str, mr_iid: str, body: str) -> Dict[str, Any]:
        payload = {"body": body}
        return self._request(
            "POST", f"/projects/{project_id}/merge_requests/{mr_iid}/notes", json=payload
        )
