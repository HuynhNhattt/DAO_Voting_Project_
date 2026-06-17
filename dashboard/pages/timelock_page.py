"""
dashboard/pages/timelock_page.py
══════════════════════════════════════════════════════════════
TRANG TIMELOCK — Quản lý quyết định đang chờ thực thi

Hiển thị:
  - Các campaign đang ở trạng thái QUEUED / EXECUTABLE
  - Countdown đếm ngược thời gian chờ
  - Nút "Thực thi quyết định" khi delay đã hết

Thêm vào app.py:
    from pages.timelock_page import render_timelock_page
    with tab_timelock:
        render_timelock_page(contracts, w3, wallet, private_key)
══════════════════════════════════════════════════════════════
"""

import streamlit as st
from datetime import datetime, timedelta
from web3 import Web3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from web3_helpers import get_all_campaigns, build_tx
from auth_service  import sign_and_send


def render_timelock_page(contracts: dict, w3, wallet: str = None, private_key: str = None):
    """Trang quản lý Timelock — hiển thị QUEUED campaigns."""

    st.header("⏳ Timelock — Quyết định đang chờ thực thi")
    st.caption(
        "Sau khi campaign PASS, quyết định được queue lên Timelock với delay "
        "2/7/14 ngày. Cổ đông có thời gian phát hiện bất thường trước khi có hiệu lực."
    )

    gov          = contracts.get("gov")
    if not gov:
        st.error("Chưa kết nối GovernanceContract"); return

    # ── Giải thích flow ──────────────────────────────────────
    with st.expander("📖 Tại sao cần Timelock?", expanded=False):
        st.markdown("""
        **Vấn đề không có Timelock:**
        - Campaign PASS → EXECUTED ngay lập tức
        - Nếu quyết định sai (bị hack, vote gian lận) → không kịp phản ứng

        **Giải pháp với Timelock:**
        - Campaign PASS → **QUEUED** (chờ delay)
        - Trong thời gian chờ, cổ đông có thể:
          - Kiểm tra lại quyết định
          - Phát hiện bất thường và báo admin
          - Chuẩn bị cho việc quyết định có hiệu lực
        - Sau delay → **EXECUTABLE** → bất kỳ ai gọi `executeDecision()`

        | Loại | Delay | Lý do |
        |------|-------|-------|
        | ROUTINE | 2 ngày | Quyết định thường lệ, ít rủi ro |
        | MAJOR | 7 ngày | Quan trọng, cần thẩm định kỹ |
        | M&A | 14 ngày | Sáp nhập, tác động lớn |
        """)

    # ── Lấy tất cả campaigns ─────────────────────────────────
    campaigns = get_all_campaigns(gov)

    # Lọc các campaign liên quan đến Timelock
    queued     = [c for c in campaigns if c["status"] == "QUEUED"]
    executable = [c for c in campaigns if c["status"] == "EXECUTABLE"]
    executed   = [c for c in campaigns if c["status"] == "EXECUTED"]

    # ── Metrics ──────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("⏳ Đang chờ delay",   len(queued))
    with col2: st.metric("✅ Sẵn sàng thực thi", len(executable))
    with col3: st.metric("🎯 Đã thực thi",        len(executed))

    st.divider()

    # ── Campaigns đang QUEUED (đang đếm ngược) ───────────────
    if queued or executable:
        st.subheader("📋 Danh sách chờ thực thi")

        for camp in (executable + queued):  # Executable hiển thị trước
            _render_timelock_card(
                camp, gov, w3, wallet, private_key,
                is_executable=(camp["status"] == "EXECUTABLE")
            )
    else:
        st.info(
            "Không có quyết định nào đang chờ Timelock.\n\n"
            "Các campaign PASS sẽ xuất hiện ở đây sau khi gọi `finalizeCampaign()`."
        )

    # ── Lịch sử đã thực thi ──────────────────────────────────
    if executed:
        st.divider()
        st.subheader("🏁 Lịch sử đã thực thi")
        for camp in executed:
            with st.container():
                st.success(
                    f"✅ **#{camp['id']} {camp['title']}**  \n"
                    f"Loại: {camp['proposalType']} · Cơ chế: {camp['mechanism']}"
                )


def _render_timelock_card(camp: dict, gov, w3, wallet: str, private_key: str, is_executable: bool):
    """Hiển thị card một campaign đang chờ Timelock."""

    # Lấy thông tin Timelock từ contract
    try:
        tl_info_raw = gov.functions.getTimelockInfo(camp["id"]).call()
        # Contract returns: (bool queued, uint256 eta, uint256 delayDays, bool isReady, bytes32 operationId)
        tl_info = {
            "queued":      tl_info_raw[0],
            "eta":         tl_info_raw[1],
            "delayDays":   tl_info_raw[2],
            "isReady":     tl_info_raw[3],
            "operationId": "0x" + tl_info_raw[4].hex() if tl_info_raw[4] else "N/A",
            "delay":       tl_info_raw[2] * 86400,  # delayDays → seconds
        }
    except Exception:
        tl_info = {"queued": False, "eta": 0, "delayDays": 0, "isReady": False, "operationId": "N/A"}

    eta_dt     = datetime.fromtimestamp(tl_info["eta"]) if tl_info["eta"] > 0 else None
    now        = datetime.now()
    time_left  = (eta_dt - now) if eta_dt and eta_dt > now else timedelta(0)

    # ── Card UI ──────────────────────────────────────────────
    border_color = "#28a745" if is_executable else "#ffc107"
    with st.container():
        st.markdown(
            f"""<div style="border-left: 4px solid {border_color};
                padding: 12px 16px; margin: 8px 0;
                background: rgba(0,0,0,0.03); border-radius: 4px;">
            </div>""",
            unsafe_allow_html=True
        )

        col_info, col_action = st.columns([3, 1])

        with col_info:
            status_badge = "🟢 SẴN SÀNG THỰC THI" if is_executable else "🟡 ĐANG CHỜ DELAY"
            st.write(f"**#{camp['id']} {camp['title']}** — {status_badge}")
            st.caption(f"Loại: `{camp['proposalType']}` · Cơ chế: `{camp['mechanism']}`")

            if tl_info["eta"] > 0:
                st.write(f"⏰ **Thời hạn:** {eta_dt.strftime('%H:%M:%S %d/%m/%Y')}")
                st.write(f"⏳ **Delay áp dụng:** {tl_info['delayDays']} ngày")

            if not is_executable and time_left.total_seconds() > 0:
                days    = time_left.days
                hours   = time_left.seconds // 3600
                minutes = (time_left.seconds % 3600) // 60
                st.write(f"🕐 **Còn lại:** {days} ngày {hours} giờ {minutes} phút")

                # Progress bar
                total_delay_secs = tl_info["delay"] if tl_info["delay"] > 0 else 1
                elapsed_secs     = total_delay_secs - time_left.total_seconds()
                progress         = min(max(elapsed_secs / total_delay_secs, 0), 1)
                st.progress(progress, text=f"Tiến trình delay: {progress*100:.1f}%")

            # Operation ID
            with st.expander("🔍 Chi tiết Timelock"):
                st.write(f"Operation ID: `{tl_info['operationId'][:30]}...`")
                st.write(f"ETA (Unix): `{tl_info['eta']}`")
                st.caption(
                    "Operation ID dùng để tra cứu trên Timelock contract.\n"
                    "Gọi `timelock.isOperationReady(operationId)` để kiểm tra."
                )

        with col_action:
            if is_executable:
                # Nút Execute — chỉ hiển thị khi delay đã hết
                if wallet and private_key:
                    if st.button(
                        "🚀 Thực thi",
                        key=f"exec_{camp['id']}",
                        type="primary",
                        help="Gọi executeDecision() — quyết định có hiệu lực"
                    ):
                        _execute_decision(gov, w3, camp["id"], wallet, private_key)
                else:
                    st.warning("Đăng nhập để thực thi")
            else:
                st.button(
                    "⏳ Chờ delay",
                    key=f"wait_{camp['id']}",
                    disabled=True,
                    help=f"Còn {time_left.days} ngày"
                )

        st.divider()


def _execute_decision(gov, w3, campaign_id: int, wallet: str, private_key: str):
    """Gọi executeDecision() on-chain."""
    with st.spinner("Đang thực thi quyết định..."):
        try:
            fn = gov.functions.executeDecision(campaign_id)
            result = sign_and_send(w3, fn, wallet, private_key)

            if result.get("success"):
                st.success(
                    f"✅ Quyết định campaign #{campaign_id} đã có hiệu lực!\n\n"
                    f"Tx: `{result['txHash'][:20]}...`\n"
                    f"Gas: {result.get('gasUsed', 'N/A')}"
                )
                st.balloons()
            else:
                st.error(f"❌ Thất bại: {result.get('error', 'Unknown error')}")
        except Exception as e:
            st.error(f"❌ Lỗi: {str(e)}")


# ── Hàm test nhanh cho demo (fast-forward Ganache) ────────────
def render_timelock_demo_controls(contracts: dict, w3, wallet: str, private_key: str):
    """
    Controls để test Timelock nhanh trên Ganache.
    Chỉ dùng khi development — không dùng trên testnet thật.
    """
    st.subheader("🧪 Demo Controls (Ganache only)")
    st.warning("Chỉ dùng trên Ganache local — không dùng trên testnet thật!")

    gov = contracts.get("gov")
    if not gov:
        return

    campaigns = get_all_campaigns(gov)
    queued    = [c for c in campaigns if c["status"] == "QUEUED"]

    if not queued:
        st.info("Không có campaign nào đang QUEUED.")
        return

    selected_id = st.selectbox(
        "Chọn campaign để fast-forward:",
        [c["id"] for c in queued],
        format_func=lambda x: next(
            f"#{c['id']} {c['title']}" for c in queued if c["id"] == x
        )
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("⏩ Fast-forward time (Ganache)", key="ff_time"):
            try:
                # Tua 15 ngày — đủ để vượt delay dài nhất (14 ngày M&A)
                w3.provider.make_request("evm_increaseTime", [15 * 24 * 3600])
                w3.provider.make_request("evm_mine", [])
                st.success("✅ Đã tua 15 ngày — delay Timelock đã hết!")
            except Exception as e:
                st.error(f"❌ {e}")

    with col2:
        if st.button("🔄 Cập nhật EXECUTABLE", key="check_ready"):
            if wallet and private_key:
                try:
                    fn     = gov.functions.checkTimelockReady(selected_id)
                    result = sign_and_send(w3, fn, wallet, private_key)
                    if result.get("success"):
                        st.success(f"✅ Campaign #{selected_id} giờ là EXECUTABLE!")
                    else:
                        st.error(result.get("error"))
                except Exception as e:
                    st.error(str(e))
            else:
                st.warning("Cần đăng nhập")
