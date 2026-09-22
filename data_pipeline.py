# data_pipeline.py
import pandas as pd

def load_and_clean_data(file_path: str) -> pd.DataFrame:
    """교통량 데이터를 로드하고 결측치를 처리합니다."""
    df = pd.read_csv(file_path)
    df = df.dropna()
    print(f"[INFO] 데이터 로드 완료: 총 {len(df)}건")
    return df

if __name__ == "__main__":
    print("데이터 파이프라인 모듈 테스트 시작")