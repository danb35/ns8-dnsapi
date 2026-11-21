#
# Copyright (C) 2026 Dan Brown
# SPDX-License-Identifier: GPL-3.0-or-later
#
# dnshelper from the actions (ns8-dnshelper README, "Using dnshelper from
# another module"; schemas read 2026-11-21 against dnshelper 0.7.0).
#
# - Grant: dnshelper@any:dnswriter. With more than one dnshelper, dnsapi uses
#   the first one discovery finds, by install order (DESIGN.md, open
#   question 7).
# - list-zones: {"zones": [{"zone", "credential", "provider", "access", "full"}]},
#   only the zones with a rule for this module. "full" is a write rule with
#   names "*" and types "*": the zones dnsapi may hand to tenants.
# - has-zone {"name"}: {"managed", "zone", "allowed", "access", "full"}.
# - Refusals come back as a validation failure, the list in "output":
#   [{"field", "parameter", "value", "error", "message"}].

import agent
import agent.tasks


class DnshelperError(Exception):
    def __init__(self, code, message=""):
        super().__init__(message or code)
        self.code = code
        self.message = message


def find_instance(rdb):
    """The agent id of the dnshelper to use, e.g. "module/dnshelper1", or None."""
    providers = agent.list_service_providers(rdb, "dnshelper") or []
    providers = sorted(providers, key=lambda p: (int(p.get("module_seq") or 0), p["module_id"]))
    return "module/" + providers[0]["module_id"] if providers else None


def call(target, action, data):
    response = agent.tasks.run(agent_id=target, action=action, data=data,
                               extra={"isNotificationHidden": True})
    if response["exit_code"] == 0:
        return response["output"]
    output = response.get("output")
    if isinstance(output, list) and output and isinstance(output[0], dict):
        raise DnshelperError(output[0].get("error", "unknown"), output[0].get("message", ""))
    raise DnshelperError("unavailable", "dnshelper did not answer")


def full_zones(target):
    """{zone: provider} for the zones dnsapi may write in full."""
    output = call(target, "list-zones", {})
    if not output or any("full" not in z for z in output.get("zones", [])):
        # dnshelper before 0.7.0 says nothing about how much a module may do.
        raise DnshelperError("dnshelper_too_old", "dnshelper 0.7.0 or later is required")
    return {z["zone"]: z.get("provider") for z in output["zones"] if z.get("full")}
