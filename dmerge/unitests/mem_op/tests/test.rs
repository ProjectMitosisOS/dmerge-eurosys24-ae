use kernel_module_testlib::{dmesg_contains, with_kernel_module};

#[test]
fn test_case() {
    // a dummy test func
    with_kernel_module(|| {
    });
}
