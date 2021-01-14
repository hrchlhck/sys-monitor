from ..monitor import Monitor
from ..collector import Collector
from ..spark_monitor import SparkMonitor
from ..merge import merge
import argparse

__all__ = ["args", "get_system", "merge"]

def get_system(sys_type, args):
    if args.host and args.port:
        if sys_type == 'collector':
            return Collector(args.host, int(args.port))
        elif sys_type == 'monitor':
            return Monitor(args.host, int(args.port), verbose=True)
    elif not args.port:
        print("Missing --port/-p PORT")
    elif not args.host:
        print("Missing --host/-H IP")

parser = argparse.ArgumentParser(description='sys-monitor commands')

parser.add_argument('-t', '--type', help='Functionality of sys-monitor. E.g. collector, monitor, merge...')
parser.add_argument('-H', '--host', help='Host that any of sys-monitor functions will be connecting', metavar='IP')
parser.add_argument('-p', '--port', help='Port of the host')
parser.add_argument('-f', '--files', nargs=2, help='Files for merge', metavar=('FILE1', 'FILE2'))
parser.add_argument('-mn', '--monitors',  default=3, help='Number of monitors that `collector` will be collecting data. By default, it`s 3')

args = parser.parse_args()