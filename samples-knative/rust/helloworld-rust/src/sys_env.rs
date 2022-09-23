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