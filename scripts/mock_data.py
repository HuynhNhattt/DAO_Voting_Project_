import pandas as pd
import random
from datetime import datetime, timedelta

class MockDataGenerator:
    def __init__(self):
        # 1. PHÂN BỔ TOKEN THEO KỊCH BẢN (Mục 4.2.1)
        # Bao gồm 5 ví cổ đông chiến lược và 2 ví người lạ để test bảo mật
        self.addresses = [
            "0xAdmin_Chutich_45", 
            "0xFund_Viquy_25", 
            "0xSmall_Retail_15", 
            "0xSmall_Retail_10", 
            "0xSmall_Retail_05",
            "0xStranger_Test_00_A", 
            "0xStranger_Test_00_B"
        ]
        
        self.names = [
            "Ví Chủ tịch (45%)", 
            "Ví Quỹ phát triển (25%)", 
            "Cổ đông nhỏ lẻ A (15%)", 
            "Cổ đông nhỏ lẻ B (10%)", 
            "Cổ đông nhỏ lẻ C (5%)",
            "Người lạ Test 01 (0%)",
            "Người lạ Test 02 (0%)"
        ]
        
        # Tỷ lệ khớp 100% kịch bản: 450k, 250k, 150k, 100k, 50k và hai ví 0 token
        self.token_balances = [450000, 250000, 150000, 100000, 50000, 0, 0]

    def generate_shareholders_df(self):
        """Tạo bảng dữ liệu cổ đông để minh họa phân bổ token"""
        data = {
            "Wallet Address": self.addresses,
            "Shareholder Name": self.names,
            "Token Balance": self.token_balances,
            "Voting Weight (%)": [(b / sum(self.token_balances)) * 100 for b in self.token_balances]
        }
        return pd.DataFrame(data)

    def generate_proposals(self):
        """Khởi tạo 3 loại đề xuất đa dạng (Mục 4.2.2)"""
        proposals = [
            {
                "Proposal ID": 101,
                "Type": "Chiến lược (M&A)",
                "Title": "Sáp nhập với Công ty Alpha",
                "Description": "Mở rộng quy mô thông qua sáp nhập hạ tầng.",
                "Status": "Active",
                "Quorum Required": 500000 
            },
            {
                "Proposal ID": 102,
                "Type": "Tài chính",
                "Title": "Chia cổ tức đợt 1/2026",
                "Description": "Trích lợi nhuận chia cổ tức bằng Token.",
                "Status": "Passed",
                "Quorum Required": 300000
            },
            {
                "Proposal ID": 103,
                "Type": "Nhân sự",
                "Title": "Bầu Giám đốc điều hành",
                "Description": "Bầu bổ sung thành viên HĐQT mới.",
                "Status": "Active",
                "Quorum Required": 400000
            }
        ]
        return pd.DataFrame(proposals)

    def generate_votes(self, proposal_id):
        """Giả lập bỏ phiếu có kiểm tra điều kiện sở hữu Token"""
        votes = []
        print(f"\n--- [LOG] Bắt đầu quá trình kiểm tra điều kiện biểu quyết cho Proposal {proposal_id} ---")
        
        for i in range(len(self.addresses)):
            # KIỂM TRA LOGIC: Chỉ ví có Token > 0 mới được quyền biểu quyết
            if self.token_balances[i] > 0:
                # Giả lập: Chủ tịch và Quỹ (i < 2) luôn tham gia, nhỏ lẻ thì ngẫu nhiên
                if i < 2 or random.random() > 0.3:
                    votes.append({
                        "Proposal ID": proposal_id,
                        "Voter Name": self.names[i],
                        "Choice": "Support" if i != 1 else "Against", # Quỹ thường đối trọng với Chủ tịch
                        "Weight": self.token_balances[i],
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
            else:
                # Ghi nhận các trường hợp bị hệ thống từ chối (Test case)
                print(f"X chặn: Ví {self.addresses[i]} bị từ chối do không có cổ phần (0 Token).")
        
        return pd.DataFrame(votes)

# --- THỰC THI KIỂM THỬ ---
if __name__ == "__main__":
    gen = MockDataGenerator()
    
    print("--- 4.2.1 PHÂN BỔ TOKEN KHỞI TẠO (Bao gồm kịch bản kiểm thử biên) ---")
    print(gen.generate_shareholders_df())
    
    print("\n--- 4.2.2 DANH SÁCH ĐỀ XUẤT MẪU ĐA DẠNG ---")
    print(gen.generate_proposals())
    
    print("\n--- 4.2.3 KẾT QUẢ MÔ PHỎNG BIỂU QUYẾT ---")
    df_votes = gen.generate_votes(101)
    print(df_votes)