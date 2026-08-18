from __future__ import annotations

import io
import os
import tarfile
from pathlib import Path


LOCAL_WORKSPACE = Path(__file__).with_name("test_workspace")
REMOTE_ARCHIVE = "/tmp/coding-agent-test-workspace.tar.gz"


def upload_test_workspace(sandbox) -> None:
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as tar:
        for path in LOCAL_WORKSPACE.rglob("*"):
            if (
                path.is_file()
                and "__pycache__" not in path.parts
                and path.suffix != ".pyc"
            ):
                tar.add(path, arcname=path.relative_to(LOCAL_WORKSPACE).as_posix())

    sandbox.files.write(REMOTE_ARCHIVE, archive.getvalue(), user="root")
    result = sandbox.commands.run(
        "rm -rf /workspace && install -d -m 755 /workspace && "
        f"tar -xzf {REMOTE_ARCHIVE} -C /workspace",
        user="root",
    )
    if result.exit_code != 0:
        raise RuntimeError(result.stderr)


def download_test_workspace(sandbox, run_name: str) -> Path:
    result = sandbox.commands.run(
        "tar --exclude='*/.git' --exclude='*/node_modules' --exclude='*/dist' "
        "--exclude='*/__pycache__' --exclude='*.pyc' "
        "-czf /tmp/coding-agent-workspace-result.tar.gz -C /workspace .",
        user="root",
    )
    if result.exit_code != 0:
        raise RuntimeError(result.stderr)

    output_dir = Path(os.environ.get("WORKSPACE_OUTPUT_DIR", "workspace-output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{run_name}.tar.gz"
    output_path.write_bytes(
        sandbox.files.read(
            "/tmp/coding-agent-workspace-result.tar.gz", format="bytes", user="root"
        )
    )
    return output_path
