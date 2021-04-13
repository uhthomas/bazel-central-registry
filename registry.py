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

from pathlib import Path
import json
import shutil
import yaml

class Module(object):
    
    def __init__(self, name = None, version = None, compatibility_level = 1):
        self.name = name
        self.version = version
        self.compatibility_level = compatibility_level
        self.module_dot_bazel = None
        self.deps = []
        self.patches = []
        self.presubmit_yml = None
        self.build_targets = []
        self.test_targets = []
        
    def add_dep(self, module_name, version):
        self.deps.append((module_name, version))
        return self
    
    def set_module_dot_bazel(self, module_dot_bazel):
        self.module_dot_bazel = module_dot_bazel
        
    def set_source(self, url, integrity, strip_prefix = None):
        self.url = url
        self.integrity = integrity
        self.strip_prefix = strip_prefix
        return self
    
    def add_patch(self, patch_file):
        self.patches.append(patch_file)
        return self
    
    def set_presubmit_yml(self, presubmit_yml):
        self.presubmit_yml = presubmit_yml
        return self
        
    def add_build_target(self, target):
        self.build_targets.append(target)
        return self
        
    def add_test_targets(self, target):
        self.test_targets.append(target)
        return self
    
    def dump(self, file):
        with open(file, "w") as f:
            json.dump(self.__dict__, f, indent=4, sort_keys=True)
            
    def from_json(self, file):
        with open(file) as f:
            self.__dict__ = json.load(f)
        
    
class RegistryModifyException(Exception):
    """
    Raised whenever something goes wrong with modifying the registry.
    """
    pass

class RegistryClient(object):
    
    _MODULE_BAZEL = """
module(
    name = "{0}",
    version = "{1}",
    compatibility_level = "{2}",
)

{3}
""".strip()
    
    def __init__(self, root):
        self.root = Path(root)
    
    def contains(self, module_name, version = None):
        """
        Check if the registry contains a module or a specific version of a 
        module
        """
        p = self.root.joinpath("modules", module_name)
        if version:
            p = p.joinpath(version)
        return p.is_dir()
    
    def init_module(self, module_name, maintainers, homepage):
        """
        Initialize a module, create the directory and metadata.json file.

        Parameters
        ----------
        module_name : str
            The module name
        maintainers : list of maps of string -> string
            The maintainer information, eg
             [{"name": "John Cater", "email": "jcater@google.com"},
              {"name": "Yun Peng", "github": "meteorcloudy"}]
        homepage : str
            A URL to the project's homepage

        """
        p = self.root.joinpath("modules", module_name)
        p.mkdir()

        # Create metadata.json file
        metadata = {
          "maintainers": maintainers,
          "homepage": homepage,
          "versions": [],
          "yanked_versions": {},
        }
        with p.joinpath("metadata.json").open("w") as f:
            json.dump(metadata, f, indent=4, sort_keys=True)
            
        # Add new module to module_list file
        module_list = self.root.joinpath("module_list")
        modules = module_list.open().readlines()
        modules.append(module_name + "\n")
        modules.sort()
        module_list.open("w").writelines(modules)
    
    def add(self, module):
        """
        Add a new module version, the module must be already initialized

        Parameters
        ----------
        module_name : Module
            A Module instance containing information of the module version to 
            be added
        """
        if self.contains(module.name, module.version):
            raise RegistryModifyException(
                f"Version {module.version} for module {module.name} already exists.")
        
        p = self.root.joinpath("modules", module.name, module.version)
        p.mkdir()
        
        # Create MODULE.bazel
        module_dot_bazel = p.joinpath("MODULE.bazel")
        if module.module_dot_bazel:
            shutil.copy(module.module_dot_bazel, module_dot_bazel)
        else:
            deps = "\n".join(
                f"bazel_dep(name = \"{name}\", version = \"{version}\")" 
                for name, version in module.deps)
            with module_dot_bazel.open("w") as f:
                f.write(self._MODULE_BAZEL.format(
                    module.name, module.version, 
                    module.compatibility_level, deps))
                
        # Create source.json & copy patch files
        source = {
          "url": module.url,
          "integrity": module.integrity,
        }
        if module.strip_prefix:
            source["strip_prefix"] = module.strip_prefix
        if module.patches:
            patch_dir = p.joinpath("patches")
            patch_dir.mkdir()
            source["patches"] = []
            for s in module.patches:
                patch = Path(s)
                source["patches"].append(patch.name)
                shutil.copy(patch, patch_dir)
        source_json = p.joinpath("source.json")
        with source_json.open("w") as f:
            json.dump(source, f, indent=4, sort_keys=True)
        
        # Create presubmit.yml file
        presubmit_yml = p.joinpath("presubmit.yml")
        if module.presubmit_yml:
            shutil.copy(module.presubmit_yml, presubmit_yml)
        else:
            platforms = {
              "linux": {},
              "macos": {},
              "windows": {},
            }
            for key in platforms:
                if module.build_targets:
                    platforms[key]["build_targets"] = module.build_targets.copy()
                if module.test_targets:
                    platforms[key]["test_targets"] = module.test_targets.copy()           
            with presubmit_yml.open("w") as f:
                yaml.dump({"platforms": platforms}, f)
            
        # Add new version to metadata.json
        metadata_path = self.root.joinpath("modules", module.name, 
                                           "metadata.json")    
        metadata = json.load(metadata_path.open())
        metadata["versions"].append(module.version)
        metadata["versions"].sort()
        with metadata_path.open("w") as f:
            json.dump(metadata, f, indent=4, sort_keys=True)
    
    def delete(self, module_name, version):
        """
        Delete an existing module version

        """
        p = self.root.joinpath("modules", module_name)
        shutil.rmtree(p.joinpath(version))
        metadata_path = p.joinpath("metadata.json")
        metadata = json.load(metadata_path.open())
        metadata["versions"].remove(version)
        with metadata_path.open("w") as f:
            json.dump(metadata, f, indent=4, sort_keys=True)
    
