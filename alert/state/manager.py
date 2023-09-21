from deepdiff import DeepDiff
from pprint import pprint, pformat

from . import stderr, stdout

from typing import List, Dict, Literal
from state.commands import GetLocalCommand, GetRemoteCommand, PostCommand, UpdateCommand, DeleteCommand, AlertMonitor, Monitor


class MonitorStateManager:
    updates = 0

    def __init__(self, dir, project_name) -> None:
        self.local = None
        self.remote = None
        self.queue: List = []
        self.project: str = dir
        self.project_name = project_name
        self.rate_limit: Literal[60] = 60 
    
    @property
    def has_remotes(self):
        if self.local is None or self.remote is None:
            stderr("Run GetLocalCommand and GetRemoteCommand before calling")
            raise Exception("Run GetLocalCommand and GetRemoteCommand before calling")
        
        if len(self.remote) < 1:
            return False
        return True

    @property
    def has_locals(self):
        if self.local is None or self.remote is None:
            stderr("Run GetLocalCommand and GetRemoteCommand before calling")
            raise Exception("Run GetLocalCommand and GetRemoteCommand before calling")
        
        if len(self.local) < 1:
            return False
        return True

    def create_monitor_map(self, monitor_list) -> Dict:
        monitor_map = {}
        for monitor in monitor_list:
            id = monitor.get("name")
            monitor_map[id] = monitor
        return monitor_map

    def monitor_diff(self, local: AlertMonitor, remote: Monitor):        
        built_local = {
            "message": local.get("message"),
            "name": local.get("name"),
            # "options": dict(local.get("options", {}).get("_data_store", {})),  # TODO these are tricky to work with dynamically
            "priority": local.get("priority"),
            "query": local.get("query"),
            "tags": local.get("tags"),
            "type": str(local.get("type"))
        }


        built_remote = {
            "message": remote.get("message"),
            "name": remote.get("name"),
            # "options": dict(remote.get("options", {}).get("_data_store", {})),  # TODO these are tricky to work with dynamically
            "priority": remote.get("priority"),
            "query": remote.get("query"),
            "tags": remote.get("tags"),
            "type": str(remote.get("type"))
        }
        diff = DeepDiff(dict(built_remote), dict(built_local), ignore_order=True)
        if diff == {}:
            return False
        else:
            stdout("Change detected:", pformat(DeepDiff(dict(built_remote), dict(built_local), ignore_order=True), indent=2))
            return True

    def run(self):
        local_monitor_map = {}
        remote_monitor_map = {}
        # we start by getting state of local and remote
        self.local = GetLocalCommand().execute(project=self.project, project_name=self.project_name)
        self.remote = GetRemoteCommand().execute(project_name=self.project_name)

        stdout(f"Found {len(self.local)} local monitors")
        if self.local:
            local_monitor_map = self.create_monitor_map(self.local)
            stdout("", "→ "+"\n→ ".join(list(local_monitor_map.keys())), "")

        stdout(f"Found {len(self.remote)} remote monitors")
        if self.remote:
            remote_monitor_map = self.create_monitor_map(self.remote)
            stdout("", "→ "+"\n→ ".join(list(remote_monitor_map.keys())), "")

        if not self.has_remotes and self.has_locals:
            # no remotes exist and we have locals to create
            for local_monitor in self.local:
                PostCommand().execute(body=local_monitor)
                self.updates += 1

        elif self.has_remotes and self.has_locals:
            for local_monitor in self.local:
                if remote_monitor_map.get(local_monitor.name):
                    # we have a matching remote
                    # diff the two to see if we need to PUT a change
                    rm = remote_monitor_map.get(local_monitor.name)
                    changed = self.monitor_diff(local=local_monitor, remote=rm)
                    if changed:
                        stdout("Found Monitor change:", local_monitor.name)
                        UpdateCommand().execute(id=rm.get("id"), name=local_monitor.get("name"), body=local_monitor)
                        self.updates += 1
                else:
                    # we don't have this monitor remotely, so we need to post it
                    stdout("Found new Monitor:", local_monitor.name)
                    PostCommand().execute(body=local_monitor)
                    self.updates += 1
            
            for remote_monitor in self.remote:
                if not local_monitor_map.get(remote_monitor["name"]):
                    # we have removed this monitor, so need to delete
                    stdout("Monitor has been removed:")
                    DeleteCommand().execute(id=remote_monitor["id"], name=remote_monitor["name"])
                    self.updates += 1

        elif not self.has_remotes and not self.has_locals:
            stdout("Completed. No remotes to manage, and no locals to push.")

        stdout(f"Monitor checks complete. {self.updates} updates performed.")