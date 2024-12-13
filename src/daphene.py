import json
import os
import platform
import argparse
from colorama import Fore, Style
from uuid import uuid4
import subprocess
import shutil
from pathlib import Path

PACKAGE_SERVER = "http://localhost:8000"
VERSION = "1.0.0"


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-r", "--run", help="The container to run", type=str
    )
    parser.add_argument(
        "-i",
        "--init",
        action="store_true",
        help="Initialize a new container",
    )
    parser.add_argument(
        "-d", "--defaults", action="store_true", help="Use default values"
    )
    return parser.parse_args()


def get_temp_dir():
    platform_name = platform.platform().split("-")[0]
    if platform_name == "Windows":
        return f"C:\\Users\\{os.getlogin()}\\AppData\\Local\\Temp\\daphne-venvs\\{uuid4()}"
    elif platform_name == "Linux":
        return f"/tmp/{uuid4()}"
    else:
        print(
            f"{Fore.RED}❌ Unsupported platform: {Fore.LIGHTBLACK_EX}{platform_name}{Style.RESET_ALL}"
        )
        exit(1)


def run(container, script="start"):
    if os.path.isdir(container):
        return run_container(container, is_built=False, script=script)
    else:
        print(f"{Fore.RED}❌ Invalid container{Style.RESET_ALL}")
        exit(1)


def clean_temp_dir(temp_dir):
    platform_name = platform.platform().split("-")[0]
    if platform_name == "Windows":
        os.system(f"rd /s /q {temp_dir}")
    elif platform_name == "Linux":
        os.system(f"rm -rf {temp_dir}")
    else:
        print(
            f"{Fore.RED}❌ Unsupported platform: {Fore.LIGHTBLACK_EX}{platform_name}{Style.RESET_ALL}"
        )
        exit(1)


def run_container(container, is_built=False, script="start"):
    print(
        f"{Fore.CYAN}🚀 Running container {Fore.LIGHTBLACK_EX}{container}{Style.RESET_ALL}"
    )

    if not is_built:
        print(
            f"{Fore.YELLOW}⚠️  Warning: Running an unbuilt container. Consider building it for production.{Style.RESET_ALL}"
        )

    try:
        metadata = load_json(f"{container}/.daphne/meta.json")

        runs_on = metadata["scripts"][script].get("runsOn", "python@latest")
        env_path = prepare_virtualenv(runs_on, container)

        try:
            start_script = metadata["scripts"][script]
        except KeyError:
            print(
                f"{Fore.RED}❌ No such script {Fore.LIGHTBLACK_EX}{script}{Style.RESET_ALL} in container {Fore.LIGHTBLACK_EX}{container}@{metadata['version']}{Style.RESET_ALL}"
            )
            exit(1)

        if not run_script_in_virtualenv(
            start_script, container, metadata["name"], env_path
        ):
            print(
                f"{Fore.RED}❌ Failed to run container {Fore.LIGHTBLACK_EX}{container}@{metadata['version']}{Style.RESET_ALL}"
            )
            exit(1)

    except Exception as e:
        print(
            f"{Fore.RED}❌ Failed to run container {Fore.LIGHTBLACK_EX}{container}@{metadata['version']}{Fore.RED}: {e}{Style.RESET_ALL}"
        )
        exit(1)

    print(
        f"{Fore.GREEN}🎉 Successfully ran container {Fore.LIGHTBLACK_EX}{container}@{metadata['version']}{Style.RESET_ALL}"
    )


def prepare_virtualenv(runs_on, container_dir):
    if not runs_on.lower() == "python":
        print(
            f"{Fore.RED}❌ Unsupported environment: {Fore.LIGHTBLACK_EX}{runs_on}{Style.RESET_ALL}"
        )
        exit(1)

    env_path = Path(get_temp_dir())

    if env_path.exists():
        shutil.rmtree(env_path)
    print(f"{Fore.BLUE}♻️  Preparing virtual environment at {env_path}{Style.RESET_ALL}")

    try:
        subprocess.run(
            ["virtualenv", str(env_path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print(
            f"{Fore.GREEN}✅ Virtual environment created at {env_path}{Style.RESET_ALL}"
        )

        subprocess.run(
            ["cp", "-r", f"{container_dir}/.", str(env_path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except Exception as e:
        print(
            f"{Fore.RED}❌ Failed to create virtual environment: {e}{Style.RESET_ALL}"
        )
        exit(1)

    return env_path


def run_script_in_virtualenv(script, path, container_name, env_path):
    env_bin = (
        env_path / "Scripts" if platform.system() == "Windows" else env_path / "bin"
    )
    env_python = (
        env_bin / "python.exe" if platform.system() == "Windows" else env_bin / "python"
    )
    env_pip = env_bin / "pip.exe" if platform.system() == "Windows" else env_bin / "pip"

    if os.path.exists(f"{path}/requirements.txt"):
        try:
            subprocess.run(
                [env_pip, "install", "-r", f"{path}/requirements.txt"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            print(
                f"{Fore.GREEN}✅ Installed dependencies in virtual environment{Style.RESET_ALL}"
            )
        except Exception as e:
            print(f"{Fore.RED}❌ Failed to install dependencies: {e}{Style.RESET_ALL}")
            exit(1)

    os.chdir(env_path)

    command = f"{env_python} {env_path / script["main"]} {script.get('args', '')}"

    try:
        print(
            f"{Fore.MAGENTA}♻️  Running script in virtual environment:{Fore.LIGHTBLACK_EX} {script["main"]}{Style.RESET_ALL}"
        )
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate()

        print()

        if stdout:
            outs = stdout.decode("utf-8").splitlines()
            for out in outs:
                print(f"{Fore.MAGENTA}📦 {container_name}{Style.RESET_ALL} {out}")
        else:
            print(
                f"{Fore.MAGENTA}📦 {container_name}{Style.RESET_ALL} had no captured output."
            )

        print()

        if process.returncode != 0:
            print(
                f"{Fore.RED}❌ Script failed {Fore.LIGHTBLACK_EX}{script["main"]}{Fore.RED}: {stderr.decode('utf-8')}{Style.RESET_ALL}"
            )
            return False
        else:
            print(
                f"{Fore.GREEN}✅ Script succeeded {Fore.LIGHTBLACK_EX}{script["main"]}{Style.RESET_ALL}"
            )
    except Exception as e:
        print(
            f"{Fore.RED}❌ Error running script {Fore.LIGHTBLACK_EX}{script['main']}{Fore.RED}: {e}{Style.RESET_ALL}"
        )
        return False

    return True


def create_container(name, version, description, license, scripts):
    if os.path.exists(f"{name}"): shutil.rmtree(f"{name}")
    
    os.mkdir(f"{name}")
    os.mkdir(f"{name}/.daphne")

    with open(f"{name}/.daphne/meta.json", "w") as f:
        json.dump(
            {
                "name": name,
                "version": version,
                "description": description,
                "license": license,
                "scripts": scripts,
            },
            f,
        )

    with open(f"{name}/{scripts['start']['main']}", "w") as f:
        f.write("print('Hello World!')")


def init_container(defaults=False):
    if defaults:
        name = "mycontainer"
        version = "1.0.0"
        description = ""
        license = "MIT"
        scripts = {
            "start": {
                "runsOn": "python",
                "main": "main.py",
            }
        }
    else:
        name = (
            input(f"{Fore.MAGENTA}📦 Container name (mycontainer):{Style.RESET_ALL} ")
            or "mycontainer"
        )
        version = (
            input(f"{Fore.MAGENTA}📦 Container version (1.0.0):{Style.RESET_ALL} ")
            or "1.0.0"
        )
        description = (
            input(f"{Fore.MAGENTA}📦 Container description (None):{Style.RESET_ALL} ")
            or ""
        )
        license = (
            input(f"{Fore.MAGENTA}📦 Container license (MIT):{Style.RESET_ALL} ")
            or "MIT"
        )
        scripts = {
            "start": {
                "runsOn": (
                    input(
                        f"{Fore.MAGENTA}📦 Container language (python):{Style.RESET_ALL} "
                    )
                    or "python"
                ),
                "main": (
                    input(
                        f"{Fore.MAGENTA}📦 Container main file (main.py):{Style.RESET_ALL} "
                    )
                    or "main.py"
                ),
            }
        }

    create_container(name, version, description, license, scripts)


def load_json(filepath):
    with open(filepath) as f:
        return json.load(f)


if __name__ == "__main__":
    print("==============================================================")
    print(f"{Fore.CYAN}🟦 Daphene v{VERSION} 🟦{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🌏 Package Server: {PACKAGE_SERVER}{Style.RESET_ALL}")
    print("==============================================================")

    args = parse_arguments()

    if args.run:
        run(args.run)
    elif args.init:
        init_container(args.defaults)
    else:
        print(
            f"{Fore.RED}❌ Please specify either {Fore.LIGHTBLACK_EX}--run{Style.RESET_ALL} or {Fore.LIGHTBLACK_EX}--init{Style.RESET_ALL}"
        )
