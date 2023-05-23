PY=~/cpython/python
LD=/home/lfm/libmalloc_wrapper.so
ADDR=
HEAP_SZ_HEX=1BA1
# BASE_HEX=100000000 TOTAL_SZ_HEX=40000000 LD_PRELOAD=/home/lfm/libmalloc_wrapper.so ~/cpython/python function.py

ppro:
	BASE_HEX=100000000 ${PY} function.py
pro:
	BASE_HEX=100000000 TOTAL_SZ_HEX=${HEAP_SZ_HEX} LD_PRELOAD=${LD} ${PY} function.py


# BASE_HEX=140000000 TOTAL_SZ_HEX=40000000 LD_PRELOAD=/home/lfm/libmalloc_wrapper.so ~/cpython/python merge.py --addr=4299386304 --connect
con-c:
	BASE_HEX=200000000 TOTAL_SZ_HEX=${HEAP_SZ_HEX} ${PY} merge.py --addr=${ADDR} --connect

con:
	BASE_HEX=200000000 TOTAL_SZ_HEX=${HEAP_SZ_HEX} ${PY} merge.py --addr=${ADDR}