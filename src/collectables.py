from metrics import *

class collectables:

    __collectables = {
        std.cpu.usage.name:                     [std.cpu.usage],
        std.memory.usage.name:                  [std.memory.usage],
        std.user.count.name:                    [std.user.count],
        std.network.packages_sent.name:         [std.network.packages_sent],
        std.network.packages_received.name:     [std.network.packages_received],
        std.network.bytes_sent.name:            [std.network.bytes_sent],
        std.network.bytes_received.name:        [std.network.bytes_received],
        "network":                              [std.network.bytes_sent,
                                                std.network.bytes_received,
                                                std.network.packages_sent,
                                                std.network.packages_received],
    }

    @staticmethod
    def listKeys():
        return list(collectables.__collectables.keys())

    @staticmethod
    def listMetricsToKey(key):
        return collectables.__collectables[key]

    @staticmethod
    def listMetricsNameToKey(key):
        return [x.name for x in collectables.__collectables[key]]

    @staticmethod
    def provide(requests = []):
        valid_keys = collectables.listKeys()
        reqs = [request for request, value in requests.items() if value=="True"]
        collectors = []
        for request in reqs:
            for item in collectables.__collectables[request]:
                collectors.append(item.harvest)
        seen = set()
        seen_add = seen.add
        return [ x for x in collectors if x not in seen and not seen_add(x)]

    @staticmethod
    def provideAll():
        return collectables.provide(collectables.listKeys())


