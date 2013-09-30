from metrics import *

class collectables:

    __collectables = {
        "cpu.usage":                    [std.cpu.usage],
        "memory.usage":                 [std.memory.usage],
        "network.packages_sent":        [std.network.packages_sent],
        "network.packages_received":    [std.network.packages_received],
        "network.bytes_sent":           [std.network.bytes_sent],
        "network.bytes_received":       [std.network.bytes_received],
        "network":                      [std.network.bytes_sent,
                                        std.network.bytes_received,
                                        std.network.packages_sent,
                                        std.network.packages_received],
    }

    @staticmethod
    def list():
        return list(collectables.__collectables.keys())

    @staticmethod
    def keyToSet(key):
        return collectables.__collectables[key]

    @staticmethod
    def provide( requests = []):
        collectors = []
        for request in requests:
            for item in collectables.__collectables[request]:
                collectors.append(item.harvest)
        seen = set()
        seen_add = seen.add
        return [ x for x in collectors if x not in seen and not seen_add(x)]

    @staticmethod
    def provideAll():
        return collectables.provide(collectables.list())


