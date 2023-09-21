import json
import glob
import time

from . import stderr, stdout

from abc import ABC, abstractmethod

from typing import List

from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api.monitors_api import MonitorsApi, Monitor, MonitorUpdateRequest

def create_client():
    configuration = Configuration()
    # TODO move to env variables
    configuration.api_key["apiKeyAuth"] = ""
    configuration.api_key["appKeyAuth"] = ""
    configuration.server_variables["site"] = "datadoghq.eu"
    configuration.debug = False
    return ApiClient(configuration)


class AlertMonitor(Monitor):

    def __init__(self, **kwargs):
        new_kwargs = kwargs
        new_kwargs["tags"].append(kwargs.pop("project_name"))
        super().__init__(**new_kwargs)


class Command(ABC):
    @abstractmethod
    def execute(**kwargs):
        ...


class GetRemoteCommand(Command):

    def execute(self, **kwargs):
        api_client = create_client()
        project_name = kwargs["project_name"]

        with api_client as client:
            api_instance = MonitorsApi(client)
            stdout(f"Searching remote for project: {project_name}")
            response = api_instance.list_monitors()
            return [i["_data_store"] for i in response if project_name in i["_data_store"].get("tags")]
        

class GetLocalCommand(Command):
    notify = "@webhook-GardenerChat @all"

    def execute(self, **kwargs):
        stdout(f"Searching folder '{kwargs['project']}'")
        files: List[str] = glob.glob(f"{kwargs['project']}/*.json")
        stdout("found files:", files)
        alerts_list: List = []

        for file in files:
            with open(file) as f:
                loaded_file = json.load(f)
                loaded_file["project_name"] = kwargs["project_name"]
                # business logic - forcefully add notifications
                loaded_file["message"] = f"{loaded_file.get('message', '')} {self.notify}"

                if loaded_file.get("options"):
                    if loaded_file.get("options", {}).get("escalation_message"):
                        loaded_file["options"]["escalation_message"] = f"{loaded_file['options']['escalation_message']} {self.notify}"

                alerts_list.append(
                    AlertMonitor(**loaded_file)
                )
            f.close()
        return alerts_list


class PostCommand(Command):
    retry_count = 0
    max_retry = 3
    rate_limit = 60

    def execute(self, **kwargs):
        client = create_client()
        with client as api_client:
            api_instance = MonitorsApi(api_client)
            body = Monitor(**kwargs['body']['_data_store'])
            try:
                response = api_instance.create_monitor(body=body)
                stdout("Successfully added monitor:", kwargs["body"]["_data_store"]["name"])
            except Exception as exc:
                for err in exc.body.get("errors", []):
                    stderr(err)
                if exc.status == 429:
                    if self.retry_count < self.max_retry:
                        self.retry_count += 1
                        stderr(f"Failed; possible rate limit. Waiting {self.rate_limit}s and retrying")
                        time.sleep(PostCommand.rate_limit)
                        stderr("Retrying...")
                        self.execute(body=kwargs['body'])
                    else:
                        stderr(f"Retried {self.max_retry} times. Aborting.")




class DeleteCommand(Command):
    retry_count = 0
    max_retry = 3
    rate_limit = 60

    def execute(self, **kwargs):
        client = create_client()
        with client as api_client:
            api_instance = MonitorsApi(api_client)
            try:
                response = api_instance.delete_monitor(monitor_id=kwargs["id"])
                stdout("Successfully removed monitor:", kwargs["name"])
            except Exception as exc:
                for err in exc.body.get("errors", []):
                    stderr(err)
                if exc.status == 429:
                    if self.retry_count < self.max_retry:
                        self.retry_count += 1
                        stderr(f"Failed; possible rate limit. Waiting {self.rate_limit}s and retrying")
                        time.sleep(DeleteCommand.rate_limit)
                        stderr("Retrying...")
                        self.execute(body=kwargs['body'])
                    else:
                        stderr(f"Retried {self.max_retry} times. Aborting.")


class UpdateCommand(Command):
    retry_count = 0
    max_retry = 3
    rate_limit = 60

    def execute(self, **kwargs):
        client = create_client()
        with client as api_client:
            api_instance = MonitorsApi(api_client)
            try:
                response = api_instance.update_monitor(monitor_id=kwargs["id"], body=MonitorUpdateRequest(**kwargs["body"]["_data_store"]))
                stdout("Successfully updated monitor:", kwargs["name"])
            except Exception as exc:
                for err in exc.body.get("errors", []):
                    stderr(err)
                if exc.status == 429:
                    if self.retry_count < self.max_retry:
                        self.retry_count += 1
                        stderr(f"Failed; possible rate limit. Waiting {self.rate_limit}s and retrying")
                        time.sleep(DeleteCommand.rate_limit)
                        stderr("Retrying...")
                        self.execute(body=kwargs['body'])
                    else:
                        stderr(f"Retried {self.max_retry} times. Aborting.")