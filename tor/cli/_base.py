import argparse
import sys


class MyParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write(f"ERROR: {message}\n\n")
        self.print_help()
        sys.exit(2)
