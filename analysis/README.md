cd SD_Task1/analysis/experiments

Para el speedup:

python3 single_node.py --mode service --mw xmlrpc  -n 1000 --csv ../graphs/single_service_xmlrpc.csv

python3 single_node.py --mode filter  --mw redis   -n 2000 --csv ../graphs/single_filter_redis.csv

Para el resto de 

python3 single_node.py --mode service  --mw redis   --duration 1.0 --csv ../graphs/single_filter_redis.csv 

python3 single_node.py --mode filter  --mw redis   --duration 1.0 --csv ../graphs/single_filter_redis.csv 