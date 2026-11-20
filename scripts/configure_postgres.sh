#!/bin/bash
TIMEFORMAT='%R %U %S'
PGUSER="postgres"
PGDATABASE="$1"
PGHOST="localhost"
PGPORT=5432
QUERY="$2"
echo "PG QUERY STARTED"
   { time psql \
      -U "$PGUSER" \
      -h "$PGHOST" \
      -p "$PGPORT" \
      -d "$PGDATABASE" \
      -c "$QUERY"; } ;

echo "PG QUERY DONE"
