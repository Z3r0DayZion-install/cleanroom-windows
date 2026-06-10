#!/usr/bin/env python3
from enable_telemetry import main
import sys
if __name__ == '__main__':
    rc = main(enable=False)
    sys.exit(rc)
