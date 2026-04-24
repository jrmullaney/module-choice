#!/bin/bash
set -e

INPUT=Data/Input
PROCESSED=Data/Processed

python3 prefix_codes.py $INPUT/AY23-24.txt $PROCESSED/AY23-24.flat.tsv
python3 prefix_codes.py $INPUT/AY24-25.txt $PROCESSED/AY24-25.flat.tsv
python3 prefix_codes.py $INPUT/AY25-26.txt $PROCESSED/AY25-26.flat.tsv --prefix MPS

python3 make_matrix.py $PROCESSED/AY23-24.flat.tsv $PROCESSED/AY23-24_processed.txt

python3 merge_year.py $PROCESSED/AY23-24_processed.txt $PROCESSED/AY24-25.flat.tsv $PROCESSED/AY24-25_processed.txt
python3 recode_modules.py $PROCESSED/AY24-25_processed.txt module_lookup.txt $PROCESSED/AY24-25_recoded.txt
python3 merge_year.py $PROCESSED/AY24-25_recoded.txt $PROCESSED/AY25-26.flat.tsv $PROCESSED/AY25-26_processed.txt
