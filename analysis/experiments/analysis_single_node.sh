#!/usr/bin/env bash
# run_stress_all.sh
#
# Script para ejecutar un conjunto exhaustivo de pruebas de rendimiento en single-node y multi-node para los middlewares: xmlrpc, redis, rabbitmq, pyro.
#
# Incluye:
#  1. Speed-up tests (service mode) variando número de peticiones.
#  2. Filter mode tests variando duración de envío continuo.
#  3. Multi-node static tests con distintos nodos y clientes.

set -euo pipefail

# Directorio de salida de CSV y gráficas
GRAPH_DIR=analysis/graphs
mkdir -p "$GRAPH_DIR"

# Lista de middlewares a probar
declare -a MW_LIST=(xmlrpc redis rabbitmq pyro)

# 1) Speed-up tests: service mode, distintos tamaños de carga
#    N valores: 500, 1k, 2k, 5k, 10k, 20k, 50k, 100k
declare -a N_VALUES=(500 1000 2000 5000 10000 20000 50000 100000)
for mw in "${MW_LIST[@]}"; do
  # CSV único por middleware para service speedup
csv_service="$GRAPH_DIR/single_service_${mw}.csv"
  # Cabecera CSV
  echo "n,threads,duration_s,ops_per_s" > "$csv_service"
  for n in "${N_VALUES[@]}"; do
    echo "[Speedup] mw=$mw, n=$n -> $csv_service"
    python3 single_node.py --mw "$mw" --mode service -n "$n" --csv "$csv_service"
  done
  echo
done

# 2) Filter mode tests: modo filter, duración continua de envío
#    Duraciones: 0.5s, 1s, 2s, 5s, 10s, 20s, 50s, 100s, 200s
declare -a DURATIONS=(0.5 1.0 2.0 5.0 10.0 20.0 50.0 100.0 200.0)
for mw in "${MW_LIST[@]}"; do
  csv_filter="$GRAPH_DIR/single_filter_${mw}.csv"
  echo "duration_s,ops_per_s" > "$csv_filter"
  for dur in "${DURATIONS[@]}"; do
    echo "[Filter] mw=$mw, duration=${dur}s -> $csv_filter"
    python3 single_node.py --mw "$mw" --mode filter --duration "$dur" --csv "$csv_filter"
  done
  echo
done

# 3) Multi-node static tests: servicio distribuido,
#    nodos 1,2,3,4,5 con clientes 5,10,20, peticiones totales 2000
declare -a NODES=(1 2 3 4 5)
declare -a CLIENTS=(5 10 20)
REQUESTS=2000
for mw in "${MW_LIST[@]}"; do
  for nodes in "${NODES[@]}"; do
    for clients in "${CLIENTS[@]}"; do
      csv_multi="$GRAPH_DIR/multi_${mw}_${nodes}nodes_${clients}clients.csv"
      echo "[Multi-node] mw=$mw, nodes=$nodes, clients=$clients -> $csv_multi"
      python3 analysis/experiments/multi_node_static.py \
        --mode service \
        --mw "$mw" \
        --nodes "$nodes" \
        --clients "$clients" \
        --requests "$REQUESTS" \
        --csv "$csv_multi"
    done
  done
  echo
done

echo "*** Todos los tests de rendimiento han finalizado. CSV generados en: $GRAPH_DIR ***"
