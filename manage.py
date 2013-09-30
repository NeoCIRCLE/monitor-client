import sys
from src import cnfparse

def main():

    if (len(sys.argv)<2):
        print("usage: manage.py run [options]")
        print("""
        options:
        --config <path> : path to the configuration file you intend
        to start the client with
        --debug : enables the debug mode and writes metrics sent to the
        server
        """)

    if (len(sys.argv)==2 and sys.argv[1]=="run"):
        configuration = cnfparse.importConf("config/client.conf")



if __name__ == "__main__":
    main()
