#!/usr/bin/env python3
#
# Copyright 2021 The Bazel Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from registry import Module
from registry import RegistryClient

from colorama import Fore, Style
import argparse
import sys
import time

def log(msg):
    print(f"{Fore.GREEN}INFO: {Style.RESET_ALL}{msg}")

def log_warning(msg):
    print(f"{Fore.YELLOW}INFO: {Style.RESET_ALL}{msg}")

def yes_or_no(question, default):
    if default:
        question += " [Y/n]: "
    else:
        question += " [y/N]: "
        
    var = None
    while var is None:
        user_input = input(question).strip().lower()
        if user_input == "y":
            var = True
        elif user_input == "n":
            var = False
        elif not user_input:
            var = default
        else:
          print("Invalid selection: {}".format(user_input))
    return var

def fromUserInput():
    name = input("Please enter the module name: ")
    version = input("Please enter the module version: ")
    compatibility = input("Please enter the compatibility level [default is 1]: ") or "1"
    module = Module(name, version, compatibility)
    
    url = input("Please enter the URL of the source archive: ")
    integrity = input("Please enter the integrity value of the archive: ")
    strip_prefix = input("Please enter the strip_prefix value of the archive [default None]: ") or None
    module.set_source(url, integrity, strip_prefix)
    
    ans = yes_or_no("Do you want to add patch files?", False)
    if ans:
        patches = input("Please input patch file paths, separated by `,`: ")
        for patch in patches.strip().split(","):
            module.add_patch(patch.strip())

    ans = yes_or_no("Do you want to specify a MODULE.bazel file?", False)
    if ans:
        path = input("Please enter the MODULE.bazel file path: ").strip()
        module.set_module_dot_bazel(path)
    else:
        ans = yes_or_no("Do you want to specify dependencies for this module?", False)
        if ans:
            deps = input("Please input dependencies in the form of <name>:<version>, separated by `,`: ")
            for dep in deps.strip().split(","):
                name, version = dep.split(":")
                module.add_dep(name, version)
    
    ans = yes_or_no("Do you wan to specify a presubmit.yml file", False)
    if ans:
        path = input("Please enter the presubmit.yml file path: ").strip()
        module.set_presubmit_yml(path)
    else:
        first = True
        while not (module.build_targets or module.test_targets):
            if not first:
                print("Build targets and test targets cannot both be empty, please re-enter!")
            first = False
            build_targets = input("Please enter a list of build targets for this module, separated by `,`: ")
            for target in build_targets.strip().split(","):
                module.add_build_target(target)
            test_targets = input("Please enter a list of test targets for this module, separated by `,`: ")
            for target in test_targets.strip().split(","):
                module.add_test_targets(target)
    return module
        
def get_maintainers_from_input():
    maintainers = []
    while True:
        maintainer = {}
        name = input("Please enter maintainer name: ")
        maintainer["name"] = name
        email = input("Please enter the maintainer's email address: ")
        maintainer["email"] = email
        username = input("(Optional) Please enter the maintainer's github username: ")
        if username:
            maintainer["github"] = username
        maintainers.append(maintainer)
        ans = yes_or_no("Do you want to add another maintainer?", True)
        if not ans:
            break
    return maintainers
         

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str)

    args = parser.parse_args(argv)

    if args.input:
        log(f"Getting module information from {args.input}...")
        module = Module()
        module.from_json(args.input)
    else:
        log("Getting module information from user input...")
        module = fromUserInput()
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        log(f"Saving module information to {module.name}.{timestamp}.json")
        log(f"You can use it via --input={module.name}.{timestamp}.json")
        module.dump(f"{module.name}.{timestamp}.json")

    client = RegistryClient(".")
    
    if not client.contains(module.name, module.version):
        log(f"{module.name} is a new Bazel module...")
        homepage = input("Please enter the homepage url for this module: ").strip()
        maintainers = get_maintainers_from_input()
        client.init_module(module.name, maintainers, homepage)
    
    client.add(module)
    log(f"{module.name} {module.version} is added into the registry.")
    

if __name__ == "__main__":
    sys.exit(main())
