import os
import shutil
import subprocess
import sys
from pathlib import Path

import nox

PROJECT_NAME = "remoteperf"


@nox.session(python=["3.8", "3.10", "3.12"])
def lint(session):
    shutil.rmtree("tmp", ignore_errors=True)
    session.install("-U", "-r", "requirements/requirements.txt")
    session.install("-U", "-r", "requirements/requirements_test.txt")
    run_lint(session)


@nox.session(python=["3.8", "3.10", "3.12"])
def test(session):
    session.install("-U", "-r", "requirements/requirements.txt")
    session.install("-U", "-r", "requirements/requirements_test.txt")
    run_test(session)


@nox.session(python="3")
def doc(session):
    session.install("-U", "-r", "requirements/requirements.txt")
    session.install("-U", "-r", "requirements/requirements_docs.txt")
    run_doc(session)


@nox.session(python="3")
def package(session):
    session.install("-U", "-r", "requirements/requirements.txt")
    session.install("-U", "-r", "requirements/requirements_dev.txt")
    build_wheel_package(session)


@nox.session
def build_integration_image(session):
    import yaml

    with open("integration_tests/docker-compose.yaml", "r") as file:
        compose_file = yaml.safe_load(file)
    docker_image = compose_file["services"]["emulator"]["image"]
    session.run(
        *[
            "docker",
            "build",
            "-t",
            docker_image,
            "./integration_tests/image",
        ]
    )


@nox.session(python="3.8")
def integration_test(session):
    flags = {"keep_container": False, "run_tests": False}
    for arg in flags:
        if arg in session.posargs:
            flags[arg] = True
    args = [arg for arg in session.posargs if arg not in flags]
    if flags["run_tests"]:
        session.run(
            *[
                "pytest",
                *args,
                "--color=yes",
                "--cov=./remoteperf",
                "--cov-report",
                "xml:tmp/report/coverage/xml/integration_report.xml",
                "--cov-report",
                "term",
                "--cov-report",
                "html:tmp/report/coverage/html",
                "--junitxml=tmp/report/junit/integration_report.xml",
                "--cov-fail-under=80",
                ".",
                "integration_tests/tests",
                "-vv",
            ]
        )
    else:
        session.install("-U", "-r", "requirements/requirements.txt")
        session.install("-U", "-r", "requirements/requirements_test.txt")

        docker_compose_command = [
            "docker",
            "compose",
            "-f",
            "integration_tests/docker-compose.yaml",
            "up",
            "-d",
            "--wait",
        ]
        docker_run_command = [
            "docker",
            "exec",
            f"{PROJECT_NAME}_integration_test",
            "bash",
            "-c",
            f"run_nox -rs integration_test -- run_tests {' '.join(session.posargs)}",
        ]
        docker_permissions_command = [
            "docker",
            "exec",
            f"{PROJECT_NAME}_integration_test",
            "chown",
            "-R",
            f"{os.getuid()}:{os.getgid()}",
            f"{os.getcwd()}/tmp",
        ]
        try:
            session.run(*docker_compose_command, external=True)
            session.run(*docker_run_command, external=True)
            session.run(*docker_permissions_command, external=True)
        finally:
            if not flags["keep_container"]:
                remove_docker_container(session, f"{PROJECT_NAME}_integration_test")
        session.log("Docker Compose command ran successfully.")


def remove_docker_container(session, container):
    existing_container_command = f"docker ps -a | grep {container} || true"
    existing_container = subprocess.check_output(["bash", "-c", existing_container_command]).decode()
    if existing_container and len(existing_container.split()[0]) == 12:
        session.run("docker", "container", "rm", "-f", container)


def build_wheel_package(session, clean=False, install=False):
    dist_directory = Path("tmp") / "dist"
    current_path = Path(__file__).resolve().parent
    session.run(
        sys.executable,
        "-m",
        "build",
        "--sdist",
        "--wheel",
        "--outdir",
        dist_directory,
        external=True,
    )
    for path in [Path("build"), next(Path(".").glob("*.egg-info"))]:
        if clean:
            shutil.rmtree(path, ignore_errors=True)
        else:
            shutil.rmtree(Path("tmp") / path, ignore_errors=True)
            shutil.move(str(path), "tmp")

    dist_dir = current_path / "tmp" / "dist"
    whl_package = next(dist_dir.glob("*.whl"))
    tar_package = next(dist_dir.glob("*.tar.gz"))
    if install:
        session.log(f"Found whl package: {whl_package}")
        session.run(
            sys.executable,
            "-m",
            "pip",
            "install",
            "-U",
            "--force-reinstall",
            whl_package,
        )
    return whl_package, tar_package


def run_lint(session):
    shutil.rmtree("tmp", ignore_errors=True)
    session.log("Running black")
    session.run("black", "--check", "remoteperf", "tests", silent=True)

    session.log("Running pylint")
    session.run(
        "pylint",
        "--output-format=colorized",
        "--reports=y",
        "--disable=W0511,R0903",  # Don't fail on FIXMEs
        "./remoteperf",
    )

    session.log("Running mypy")
    session.run("mypy", "./remoteperf", success_codes=[1, 0])


def run_test(session):
    env = {
        "COVERAGE_FILE": "/tmp/report/coverage/junk/coverage",
    }

    command = [
        "pytest",
        *session.posargs,
        "--color=yes",
        "--cov=./remoteperf",
        "--cov-report",
        "xml:tmp/report/coverage/xml/report.xml",
        "--cov-report",
        "term",
        "--cov-report",
        "html:tmp/report/coverage/html",
        "--junitxml=tmp/report/junit/report.xml",
        "--cov-fail-under=70",
        ".",
        "tests",
        "--ignore=integration_tests",
    ]
    command.extend(session.posargs)
    session.run(*command, env=env)


def run_doc(session):
    for path in Path("docs/source/code").glob("*"):
        path.unlink()
    session.run(
        "sphinx-apidoc",
        "-o",
        "docs/source/code",
        "remoteperf",
        "-e",
        "--force",
        "-d",
        "20",
        "-P",
        "--implicit-namespaces",
        "-M",
    )
    session.run("sphinx-build", "docs/source", "tmp/docs/build/html")
