"""
dashboard/pages/amoy_network_widget.py
══════════════════════════════════════════════════════════════
Widget chuyển đổi mạng Ganache ↔ Polygon Amoy trong Dashboard.

Thêm vào app.py:
    from pages.amoy_network_widget import render_network_selector, get_connection

    # Trong sidebar của app.py:
    w3, contracts, net_cfg = get_connection()
══════════════════════════════════════════════════════════════
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from web3_helpers_amoy import (
    connect_web3_auto, load_addresses_auto, get_network_config,
    get_explorer_url, switch_network, check_matic_balance
)
from web3_helpers import get_contract, get_all_contracts


def render_network_selector():
    """
    Hiển thị selector chọn mạng trong sidebar.
    Trả về tên mạng đang chọn.
    """
    st.sidebar.markdown("---")
    st.sidebar.subheader("🌐 Mạng blockchain")

    network_options = {
        "🏠 Ganache (Local Dev)": "ganache",
        "🔷 Polygon Amoy (Testnet)": "amoy",
    }

    selected_label = st.sidebar.radio(
        "Chọn mạng:",
        list(network_options.keys()),
        index=0,
        help=(
            "Ganache: chạy local, không cần internet\n"
            "Amoy: testnet thật, cần MATIC test và internet"
        )
    )

    selected_network = network_options[selected_label]
    switch_network(selected_network)

    cfg = get_network_config()

    # Hiển thị thông tin mạng
    if selected_network == "amoy":
        st.sidebar.success(
            f"**{cfg['name']}**\n\n"
            f"ChainID: {cfg['chain_id']}\n\n"
            f"[Polygonscan ↗]({cfg['explorer']})"
        )
        st.sidebar.caption(
            "Lấy MATIC test tại:\n"
            "[faucet.polygon.technology](https://faucet.polygon.technology)"
        )
    else:
        st.sidebar.info(
            f"**{cfg['name']}**\n\n"
            f"ChainID: {cfg['chain_id']}\n\n"
            "Không cần internet"
        )

    return selected_network


def get_connection():
    """
    Tạo kết nối Web3 và load contracts dựa trên mạng đang chọn.

    Returns:
        (w3, contracts, net_cfg)
        hoặc (None, None, cfg) nếu kết nối thất bại
    """
    cfg = get_network_config()
    try:
        w3, cfg = connect_web3_auto()
        addrs   = load_addresses_auto()

        from web3 import Web3
        contracts = {
            "hst":      get_contract(w3, "HSTToken",            addrs["hstToken"]),
            "registry": get_contract(w3, "ShareholderRegistry", addrs["registry"]),
            "gov":      get_contract(w3, "GovernanceContract",  addrs["governance"]),
            "cert":     None,
        }
        if addrs.get("votingCertificate"):
            try:
                contracts["cert"] = get_contract(
                    w3, "VotingCertificate", addrs["votingCertificate"]
                )
            except Exception:
                pass

        return w3, contracts, cfg, addrs

    except Exception as e:
        st.error(f"❌ Không thể kết nối: {e}")
        return None, None, cfg, {}


def render_wallet_info(w3, wallet_address: str):
    """
    Hiển thị thông tin ví trong sidebar khi dùng Amoy.
    Bao gồm MATIC balance và link Polygonscan.
    """
    cfg = get_network_config()

    st.sidebar.markdown("---")
    st.sidebar.subheader("👛 Thông tin ví")

    short = wallet_address[:8] + "..." + wallet_address[-6:]
    st.sidebar.write(f"**Địa chỉ:** `{short}`")

    # MATIC balance (chỉ hiển thị trên Amoy vì Ganache không cần)
    if cfg["is_testnet"] and w3:
        matic_info = check_matic_balance(w3, wallet_address)
        if matic_info["sufficient"]:
            st.sidebar.success(matic_info["hint"])
        else:
            st.sidebar.warning(matic_info["hint"])

    # Link explorer
    explorer_url = get_explorer_url(wallet_address)
    if explorer_url:
        st.sidebar.markdown(f"[🔗 Xem trên Polygonscan]({explorer_url})")
