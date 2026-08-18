#!/usr/bin/env python3
import argparse
import os
import time

from examples.workspace import download_test_workspace, upload_test_workspace


parser = argparse.ArgumentParser()
parser.add_argument("--dev-sidecar", action="store_true")
args = parser.parse_args()
if args.dev_sidecar:
    from examples.dev_sidecar import setup_dev_sidecar

    setup_dev_sidecar()

from e2b import Sandbox


template = os.environ["CUBE_TEMPLATE_ID"]

with Sandbox.create(template, timeout=600) as sandbox:
    upload_test_workspace(sandbox)

    for _ in range(60):
        info = sandbox.commands.run(
            "docker info --format '{{.ServerVersion}} {{.Driver}}' 2>/dev/null || true",
            user="root",
        )
        if info.stdout.strip():
            break
        time.sleep(0.5)
    else:
        raise RuntimeError("Docker daemon did not become ready")

    version, driver = info.stdout.strip().split(maxsplit=1)
    if driver != "vfs":
        raise RuntimeError(f"Expected Docker storage driver vfs, got {driver}")

    build = sandbox.commands.run(
        "docker build --tag coding-agent-workspace /workspace",
        user="root",
        timeout=600,
        on_stdout=lambda data: print(data, end=""),
    )
    if build.exit_code != 0:
        raise RuntimeError(build.stderr)

    run = sandbox.commands.run(
        "docker run --rm coding-agent-workspace",
        user="root",
        timeout=120,
    )
    if run.exit_code != 0:
        raise RuntimeError(run.stderr)

    print(f"Docker {version}, storage driver {driver}")
    print(run.stdout, end="")
    print(f"Workspace: {download_test_workspace(sandbox, 'docker')}")
