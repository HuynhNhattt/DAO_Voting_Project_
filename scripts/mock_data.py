import pandas as pd
import random
from datetime import datetime, timedelta

class MockDataGenerator:
    def __init__(self):
        # 1. PHÂN BỔ TOKEN THEO KỊCH BẢN (Tổng 1,000,000 Token)
        self.addresses = [
            "0xAdmin_Chutich_45", 
            "0xFund_Viquy_25", 
            "0xSmall_Retail_15", 
            "0xSmall_Retail_10", 
            "0xSmall_Retail_05"
        ]
        
        self.names = [
            "Ví Chủ tịch (Thành viên sáng lập)", 
            "Ví Quỹ phát triển hệ thống", 
            "Cổ đông nhỏ lẻ A", 
            "Cổ đông nhỏ lẻ B", 
            "Cổ đông nhỏ lẻ C"
        ]
        
        # Tỷ lệ: 45%, 25%, 15%, 10%, 5%
        self.token_balances = [450000, 250000, 150000, 100000, 50000]

    def generate_shareholders_df(self):
        data = {
            "Wallet Address": self.addresses,
            "Shareholder Name": self.names,
            "Token Balance": self.token_balances,
            "Voting Weight (%)": [(b / sum(self.token_balances)) * 100 for b in self.token_balances]
        }
        return pd.DataFrame(data)

    def generate_proposals(self):
        # 2. KHỞI TẠO ĐỀ XUẤT ĐA DẠNG (Mục 4.2.2)
        proposals = [
            {
                "Proposal ID": 101,
                "Type": "Sáp nhập & Mua lại (M&A)",
                "Title": "Sáp nhập với Công ty Công nghệ Alpha",
                "Description": "Mở rộng thị phần bằng cách sáp nhập toàn bộ nhân sự và hạ tầng của Alpha.",
                "Status": "Active",
                "Quorum Required": 500000 # Đề xuất quan trọng cần 50% tham gia
            },
            {
                "Proposal ID": 102,
                "Type": "Tài chính",
                "Title": "Chi trả cổ tức đợt 1 năm 2026",
                "Description": "Trích 30% lợi nhuận sau thuế để chia cổ tức bằng Token cho cổ đông.",
                "Status": "Passed",
                "Quorum Required": 300000
            },
            {
                "Proposal ID": 103,
                "Type": "Nhân sự thượng tầng",
                "Title": "Bầu bổ sung thành viên Hội đồng quản trị",
                "Description": "Bầu chọn ông Nguyễn Văn A vào vị trí Giám đốc điều hành.",
                "Status": "Active",
                "Quorum Required": 400000
            }
        ]
        return pd.DataFrame(proposals)

    def generate_votes(self, proposal_id):
        votes = []
        for i in range(len(self.addresses)):
            # Giả lập: Chủ tịch và Quỹ luôn đi bầu cho các đề xuất lớn
            is_major = i < 2 
            if is_major or random.random() > 0.4:
                choice = "Support" if i != 1 else "Against" # Giả lập Quỹ và Chủ tịch có thể đối đầu
                votes.append({
                    "Proposal ID": proposal_id,
                    "Voter Name": self.names[i],
                    "Choice": choice,
                    "Weight": self.token_balances[i],
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
        return pd.DataFrame(votes)

if __name__ == "__main__":
    gen = MockDataGenerator()
    print("--- 4.2.1 PHÂN BỔ TOKEN KHỞI TẠO ---")
    print(gen.generate_shareholders_df())
    print("\n--- 4.2.2 CÁC ĐỀ XUẤT MẪU ĐA DẠNG ---")
    print(gen.generate_proposals())
    print("\n--- CHI TIẾT BIỂU QUYẾT MẪU (SÁP NHẬP) ---")
    print(gen.generate_votes(101))