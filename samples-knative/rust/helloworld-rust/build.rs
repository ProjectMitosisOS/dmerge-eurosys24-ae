extern crate bindgen;
extern crate cc;

use std::env;
use std::path::PathBuf;

const INCLUDED_TYPES: &[&str] = &[
    "connect_req_t"
];
const INCLUDED_FUNCS: &[&str] = &[
    "create_heap",
    "sopen",
    "call_register",
    "call_pull",
    "call_connect_session",
];

#[inline]
fn proto_gen() {
    protobuf_codegen::Codegen::new()
        .cargo_out_dir("protos")
        .include("src")
        .input("src/protos/example.proto")
        .run_from_script();
}

fn main() {
    proto_gen();
    let lib_path =
        PathBuf::from(env::current_dir().unwrap().join("target"));

    println!("cargo:rustc-link-search={}", lib_path.display());
    println!("cargo:rustc-link-lib=static=wrapper");
    println!("cargo:rerun-if-changed=src/native/wrapper.h");
    let mut builder = bindgen::Builder::default()
        .header("src/native/wrapper.h");

    for t in INCLUDED_TYPES {
        builder = builder.whitelist_type(t);
    }
    for f in INCLUDED_FUNCS {
        builder = builder.whitelist_function(f);
    }

    let bindings = builder
        .generate()
        .expect("unable to generate bindings");

    let out_path = PathBuf::from(env::var("OUT_DIR").unwrap());
    bindings.write_to_file(out_path.join("bindings.rs"))
        .expect("couldn't write bindings!");
}