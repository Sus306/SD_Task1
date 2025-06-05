RECORDAR: tener el framework encendido en otra terminal.

cd SD_Task1/analysis/experiments

Para el speedup:

python3 single_node.py --mw xmlrpc  -n 1000 --csv ../graphs/single_service_xmlrpc.csv

Para el resto de 

python3 single_node.py --mw redis  --duration 1.0 --csv ../graphs/single_filter_redis.csv 

multi-node estatico:
cd analysis/experiments
python3 multi_node_static.py \
  --mode service \
  --mw xmlrpc \
  --nodes 3 \
  --clients 5 \
  --requests 2000 \
  --csv resultados_xmlrpc.csv

