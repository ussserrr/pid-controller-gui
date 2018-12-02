"""
Controller-specific definitions and values
"""

# TODO: add me
# TODO: add logging maybe

pv_graph_min_max = (-2.0, 2.0)
co_graph_min_max = (-2.0, 2.0)

setpoint_fmt_str = '{:.3f}'

pv_str = 'Process variable'  # e.g. 'Voltage'
co_str = 'Controller output'  # e.g. 'Speed'

pv_measure_unit = 'V'  # will be converted using metric prefixes if needed
co_measure_unit = 'm/s'
