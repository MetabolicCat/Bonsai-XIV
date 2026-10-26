"""Reading a repository hosted on GitHub at a given commit."""

import httpx


def head_commit(client: httpx.Client, repository: str) -> str:
    """The commit at the head of the default branch of `repository`."""
    response = client.get(
        f"https://api.github.com/repos/{repository}/commits/HEAD",
        headers={"Accept": "application/vnd.github.sha"},
    )
    response.raise_for_status()
    return response.text.strip()


def raw_file(client: httpx.Client, repository: str, commit: str, path: str) -> bytes:
    response = client.get(
        f"https://raw.githubusercontent.com/{repository}/{commit}/{path}"
    )
    response.raise_for_status()
    return response.content
