use std::env;

/// Env consts
pub(crate) const CE_TYPE_ENV_KEY: &str = "CeType";
pub(crate) const NAME_SPACE_ENV_KEY: &str = "NameSpace";
pub(crate) const SERVICE_NAME_ENV_KEY: &str = "ServiceName";
pub(crate) const REVISION_ENV_KEY: &str = "Revision";

#[inline]
pub(crate) fn fetch_env(key: &str, default: &str) -> String {
    match env::var(key) {
        Ok(env_val) => env_val,
        _ => default.to_string()
    }
}

#[inline]
pub(crate) fn server_port() -> String {
    match env::var("PORT") {
        Ok(env_val) => env_val,
        _ => "8080".to_string()
    }
}

pub(crate) fn hex_str_to_val(s: &String) -> u64 {
    use std::i64;
    i64::from_str_radix(s.trim_start_matches("0x"), 16).expect("not valid hex string") as u64
}

#[inline]
pub(crate) fn heap_base() -> u64 {
    use std::i64;
    match env::var("HEAP_BASE_HEX") {
        Ok(base_addr_str) => {
            hex_str_to_val(&base_addr_str)
        }
        _ => crate::DEFAULT_HEAP_BASE_ADDR
    }
}

#[inline]
pub(crate) fn heap_hint() -> usize {
    match env::var("HEAP_HINT") {
        Ok(env_val) => {
            match env_val.parse::<usize>() {
                Ok(val) => val,
                _ => 73
            }
        }
        _ => 73
    }
}