#!/bin/bash
EXCLUDED_TABLES=(
core_url_rewrite
dataflow_batch_export
dataflow_batch_import
index_process_event
log_customer
log_quote
log_summary
log_summary_type
log_url
log_url_info
log_visitor
log_visitor_info
log_visitor_online
report_event   
)

read -p "Host: " HOST
if [[ "$HOST" == "" ]]; then 
 HOST=localhost
fi

read -p "Username: " USER


read -p "Password: " PASSWORD

read -p "Database: " DATABASE

read -p "Prefix: " PREFIX

read -p "File name export: " DB_FILE
if [[ "$DB_FILE" == "" ]]; then 
 DB_FILE=export_db.sql
fi

IGNORED_TABLES_STRING=''
for TABLE in "${EXCLUDED_TABLES[@]}"
do :
   IGNORED_TABLES_STRING+=" --ignore-table=${DATABASE}.${PREFIX}${TABLE}"
done


echo "Dump structure"
mysqldump --host=${HOST} --user=${USER} --password=${PASSWORD} --single-transaction --no-data ${DATABASE} > ${DB_FILE}

echo "Dump content"
mysqldump --host=${HOST} --user=${USER} --password=${PASSWORD} ${DATABASE} --no-create-info ${IGNORED_TABLES_STRING} >> ${DB_FILE}

