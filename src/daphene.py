import json
import os
import platform
import argparse
from uuid import uuid4
import subprocess
import shutil
from pathlib import Path
import atexit
import zipfile

from colorama import Fore, Style


VERSION = "1.3.0"


def register_cleanup(temp_dir):
    atexit.register(lambda: clean_temp_dir(temp_dir))


def printerror(message):
    print(f"{Fore.RED}❌ {message}{Style.RESET_ALL}")
    
def printwarning(message):
    print(f"{Fore.YELLOW}⚠️  {message}{Style.RESET_ALL}")
    
def printsuccess(message):
    print(f"{Fore.GREEN}✅ {message}{Style.RESET_ALL}")


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--run", help="The container to run", type=str)
    parser.add_argument(
        "-i",
        "--init",
        action="store_true",
        help="Initialize a new container",
    )
    parser.add_argument(
        "-t", "--template", help="Template file for container initialization", type=str
    )
    parser.add_argument(
        "-d", "--defaults", action="store_true", help="Use default values"
    )
    parser.add_argument("-v", "--version", action="version", version=VERSION)
    parser.add_argument(
        "-l", "--list", action="store_true", help="List available containers"
    )
    return parser.parse_args()


def get_temp_dir():
    platform_name = platform.platform().split("-")[0]
    if platform_name == "Windows":
        return (
            f"C:\\Users\\{os.getlogin()}\\AppData\\Local\\Temp\\daphne-venvs\\{uuid4()}"
        )
    elif platform_name == "Linux":
        return f"/tmp/{uuid4()}"
    else:
        print(
            f"{Fore.RED}❌ Unsupported platform: {Fore.LIGHTBLACK_EX}{platform_name}{Style.RESET_ALL}"
        )
        printerror(f"Unsupported platform: {Fore.LIGHTBLACK_EX}{platform_name}")
        exit(1)


def list_containers(base_dir="."):
    containers = [
        d
        for d in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, d))
        and os.path.exists(os.path.join(base_dir, d, ".daphene", "meta.json"))
    ]
    if containers:
        print(f"{Fore.GREEN}Available containers:{Style.RESET_ALL}")
        for container in containers:
            print(f" - {container}")
    else:
        print(f"{Fore.YELLOW}No containers found in the directory{Style.RESET_ALL}")


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
        metadata = load_json(f"{container}/.daphene/meta.json")

        runtime = metadata["scripts"][script].get("runtime")
        env_path, runtime_meta = prepare_virtualenv(runtime, container)

        try:
            script = metadata["scripts"][script]
        except KeyError:
            print(
                f"{Fore.RED}❌ No such script {Fore.LIGHTBLACK_EX}{script}{Style.RESET_ALL} in container {Fore.LIGHTBLACK_EX}{container}@{metadata["version"]}{Style.RESET_ALL}"
            )
            exit(1)

        if not run_script_in_virtualenv(
            script, container, metadata["name"], env_path, runtime, runtime_meta
        ):
            print(
                f"{Fore.RED}❌ Failed to run container {Fore.LIGHTBLACK_EX}{container}@{metadata["version"]}{Style.RESET_ALL}"
            )
            exit(1)

    except Exception as e:
        print(
            f"{Fore.RED}❌ Failed to run container {Fore.LIGHTBLACK_EX}{container}@{metadata["version"]}{Fore.RED}: {e}{Style.RESET_ALL}"
        )
        exit(1)

    print(
        f"{Fore.GREEN}🎉 Successfully ran container {Fore.LIGHTBLACK_EX}{container}@{metadata["version"]}{Style.RESET_ALL}"
    )


def prepare_virtualenv(runtime, container_dir):
    if not (runtime.lower() + ".zip") in os.listdir("runtimes"):
        print(
            f"{Fore.RED}❌ Unsupported runtime: {Fore.LIGHTBLACK_EX}{runtime}{Style.RESET_ALL}"
        )
        exit(1)

    env_path = Path(get_temp_dir())
    register_cleanup(env_path)

    extract_zip(f"runtimes/{runtime}.zip", env_path / "runtime")
    runtime_meta = load_json(env_path / "runtime" / ".daphene" / "meta.json")

    if env_path.exists():
        shutil.rmtree(env_path)
    print(
        f"{Fore.BLUE}♻️  Creating {runtime_meta["name"]} virtual environment{Style.RESET_ALL}"
    )

    try:
        print(
            f"{Fore.GREEN}✅ {"Python" if runtime == 'python' else "NodeJS"} virtual environment created{Style.RESET_ALL}"
        )

        subprocess.run(
            ["cp", "-r", f"{container_dir}/.", str(env_path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except Exception as e:
        print(
            f"{Fore.RED}❌ Failed to create {'Python' if runtime == 'python' else 'NodeJS'} virtual environment: {e}{Style.RESET_ALL}"
        )
        exit(1)

    return env_path, runtime_meta


def run_script_in_virtualenv(
    script, path, container_name, env_path, runtime, runtime_meta
):
    env_executable = runtime_meta["executables"]["exec"]
    env_packagemanager = runtime_meta["executables"]["packagemanager"]

    if os.path.exists(f"{path}/requirements.txt") and runtime == "python":
        try:
            subprocess.run(
                [env_packagemanager, "install", "-r", f"{path}/requirements.txt"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            print(
                f"{Fore.GREEN}✅ Installed dependencies in virtual environment for {Fore.LIGHTBLACK_EX}{container_name}{Style.RESET_ALL}"
            )
        except Exception as e:
            print(
                f"{Fore.RED}❌ Failed to install dependencies in virtual environment for {Fore.LIGHTBLACK_EX}{container_name}{Fore.RED}: {e}{Style.RESET_ALL}"
            )
            exit(1)
    elif os.path.exists(f"{path}/package.json") and runtime == "nodejs":
        try:
            subprocess.run(
                [env_packagemanager, "install"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            print(
                f"{Fore.GREEN}✅ Installed dependencies in virtual environment for {Fore.LIGHTBLACK_EX}{container_name}{Style.RESET_ALL}"
            )
        except Exception as e:
            print(
                f"{Fore.RED}❌ Failed to install dependencies in virtual environment for {Fore.LIGHTBLACK_EX}{container_name}{Fore.RED}: {e}{Style.RESET_ALL}"
            )
            exit(1)

    os.chdir(env_path)

    command = f"{env_executable} {env_path / script["main"]} {script.get("args", "")}"

    try:
        print(
            f"{Fore.MAGENTA}♻️  Running script in virtual environment for {Fore.LIGHTBLACK_EX}{container_name}{Style.RESET_ALL}{Fore.MAGENTA}:{Fore.LIGHTBLACK_EX} {script["main"]}{Style.RESET_ALL}"
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
                f"{Fore.RED}❌ Script {Fore.LIGHTBLACK_EX}{script["main"]}{Fore.RED} failed in {Fore.LIGHTBLACK_EX}{container_name}{Fore.RED}: {stderr.decode("utf-8")}{Style.RESET_ALL}"
            )
            return False
        else:
            print(
                f"{Fore.GREEN}✅ Script {Fore.LIGHTBLACK_EX}{script["main"]}{Fore.GREEN} ran successfully in {Fore.LIGHTBLACK_EX}{container_name}{Style.RESET_ALL}"
            )
    except Exception as e:
        print(
            f"{Fore.RED}❌ Error running script {Fore.LIGHTBLACK_EX}{script["main"]}{Fore.RED} in {Fore.LIGHTBLACK_EX}{container_name}{Fore.RED}: {e}{Style.RESET_ALL}"
        )
        return False

    return True


def create_container(name, version, description, license, scripts):
    if os.path.exists(f"{name}"):
        shutil.rmtree(f"{name}")

    os.mkdir(f"{name}")
    os.mkdir(f"{name}/.daphene")

    with open(f"{name}/.daphene/meta.json", "w") as f:
        json.dump(
            {
                "$schema": "https://github.com/proplayer919/daphene/blob/main/container.schema.json",
                "name": name,
                "version": version,
                "description": description,
                "license": license,
                "scripts": scripts,
            },
            f,
        )

    default_code = {
        "python": "print('Hello World!')",
        "node": "console.log('Hello World!')",
    }

    with open(f"{name}/{scripts["start"]["main"]}", "w") as f:
        f.write(default_code.get(scripts["start"]["runtime"], "Your code here."))


def init_container(defaults=False, template_path=None):
    if template_path:
        try:
            with open(template_path, "r") as template_file:
                template = json.load(template_file)
                name = template["name"]
                version = template["version"]
                description = template["description"]
                license = template["license"]
                scripts = template["scripts"]
                create_container(name, version, description, license, scripts)
                print(
                    f"{Fore.GREEN}✅ Container created from template.{Style.RESET_ALL}"
                )
                return
        except Exception as e:
            print(f"{Fore.RED}❌ Failed to load template: {e}{Style.RESET_ALL}")

    if defaults:
        name = "mycontainer"
        version = "1.0.0"
        description = ""
        license = "MIT"
        scripts = {
            "start": {
                "runtime": "python",
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
        runtime = (
            input(f"{Fore.MAGENTA}📦 Container runtime (python):{Style.RESET_ALL} ")
            or "python"
        )
        main = input(
            f"{Fore.MAGENTA}📦 Container main file ({"main.py" if runtime.lower() == "python" else "index.js"}):{Style.RESET_ALL} "
        ) or ("main.py" if runtime.lower() == "python" else "index.js")
        scripts = {"start": {"runtime": runtime, "main": main}}

    create_container(name, version, description, license, scripts)


def load_json(filepath):
    with open(filepath) as f:
        return json.load(f)


def extract_zip(zip_path, extract_path):
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_path)


if __name__ == "__main__":
    print("==============================================================")
    print(f"{Fore.CYAN}🟦 Daphene v{VERSION} 🟦{Style.RESET_ALL}")
    print("==============================================================")

    args = parse_arguments()

    if args.run:
        run(args.run)
    elif args.init:
        init_container(args.defaults, args.template)
    elif args.list:
        list_containers()
    else:
        print(f"{Fore.RED}❌ Please specify an argument(s)!{Style.RESET_ALL}")
