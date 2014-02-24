import sys
if sys.version_info < (3, 0):
    import ConfigParser as configparser
else:
    import configparser


def import_conf(path_to_file):
    config = configparser.RawConfigParser(allow_no_value=False)
    try:
        config.read(path_to_file)
        params = {}
        metrics = {}
        params["debugMode"] = config.get("Client", "Debug")
        ##
        ## Metrics
        ##
        metrics["cpu.usage"] = int(config.get("Metrics", "cpuUsage"))
        metrics["cpu.times"] = int(config.get("Metrics", "cpuTimes"))
        metrics["memory.usage"] = int(config.get("Metrics", "memoryUsage"))
        metrics["user.count"] = int(config.get("Metrics", "userCount"))
        metrics["swap.usage"] = int(config.get("Metrics", "swapUsage"))
        metrics["system.boot_time"] = int(config.get("Metrics",
                                                     "systemBootTime"))
        metrics["network"] = int(config.get("Metrics", "dataTraffic"))
        ##
        ## Params
        ##
        params["kvmCpuUsage"] = int(config.get("KVM", "cpuUsage"))
        params["kvmMemoryUsage"] = int(config.get("KVM", "memoryUsage"))
        params["kvmNetworkUsage"] = int(config.get("KVM", "networkUsage"))
    except configparser.NoSectionError:
        print("[ERROR] Config file contains error! "
              "Reason: Missing section.")
        raise
    except configparser.ParsingError:
        print("[ERROR] Config file contains error! "
              "Reason: Cannot parse.")
        raise
    except configparser.MissingSectionHeaderError:
        print("[ERROR] Config file contains error! "
              "Reason: Missing section-header.")
        raise

    return params, metrics
