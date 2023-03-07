### Python demo for dmerge

1. You shall firstly build the pyx bindings from project root path `${PROJECT_PATH}/pyx`.
You can directly use `make bindgen` to generate the result.
2. Copy the generated `*.so` (e.g. `bindings.cpython-37dm-x86_64-linux-gnu.so`) files into the same path as what your python file in.
3. Please make sure the dynlib-wrappers has been correctly installed (in `${PROJECT_PATH}/deps/dynlib-wrappers`)

#### Structure
- `fucntion.py`: The producer of the data
- `merge.py`: The consumer of the data