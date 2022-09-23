// use actix_web::{error, web};
// use futures::StreamExt;
//
// const MAX_SIZE: usize = 262_144;

// pub async fn DeserilizeBody<'a, T: Clone>(mut payload: web::Payload)
//                                           -> Result<T, actix_web::Error>
//     where T: serde::Deserialize<'a> {
//     let mut body = web::BytesMut::new();
//     while let Some(chunk) = payload.next().await {
//         let chunk = chunk?;
//         // limit max size of in-memory payload
//         if (body.len() + chunk.len()) > MAX_SIZE {
//             return Err(error::ErrorBadRequest("overflow"));
//         }
//         body.extend_from_slice(&chunk);
//     }
//
//     // body is loaded, now we can deserialize serde-json
//     let obj = serde_json::from_slice::<T>(&body)?;
//     Ok(obj.clone())
// }