#!/bin/bash

set -euo pipefail

ROOT="$(pwd)"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMS="${SYSTEMS:-mysql postgres}"
N17="${N17:-1000000}"
export PGPASSWORD=pwd
export PYTHONPATH="${PROBLEM1:?set PROBLEM1 to the folder containing q1_fractal_symbols.py}"
PSQL=(psql -h 127.0.0.1 -U postgres -q -v ON_ERROR_STOP=1)
export MYSQL_PWD=pwd
MY=(mysql -h127.0.0.1 -uroot --local-infile=1)
BREW="$(brew --prefix 2>/dev/null || true)"
PATH="$BREW/opt/mysql-client/bin:$BREW/opt/libpq/bin:$PATH"

has() { [[ " $SYSTEMS " == *" $1 "* ]]; }
step() { printf '\n=== %s ===\n' "$*"; }

e111() {
  step "11.1: generate employees tables (10^3 and 10^4 rows, all columns unique)"
  local D="$ROOT/data_generation/employees"
  for n in 1000 10000; do
    [ -f "$D/employees_small_$n.csv" ] && continue
    (cd "$D" && echo $n | python3 employees_smalltable.py >/dev/null && mv employeesindex_small.csv employees_small_$n.csv)
  done

  step "11.1: load"
  local SCHEMA="CREATE TABLE employees (ssnum INT PRIMARY KEY, name VARCHAR(255), lat INT, longitude INT, hundreds1 INT, hundreds2 INT); CREATE INDEX nc ON employees(hundreds2);"
  for n in 1000 10000; do
    local db=employees_small_$n
    if has postgres; then
      "${PSQL[@]}" -c "DROP DATABASE IF EXISTS $db" -c "CREATE DATABASE $db"
      "${PSQL[@]}" -d $db -c "$SCHEMA" -c "\copy employees FROM '$D/employees_small_$n.csv' CSV HEADER" \
        -c "CLUSTER employees USING employees_pkey" -c "ANALYZE employees"
    fi
    if has mysql; then
      "${MY[@]}" -e "DROP DATABASE IF EXISTS $db; CREATE DATABASE $db"
      "${MY[@]}" $db -e "$SCHEMA LOAD DATA LOCAL INFILE '$D/employees_small_$n.csv' INTO TABLE employees FIELDS TERMINATED BY ',' IGNORE 1 LINES;"
    fi
  done

  step "11.1: run (clustered index vs no index; uniform, skewed over 5 rows, all on 1 row)"
  cd "$ROOT/scripts"
  rm -f results/*_index_small_update_*process.csv
  for S in $SYSTEMS; do
    local U=index_on_small_table/update/$S big=index_on_small_table/update/$S/big_10process.py
    [ $S = postgres ] && big=$U/big_10process.sh
    DB=employees_small_1000  CSV=$D/employees_small_1000.csv  TAG=uni_              python3 $U/small_2process.py
    DB=employees_small_1000  CSV=$D/employees_small_1000.csv  TAG=hot5_ HOT_KEYS=5 python3 $U/small_2process.py
    DB=employees_small_10000 CSV=$D/employees_small_10000.csv TAG=uni_              python3 $big
    DB=employees_small_10000 CSV=$D/employees_small_10000.csv TAG=hot5_ HOT_KEYS=5 python3 $big
    DB=employees_small_10000 CSV=$D/employees_small_10000.csv TAG=hot1_ HOT_KEYS=1 python3 $big
  done

  step "11.1: summary"
  python3 "$HERE/summarize_small_table.py" --setting uni_="Uniform keys" hot5_="Skewed: 5 hot rows" hot1_="All updates hit 1 row"
  cd "$ROOT"
}

e17() {
  local G="$ROOT/data_generation/store" exp=$(( ${#N17} - 1 ))
  step "17: generate store data (uniform 10^$exp, fractal 10^5) and the 1000-row insert file"
  cd "$G"
  [ -f orders_10_$exp.csv ] || echo $N17 | python3 outstanding_uniform.py >/dev/null
  [ -f order_fractal_10_5.csv ] || echo 100000 | python3 outstanding_fractal.py >/dev/null
  [ -f triggers_input.csv ] || python3 triggers_inserts.py >/dev/null
  sed -n '/^CREATE TABLE/,/);/p' outstanding_schema.txt | sed -E 's/(price|amount) int/\1 DECIMAL(12,2)/' > schema.sql

  step "17: load (unkeyed, keyed, fractal + keys + orders(vendorid) index)"
  local KEYS="ALTER TABLE vendorOutstanding ADD PRIMARY KEY (vendorid); ALTER TABLE storeOutstanding ADD PRIMARY KEY (storeid);"
  local VIDX="CREATE INDEX iv ON orders(vendorid);"
  local IIDX="CREATE INDEX i_item ON item(itemnum);"
  load() {  # db orders_csv suffix extra_sql
    if has postgres; then
      "${PSQL[@]}" -c "DROP DATABASE IF EXISTS $1" -c "CREATE DATABASE $1"
      "${PSQL[@]}" -d $1 -f schema.sql -c "\copy orders FROM '$2' CSV HEADER"
      for t in store item vendorOutstanding storeOutstanding; do
        "${PSQL[@]}" -d $1 -c "\copy $t FROM '${t}$3.csv' CSV HEADER"
      done
      "${PSQL[@]}" -d $1 -c "$4 ANALYZE;"
    fi
    if has mysql; then
      "${MY[@]}" -e "DROP DATABASE IF EXISTS $1; CREATE DATABASE $1"
      "${MY[@]}" $1 < schema.sql
      "${MY[@]}" $1 -e "LOAD DATA LOCAL INFILE '$2' INTO TABLE orders FIELDS TERMINATED BY ',' IGNORE 1 LINES"
      for t in store item vendorOutstanding storeOutstanding; do
        "${MY[@]}" $1 -e "LOAD DATA LOCAL INFILE '${t}$3.csv' INTO TABLE $t FIELDS TERMINATED BY ',' IGNORE 1 LINES"
      done
      if [ -n "$4" ]; then "${MY[@]}" $1 -e "$4"; fi
    fi
  }
  load store_plain orders_10_$exp.csv _10_$exp "$IIDX"
  load store_keyed orders_10_$exp.csv _10_$exp "$KEYS $IIDX"
  load store_f5 order_fractal_10_5.csv _fractal_10_5 "$KEYS $VIDX $IIDX"

  local HOT MED
  HOT=$(tail -n +2 order_fractal_10_5.csv | cut -d, -f5 | sort | uniq -c | sort -k1,1nr -k2,2n | head -1 | awk '{print $2}')
  MED=$(tail -n +2 order_fractal_10_5.csv | cut -d, -f5 | sort | uniq -c | sort -k1,1n -k2,2n | awk '{a[NR]=$2} END{print a[int((NR+1)/2)]}')
  echo "hot vendor: $HOT, median vendor: $MED"

  step "17: run (with vs without trigger; keyed vs unkeyed; hot vs median vendor)"
  cd "$ROOT/scripts"
  rm -f results/*_aggregate_triggers_*.csv
  export REPEAT="${REPEAT:-50}" INS="$G/triggers_input.csv"
  for S in $SYSTEMS; do
    local R="Aggregate_Maintenance_triggers /$S/run_$S.sh"
    DB=store_keyed TAG=keyed_  bash "$R"
    DB=store_plain TAG=plain_  bash "$R"
    DB=store_f5    TAG=hot_    VENDOR=$HOT bash "$R"
    DB=store_f5    TAG=median_ VENDOR=$MED bash "$R"
  done

  step "17: summary (1000 inserts + 20 vendor queries)"
  python3 "$HERE/summarize_triggers.py" --ratio 50 \
    --setting keyed_='$10^6$ orders, uniform vendors\nsummary table keyed on vendorid' plain_='$10^6$ orders, uniform vendors\nsummary table without a key' \
    --setting hot_='$10^5$ orders, skewed vendors\nquery the busiest vendor' median_='$10^5$ orders, skewed vendors\nquery a typical (median) vendor'
  cd "$ROOT"
}

case "${1:-all}" in
  e111) e111 ;;
  e17)  e17 ;;
  all)  e111; e17 ;;
  *) echo "usage: bash run_q2.sh [e111|e17|all]"; exit 1 ;;
esac
step "done: tables and plots are in scripts/"
