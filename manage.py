import sys
from src import cnfparse, client, collectables


def main():
	if len(sys.argv) < 2:
		print("usage: manage.py run [options]")

	if len(sys.argv) is not 2 and sys.argv[1] is not "run":
		print("[ERROR] Command cannot be parsed. Exiting...")
		return

	configuration, metrics = cnfparse.importConf("config/client.conf")
	cli = client.Client(configuration)
	cli.startReporting(metricCollectors=
	collectables.collectables.provide(metrics))


if __name__ == "__main__":
	main()
