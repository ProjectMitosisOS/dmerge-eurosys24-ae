use crate::rpc_service::rpc_handlers::HeapDescriptorQueryReply;
use mitosis::os_network::rpc::Caller;
use mitosis::os_network::rpc::impls::ud::UDSession;
use mitosis::os_network::ud_receiver::UDReceiver;
use mitosis::os_network;
use mitosis::os_network::timeout::TimeoutWRef;
use mitosis::os_network::Conn;
use mitosis::KRdmaKit::rust_kernel_rdma_base::bindings::*;
use os_network::msg::UDMsg as RMemory;
use os_network::block_on;
use core::pin::Pin;

pub(crate) type UDCaller<'a> = Caller<UDReceiver<'a>, UDSession<'a>>;
pub(crate) type DCReqPayload = os_network::rdma::payload::Payload<ib_dc_wr>;
pub const TIMEOUT_USEC: i64 = 1000_000; // 1s

#[inline]
pub(crate) fn remote_descriptor_fetch(
    d: HeapDescriptorQueryReply,
    caller: &mut UDCaller<'static>,
    session_id: usize,
) -> Result<RMemory, <os_network::rdma::dc::DCConn<'static> as Conn>::IOResult> {

    let descriptor_buf = RMemory::new(d.sz, 0);
    let point = caller.get_ss(session_id).unwrap().0.get_ss_meta();

    let pool_idx = unsafe { mitosis::bindings::pmem_get_current_cpu() } as usize;
    let (dc_qp, lkey) = unsafe { mitosis::get_dc_pool_service_mut().get_dc_qp_key(pool_idx) }
        .expect("failed to get DCQP");

    let mut payload = DCReqPayload::default()
        .set_laddr(descriptor_buf.get_pa())
        .set_raddr(d.pa) // copy from src into dst
        .set_sz(d.sz as _)
        .set_lkey(*lkey)
        .set_rkey(point.mr.get_rkey())
        .set_send_flags(ib_send_flags::IB_SEND_SIGNALED)
        .set_opcode(ib_wr_opcode::IB_WR_RDMA_READ)
        .set_ah(point);

    let mut payload = unsafe { Pin::new_unchecked(&mut payload) };
    os_network::rdma::payload::Payload::<ib_dc_wr>::finalize(payload.as_mut());

    // now sending the RDMA request
    dc_qp.post(&payload.as_ref())?;

    // wait for the request to complete
    let mut timeout_dc = TimeoutWRef::new(dc_qp, 10 * TIMEOUT_USEC);
    match block_on(&mut timeout_dc) {
        Ok(_) => Ok(descriptor_buf),
        Err(e) => {
            if e.is_elapsed() {
                // The fallback path? DC cannot distinguish from failures
                unimplemented!();
            }
            Err(e.into_inner().unwrap())
        }
    }
}